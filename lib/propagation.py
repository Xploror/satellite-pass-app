import math
from datetime import datetime, timedelta

import numpy as np
from sgp4.api import SGP4_ERRORS, Satrec, jday

WGS84_A_KM = 6378.137
WGS84_F = 1 / 298.257223563
WGS84_B_KM = WGS84_A_KM * (1 - WGS84_F)
WGS84_E2 = WGS84_F * (2 - WGS84_F)

REV_SCAN_STEP_S = 60.0  # coarse step for counting nodes between TLE epoch and window start


def make_satrec(sat) -> Satrec:
    """
    Builds the SGP4 satellite record from the satellite's TLE.
    """

    if sat.tle is None:
        raise ValueError(f"Satellite {sat.norad_id} has no TLE")
    return Satrec.twoline2rv(sat.tle[0], sat.tle[1])


def offsets_to_jd(start: datetime, offsets_s) -> tuple:
    """
    Converts second offsets from `start` into split Julian dates (whole, fraction).
    """

    jd0, fr0 = jday(
        start.year,
        start.month,
        start.day,
        start.hour,
        start.minute,
        start.second + start.microsecond * 1e-6,
    )
    fr = fr0 + np.asarray(offsets_s, dtype=float) / 86400.0
    whole = np.floor(fr)
    return jd0 + whole, fr - whole


def sample_offsets(duration_s: float, step_s: float) -> np.ndarray:
    """
    Sample times (s from window start) every step_s, always including the window end.
    """

    offsets = np.arange(int(math.floor(duration_s / step_s)) + 1) * step_s
    if duration_s - offsets[-1] > 1e-9:
        offsets = np.append(offsets, duration_s)
    return offsets


def time_grid(start: datetime, duration_s: float, step_s: float) -> tuple:
    """
    Returns (datetimes, jd, fr) for the sampled propagation window.
    """

    offsets = sample_offsets(duration_s, step_s)
    jd, fr = offsets_to_jd(start, offsets)
    return [start + timedelta(seconds=float(o)) for o in offsets], jd, fr


def propagate(satrec: Satrec, jd, fr) -> tuple:
    """
    Vectorised SGP4 propagation; returns TEME position (km) and velocity (km/s), shape (N, 3).
    """

    errors, r, v = satrec.sgp4_array(np.atleast_1d(jd), np.atleast_1d(fr))
    if np.any(errors):
        code = int(errors[errors != 0][0])
        raise RuntimeError(f"SGP4 failed for {satrec.satnum}: {SGP4_ERRORS[code]}")
    return r, v


def gmst_rad(jd, fr) -> np.ndarray:
    """
    Greenwich mean sidereal time (IAU-82), vectorised copy of sgp4.propagation.gstime.
    """

    tut1 = (np.asarray(jd) - 2451545.0 + np.asarray(fr)) / 36525.0
    seconds = (
        -6.2e-6 * tut1**3
        + 0.093104 * tut1**2
        + (876600.0 * 3600 + 8640184.812866) * tut1
        + 67310.54841
    )
    return np.mod(np.radians(seconds / 240.0), 2 * np.pi)


def teme_to_ecef(r_teme, jd, fr) -> np.ndarray:
    """
    Rotates TEME positions into ECEF about z by GMST (polar motion ignored, a few tens of m).
    """

    theta = gmst_rad(jd, fr)
    r = np.atleast_2d(r_teme)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    return np.column_stack(
        (cos_t * r[:, 0] + sin_t * r[:, 1], -sin_t * r[:, 0] + cos_t * r[:, 1], r[:, 2])
    )


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float = 0.0) -> np.ndarray:
    """
    WGS84 geodetic coordinates to ECEF position in km.
    """

    lat, lon, h = math.radians(lat_deg), math.radians(lon_deg), alt_m / 1000.0
    n = WGS84_A_KM / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    return np.array(
        [
            (n + h) * math.cos(lat) * math.cos(lon),
            (n + h) * math.cos(lat) * math.sin(lon),
            (n * (1 - WGS84_E2) + h) * math.sin(lat),
        ]
    )


def ecef_to_aer(r_sat_ecef, r_stn_ecef, lat_deg: float, lon_deg: float) -> tuple:
    """
    Azimuth (deg from north), elevation (deg) and range (km) of satellites seen from a station.
    """

    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    d = np.atleast_2d(r_sat_ecef) - r_stn_ecef
    east = -math.sin(lon) * d[:, 0] + math.cos(lon) * d[:, 1]
    north = (
        -math.sin(lat) * math.cos(lon) * d[:, 0]
        - math.sin(lat) * math.sin(lon) * d[:, 1]
        + math.cos(lat) * d[:, 2]
    )
    up = (
        math.cos(lat) * math.cos(lon) * d[:, 0]
        + math.cos(lat) * math.sin(lon) * d[:, 1]
        + math.sin(lat) * d[:, 2]
    )
    rng = np.sqrt(east**2 + north**2 + up**2)
    az = np.mod(np.degrees(np.arctan2(east, north)), 360.0)
    el = np.degrees(np.arcsin(np.clip(up / rng, -1.0, 1.0)))
    return az, el, rng


def ascending_nodes(offsets_s, z_teme) -> np.ndarray:
    """
    Times (same units as offsets_s) where TEME z crosses from negative to non-negative.
    """

    t, z = np.asarray(offsets_s, dtype=float), np.asarray(z_teme, dtype=float)
    idx = np.nonzero((z[:-1] < 0) & (z[1:] >= 0))[0]
    return t[idx] + (0 - z[idx]) * (t[idx + 1] - t[idx]) / (z[idx + 1] - z[idx])


def rev_at_start(satrec: Satrec, start: datetime) -> int:
    """
    Revolution number at `start`, counting ascending nodes from the TLE epoch rev number.

    NORAD increments the rev number at each ascending node. The TLE field is only 5 digits
    and wraps at 100000 (e.g. ISS); the raw value is used without wrap correction.
    """

    jd0, fr0 = offsets_to_jd(start, [0.0])
    delta_s = ((jd0[0] - satrec.jdsatepoch) + (fr0[0] - satrec.jdsatepochF)) * 86400.0
    if abs(delta_s) < 1e-3:
        return int(satrec.revnum)

    steps = int(math.ceil(abs(delta_s) / REV_SCAN_STEP_S))
    offsets = np.linspace(0.0, delta_s, steps + 1)  # epoch -> start (backwards if negative)
    fr = satrec.jdsatepochF + offsets / 86400.0
    whole = np.floor(fr)
    r, _ = propagate(satrec, satrec.jdsatepoch + whole, fr - whole)
    z = r[:, 2]

    if delta_s > 0:
        return int(satrec.revnum) + len(ascending_nodes(offsets, z))
    return int(satrec.revnum) - len(ascending_nodes(offsets[::-1], z[::-1]))


def rev_numbers(satrec: Satrec, start: datetime, offsets_s, z_teme) -> np.ndarray:
    """
    Revolution number at each sample time, given TEME z sampled at `offsets_s` from `start`.
    """

    nodes = ascending_nodes(offsets_s, z_teme)
    return rev_at_start(satrec, start) + np.searchsorted(nodes, offsets_s, side="right")

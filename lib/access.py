import math
from datetime import timedelta

import numpy as np

from lib.propagation import (
    WGS84_A_KM,
    WGS84_B_KM,
    ascending_nodes,
    ecef_to_aer,
    geodetic_to_ecef,
    make_satrec,
    offsets_to_jd,
    propagate,
    rev_at_start,
    sample_offsets,
    teme_to_ecef,
)
from lib.systems import AccessInterval

GOLDEN = (math.sqrt(5) - 1) / 2


def refraction_deg(el_deg) -> np.ndarray:
    """
    Standard-atmosphere refraction (Saemundsson) for a geometric elevation, in degrees.

    Saemundsson's form takes the true (geometric) altitude, the inverse of Bennett's formula.
    Refraction is taken as zero below -1 deg where the formula is no longer meaningful.
    """

    el = np.asarray(el_deg, dtype=float)
    arcmin = 1.02 / np.tan(np.radians(el + 10.3 / (el + 5.11)))
    return np.where(el > -1.0, arcmin / 60.0, 0.0)


def aer_mask(az, el, rng, aer_cfg) -> np.ndarray:
    """
    True where elevation, azimuth (any allowed sector) and range are all within bounds.
    """

    el_min, el_max = aer_cfg.elevation_deg
    mask = np.asarray(el) <= el_max
    if el_min is not None:
        mask &= np.asarray(el) >= el_min

    in_sector = np.zeros_like(mask)
    for lo, hi in aer_cfg.azimuth_deg:
        if lo <= hi:
            in_sector |= (az >= lo) & (az <= hi)
        else:  # sector wraps through north, e.g. [300, 60]
            in_sector |= (az >= lo) | (az <= hi)
    mask &= in_sector

    rng_min, rng_max = aer_cfg.range_km
    mask &= np.asarray(rng) >= rng_min
    if rng_max is not None:
        mask &= np.asarray(rng) <= rng_max
    return mask


def los_mask(r_sat_ecef, r_stn_ecef, grazing_km: float = 0.0) -> np.ndarray:
    """
    Geometric line of sight: True where the station-satellite segment clears the WGS84
    ellipsoid inflated by grazing_km. Scaling the axes maps that ellipsoid to the unit sphere.
    """

    scale = np.array(
        [
            1 / (WGS84_A_KM + grazing_km),
            1 / (WGS84_A_KM + grazing_km),
            1 / (WGS84_B_KM + grazing_km),
        ]
    )
    s = np.asarray(r_stn_ecef) * scale
    d = np.atleast_2d(r_sat_ecef) * scale - s
    t = np.clip(-(d @ s) / np.einsum("ij,ij->i", d, d), 0.0, 1.0)
    closest = s + t[:, None] * d
    return (t == 0.0) | (np.linalg.norm(closest, axis=1) >= 1.0)


def visibility_mask(az, el, rng, r_sat_ecef, r_stn_ecef, vis_cfg) -> np.ndarray:
    """
    Combines the AER and LOS criteria as configured (aer, los or both).
    """

    if vis_cfg.criterion == "aer":
        return aer_mask(az, el, rng, vis_cfg.aer)
    los = los_mask(r_sat_ecef, r_stn_ecef, vis_cfg.los.grazing_altitude_km)
    if vis_cfg.criterion == "los":
        return los
    return aer_mask(az, el, rng, vis_cfg.aer) & los


def find_intervals(mask) -> list:
    """
    (first, last) sample indices of each run of True values in the mask.
    """

    padded = np.concatenate(([False], np.asarray(mask, dtype=bool), [False]))
    edges = np.flatnonzero(np.diff(padded.astype(np.int8)))
    return [(int(start), int(end) - 1) for start, end in zip(edges[::2], edges[1::2])]


def refine_edge(t_a: float, t_b: float, predicate, tol: float) -> float:
    """
    Bisects the time where predicate flips between t_a and t_b (predicate(t_a) != predicate(t_b)).
    """

    state_a = predicate(t_a)
    while t_b - t_a > tol:
        t_mid = (t_a + t_b) / 2
        if predicate(t_mid) == state_a:
            t_a = t_mid
        else:
            t_b = t_mid
    return (t_a + t_b) / 2


class _Geometry:
    """
    Evaluates satellite geometry relative to the lab at arbitrary offsets from the window start.
    """

    def __init__(self, sat, lab, report_cfg):
        self.satrec = make_satrec(sat)
        self.start = report_cfg.window.start_utc
        self.lab = lab
        self.vis = report_cfg.visibility
        self.r_stn = geodetic_to_ecef(lab.lat, lab.lng, lab.alt_m)

    def at(self, offsets) -> tuple:
        """
        Returns (az, el, range, r_ecef, z_teme); el is apparent when refraction is enabled.
        """

        jd, fr = offsets_to_jd(self.start, np.atleast_1d(offsets))
        r_teme, _ = propagate(self.satrec, jd, fr)
        r_ecef = teme_to_ecef(r_teme, jd, fr)
        az, el, rng = ecef_to_aer(r_ecef, self.r_stn, self.lab.lat, self.lab.lng)
        if self.vis.apply_refraction:
            el = el + refraction_deg(el)
        return az, el, rng, r_ecef, r_teme[:, 2]

    def visible(self, offset: float) -> bool:
        az, el, rng, r_ecef, _ = self.at(offset)
        return bool(visibility_mask(az, el, rng, r_ecef, self.r_stn, self.vis)[0])

    def elevation(self, offset: float) -> float:
        return float(self.at(offset)[1][0])


def _max_elevation(geo: _Geometry, lo: float, hi: float, tol: float) -> float:
    """
    Golden-section search for the time of maximum elevation within [lo, hi].
    """

    a, b = lo, hi
    c, d = b - GOLDEN * (b - a), a + GOLDEN * (b - a)
    el_c, el_d = geo.elevation(c), geo.elevation(d)
    while b - a > tol:
        if el_c > el_d:
            b, d, el_d = d, c, el_c
            c = b - GOLDEN * (b - a)
            el_c = geo.elevation(c)
        else:
            a, c, el_c = c, d, el_d
            d = a + GOLDEN * (b - a)
            el_d = geo.elevation(d)
    return (a + b) / 2


def compute_access(sat, lab, report_cfg) -> list:
    """
    Propagates one satellite over the report window and returns its access intervals.

    Passes shorter than Window.time_step_s can fall between samples and be missed.
    """

    window = report_cfg.window
    step, tol = window.time_step_s, window.refine_tolerance_s
    offsets = sample_offsets(window.duration_hours * 3600.0, step)

    geo = _Geometry(sat, lab, report_cfg)
    az, el, rng, r_ecef, z_teme = geo.at(offsets)
    mask = visibility_mask(az, el, rng, r_ecef, geo.r_stn, report_cfg.visibility)

    nodes = ascending_nodes(offsets, z_teme)
    rev0 = rev_at_start(geo.satrec, geo.start)

    intervals = []
    for pass_no, (i0, i1) in enumerate(find_intervals(mask), start=1):
        aos_truncated, los_truncated = i0 == 0, i1 == len(offsets) - 1
        aos, los = float(offsets[i0]), float(offsets[i1])
        if window.refine_edges and not aos_truncated:
            aos = refine_edge(float(offsets[i0 - 1]), aos, geo.visible, tol)
        if window.refine_edges and not los_truncated:
            los = refine_edge(los, float(offsets[i1 + 1]), geo.visible, tol)

        k = i0 + int(np.argmax(el[i0 : i1 + 1]))
        lo, hi = max(aos, float(offsets[k]) - step), min(los, float(offsets[k]) + step)
        tca = _max_elevation(geo, lo, hi, tol) if hi > lo else float(offsets[k])
        if geo.elevation(tca) < float(el[k]):
            tca = float(offsets[k])

        edge_az, edge_el, edge_rng, _, _ = geo.at([aos, tca, los])
        min_range = min(float(np.min(rng[i0 : i1 + 1])), float(np.min(edge_rng)))

        intervals.append(
            AccessInterval(
                norad_id=sat.norad_id,
                sat_name=sat.name,
                pass_no=pass_no,
                aos_utc=geo.start + timedelta(seconds=aos),
                los_utc=geo.start + timedelta(seconds=los),
                duration_s=los - aos,
                rev_aos=int(rev0 + np.searchsorted(nodes, aos, side="right")),
                rev_los=int(rev0 + np.searchsorted(nodes, los, side="right")),
                max_el_deg=float(edge_el[1]),
                tca_utc=geo.start + timedelta(seconds=tca),
                aos_az_deg=float(edge_az[0]),
                los_az_deg=float(edge_az[2]),
                min_range_km=min_range,
                aos_truncated=aos_truncated,
                los_truncated=los_truncated,
            )
        )
    return intervals

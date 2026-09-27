from datetime import timedelta

import numpy as np
import pytest
from sgp4.propagation import gstime

from lib.propagation import (
    WGS84_A_KM,
    WGS84_B_KM,
    ecef_to_aer,
    geodetic_to_ecef,
    gmst_rad,
    make_satrec,
    offsets_to_jd,
    propagate,
    rev_at_start,
    rev_numbers,
    sample_offsets,
)
from lib.providers.tle import tle_epoch


def test_propagate_at_epoch_is_plausible_and_matches_scalar(iss_sat):
    satrec = make_satrec(iss_sat)
    jd, fr = np.array([satrec.jdsatepoch]), np.array([satrec.jdsatepochF])
    r, v = propagate(satrec, jd, fr)

    assert 6650 < np.linalg.norm(r[0]) < 6800  # ~350 km altitude
    assert 7.6 < np.linalg.norm(v[0]) < 7.8
    _, r_scalar, _ = satrec.sgp4(satrec.jdsatepoch, satrec.jdsatepochF)
    assert np.allclose(r[0], r_scalar)


def test_propagate_raises_on_sgp4_error(iss_sat):
    satrec = make_satrec(iss_sat)
    with pytest.raises(RuntimeError):
        propagate(satrec, np.array([satrec.jdsatepoch + 36500.0]), np.array([0.0]))


def test_gmst_matches_sgp4_gstime():
    jd = np.array([2451545.0, 2454730.0, 2461300.0])
    fr = np.array([0.0, 0.51782528, 0.25])
    expected = [gstime(j + f) for j, f in zip(jd, fr)]
    assert np.allclose(gmst_rad(jd, fr), expected, atol=1e-8)


def test_geodetic_to_ecef():
    assert np.allclose(geodetic_to_ecef(0, 0, 0), [WGS84_A_KM, 0, 0])
    assert np.allclose(geodetic_to_ecef(90, 0, 0), [0, 0, WGS84_B_KM])
    assert np.allclose(geodetic_to_ecef(0, 90, 1000), [0, WGS84_A_KM + 1, 0])


def test_satellite_at_zenith():
    stn = geodetic_to_ecef(0, 0, 0)
    az, el, rng = ecef_to_aer(stn + [500.0, 0, 0], stn, 0, 0)
    assert el[0] == pytest.approx(90.0)
    assert rng[0] == pytest.approx(500.0)


@pytest.mark.parametrize(
    "offset, expected_az",
    [([10, 0, 100], 0), ([10, 100, 0], 90), ([10, 0, -100], 180), ([10, -100, 0], 270)],
)
def test_azimuth_quadrants(offset, expected_az):
    stn = geodetic_to_ecef(0, 0, 0)  # up = +x, east = +y, north = +z
    az, el, _ = ecef_to_aer(stn + np.array(offset, dtype=float), stn, 0, 0)
    assert az[0] % 360 == pytest.approx(expected_az)
    assert el[0] > 0


def test_rev_number_equals_revnum_at_epoch(iss_sat, iss_tle):
    satrec = make_satrec(iss_sat)
    assert rev_at_start(satrec, tle_epoch(iss_tle[0])) == 56353


def test_rev_number_before_and_after_epoch(iss_sat, iss_tle):
    satrec = make_satrec(iss_sat)
    epoch = tle_epoch(iss_tle[0])
    # 15.72 revs/day, so a day holds 15 or 16 ascending nodes depending on phase
    assert rev_at_start(satrec, epoch + timedelta(days=1)) - 56353 in (15, 16)
    assert 56353 - rev_at_start(satrec, epoch - timedelta(days=1)) in (15, 16)


def test_rev_increments_once_per_ascending_node(iss_sat, iss_tle):
    satrec = make_satrec(iss_sat)
    start = tle_epoch(iss_tle[0])
    offsets = sample_offsets(86400, 10)
    jd, fr = offsets_to_jd(start, offsets)
    z = propagate(satrec, jd, fr)[0][:, 2]

    revs = rev_numbers(satrec, start, offsets, z)
    steps = np.diff(revs)
    ascending = np.sum((z[:-1] < 0) & (z[1:] >= 0))

    assert revs[0] == 56353
    assert set(np.unique(steps)) <= {0, 1}
    assert steps.sum() == ascending
    assert np.all(z[1:][steps == 1] >= 0)  # rev ticks exactly where z turns non-negative

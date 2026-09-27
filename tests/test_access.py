import math

import numpy as np
import pytest

from lib.access import (
    aer_mask,
    compute_access,
    find_intervals,
    los_mask,
    refine_edge,
    refraction_deg,
)
from lib.propagation import (
    ecef_to_aer,
    geodetic_to_ecef,
    make_satrec,
    offsets_to_jd,
    propagate,
    teme_to_ecef,
)
from lib.report_config import AERCfg, parse_report_config, resolve
from lib.systems import Lab

START = "2008-09-20T12:00:00Z"


def report_cfg(**visibility) -> object:
    raw = {"Window": {"start_utc": START, "duration_hours": 24, "time_step_s": 10}}
    if visibility:
        raw["Visibility"] = visibility
    return parse_report_config(raw)


@pytest.fixture
def lab() -> Lab:
    return Lab([40.0, -75.0], {"min_elev": 10})


@pytest.mark.parametrize(
    "mask, expected",
    [
        ([False, False, False], []),
        ([False, True, True, False], [(1, 2)]),
        ([True, False, True, True, False, True], [(0, 0), (2, 3), (5, 5)]),
        ([True, True, True], [(0, 2)]),
    ],
)
def test_find_intervals(mask, expected):
    assert find_intervals(np.array(mask)) == expected


def test_aer_mask_wrapping_sector_and_range():
    cfg = AERCfg(elevation_deg=(5.0, 90.0), azimuth_deg=((300.0, 60.0),), range_km=(0.0, 2000.0))
    az = np.array([310.0, 10.0, 100.0, 10.0, 10.0])
    el = np.array([20.0, 20.0, 20.0, 2.0, 20.0])
    rng = np.array([500.0, 500.0, 500.0, 500.0, 2500.0])
    assert aer_mask(az, el, rng, cfg).tolist() == [True, True, False, False, False]


def test_aer_mask_multiple_sectors():
    cfg = AERCfg(
        elevation_deg=(None, 90.0), azimuth_deg=((0.0, 90.0), (180.0, 270.0)), range_km=(0, None)
    )
    az = np.array([45.0, 135.0, 225.0, 315.0])
    assert aer_mask(az, np.full(4, 30.0), np.full(4, 1e4), cfg).tolist() == [
        True,
        False,
        True,
        False,
    ]


def test_los_blocked_by_earth_clear_at_zenith():
    stn = geodetic_to_ecef(0, 0, 0)
    sats = np.array([[-7000.0, 0, 0], [7000.0, 0, 0]])  # antipodal, zenith
    assert los_mask(sats, stn).tolist() == [False, True]


def test_los_grazing_margin():
    stn = geodetic_to_ecef(0, 0, 10_000)  # 10 km up: horizon dip ~3.2 deg
    dip = math.radians(-1.0)  # ray grazes ~9 km above the surface
    up, north = np.array([1.0, 0, 0]), np.array([0, 0, 1.0])
    sat = stn + 2000.0 * (math.cos(dip) * north + math.sin(dip) * up)

    assert los_mask(sat, stn, grazing_km=0.0)[0]
    assert not los_mask(sat, stn, grazing_km=20.0)[0]


def test_refraction_is_positive_and_about_half_degree_at_horizon():
    r = refraction_deg(np.array([0.0, 10.0, 90.0, -5.0]))
    assert 0.4 < r[0] < 0.6
    assert r[1] < r[0] and r[2] < 1e-3
    assert r[3] == 0.0


def test_refine_edge_converges():
    edge = refine_edge(3.0, 4.0, lambda t: t >= 3.337, tol=1e-3)
    assert edge == pytest.approx(3.337, abs=1e-3)


def test_compute_access_refined_edges_sit_on_elevation_mask(iss_sat, lab):
    cfg = resolve(report_cfg(), lab)
    intervals = compute_access(iss_sat, lab, cfg)
    assert len(intervals) >= 3

    satrec = make_satrec(iss_sat)
    stn = geodetic_to_ecef(lab.lat, lab.lng, 0)
    start = cfg.window.start_utc
    for iv in intervals:
        assert iv.aos_utc < iv.tca_utc < iv.los_utc
        assert iv.max_el_deg >= 10.0
        assert iv.rev_aos <= iv.rev_los
        for t in (iv.aos_utc, iv.los_utc):
            jd, fr = offsets_to_jd(start, [(t - start).total_seconds()])
            r = teme_to_ecef(propagate(satrec, jd, fr)[0], jd, fr)
            el = ecef_to_aer(r, stn, lab.lat, lab.lng)[1][0]
            assert el == pytest.approx(10.0, abs=0.05)


def test_coarse_and_fine_steps_agree(iss_sat, lab):
    coarse = compute_access(iss_sat, lab, resolve(report_cfg(), lab))
    raw = {"Window": {"start_utc": START, "duration_hours": 24, "time_step_s": 1}}
    fine = compute_access(iss_sat, lab, resolve(parse_report_config(raw), lab))

    assert len(coarse) == len(fine)
    for a, b in zip(coarse, fine):
        assert abs((a.aos_utc - b.aos_utc).total_seconds()) < 0.5
        assert abs((a.los_utc - b.los_utc).total_seconds()) < 0.5
        assert a.max_el_deg == pytest.approx(b.max_el_deg, abs=0.05)


def test_both_criterion_is_subset_of_each(iss_sat, lab):
    def run(criterion):
        return compute_access(iss_sat, lab, resolve(report_cfg(criterion=criterion), lab))

    aer, los, both = run("aer"), run("los"), run("both")
    assert both

    def covered(iv, intervals):
        return any(
            (iv.aos_utc - o.aos_utc).total_seconds() > -1
            and (o.los_utc - iv.los_utc).total_seconds() > -1
            for o in intervals
        )

    assert all(covered(iv, aer) and covered(iv, los) for iv in both)

from datetime import datetime, timezone

import pytest

from lib.report_config import load_report_config, parse_report_config, resolve
from lib.systems import Lab


def test_default_file_loads():
    cfg = load_report_config("config_files/report_default.yaml")
    assert cfg.window.duration_hours == 24
    assert cfg.window.time_step_s == 10
    assert cfg.visibility.criterion == "aer"
    assert cfg.visibility.aer.azimuth_deg == ((0.0, 360.0),)
    assert cfg.tle.sources == ("celestrak", "n2yo")
    assert cfg.output.formats == ("stdout", "csv", "json")
    assert cfg.window.start_utc.tzinfo is not None


def test_missing_file_exits():
    with pytest.raises(SystemExit):
        load_report_config("config_files/does_not_exist.yaml")


def test_null_min_elevation_falls_back_to_lab():
    cfg = resolve(parse_report_config({}), Lab([0, 0], {"min_elev": 12}))
    assert cfg.visibility.aer.elevation_deg == (12.0, 90.0)


def test_explicit_min_elevation_is_kept():
    raw = {"Visibility": {"AER": {"elevation_deg": [3, 80]}}}
    cfg = resolve(parse_report_config(raw), Lab([0, 0], {"min_elev": 12}))
    assert cfg.visibility.aer.elevation_deg == (3.0, 80.0)


def test_iso_start_and_single_azimuth_pair():
    raw = {
        "Window": {"start_utc": "2026-09-26T06:30:00Z"},
        "Visibility": {"AER": {"azimuth_deg": [300, 60]}},
    }
    cfg = parse_report_config(raw)
    assert cfg.window.start_utc == datetime(2026, 9, 26, 6, 30, tzinfo=timezone.utc)
    assert cfg.visibility.aer.azimuth_deg == ((300.0, 60.0),)


@pytest.mark.parametrize(
    "raw",
    [
        {"Visibility": {"criterion": "radar"}},
        {"Window": {"time_step_s": 0}},
        {"Window": {"duration_hours": -1}},
        {"Window": {"start_utc": "tomorrow"}},
        {"Visibility": {"AER": {"azimuth_deg": [[0, 400]]}}},
        {"Visibility": {"AER": {"elevation_deg": [50, 10]}}},
        {"Visibility": {"AER": {"range_km": [500, 100]}}},
        {"TLE": {"sources": ["spacetrack"]}},
        {"TLE": {"sources": ["file"]}},
        {"Output": {"formats": ["xlsx"]}},
    ],
)
def test_invalid_settings_raise(raw):
    with pytest.raises(ValueError):
        parse_report_config(raw)

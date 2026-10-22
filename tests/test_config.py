import pytest

from lib.config import claude_geoloc, load_mission_info
from lib.report_config import OutputCfg, ReportConfig, StationCfg, TLECfg, VisibilityCfg, WindowCfg


@pytest.fixture
def file_paths() -> list:
    return [
        "config_files/" + "conf_test2.yaml",
        "config_files/" + "conf_test1.yaml",
        "config_files/" + "conf_default.yaml",
    ]


@pytest.fixture
def demo_cities() -> dict:
    return {
        "London": [51.507351, -0.127758],
        "Istanbul": [41.008238, 28.978359],
        "Beijing": [39.9042, 116.4074],
    }


def test_load_mission_info(file_paths: list):

    for itr, file_path in enumerate(file_paths):
        sats, lab, out_type = load_mission_info(file_path)

        if itr == 0:
            out_type = out_type[-1]
            assert len(sats) == 8
            assert sats[0].norad_id == 25544
            assert sats[0].color == "Red"
            assert sats[1].norad_id == 63733
            assert sats[1].color == "Green"
            assert sats[2].norad_id == 45198
            assert sats[2].color == "Blue"
            assert sats[3].norad_id == 45098
            assert sats[3].color == "Maroon"
            assert sats[4].norad_id == 42809
            assert sats[4].color == "Yellow"
            assert sats[5].norad_id == 45427
            assert sats[5].color == "Gray"
            assert sats[6].norad_id == 69049
            assert sats[6].color == "Orange"
            assert sats[7].norad_id == 41921
            assert sats[7].color == "Pink"
            assert lab.lat == 37.7749
            assert lab.lng == -122.4194
            assert lab.alt_m == 0
            assert lab.min_elev == 5
            assert isinstance(out_type, ReportConfig)
            assert isinstance(out_type.window, WindowCfg)
            assert isinstance(out_type.tle, TLECfg)
            assert isinstance(out_type.station, StationCfg)
            assert isinstance(out_type.visibility, VisibilityCfg)
            assert isinstance(out_type.output, OutputCfg)
        elif itr == 1:
            out_type = out_type[0]
            assert len(sats) == 8
            assert sats[0].norad_id == 25544
            assert sats[0].color == "Red"
            assert lab.lat == 37.7749
            assert lab.lng == -122.4194
            assert lab.min_elev == 5
            assert out_type == 3
        elif itr == 2:
            out_type = out_type[0]
            claude_loc = claude_geoloc("Blacksburg")
            assert len(sats) == 4
            assert sats[0].norad_id == 25544
            assert sats[0].color == "Red"
            assert abs(claude_loc[0] - lab.lat) < 0.0001
            assert abs(claude_loc[1] - lab.lng) < 0.0001
            assert lab.min_elev == 30
            assert out_type == 3


def test_claude_geoloc(demo_cities: dict):

    for city, loc in demo_cities.items():
        claude_loc = claude_geoloc(city)
        assert abs(claude_loc[0] - loc[0]) < 0.0001
        assert abs(claude_loc[1] - loc[1]) < 0.0001

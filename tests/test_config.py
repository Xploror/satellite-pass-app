import pytest

from lib.config import load_mission_info, opencage_geoloc


@pytest.fixture
def file_paths() -> list:
    return ["config_files/" + "conf_test1.yaml", "config_files/" + "conf_default.yaml"]


@pytest.fixture
def demo_cities() -> dict:
    return {
        "London": [51.5099, -0.1181],
        "Istanbul": [41.0138, 28.9497],
        "Beijing": [39.9075, 116.3972],
    }


def test_load_mission_info(file_paths: list):

    for itr, file_path in enumerate(file_paths):
        sats, lab, out_type = load_mission_info(file_path)

        if itr == 0:
            assert len(sats) == 8
            assert sats[0].norad_id == 25544
            assert sats[0].color == "Red"
            assert lab.lat == 37.7749
            assert lab.lng == -122.4194
            assert lab.min_elev == 5
            assert out_type == 3
        else:
            opencage_loc = opencage_geoloc("Blacksburg")
            assert len(sats) == 4
            assert sats[0].norad_id == 25544
            assert sats[0].color == "Red"
            assert lab.lat == opencage_loc[0]
            assert lab.lng == opencage_loc[1]
            assert lab.min_elev == 30
            assert out_type == 3


def test_opencage_geoloc(demo_cities: dict):

    for city, loc in demo_cities.items():
        opencage_loc = opencage_geoloc(city)
        assert abs(opencage_loc[0] - loc[0]) < 0.04
        assert abs(opencage_loc[1] - loc[1]) < 0.04

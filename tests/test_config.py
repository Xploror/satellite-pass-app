import pytest

from lib.config import claude_geoloc, load_mission_info


@pytest.fixture
def file_paths() -> list:
    return ["config_files/" + "conf_test1.yaml", "config_files/" + "conf_default.yaml"]


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
            assert len(sats) == 8
            assert sats[0].norad_id == 25544
            assert sats[0].color == "Red"
            assert lab.lat == 37.7749
            assert lab.lng == -122.4194
            assert lab.min_elev == 5
            assert out_type == 3
        else:
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

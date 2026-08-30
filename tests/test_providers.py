import pytest
from random import random

from lib.systems import MySatellites, Lab
from lib.providers.n2yo import fetch_API as n2yo_fetch
from lib.providers.terrestre import fetch_API as terrestre_fetch


@pytest.fixture
def demo_sat_data() -> list:
    s1 = MySatellites("S1", 25544, "Red")
    s2 = MySatellites("S2", 45427, "Black")
    s1.is_visible = True
    s2.is_visible = False
    return [s1, s2]

@pytest.fixture
def demo_lab() -> Lab:
    lat = -90 + 180*random()
    lng = -180 + 360*random()
    min_elev = 90*random()
    return Lab([lat,lng], {'min_elev':min_elev})


def test_fetch_APIs(demo_sat_data: list, demo_lab: Lab):

    for demo_sat in demo_sat_data:
        demo_sat.is_visible = None

    terrestre_fetch(demo_sat_data, demo_lab)
    assert all([s.is_visible is not None for s in demo_sat_data])

    for demo_sat in demo_sat_data:
        demo_sat.is_visible = None

    n2yo_fetch(demo_sat_data, demo_lab)
    assert all([s.is_visible is not None for s in demo_sat_data])
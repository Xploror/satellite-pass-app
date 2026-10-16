import pytest

from lib.systems import MySatellites

ISS_LINE1 = "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927"
ISS_LINE2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
ISS_EPOCH_ISO = "2008-09-20T12:25:40.104192+00:00"


@pytest.fixture
def iss_tle() -> tuple:
    return ISS_LINE1, ISS_LINE2


@pytest.fixture
def iss_sat(iss_tle) -> MySatellites:
    return MySatellites("ISS", 25544, "Red", tle=iss_tle, tle_source="test")

import pytest
import os
from random import random

from lib.output import author
from lib.systems import MySatellites, Lab


@pytest.fixture
def testhost() -> str:
    return "127.0.0.1"


@pytest.fixture
def testoutf() -> str:
    return "randomname"


@pytest.fixture
def testport() -> int:
    return 12349


@pytest.fixture
def demo_sat_data() -> list:
    s1 = MySatellites("S1", 25544, "Red")
    s2 = MySatellites("S2", 45427, "Black")
    s1.is_visible = True
    s2.is_visible = False
    return [s1, s2]


@pytest.fixture
def demo_lab() -> Lab:
    lat = -90 + 180 * random()
    lng = -180 + 360 * random()
    min_elev = 90 * random()
    return Lab([lat, lng], {"min_elev": min_elev})


def test_stdoutWriter(demo_sat_data: list, testoutf: str, testhost: str, testport: int, capsys):
    s1 = demo_sat_data[0]
    s2 = demo_sat_data[1]
    out = author(1, out_f=testoutf, host=testhost, port=testport)
    out.write(demo_sat_data)

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured == [str(s1.norad_id) + ": Red", str(s2.norad_id) + ": NOT PASSING"]


def test_FileWriter(demo_sat_data: list, testoutf: str, testhost: str, testport: int):
    s1 = demo_sat_data[0]
    s2 = demo_sat_data[1]
    out = author(2, out_f=testoutf, host=testhost, port=testport)
    out.write(demo_sat_data)

    assert os.path.exists(out.out_f) and os.path.getsize(out.out_f) > 0

    # content check
    with open(out.out_f, "r") as f:
        lines = [line.strip() for line in f]
    assert str(s1.norad_id) + ": Red" in lines and str(s2.norad_id) + ": NOT PASSING" in lines

    # Remove demo output file generated
    os.remove(out.out_f)


def test_TCPWriter(demo_sat_data: list, testoutf: str, testhost: str, testport: int, capsys):
    s1 = demo_sat_data[0]
    s2 = demo_sat_data[1]
    out = author(3, out_f=testoutf, host=testhost, port=testport)
    # Testing write function for arbitrary iterations between 1-10
    for i in range(int(1 + 9 * random())):
        out.write(demo_sat_data)
        captured = capsys.readouterr().out.strip().splitlines()
        data = captured[0].split("\\n")
        assert data[1] == str(s1.norad_id) + ": Red"
        assert data[2] == str(s2.norad_id) + ": NOT PASSING"
    del out


# def test_HTTPWriter(demo_sat_data: list, testoutf: str, testhost: str, testport: int):
#     s1 = demo_sat_data[0]
#     s2 = demo_sat_data[1]
#     out = author(4, out_f=testoutf, host=testhost, port=testport)
#     #Testing write function for arbitrary iterations between 1-10
#     for i in range(int(1 + 9*random())):
#         out.write(demo_sat_data)
#         local_url = "http://localhost:" + str(testport)
#         resp = requests.get(local_url, timeout=3)
#         assert resp.status_code == 200
#         assert str(s1.norad_id) + ": Red" in resp.text
#         assert str(s2.norad_id) + ": NOT PASSING" in resp.text
#     del(out)

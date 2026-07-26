import pytest
import os
import requests

from lib.config import load_mission_info
from lib.output import FileWriter, stdoutWriter, author
from lib.systems import MySatellites, Lab
from lib.utils import fetch_API1, fetch_API2

@pytest.fixture
def file_path() -> str:
    return "config_files/" + "conf_test1.yaml"

@pytest.fixture
def demo_sat_data() -> list:
    s1 = MySatellites("S1", 25544, "Red")
    s2 = MySatellites("S2", 45427, "Black")
    s1.is_visible = True
    s2.is_visible = False
    return [s1, s2]

@pytest.fixture
def demo_lab() -> Lab:
    from random import random
    lat = -90 + 180*random()
    lng = -180 + 360*random()
    min_elev = 90*random()
    return Lab([lat,lng], {'min_elev':min_elev})


def test_load_mission_info(file_path):
    
    sats, lab, out_type = load_mission_info(file_path)

    assert len(sats) == 8
    assert sats[0].id == 25544
    assert sats[0].color == "Red"
    assert lab.lat == 37.7749
    assert lab.lng == -122.4194
    assert lab.min_elev == 5
    assert out_type == 2


def test_fetch_APIs(demo_sat_data:list, demo_lab:Lab):

    for demo_sat in demo_sat_data:
        demo_sat.is_visible = None

    fetch_API1(demo_sat_data, demo_lab)
    assert all([s.is_visible is not None for s in demo_sat_data])

    for demo_sat in demo_sat_data:
        demo_sat.is_visible = None

    fetch_API2(demo_sat_data, demo_lab)
    assert all([s.is_visible is not None for s in demo_sat_data])



def test_stdoutWriter(demo_sat_data, capsys):
    s1 = demo_sat_data[0]
    s2 = demo_sat_data[1]
    out = author(1)
    out.write(demo_sat_data)

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured == [str(s1.id)+": Red", str(s2.id)+": NOT PASSING"]


def test_FileWriter(demo_sat_data):
    s1 = demo_sat_data[0]
    s2 = demo_sat_data[1]
    out = author(2)
    out.write(demo_sat_data)

    output_path = "output.txt"
    assert os.path.exists(output_path) and os.path.getsize(output_path) > 0

    # content check
    with open(output_path, "r") as f:
        lines = [line.strip() for line in f]
    assert str(s1.id)+": Red" in lines and str(s2.id)+": NOT PASSING" in lines

    # Remove demo output file generated
    os.remove(output_path)


# def test_TCPWriter(demo_sat_data):
#     s1 = demo_sat_data[0]
#     s2 = demo_sat_data[1]
#     out = author(3)
#     out.write(demo_sat_data)

#     local_url = "http://localhost:12346"
#     resp = requests.get(local_url, timeout=3)
#     assert resp.status_code == 200
#     assert str(s1.id) in resp.text
#     assert str(s2.id) in resp.text
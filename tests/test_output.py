import csv
import json
import os
from datetime import datetime, timedelta, timezone
from random import random

import pytest

from lib.output import AccessReport, author
from lib.report_config import parse_report_config, resolve
from lib.systems import AccessInterval, Lab, MySatellites


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


@pytest.fixture
def access_report(tmp_path, iss_sat) -> AccessReport:
    lab = Lab([40.0, -75.0], {"min_elev": 10}, alt_m=120.0)
    raw = {
        "Window": {"start_utc": "2008-09-20T12:00:00Z"},
        "Output": {"directory": str(tmp_path / "reports"), "formats": ["stdout", "csv", "json"]},
    }
    cfg = resolve(parse_report_config(raw), lab)
    aos = datetime(2008, 9, 21, 0, 25, 43, tzinfo=timezone.utc)
    interval = AccessInterval(
        norad_id=25544,
        sat_name="ISS",
        pass_no=1,
        aos_utc=aos,
        los_utc=aos + timedelta(seconds=343.8),
        duration_s=343.8,
        rev_aos=56361,
        rev_los=56361,
        max_el_deg=48.1,
        tca_utc=aos + timedelta(seconds=170),
        aos_az_deg=250.0,
        los_az_deg=43.0,
        min_range_km=468.0,
    )
    report = AccessReport(lab, cfg)
    report.add(iss_sat, [interval])
    report.add(MySatellites("Idle", 45427, "Gray", tle=iss_sat.tle, tle_source="test"), [])
    return report


def test_AccessReport_stdout(access_report, capsys):
    access_report.write()
    out = capsys.readouterr().out
    assert "ACCESS REPORT" in out
    assert "ISS (NORAD 25544)" in out
    assert "56361" in out and "48.1" in out
    assert "no access in window" in out


def test_AccessReport_csv_and_json(access_report, tmp_path):
    paths = access_report.write()
    csv_path = next(p for p in paths if p.suffix == ".csv")
    json_path = next(p for p in paths if p.suffix == ".json")

    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["rev_aos"] == "56361"
    assert rows[0]["aos_utc"].startswith("2008-09-21T00:25:43")

    with open(json_path) as f:
        document = json.load(f)
    assert document["meta"]["station"]["alt_m"] == 120.0
    assert document["meta"]["config"]["visibility"]["criterion"] == "aer"
    assert [s["norad_id"] for s in document["satellites"]] == [25544, 45427]
    assert document["satellites"][0]["intervals"][0]["max_el_deg"] == 48.1
    assert document["satellites"][1]["intervals"] == []

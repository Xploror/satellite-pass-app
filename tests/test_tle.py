from datetime import datetime

import pytest
import requests

from lib.providers import tle as tle_provider
from lib.providers.tle import _catalog_number, _checksum_ok, fetch_tle, parse_tle, tle_epoch
from lib.report_config import TLECfg
from lib.systems import MySatellites
from tests.conftest import ISS_EPOCH_ISO, ISS_LINE1, ISS_LINE2


class FakeResponse:
    def __init__(self, text: str = "", payload: dict | None = None):
        self.text = text
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload or {}


def make_cfg(tmp_path, sources=("celestrak", "n2yo"), file_path=None) -> TLECfg:
    return TLECfg(
        sources=tuple(sources),
        file_path=file_path,
        cache_dir=str(tmp_path / "cache"),
        cache_max_age_hours=2,
        max_epoch_age_days=7,
    )


def test_checksum():
    assert _checksum_ok(ISS_LINE1)
    assert _checksum_ok(ISS_LINE2)
    assert not _checksum_ok(ISS_LINE1[:68] + "0")


def test_parse_2le_and_3le():
    assert parse_tle(f"{ISS_LINE1}\n{ISS_LINE2}") == (ISS_LINE1, ISS_LINE2)
    assert parse_tle(f"ISS (ZARYA)\r\n{ISS_LINE1}\r\n{ISS_LINE2}\r\n", 25544) == (
        ISS_LINE1,
        ISS_LINE2,
    )


def test_parse_rejects_bad_checksum():
    with pytest.raises(ValueError):
        parse_tle(f"{ISS_LINE1[:68]}0\n{ISS_LINE2}")


def test_parse_rejects_catalog_mismatch():
    with pytest.raises(ValueError):
        parse_tle(f"{ISS_LINE1}\n{ISS_LINE2}", 12345)


def test_catalog_number_alpha5():
    assert _catalog_number("25544") == 25544
    assert _catalog_number("A0001") == 100001
    assert _catalog_number("J2345") == 182345  # I is skipped, so J -> 18


def test_tle_epoch():
    assert tle_epoch(ISS_LINE1) == datetime.fromisoformat(ISS_EPOCH_ISO)


def test_celestrak_falls_back_to_n2yo(monkeypatch, tmp_path):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        if "celestrak" in url:
            return FakeResponse(text="No GP data found")
        return FakeResponse(payload={"info": {}, "tle": f"{ISS_LINE1}\r\n{ISS_LINE2}"})

    monkeypatch.setenv("N2YO_APIKEY", "dummy")
    monkeypatch.setattr(tle_provider.requests, "get", fake_get)

    sat = MySatellites("ISS", 25544, "Red")
    fetch_tle([sat], make_cfg(tmp_path))

    assert sat.tle == (ISS_LINE1, ISS_LINE2)
    assert sat.tle_source == "n2yo"
    assert "celestrak" in calls[0] and "n2yo" in calls[1]


def test_cache_hit_skips_network(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(
        tle_provider.requests,
        "get",
        lambda url, params=None, timeout=None: FakeResponse(
            text=f"ISS\n{ISS_LINE1}\n{ISS_LINE2}\n"
        ),
    )
    fetch_tle([MySatellites("ISS", 25544, "Red")], cfg)

    def no_network(*args, **kwargs):
        raise requests.exceptions.ConnectionError("network must not be used")

    monkeypatch.setattr(tle_provider.requests, "get", no_network)
    sat = MySatellites("ISS", 25544, "Red")
    fetch_tle([sat], cfg)

    assert sat.tle == (ISS_LINE1, ISS_LINE2)
    assert sat.tle_source == "celestrak (cached)"


def test_all_sources_failing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("N2YO_APIKEY", raising=False)
    monkeypatch.setattr(
        tle_provider.requests,
        "get",
        lambda url, params=None, timeout=None: FakeResponse(text="No GP data found"),
    )
    with pytest.raises(LookupError, match="25544"):
        fetch_tle([MySatellites("ISS", 25544, "Red")], make_cfg(tmp_path))


def test_file_source(tmp_path):
    tle_file = tmp_path / "sats.tle"
    tle_file.write_text(f"ISS (ZARYA)\n{ISS_LINE1}\n{ISS_LINE2}\n")

    sat = MySatellites("ISS", 25544, "Red")
    fetch_tle([sat], make_cfg(tmp_path, sources=["file"], file_path=str(tle_file)))

    assert sat.tle == (ISS_LINE1, ISS_LINE2)
    assert sat.tle_source == "file"
    assert not (tmp_path / "cache").exists()  # local files are not cached

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
N2YO_TLE_URL = "https://api.n2yo.com/rest/v1/satellite/tle/"
NETWORK_SOURCES = ("celestrak", "n2yo")

ALPHA5 = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Alpha-5 catalog prefix letters (I and O are skipped)


class QuotaExceededError(RuntimeError):
    """
    Raised when N2YO answers without TLE data (bad API key or exhausted quota).
    """


def fetch_tle(sat_objs: list, tle_cfg) -> None:
    """
    Populates sat.tle / sat.tle_source for every satellite, trying the configured sources in order.
    """

    missing = []
    for sat in sat_objs:
        cached = _read_cache(sat.norad_id, tle_cfg)
        if cached:
            source, lines = cached
            sat.tle, sat.tle_source = lines, f"{source} (cached)"
            continue

        errors = []
        for source in tle_cfg.sources:
            try:
                lines = _fetch_from(source, sat.norad_id, tle_cfg)
            except (ConnectionError, QuotaExceededError, ValueError, OSError) as e:
                errors.append(f"{source}: {e}")
                continue
            if lines is None:
                errors.append(f"{source}: not found")
                continue

            sat.tle, sat.tle_source = lines, source
            if source in NETWORK_SOURCES:
                _write_cache(sat.norad_id, source, lines, tle_cfg)
            break
        else:
            missing.append(f"{sat.norad_id} ({sat.name}) [{'; '.join(errors)}]")

    if missing:
        raise LookupError("No TLE available for: " + ", ".join(missing))


def parse_tle(text: str, norad_id: int | None = None) -> tuple:
    """
    Extracts the (line1, line2) pair from 2LE/3LE text, optionally matching a catalog number.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for first, second in zip(lines, lines[1:]):
        if not (first.startswith("1 ") and second.startswith("2 ")):
            continue
        if len(first) < 69 or len(second) < 69:
            raise ValueError("TLE lines are shorter than 69 characters")
        if not (_checksum_ok(first) and _checksum_ok(second)):
            raise ValueError("TLE checksum mismatch")

        catalog = _catalog_number(first[2:7])
        if catalog != _catalog_number(second[2:7]):
            raise ValueError("TLE lines have different catalog numbers")
        if norad_id is None or catalog == int(norad_id):
            return first[:69], second[:69]

    raise ValueError(f"No TLE for catalog number {norad_id} in the given text")


def tle_epoch(line1: str) -> datetime:
    """
    Returns the UTC epoch encoded in TLE line 1 (columns 19-32, YYDDD.DDDDDDDD).
    """

    year = int(line1[18:20])
    year += 2000 if year < 57 else 1900
    day_of_year = float(line1[20:32])
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)


def _checksum_ok(line: str) -> bool:
    """
    Verifies the modulo-10 checksum in column 69 (digits count their value, '-' counts 1).
    """

    total = sum(int(c) if c.isdigit() else c == "-" for c in line[:68])
    return line[68].isdigit() and total % 10 == int(line[68])


def _catalog_number(field: str) -> int:
    """
    Decodes a 5-character catalog field, including Alpha-5 numbers above 99999.
    """

    field = field.strip()
    if field and field[0].isalpha():
        return (ALPHA5.index(field[0].upper()) + 10) * 10000 + int(field[1:])
    return int(field)


def _fetch_from(source: str, norad_id: int, tle_cfg) -> tuple | None:
    """
    Dispatches to one TLE source; returns None when the source has no data for the satellite.
    """

    if source == "celestrak":
        text = _get(CELESTRAK_URL, params={"CATNR": norad_id, "FORMAT": "TLE"}).text
        if not text.strip() or "No GP data found" in text:
            return None
        return parse_tle(text, norad_id)

    if source == "n2yo":
        api_key = os.getenv("N2YO_APIKEY")
        if not api_key:
            raise ValueError("N2YO_APIKEY is not set")
        data = _get(N2YO_TLE_URL + f"{norad_id}&apiKey={api_key}").json()
        if "tle" not in data:
            raise QuotaExceededError("Wrong API key or exceeded API transaction limit.")
        return parse_tle(data["tle"], norad_id) if data["tle"] else None

    if source == "file":
        try:
            return parse_tle(Path(tle_cfg.file_path).read_text(), norad_id)
        except ValueError:
            return None

    raise ValueError(f"Unknown TLE source {source!r}")


def _get(url: str, params: dict | None = None) -> requests.Response:
    """
    GET with the same 5-attempt retry policy as the other providers.
    """

    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=3)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == 4:
                raise ConnectionError(f"{url.split('&apiKey=')[0]} unreachable!") from e
    raise ConnectionError(f"{url} unreachable!")


def _cache_path(norad_id: int, tle_cfg) -> Path:
    return Path(tle_cfg.cache_dir) / f"{norad_id}.tle"


def _read_cache(norad_id: int, tle_cfg) -> tuple | None:
    """
    Returns (source, (line1, line2)) from a fresh cache entry whose source is still configured.
    """

    path = _cache_path(norad_id, tle_cfg)
    if not path.is_file():
        return None
    if time.time() - path.stat().st_mtime > tle_cfg.cache_max_age_hours * 3600:
        return None

    source, *rest = path.read_text().splitlines()
    if source not in tle_cfg.sources:
        return None
    try:
        return source, parse_tle("\n".join(rest), norad_id)
    except ValueError:
        return None


def _write_cache(norad_id: int, source: str, lines: tuple, tle_cfg) -> None:
    """
    Stores the TLE as three lines: source name, line 1, line 2.
    """

    path = _cache_path(norad_id, tle_cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{source}\n{lines[0]}\n{lines[1]}\n")

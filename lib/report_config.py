import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import yaml

CRITERIA = ("aer", "los", "both")
TLE_SOURCES = ("celestrak", "n2yo", "file")
OUTPUT_FORMATS = ("stdout", "csv", "json")

DEFAULTS: dict = {
    "Window": {
        "start_utc": "now",
        "duration_hours": 24,
        "time_step_s": 10,
        "refine_edges": True,
        "refine_tolerance_s": 0.1,
    },
    "TLE": {
        "sources": ["celestrak", "n2yo"],
        "file_path": None,
        "cache_dir": "tle_cache",
        "cache_max_age_hours": 2,
        "max_epoch_age_days": 7,
    },
    "Station": {"altitude_m": 0},
    "Visibility": {"criterion": "aer", "apply_refraction": False},
    "AER": {"elevation_deg": [None, 90], "azimuth_deg": [[0, 360]], "range_km": [0, None]},
    "LOS": {"grazing_altitude_km": 0},
    "Output": {
        "formats": ["stdout", "csv", "json"],
        "directory": "reports",
        "filename_prefix": "access_report",
    },
}


@dataclass(frozen=True)
class WindowCfg:
    start_utc: datetime
    duration_hours: float
    time_step_s: float
    refine_edges: bool
    refine_tolerance_s: float


@dataclass(frozen=True)
class TLECfg:
    sources: tuple
    file_path: str | None
    cache_dir: str
    cache_max_age_hours: float
    max_epoch_age_days: float


@dataclass(frozen=True)
class StationCfg:
    altitude_m: float


@dataclass(frozen=True)
class AERCfg:
    elevation_deg: tuple  # (min | None, max)
    azimuth_deg: tuple  # ((lo, hi), ...)
    range_km: tuple  # (min, max | None)


@dataclass(frozen=True)
class LOSCfg:
    grazing_altitude_km: float


@dataclass(frozen=True)
class VisibilityCfg:
    criterion: str
    apply_refraction: bool
    aer: AERCfg
    los: LOSCfg


@dataclass(frozen=True)
class OutputCfg:
    formats: tuple
    directory: str
    filename_prefix: str


@dataclass(frozen=True)
class ReportConfig:
    window: WindowCfg
    tle: TLECfg
    station: StationCfg
    visibility: VisibilityCfg
    output: OutputCfg


def load_report_config(file_path: str) -> ReportConfig:
    """
    Loads and validates the access-report YAML file.
    """

    try:
        with open(file_path, "r") as file:
            raw = yaml.safe_load(file) or {}
    except FileNotFoundError:
        print(
            "\033[31mReport configuration file not found. Check path and try again.\033[0m",
            file=sys.stderr,
        )
        sys.exit(1)

    return parse_report_config(raw)


def parse_report_config(raw: dict) -> ReportConfig:
    """
    Builds a validated ReportConfig from a raw config dict, filling in defaults.
    """

    vis_raw = raw.get("Visibility") or {}
    window = {**DEFAULTS["Window"], **(raw.get("Window") or {})}
    tle = {**DEFAULTS["TLE"], **(raw.get("TLE") or {})}
    station = {**DEFAULTS["Station"], **(raw.get("Station") or {})}
    vis = {**DEFAULTS["Visibility"], **vis_raw}
    aer = {**DEFAULTS["AER"], **(vis_raw.get("AER") or {})}
    los = {**DEFAULTS["LOS"], **(vis_raw.get("LOS") or {})}
    output = {**DEFAULTS["Output"], **(raw.get("Output") or {})}

    config = ReportConfig(
        window=WindowCfg(
            start_utc=_parse_start(window["start_utc"]),
            duration_hours=float(window["duration_hours"]),
            time_step_s=float(window["time_step_s"]),
            refine_edges=bool(window["refine_edges"]),
            refine_tolerance_s=float(window["refine_tolerance_s"]),
        ),
        tle=TLECfg(
            sources=tuple(tle["sources"]),
            file_path=tle["file_path"],
            cache_dir=tle["cache_dir"],
            cache_max_age_hours=float(tle["cache_max_age_hours"]),
            max_epoch_age_days=float(tle["max_epoch_age_days"]),
        ),
        station=StationCfg(altitude_m=float(station["altitude_m"])),
        visibility=VisibilityCfg(
            criterion=str(vis["criterion"]).lower(),
            apply_refraction=bool(vis["apply_refraction"]),
            aer=AERCfg(
                elevation_deg=_pair(aer["elevation_deg"], "AER.elevation_deg"),
                azimuth_deg=_sectors(aer["azimuth_deg"]),
                range_km=_pair(aer["range_km"], "AER.range_km"),
            ),
            los=LOSCfg(grazing_altitude_km=float(los["grazing_altitude_km"])),
        ),
        output=OutputCfg(
            formats=tuple(output["formats"]),
            directory=output["directory"],
            filename_prefix=output["filename_prefix"],
        ),
    )
    _validate(config)
    return config


def resolve(config: ReportConfig, lab) -> ReportConfig:
    """
    Fills a null minimum elevation with the lab's min_elevation from the mission config.
    """

    el_min, el_max = config.visibility.aer.elevation_deg
    if el_min is not None:
        return config

    aer = replace(config.visibility.aer, elevation_deg=(float(lab.min_elev), el_max))
    return replace(config, visibility=replace(config.visibility, aer=aer))


def _parse_start(value) -> datetime:
    """
    Parses the window start ("now", an ISO-8601 string, or a YAML timestamp) as aware UTC.
    """

    if isinstance(value, datetime):
        start = value
    elif str(value).strip().lower() == "now":
        start = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        try:
            start = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Window.start_utc is not 'now' or ISO-8601: {value!r}") from e

    if start.tzinfo is None:
        return start.replace(tzinfo=timezone.utc)
    return start.astimezone(timezone.utc)


def _pair(value, name: str) -> tuple:
    """
    Converts a two-element [min, max] list into a tuple of float-or-None.
    """

    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{name} must be a [min, max] pair, got {value!r}")
    return tuple(None if v is None else float(v) for v in value)


def _sectors(value) -> tuple:
    """
    Normalises azimuth sectors to ((lo, hi), ...), accepting a single [lo, hi] pair too.
    """

    if isinstance(value, (list, tuple)) and len(value) == 2 and not isinstance(value[0], list):
        value = [value]
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"AER.azimuth_deg must be a list of [lo, hi] sectors, got {value!r}")
    return tuple(_pair(sector, "AER.azimuth_deg sector") for sector in value)


def _validate(config: ReportConfig) -> None:
    """
    Raises ValueError for settings that cannot produce a meaningful report.
    """

    window, vis, aer = config.window, config.visibility, config.visibility.aer
    if window.duration_hours <= 0:
        raise ValueError("Window.duration_hours must be > 0")
    if window.time_step_s <= 0:
        raise ValueError("Window.time_step_s must be > 0")
    if window.refine_tolerance_s <= 0:
        raise ValueError("Window.refine_tolerance_s must be > 0")

    if vis.criterion not in CRITERIA:
        raise ValueError(f"Visibility.criterion must be one of {CRITERIA}, got {vis.criterion!r}")

    el_min, el_max = aer.elevation_deg
    if el_max is None or not -90 <= el_max <= 90:
        raise ValueError("AER.elevation_deg max must be within [-90, 90]")
    if el_min is not None and not -90 <= el_min <= el_max:
        raise ValueError("AER.elevation_deg min must be within [-90, max]")

    for lo, hi in aer.azimuth_deg:
        if lo is None or hi is None or not (0 <= lo <= 360 and 0 <= hi <= 360):
            raise ValueError("AER.azimuth_deg sectors must lie within [0, 360]")

    rng_min, rng_max = aer.range_km
    if rng_min is None or rng_min < 0:
        raise ValueError("AER.range_km min must be >= 0")
    if rng_max is not None and rng_max < rng_min:
        raise ValueError("AER.range_km max must be >= min")

    if vis.los.grazing_altitude_km < 0:
        raise ValueError("LOS.grazing_altitude_km must be >= 0")

    unknown_sources = set(config.tle.sources) - set(TLE_SOURCES)
    if not config.tle.sources or unknown_sources:
        raise ValueError(f"TLE.sources must be a non-empty subset of {TLE_SOURCES}")
    if "file" in config.tle.sources and not config.tle.file_path:
        raise ValueError("TLE.file_path is required when 'file' is in TLE.sources")

    unknown_formats = set(config.output.formats) - set(OUTPUT_FORMATS)
    if not config.output.formats or unknown_formats:
        raise ValueError(f"Output.formats must be a non-empty subset of {OUTPUT_FORMATS}")

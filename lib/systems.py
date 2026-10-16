from dataclasses import dataclass
from datetime import datetime


@dataclass
class MySatellites:
    name: str
    norad_id: int
    color: str
    is_visible: bool = False
    tle: tuple[str, str] | None = None
    tle_source: str | None = None


class Lab:
    def __init__(self, location: list, constraints: dict, alt_m: float = 0.0):
        self.lat = location[0]
        self.lng = location[1]
        self.min_elev = constraints["min_elev"]  # deg
        self.alt_m = alt_m  # height above the WGS84 ellipsoid


@dataclass
class AccessInterval:
    norad_id: int
    sat_name: str
    pass_no: int
    aos_utc: datetime
    los_utc: datetime
    duration_s: float
    rev_aos: int
    rev_los: int
    max_el_deg: float
    tca_utc: datetime
    aos_az_deg: float
    los_az_deg: float
    min_range_km: float
    aos_truncated: bool = False  # interval already open at the window start
    los_truncated: bool = False  # interval still open at the window end

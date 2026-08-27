from dataclasses import dataclass


@dataclass
class MySatellites:
    name: str
    norad_id: int
    color: str
    is_visible: bool = False

class Lab:

    def __init__(self, location : list, constraints : dict):
        self.lat = location[0]
        self.lng = location[1]
        self.min_elev = constraints['min_elev'] #deg
from lib.utils import *

class MySatellites:

    def __init__(self, name, id, color):
        self.name = name
        self.id = id
        self.color = color

        self.is_visible = False


class Lab:

    def __init__(self, location, constraints):
        self.lat = location[0]
        self.lng = location[1]
        self.min_elev = constraints['min_elev'] #deg
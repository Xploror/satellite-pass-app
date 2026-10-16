import time

import requests

from lib.utils import get_response


def fetch_API(sat_objs: list, lab_obj, limit: int = 1, visible_only: bool = False) -> None:
    """
    Fetching satellite information from the terrestre tracking APIs.
    """

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng

    parent_url = "https://sat.terrestre.ar/passes/"

    for sat_obj in sat_objs:
        sat_id = sat_obj.norad_id

        url = parent_url + str(sat_id)

        data = get_response(url, params={"lat": lab_lat, "lon": lab_lng, "limit": limit, "visible_only": visible_only}).json()
        if len(data) != 0:
            timestamp_interval = [
                float(data[0]["rise"]["utc_timestamp"]),
                float(data[0]["set"]["utc_timestamp"]),
            ]
            sat_obj.is_visible = (
                time.time() > timestamp_interval[0] and time.time() < timestamp_interval[1]
            )
            break
        else:
            pass

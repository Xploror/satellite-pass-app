import requests
import time

def fetch_API(sat_objs: list, lab_obj, limit: int = 1, visible_only: bool = False) -> None:
    '''
    Fetching satellite information from the terrestre tracking APIs.
    '''

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng

    parent_url = "https://sat.terrestre.ar/passes/"

    for sat_obj in sat_objs:
        sat_id = sat_obj.norad_id

        url = parent_url + str(sat_id)

        for attempt in range(5):
            try:
                response = requests.get(url, 
                                    params={"lat":lab_lat, 
                                            "lon":lab_lng, 
                                            "limit":limit, 
                                            "visible_only":visible_only},
                                            timeout=3)
                response.raise_for_status()
                data = response.json()
                if len(data) != 0:
                    timestamp_interval = [float(data[0]['rise']['utc_timestamp']), float(data[0]['set']['utc_timestamp'])]
                    sat_obj.is_visible = time.time() > timestamp_interval[0] and time.time() < timestamp_interval[1]
                    break
                else:
                    pass
            except requests.exceptions.RequestException as e:
                if attempt == 4:
                    raise ConnectionError(f"{url} unreachable!") from e
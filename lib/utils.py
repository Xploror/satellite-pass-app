import requests
import time
import sys
import os

API_KEY = os.environ["N2YO_APIKEY"]

def fetch_API1(sat_objs: list, lab_obj, limit: int = 1, visible_only: bool = False) -> None:
    '''
    Fetching satellite information from the terrestre tracking APIs.
    '''

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng

    parent_url = "https://sat.terrestre.ar/passes/"

    for sat_obj in sat_objs:
        sat_id = sat_obj.id

        url = parent_url + str(sat_id)

        for attempt in range(5):
            response = requests.get(url, 
                                    params={"lat":lab_lat, 
                                            "lon":lab_lng, 
                                            "limit":limit, 
                                            "visible_only":visible_only},
                                            timeout=3)

            if response.status_code == 200:
                if response.json() != []:
                    data = response.json()[0]
                    timestamp_interval = [float(data['rise']['utc_timestamp']), float(data['set']['utc_timestamp'])]
                else:
                    timestamp_interval = [0, 0] #For given lab position, satellite is never visible even in future
                break
            elif attempt == 4:
                print("Runtime exceed limit", file=sys.stderr)

        sat_obj.is_visible = time.time() > timestamp_interval[0] and time.time() < timestamp_interval[1]


def fetch_API2(sat_objs : list, lab_obj, sec_ahead: int = 1) -> None:
    '''
    Fetching satellite information from the N2YO tracking APIs.
    '''

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng
    lab_alt = 0
    min_elev = lab_obj.min_elev
    parent_url = "https://api.n2yo.com/rest/v1/satellite/"

    for sat_obj in sat_objs:
        sat_id = sat_obj.id

        url = parent_url + "positions" + "/" + str(sat_id) + "/" + str(lab_lat) + "/" + str(lab_lng) + "/" + str(lab_alt) + "/" + str(sec_ahead) + "/&apiKey=" + API_KEY

        for attempt in range(5):
            try:
                response = requests.get(url, timeout=3)
                response.raise_for_status()
                data = response.json()
                break
            except:
                if attempt == 4:
                    print("Runtime exceed limit", file=sys.stderr)

        try:
            first_pass = data["positions"][0]
            sat_obj.is_visible = first_pass['elevation'] > min_elev and first_pass['elevation'] < 180 - min_elev
        except KeyError:
            raise KeyError("Exceeded transaction limit for the given API key. Try using a new one!")


def is_port_available(host: str, port: int):
    '''
    Checks if the host/port address is available to use
    '''
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skt:
        try:
            skt.bind((host, port))
            return True
        except:
            return False
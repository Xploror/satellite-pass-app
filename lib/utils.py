from lib.systems import Lab
import requests
import time

API_KEY = "TBAH4F-ECZHJF-QRNFGX-5T0R"

def fetch_API1(sat_objs : list, lab_obj : Lab, limit=1, days=1, visible_only=False) -> None:
    '''
    Fetching satellite information from the terrestre tracking APIs.
    '''

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng

    parent_url = "https://sat.terrestre.ar/passes/"

    for sat_obj in sat_objs:
        sat_id = sat_obj.id

        url = parent_url + str(sat_id)

        count = 0 
        while True:
            response = requests.get(url, 
                                    params={"lat":lab_lat, 
                                            "lon":lab_lng, 
                                            "limit":limit, 
                                            "visible_only":visible_only})

            count = count + 1
            if response.status_code == 200:
                data = response.json()[0]
                break
            elif count > 100:
                return 0

        timestamp_interval = [float(data['rise']['utc_timestamp']), float(data['set']['utc_timestamp'])]

        sat_obj.is_visible = time.time() > timestamp_interval[0] and time.time() < timestamp_interval[1]



def fetch_API2(sat_objs : list, lab_obj : Lab, v_type='radiopasses', days=1) -> None:
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

        url = parent_url + "positions" + "/" + str(sat_id) + "/" + str(lab_lat) + "/" + str(lab_lng) + "/" + str(lab_alt) + "/" + str(1) + "/&apiKey=" + API_KEY

        count = 0 
        while True:
            response = requests.get(url)

            count = count + 1
            if response.status_code == 200:
                data = response.json()
                break
            elif count > 100:
                print("Runtime exceed limit")
                return 0

        first_pass = data["positions"][0]
        sat_obj.is_visible = first_pass['elevation'] > min_elev and first_pass['elevation'] < 180 - min_elev


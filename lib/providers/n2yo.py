import os

import requests

API_KEY = os.environ["N2YO_APIKEY"]


class QuotaExceededError(RuntimeError):
    """
    Class to define whenever the API quota is exceeded
    """

    pass


def fetch_API(sat_objs: list, lab_obj, sec_ahead: int = 1) -> None:
    """
    Fetching satellite information from the N2YO tracking APIs.
    """

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng
    lab_alt = 0
    min_elev = lab_obj.min_elev
    parent_url = "https://api.n2yo.com/rest/v1/satellite/"

    for sat_obj in sat_objs:
        sat_id = sat_obj.norad_id

        url = (
            parent_url
            + "positions"
            + "/"
            + str(sat_id)
            + "/"
            + str(lab_lat)
            + "/"
            + str(lab_lng)
            + "/"
            + str(lab_alt)
            + "/"
            + str(sec_ahead)
            + "/&apiKey="
            + API_KEY
        )

        for attempt in range(5):
            try:
                response = requests.get(url, timeout=3)
                response.raise_for_status()
                data = response.json()
                try:
                    first_pass = data["positions"][0]
                    sat_obj.is_visible = first_pass["elevation"] > min_elev
                except KeyError as e:
                    raise QuotaExceededError(
                        "Wrong API key or exceeded API transaction limit. Try using a new one!"
                    ) from e
                break
            except requests.exceptions.RequestException as e:
                if attempt == 4:
                    raise ConnectionError(f"{url} unreachable!") from e


def fetch_trajectory(sat_objs: list, lab_obj, sec_ahead: int = 300) -> tuple[dict, dict]:
    """
    Fetching satellite trajectories (multiple future positions) from the N2YO tracking APIs.
    """

    lab_lat = lab_obj.lat
    lab_lng = lab_obj.lng
    lab_alt = 0
    min_elev = lab_obj.min_elev
    parent_url = "https://api.n2yo.com/rest/v1/satellite/"

    trajectories: dict = {}
    visibilities: dict = {}

    for sat_obj in sat_objs:
        sat_id = sat_obj.norad_id

        url = (
            parent_url
            + "positions"
            + "/"
            + str(sat_id)
            + "/"
            + str(lab_lat)
            + "/"
            + str(lab_lng)
            + "/"
            + str(lab_alt)
            + "/"
            + str(sec_ahead)
            + "/&apiKey="
            + API_KEY
        )

        for attempt in range(5):
            try:
                response = requests.get(url, timeout=3)
                response.raise_for_status()
                data = response.json()
                try:
                    positions = data["positions"]
                    first_pass = data["positions"][0]
                    sat_obj.is_visible = first_pass["elevation"] > min_elev
                except KeyError as e:
                    raise QuotaExceededError(
                        "Wrong API key or exceeded API transaction limit. Try using a new one!"
                    ) from e
                trajectories[sat_id] = [
                    {
                        "lat": pos["satlatitude"],
                        "lng": pos["satlongitude"],
                        "alt": pos["sataltitude"],
                        "elevation": pos["elevation"],
                        "timestamp": pos["timestamp"],
                        "eclipsed": pos["eclipsed"],
                    }
                    for pos in positions
                ]
                visibilities[sat_id] = [pos["elevation"] > min_elev for pos in positions]
                break
            except requests.exceptions.RequestException as e:
                if attempt == 4:
                    raise ConnectionError(f"{url} unreachable!") from e

    return trajectories, visibilities

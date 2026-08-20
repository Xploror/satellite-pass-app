import os
import yaml
import sys
from lib.systems import *

OPENCAGE_API = os.environ["OPENCAGE_APIKEY"]

def load_config(file_path: str) -> dict:
    '''
    Load configuration from a YAML file.

    Args:
        file_path (str): Path to the YAML configuration file.
    '''

    try:
        with open(file_path, 'r') as file:
            configs = yaml.safe_load(file)
        # Checks if City attribute is non-empty to run opencage API and override Lat, Lng from config file
        if configs['Lab']['City'] and (not configs['Lab']['Latitude'] or not configs['Lab']['Longitude']):
            loc = opencage_geoloc(configs['Lab']['City'])
            configs['Lab']['Latitude'] = loc[0]
            configs['Lab']['Longitude'] = loc[1]
    except FileNotFoundError:
        print("\033[31mConfiguration file not found or missing necessary data. Please check the file path or fill necessary data and try again.\033[0m", file=sys.stderr)
        configs = {} #Empty dictionary

    # print(f"Loaded configuration from {file_path}")
    return configs


def load_mission_info(file_path: str) -> tuple:
    '''
    Load mission information from a YAML file.

    Args:
        file_path (str): Path to the YAML mission information file.
    '''
    configs = load_config(file_path)
    return [MySatellites(sat_name,sat_info['ID'],sat_info['Color']) for sat_name, sat_info in configs['Assets'].items()], Lab([configs['Lab']['Latitude'],configs['Lab']['Longitude']], {'min_elev': configs['Lab']['min_elevation']}), configs['Output']


def opencage_geoloc(city: str) -> list:
    '''
    Takes the city name and returns the latitude and longitude using the OpenCage Geocoding API.
    '''
    from opencage.geocoder import OpenCageGeocode

    coder = OpenCageGeocode(OPENCAGE_API)
    results = coder.geocode(city)
    if results == []:
        print("\033[31mCould not find the desired city in the database. Please check the spelling or try latitude and longitude values!\033[0m", file=sys.stderr)
        sys.exit(0)
    return [results[0]['geometry']['lat'], results[0]['geometry']['lng']]
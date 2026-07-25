import yaml
from typing import Union
from lib.systems import *

def load_config(file_path: str) -> dict:
    '''
    Load configuration from a YAML file.

    Args:
        file_path (str): Path to the YAML configuration file.
    '''

    try:
        with open(file_path, 'r') as file:
            configs = yaml.safe_load(file)
    except Exception as exc:
        print(exc)
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
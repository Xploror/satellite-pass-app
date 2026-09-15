import os
import sys

import requests
import yaml

from lib.systems import Lab, MySatellites

ANTHROPIC_APIKEY = os.environ["ANTHROPIC_APIKEY"]
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5"

COORDINATES_TOOL = {
    "name": "report_coordinates",
    "description": "Reports the latitude and longitude of a city in signed decimal degrees.",
    "input_schema": {
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Latitude in signed decimal degrees"},
            "longitude": {"type": "number", "description": "Longitude in signed decimal degrees"},
        },
        "required": ["latitude", "longitude"],
    },
}


def load_config(file_path: str) -> dict:
    """
    Load configuration from a YAML file.

    Args:
        file_path (str): Path to the YAML configuration file.
    """

    try:
        with open(file_path, "r") as file:
            configs = yaml.safe_load(file)
        # Checks if City attribute is non-empty to override Lat, Lng from config file
        if configs["Lab"]["City"]:
            loc = claude_geoloc(configs["Lab"]["City"])
            configs["Lab"]["Latitude"] = loc[0]
            configs["Lab"]["Longitude"] = loc[1]
    except FileNotFoundError:
        print(
            "\033[31mConfiguration file not found. Check path and try again.\033[0m",
            file=sys.stderr,
        )
        sys.exit(1)

    # print(f"Loaded configuration from {file_path}")
    return configs


def load_mission_info(file_path: str) -> tuple:
    """
    Load mission information from a YAML file.

    Args:
        file_path (str): Path to the YAML mission information file.
    """
    configs = load_config(file_path)
    return (
        [
            MySatellites(sat_name, sat_info["ID"], sat_info["Color"])
            for sat_name, sat_info in configs["Assets"].items()
        ],
        Lab(
            [configs["Lab"]["Latitude"], configs["Lab"]["Longitude"]],
            {"min_elev": configs["Lab"]["min_elevation"]},
        ),
        configs["Output"],
    )


def _parse_coordinates(response_body: dict) -> list:
    """
    Extracts latitude/longitude from the report_coordinates tool call in Claude's response.
    """

    for block in response_body["content"]:
        if block["type"] == "tool_use" and block["name"] == "report_coordinates":
            return [block["input"]["latitude"], block["input"]["longitude"]]
    raise ValueError("No coordinates reported")


def claude_geoloc(city: str) -> list:
    """
    Takes the city name and returns lat-lon using the Anthropic Claude API.
    """

    headers = {
        "x-api-key": ANTHROPIC_APIKEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 256,
        "system": "You are a precise geocoding assistant. Always call report_coordinates with "
        "the accurate real-world latitude and longitude of the given city upto 6 point precision.",
        "tools": [COORDINATES_TOOL],
        "tool_choice": {"type": "tool", "name": "report_coordinates"},
        "messages": [{"role": "user", "content": f"What is the latitude and longitude of {city}?"}],
    }

    response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=10)

    if response.status_code == 200:
        try:
            return _parse_coordinates(response.json())
        except (KeyError, ValueError):
            pass

    print(
        "\033[31mCould not find the desired city. Please check the spelling!\033[0m",
        file=sys.stderr,
    )
    sys.exit(0)

import os

import requests

API_KEY = os.environ["N2YO_APIKEY"]


class QuotaExceededError(RuntimeError):
    """
    Class to define whenever the API quota is exceeded
    """

    pass


def is_port_available(host: str, port: int):
    """
    Checks if the host/port address is available to use
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skt:
        try:
            skt.bind((host, port))
            return True
        except Exception:
            return False


def get_response(url: str, params: dict | None = None) -> requests.Response:
    """
    GET with the 5-attempt retry policy.
    """

    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=3)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == 4:
                if "&apiKey=" in url:
                    raise ConnectionError(f"{url.split('&apiKey=')[0]} unreachable!") from e
                else:
                    raise ConnectionError(f"{url} unreachable!") from e
    raise ConnectionError(f"{url} unreachable!")


# ============== REPORT UTILS ===================

# ===============================================

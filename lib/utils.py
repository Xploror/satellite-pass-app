import os

import requests

API_KEY = os.environ["N2YO_APIKEY"]


class QuotaExceededError(RuntimeError):
    """
    Class to define whenever the API quota is exceeded
    """

    pass


def colored_string(text: str, col: str) -> str:
    """
    Prints the text with the specified ANSI color code.

    Args:
        text (str): The text to print.
        col (str): The color to use (SUPPORTS: red, green, blue, yellow, orange,
        magenta, cyan, white).
    Returns:
        str: The text with the ANSI color code applied.
    """
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "orange": "\033[38;5;208m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
    }
    color_code = colors.get(col.lower(), "")
    return f"{color_code}{text}\033[0m"


def list_tuple_conversion(data: list | tuple) -> list | tuple:
    """
    Converts a 1D/2D list to respective 1D/2D tuple or vice versa.

    Args:
        lst (list | tuple): The list or tuple to convert.

    Returns:
        list | tuple: The converted list or tuple.
    """
    if isinstance(data, list):
        if not isinstance(data[0], list):
            return tuple(data)
        else:
            return tuple(map(tuple, data))
    elif isinstance(data, tuple):
        if not isinstance(data[0], tuple):
            return list(data)
        else:
            return list(map(list, data))
    else:
        raise TypeError("Input must be a consistent datatype of list or tuple.")


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

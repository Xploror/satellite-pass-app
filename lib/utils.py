import os

API_KEY = os.environ["N2YO_APIKEY"]


class QuotaExceededError(RuntimeError):
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
        except:
            return False

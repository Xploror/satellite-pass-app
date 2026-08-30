import pytest
import os
from random import random

from lib.config import load_mission_info
from lib.output import author
from lib.systems import MySatellites, Lab
from lib.utils import is_port_available
from lib.providers.n2yo import fetch_API as n2yo_fetch
from lib.providers.terrestre import fetch_API as terrestre_fetch


@pytest.fixture
def testhost() -> str:
    return "127.0.0.1"

@pytest.fixture
def testport() -> int:
    return 12349


def test_is_port_available(testhost: str, testport: int):

    # Free port
    new_testport = testport + 1 # Using a different port
    boolval = is_port_available(testhost, new_testport)
    assert boolval == True

    # Busy port
    import socket
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.bind((testhost, new_testport))
    skt.listen()

    boolval = is_port_available(testhost, new_testport)
    assert boolval == False

    skt.close()
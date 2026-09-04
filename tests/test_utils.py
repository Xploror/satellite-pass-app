import pytest

from lib.utils import is_port_available


@pytest.fixture
def testhost() -> str:
    return "127.0.0.1"


@pytest.fixture
def testport() -> int:
    return 12349


def test_is_port_available(testhost: str, testport: int):

    # Free port
    new_testport = testport + 1  # Using a different port
    boolval = is_port_available(testhost, new_testport)
    assert boolval == 1

    # Busy port
    import socket

    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.bind((testhost, new_testport))
    skt.listen()

    boolval = is_port_available(testhost, new_testport)
    assert boolval == 0

    skt.close()

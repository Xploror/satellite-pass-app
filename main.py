import os
import sys
import time

from lib.config import load_mission_info
from lib.output import author
from lib.providers.n2yo import fetch_API
from lib.utils import is_port_available

# CONFIG_FOLDER = "config_files/"

CONF_PATH = os.getenv("CONFIG_FILENAME", "config_files/conf_default")
OUT_F = os.getenv("APP_OUTFILE", "output")
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "12346"))


def main():
    # INPUT DESIRED CONFIG FILE FROM ARGV ($out_type PRIORITY: 1. CLI  2. YAML, $port PRIORITY: 1. CLI  2. ENV_VAR)
    conf_file_path = (
        sys.argv[1] if len(sys.argv) > 1 else None
    ) or CONF_PATH.strip()  # conf_file path PRIORITY: 1. CLI  2. ENV_VAR
    out_type_cli = (
        int(sys.argv[2]) if len(sys.argv) > 2 else None
    )  # output_type as second argument (OPTIONAL)
    port_cli = sys.argv[3] if len(sys.argv) > 3 else 0  # port as third argument (OPTIONAL)

    # FIRST READ THE CONFIG YAML FILE AND CREATE DESIRED OBJECTS
    sats, lab, out_type = load_mission_info(conf_file_path + ".yaml")

    out_type = out_type_cli or out_type  # out_type PRIORITY: 1. CLI  2. YAML
    port = port_cli or (
        PORT if is_port_available(HOST, PORT) else 8080
    )  # Checks if host/port address is available, if not then use port_cli

    # DEFINE OUTPUTWRITER OBJECT
    writer = author(out_type, out_f=OUT_F, host=HOST, port=port)

    while True:
        # USING THE API TO UPDATE SAT OBJECTS GIVEN A DESIRED LOCATION
        fetch_API(sats, lab)

        # WRITING OUTPUT
        writer.write(sats)

        # 10 SECOND INTERVAL
        time.sleep(10)


if __name__ == "__main__":
    main()

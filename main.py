from lib.config import load_mission_info
from lib.utils import *
from lib.output import *
from datetime import datetime, timezone
import time

# FIRST READ THE CONFIG YAML FILE AND CREATE DESIRED OBJECTS
sats, lab, out_type = load_mission_info("config_files/conf_1.yaml")

while True:

    # NOW USE THE API TO UPDATE SAT OBJECTS GIVEN A DESIRED LOCATION
    fetch_API2(sats, lab)

    # OUTPUT
    write_output(sats, out_type)

    time.sleep(10)
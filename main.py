from lib.config import load_mission_info
from lib.utils import *
from lib.output import *
import time
import os
import sys

CONFIG_FOLDER = "config_files/"
DEFAULT_CONF_FILE = "conf_default"

# INPUT DESIRED CONFIG FILE FROM ARGV
conf_file_name = os.getenv("CONFIG_FILENAME", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONF_FILE) 

# FIRST READ THE CONFIG YAML FILE AND CREATE DESIRED OBJECTS
sats, lab, out_type = load_mission_info(CONFIG_FOLDER + conf_file_name + ".yaml")

# DEFINE OUTPUTWRITER OBJECT
writer = author(out_type)

while True:

    # NOW USE THE API TO UPDATE SAT OBJECTS GIVEN A DESIRED LOCATION
    fetch_API2(sats, lab)

    # OUTPUT
    writer.write(sats)

    time.sleep(10)
from lib.config import load_mission_info
from lib.utils import *
from lib.output import *
import time

CONFIG_FOLDER = "config_files/"

# INPUT DESIRED CONFIG FILE
conf_file_name = input("Enter config file name (default: conf_default): ")
if conf_file_name == "":
    conf_file_name = "conf_default" 

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
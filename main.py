import os
import sys
import time

from lib.access import compute_access
from lib.config import load_mission_info
from lib.output import AccessReport, author
from lib.providers.n2yo import fetch_API
from lib.providers.tle import fetch_tle, tle_epoch
from lib.utils import colored_string, is_port_available

CONF_PATH = os.getenv("CONFIG_FILENAME", "config_files/conf_default")
OUT_F = os.getenv("APP_OUTFILE", "output")
HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "12346"))


def main() -> None:
    # INPUT DESIRED CONFIG FILE FROM ARGV
    conf_file_path = (
        sys.argv[1] if len(sys.argv) > 1 else None
    ) or CONF_PATH.strip()  # conf_file path PRIORITY: 1. CLI  2. ENV_VAR
    out_type_cli = (
        int(sys.argv[2]) if len(sys.argv) > 2 else None
    )  # output_type as second argument (OPTIONAL)
    port_cli = int(sys.argv[3]) if len(sys.argv) > 3 else 0  # port as third argument (OPTIONAL)

    # FIRST READ THE CONFIG YAML FILE AND CREATE DESIRED OBJECTS
    sats, lab, out = load_mission_info(conf_file_path + ".yaml")

    if isinstance(out, int):  # Sync mode
        out_type = out_type_cli or out  # out_type PRIORITY: 1. CLI  2. YAML
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

    else:  # Async mode
        config = out
        fetch_tle(sats, config.tle)

        report = AccessReport(lab, config)
        for sat in sats:
            age_days = (config.window.start_utc - tle_epoch(sat.tle[0])).total_seconds() / 86400
            if abs(age_days) > config.tle.max_epoch_age_days:
                print(
                    colored_string(
                        f"Warning: TLE for {sat.norad_id} is {age_days:+.1f} days from the "
                        "window start; accuracy will be degraded.",
                        "yellow",
                    ),
                    file=sys.stderr,
                )
            try:
                report.add(sat, compute_access(sat, lab, config))
            except RuntimeError as e:  # SGP4 failure, e.g. decayed satellite
                print(colored_string(f"Skipping {sat.norad_id}: {e}", "red"), file=sys.stderr)

        for path in report.write():
            print(colored_string(f"Saved access report to {path}", "cyan"))


if __name__ == "__main__":
    main()

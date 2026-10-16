import os
import sys

from lib.access import compute_access
from lib.config import load_mission_info
from lib.output import AccessReport
from lib.providers.tle import fetch_tle, tle_epoch
from lib.report_config import load_report_config, resolve_nullelev
from lib.utils import colored_string

CONF_PATH = os.getenv("CONFIG_FILENAME", "config_files/conf_default")
REPORT_CONF_PATH = os.getenv("REPORT_CONFIG_FILENAME", "config_files/report_default")


def main() -> None:
    conf_file_path = (
        sys.argv[1] if len(sys.argv) > 1 else None
    ) or CONF_PATH.strip()  # mission conf PRIORITY: 1. CLI  2. ENV_VAR
    report_file_path = (
        sys.argv[2] if len(sys.argv) > 2 else None
    ) or REPORT_CONF_PATH.strip()  # report conf PRIORITY: 1. CLI  2. ENV_VAR

    sats, lab, _ = load_mission_info(conf_file_path + ".yaml")
    config = resolve_nullelev(load_report_config(report_file_path + ".yaml"), lab)
    lab.alt_m = config.station.altitude_m

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

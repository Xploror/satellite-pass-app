import os
import sys

from lib.access import compute_access
from lib.config import load_mission_info
from lib.output import AccessReport
from lib.providers.tle import fetch_tle, tle_epoch
from lib.report_config import load_report_config, resolve

CONF_PATH = os.getenv("CONFIG_FILENAME", "config_files/conf_default")
REPORT_CONF_PATH = os.getenv("REPORT_CONFIG_FILENAME", "config_files/report_default")


def main() -> None:
    conf_file_path = (
        sys.argv[1] if len(sys.argv) > 1 else None
    ) or CONF_PATH.strip()  # mission conf PRIORITY: 1. CLI  2. ENV_VAR
    report_file_path = (
        sys.argv[2] if len(sys.argv) > 2 else None
    ) or REPORT_CONF_PATH.strip()  # report conf PRIORITY: 1. CLI  2. ENV_VAR

    sats, lab, _out_type = load_mission_info(conf_file_path + ".yaml")
    config = resolve(load_report_config(report_file_path + ".yaml"), lab)
    lab.alt_m = config.station.altitude_m

    fetch_tle(sats, config.tle)

    report = AccessReport(lab, config)
    for sat in sats:
        age_days = (config.window.start_utc - tle_epoch(sat.tle[0])).total_seconds() / 86400
        if abs(age_days) > config.tle.max_epoch_age_days:
            print(
                f"\033[33mWarning: TLE for {sat.norad_id} is {age_days:+.1f} days from the "
                "window start; accuracy will be degraded.\033[0m",
                file=sys.stderr,
            )
        try:
            report.add(sat, compute_access(sat, lab, config))
        except RuntimeError as e:  # SGP4 failure, e.g. decayed satellite
            print(f"\033[31mSkipping {sat.norad_id}: {e}\033[0m", file=sys.stderr)

    for path in report.write():
        print(f"Saved access report to {path}")


if __name__ == "__main__":
    main()

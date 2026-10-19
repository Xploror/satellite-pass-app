import csv
import datetime
import json
import os
import socket
import sys
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from lib.providers.tle import tle_epoch
from lib.utils import colored_string, list_tuple_conversion


class OutputWriter:
    def __init__(self, out_f: str, host: str, port: int):
        self.host = host
        self.port = port

        self.out_folder = "log/"
        self.out_f = Path(self.out_folder + out_f).with_suffix(".txt")  # Default output folder

    def write(self, sat_objs: list):
        print("Parent OutputWriter object!")


class stdoutWriter(OutputWriter):
    def write(self, sat_objs: list) -> None:
        """
        Write the output as STDOUT
        """

        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                print(str(sat_obj.norad_id) + ": " + sat_obj.color)
            else:
                print(str(sat_obj.norad_id) + ": NOT PASSING")


class FileWriter(OutputWriter):
    def __init__(self, out_f: str, host: str, port: int):
        super().__init__(out_f, host, port)
        self.prepare_outfile()  # prepare the output file

    def prepare_outfile(self) -> None:
        """
        Handles the existence of output folder and cleans the output file
        """
        if not os.path.isdir(self.out_folder):
            os.makedirs(self.out_folder)
            pass
        open(self.out_f, "w").close() if os.path.isfile(
            self.out_f
        ) else 0  # Clears the file before writing starts

    def write(self, sat_objs: list) -> None:
        """
        Write the output in a file
        """
        now = datetime.datetime.now()

        lines = ["[" + now.strftime("%Y-%m-%d %H:%M:%S") + "]\n"]
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                lines.append(str(sat_obj.norad_id) + ": " + sat_obj.color + "\n")
            else:
                lines.append(str(sat_obj.norad_id) + ": NOT PASSING\n")

        with open(self.out_f, "a+") as f:
            f.writelines(lines)


class HTTPWriter(OutputWriter):
    def __init__(self, out_f: str, host: str, port: int):
        super().__init__(out_f, host, port)
        self.msg = b""  # Empty byte object
        self._this_server: HTTPServer | None = None
        self._this_thread: threading.Thread | None = None
        self._initialize_server()

    def __del__(self):
        """
        Destructor terminates any ongoing server and threads
        """
        self.stop_server()

    def _initialize_server(self):
        """
        Tracks and initializes a HTTP server to update with the most recent message
        """
        if self._this_server:
            return

        # Make Handler class derived from BaseHTTPRequestHandler for HTTPServer object
        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                """
                Setup the contents for the services using message attribute from TCPWriter
                """
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", "text/plain; charset=utf-8")
                handler_self.send_header("Content-Length", str(len(self.msg)))
                handler_self.end_headers()
                handler_self.wfile.write(self.msg)

            # Helps in suppressing the logs by returning nothing
            def log_message(self, format: str, *args: Any) -> None:
                # return super().log_message(format, *args)
                return

        # Make the HTTPServer object to run the service on a thread as background daemon
        try:
            self._this_server = HTTPServer((self.host, self.port), Handler)
            self._this_thread = threading.Thread(
                target=self._this_server.serve_forever, daemon=True
            )
            self._this_thread.start()
        except OSError:
            raise RuntimeError(
                colored_string(
                    self.host
                    + "/"
                    + str(self.port)
                    + " seems unavailable. Try killing the process",
                    "yellow",
                )
            )

    def stop_server(self):
        """
        Stops a running server and the associated threads
        """
        if self._this_server and self._this_thread:
            self._this_server.shutdown()
            time.sleep(2)
            self._this_thread.join()
            self._this_server.server_close()

    def write(self, sat_objs: list) -> None:
        """
        Write the output as a TCP socket client
        """

        lines = ["[" + str(datetime.datetime.now()) + "]" + "\n"]
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                lines.append(f"{sat_obj.norad_id}: {sat_obj.color}\n")
            else:
                lines.append(f"{sat_obj.norad_id}: NOT PASSING\n")

        msg = "".join(lines).encode("utf-8")
        self.msg = msg


class TCPWriter(OutputWriter):
    def __init__(self, out_f: str, host: str, port: int):
        super().__init__(out_f, host, port)
        self.msg = b""  # Empty byte object
        self._server_socket: socket.socket | None = None
        self._client_socket: socket.socket | None = None
        self._this_thread = None
        self.running = True
        self._initialize_sockets()

    def __del__(self):
        """
        Destructor terminates any ongoing server and threads
        """
        self.stop_server()

    def get_server(self):
        return self._server_socket

    def get_client(self):
        return self._client_socket

    def listen_loop(self):
        while self.running:
            if self._server_socket:
                conn, addr = self._server_socket.accept()
                try:
                    msg_recv = conn.recv(1024)
                    ack_msg = b"Data received from client:" + msg_recv
                    conn.sendall(ack_msg)
                except Exception as e:
                    print(f"Error occurred: {e}")
                    break

    def sender_loop(self):

        self._client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._client_socket.connect((self.host, self.port))
        if self.msg:
            try:
                self._client_socket.sendall(self.msg)
                while True:
                    data = self._client_socket.recv(1024)
                    if data:
                        print(data)
                        break
                    else:
                        print("no data received")
            except Exception as e:
                print(f"Error occurred: {e}")

    def _initialize_sockets(self):
        """
        Initiates the socket and binds it to listen to the host port address.
        It also starts a thread to handle the incoming connections and send the most recent message.
        """
        # SERVER LISTENING
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(1)

        self._server_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self._server_thread.start()

    def stop_server(self):
        """
        Stops a running socket and the associated threads
        """
        self.running = False
        if self._server_socket:
            self._server_socket.close()
        if self._client_socket:
            self._client_socket.close()
        time.sleep(2)
        self._server_thread.join()

    def write(self, sat_objs: list) -> None:
        """
        Changing the message for the TCP client to send
        """

        lines = ["[" + str(datetime.datetime.now()) + "]" + "\n"]
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                lines.append(f"{sat_obj.norad_id}: {sat_obj.color}\n")
            else:
                lines.append(f"{sat_obj.norad_id}: NOT PASSING\n")

        msg = "".join(lines).encode("utf-8")
        self.msg = msg
        self.sender_loop()


def author(out_type: int, out_f: str, host: str, port: int) -> OutputWriter:
    """
    Writes output based on the specified output type.
    """
    writer: OutputWriter
    if out_type == 1:
        writer = stdoutWriter(out_f, host, port)
    elif out_type == 2:
        writer = FileWriter(out_f, host, port)
    elif out_type == 3:
        writer = TCPWriter(out_f, host, port)
    elif out_type == 4:
        writer = HTTPWriter(out_f, host, port)
    else:
        raise ValueError("Invalid output type specified.")

    return writer


class AccessReport:
    """
    Collects access intervals per satellite and writes them as stdout / csv / json.
    """

    TIME_FMT = "%Y-%m-%d %H:%M:%S"
    CSV_FIELDS = [
        "norad_id",
        "sat_name",
        "pass_no",
        "rev_aos",
        "rev_los",
        "aos_utc",
        "los_utc",
        "duration_s",
        "max_el_deg",
        "tca_utc",
        "aos_az_deg",
        "los_az_deg",
        "min_range_km",
        "aos_truncated",
        "los_truncated",
    ]

    def __init__(self, lab, report_cfg):
        self.lab = lab
        self.cfg = report_cfg
        self.entries: list = []  # (sat, intervals)
        self.generated_utc = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        self.report_header() # TODO

    @staticmethod
    def _flags(interval) -> str:
        flags = []
        if interval.aos_truncated:
            flags.append("AOS<window")
        if interval.los_truncated:
            flags.append("LOS>window")
        return ",".join(flags)

    @staticmethod
    def _json_default(value):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        raise TypeError(f"{type(value).__name__} is not JSON serializable")

    def report_header(self) -> None:
        """
        Stores the header information for the report.
        """
        self.report_header_info = None

    def _criterion_summary(self) -> str:
        vis = self.cfg.visibility
        el_lims = list_tuple_conversion(vis.aer.elevation_deg)
        az_sectors = list_tuple_conversion(vis.aer.azimuth_deg)
        rng_min, rng_max = vis.aer.range_km
        parts = []
        if vis.criterion in ("aer", "both"):
            parts.append(
                f"el {el_lims} deg, az {az_sectors} deg, "
                f"range [{rng_min:g}, {'inf' if rng_max is None else f'{rng_max:g}'}] km"
            )
        if vis.criterion in ("los", "both"):
            parts.append(f"LOS grazing {vis.los.grazing_altitude_km:g} km")
        parts.append(f"refraction {'on' if vis.apply_refraction else 'off'}")
        return " | ".join(parts)

    def _tle_summary(self, sat) -> str:
        if sat.tle is None:
            return "no TLE"
        epoch = tle_epoch(sat.tle[0])
        age_days = (self.cfg.window.start_utc - epoch).total_seconds() / 86400
        return (
            f"TLE source: {sat.tle_source}, "
            f"TLE epoch: {epoch:{self.TIME_FMT}} UTC ({age_days:+.2f} d)"
        )

    def _rows(self) -> list:
        rows = []
        for _sat, intervals in self.entries:
            for iv in intervals:
                row = asdict(iv)
                for key in ("aos_utc", "los_utc", "tca_utc"):
                    row[key] = row[key].isoformat()
                rows.append(row)
        return rows

    def add(self, sat, intervals: list) -> None:
        self.entries.append((sat, intervals))

    def write(self) -> list:
        """
        Writes every configured format; returns the paths of the files created.
        """

        if not self.entries:
            print(
                colored_string("Cannot write an empty report!", "red"),
                file=sys.stderr,
            )
            sys.exit(0)

        paths = []
        file_name = f"{self.cfg.output.filename_prefix}_{self.generated_utc:%Y%m%dT%H%M%SZ}"
        out_dir = Path(self.cfg.output.directory)
        if {"csv", "json"} & set(self.cfg.output.formats):
            out_dir.mkdir(parents=True, exist_ok=True)

        for fmt in self.cfg.output.formats:
            if fmt == "stdout":
                print(self.render_text())
            elif fmt == "csv":
                paths.append(self._write_csv(out_dir / f"{file_name}.csv"))
            elif fmt == "json":
                paths.append(self._write_json(out_dir / f"{file_name}.json"))
        return paths

    def render_text(self) -> str:
        """
        Header block with station/window/criterion settings, then one table per satellite.
        """

        window, vis, lab = self.cfg.window, self.cfg.visibility, self.cfg.station
        end = window.start_utc + datetime.timedelta(hours=window.duration_hours)
        lines = [
            "=" * 118,
            "ACCESS REPORT",
            f"Generated : {self.generated_utc:{self.TIME_FMT}} UTC",
            f"Station   : lat {lab.lat_deg:.5f}  lon {lab.lng_deg:.5f}"
            f"  alt {lab.altitude_m:.1f} m  minimum elevation {lab.min_elev_deg:.1f} deg",
            f"Window    : {window.start_utc:{self.TIME_FMT}} -> {end:{self.TIME_FMT}} UTC"
            f"  (duration {window.duration_hours:g} hr, step {window.time_step_s:g} s, "
            f"refine {'on' if window.refine_edges else 'off'})",
            f"Criterion : {vis.criterion}  | {self._criterion_summary()}",
            "=" * 118,
        ]

        header = (
            f"{'Pass':^4} {'Rev(AOS)':^8} {'Rev(LOS)':^8}  {'UTC(AOS)':^19}  {'UTC(LOS)':^19} "
            f"{'Dur (s)':^8} {'MaxEl':^6}  {'TCA':^8} {'Az(AOS)':^6} {'Az(LOS)':^6} "
            f"{'MinRng':^9}  Flags"
        )
        for sat, intervals in self.entries:
            lines.append("")
            lines.append(
                colored_string(
                    f"{sat.name} (NORAD {sat.norad_id}) - {self._tle_summary(sat)}", "green"
                )
            )
            if not intervals:
                lines.append(colored_string(" No access in window", "yellow"))
                continue
            lines.append(header)
            lines.append("-" * len(header))
            for iv in intervals:
                lines.append(
                    f"{iv.pass_no:^4} {iv.rev_aos:^8} {iv.rev_los:^8}  "
                    f"{iv.aos_utc:{self.TIME_FMT}}  {iv.los_utc:{self.TIME_FMT}} "
                    f"{iv.duration_s:^7.1f} {iv.max_el_deg:^7.1f}  {iv.tca_utc:%H:%M:%S} "
                    f"{iv.aos_az_deg:^7.1f} {iv.los_az_deg:^7.1f} {iv.min_range_km:^8.1f}  "
                    f"{self._flags(iv)}"
                )
        return "\n".join(lines)

    def _write_csv(self, path: Path) -> Path:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self._rows())
        return path

    def _write_json(self, path: Path) -> Path:
        satellites = []
        for sat, intervals in self.entries:
            satellites.append(
                {
                    "norad_id": sat.norad_id,
                    "name": sat.name,
                    "tle_source": sat.tle_source,
                    "tle": list(sat.tle) if sat.tle else None,
                    "tle_epoch_utc": tle_epoch(sat.tle[0]).isoformat() if sat.tle else None,
                    "intervals": [row for row in self._rows() if row["norad_id"] == sat.norad_id],
                }
            )
        station_setting = self.cfg.station
        window_setting = self.cfg.window
        vis_setting = self.cfg.visibility
        tle_setting = self.cfg.tle
        output_setting = self.cfg.output
        document = {
            "meta": {
                "generated_utc": self.generated_utc.isoformat(),
                "simulation-window": asdict(window_setting),
                "station": {
                    "lat": station_setting.lat_deg,
                    "lon": station_setting.lng_deg,
                    "alt": station_setting.altitude_m,
                    "min_elev": station_setting.min_elev_deg,
                    "visibility": asdict(vis_setting),
                },
                "tle-settings": asdict(tle_setting),
                "output-settings": asdict(output_setting),
            },
            "satellites": satellites,
        }
        with open(path, "w") as f:
            json.dump(document, f, indent=2, default=self._json_default)
        return path

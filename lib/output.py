from typing import Any

from lib.systems import *
import os
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class OutputWriter:

    def __init__(self, out_f: str, host: str, port: int):
        self.host = host
        self.port = port

        self.out_folder = "log/"
        self.out_f = Path(self.out_folder + out_f).with_suffix(".txt") #Default output folder

    def write(self, sat_objs: list):
        print("Parent OutputWriter object!")


class stdoutWriter(OutputWriter):

    def write(self, sat_objs: list) -> None:
        '''
        Write the output as STDOUT
        '''

        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                print(str(sat_obj.id) + ": " + sat_obj.color)
            else:
                print(str(sat_obj.id) + ": NOT PASSING")


class FileWriter(OutputWriter):

    def __init__(self, out_f: str, host: str, port: int):
        super().__init__(out_f, host, port)
        self.prepare_outfile() #prepare the output file

    def prepare_outfile(self) -> None:
        '''
        Handles the existence of output folder and cleans the output file
        '''
        if not os.path.isdir(self.out_folder):
            os.makedirs(self.out_folder)
            pass
        open(self.out_f, "w").close() if os.path.isfile(self.out_f) else 0 #Clears the file before writing starts
        

    def write(self, sat_objs: list) -> None:
        '''
        Write the output in a file
        '''
        import datetime
        now = datetime.datetime.now()

        lines = ["[" + now.strftime("%Y-%m-%d %H:%M:%S") + "]\n"]
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                lines.append(str(sat_obj.id) + ": " + sat_obj.color + "\n")
            else:
                lines.append(str(sat_obj.id) + ": NOT PASSING\n")

        with open(Path(self.out_f).with_suffix(".txt"), "a+") as f:
            f.writelines(lines)


class TCPWriter(OutputWriter):

    def __init__(self, out_f: str, host: str, port: int):
        super().__init__(out_f, host, port)
        self.msg = b'' #Empty byte object
        self._this_server = None
        self._this_thread = None
        self._initialize_server()

    def __del__(self):
        '''
        Destructor terminates any ongoing server and threads
        '''
        self.stop_server()

    def _initialize_server(self):
        '''
        Tracks and initializes a HTTP server to update with the most recent message
        '''
        if self._this_server:
            return

        # Make Handler class derived from BaseHTTPRequestHandler for HTTPServer object
        class Handler(BaseHTTPRequestHandler):

            def do_GET(handler_self):
                '''
                Setup the contents for the services using message attribute from TCPWriter
                '''
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", "text/plain; charset=utf-8")
                handler_self.send_header("Content-Length", str(len(self.msg)))
                handler_self.end_headers()
                handler_self.wfile.write(self.msg)

            # Helps in suppressing the logs by returning nothing
            def log_message(self, format: str, *args: Any) -> None:
                #return super().log_message(format, *args)
                return

        #Make the HTTPServer object using the Handler for writing on the host and run the service in a thread as background daemon
        try:
            self._this_server = HTTPServer((self.host, self.port), Handler)
            self._this_thread = threading.Thread(target=self._this_server.serve_forever, daemon=True)
            self._this_thread.start()
        except OSError:
            raise RuntimeError("\033[33m"+self.host+"/"+str(self.port)+" seems unavailable. Try killing the process\033[0m")

    def stop_server(self):
        '''
        Stops a running server and the associated threads
        '''
        if self._this_server and self._this_thread:
            self._this_server.shutdown()
            time.sleep(2)
            self._this_thread.join()
            self._this_server.server_close()

    def write(self, sat_objs: list) -> None:
        '''
        Write the output as a TCP socket client
        '''

        import datetime
        lines = ["[" + str(datetime.datetime.now()) + "]" + "\n"]
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                lines.append(f"{sat_obj.id}: {sat_obj.color}\n")
            else:
                lines.append(f"{sat_obj.id}: NOT PASSING\n")

        msg = "".join(lines).encode("utf-8")
        self.msg = msg

def author(out_type: int, out_f: str = "output", host: str = "127.0.0.1", port: int = 12346) -> OutputWriter:
    '''
    Writes output based on the specified output type.
    '''
    if out_type==1:
        writer = stdoutWriter(out_f, host, port)
    elif out_type==2:
        writer = FileWriter(out_f, host, port)
    elif out_type==3:
        writer = TCPWriter(out_f, host, port)
    else:
        raise ValueError("Invalid output type specified.")

    return writer
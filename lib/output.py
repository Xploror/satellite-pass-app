from lib.systems import *
import os

class OutputWriter:

    def __init__(self, out_f, host, port):
        self.host = host
        self.port = port

        self.out_f = out_f

    def write(self, sat_objs : list):
        print("Parent OutputWriter object!")


class stdoutWriter(OutputWriter):

    def write(self, sat_objs : list) -> None:
        '''
        Write the output as STDOUT
        '''

        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                print(str(sat_obj.id) + ": " + sat_obj.color)
            else:
                print(str(sat_obj.id) + ": NOT PASSING")


class FileWriter(OutputWriter):

    def write(self, sat_objs : list) -> None:
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

        with open(self.out_f + ".txt", "a+") as f:
            f.writelines(lines)


class TCPWriter(OutputWriter):

    def write(self, sat_objs : list) -> None:
        '''
        Write the output as a TCP socket client
        '''
        import socket

        import datetime
        lines = [str(datetime.datetime.now()) + "\n"]
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                lines.append(f"{sat_obj.id}: {sat_obj.color}\n")
            else:
                lines.append(f"{sat_obj.id}: NOT PASSING\n")

        msg = "".join(lines).encode("utf-8")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((self.host, self.port))
                sock.listen()
                c, addr = sock.accept()
                response = (
                                "HTTP/1.1 200 OK\r\n"
                                "Content-Type: text/plain; charset=utf-8\r\n"
                                f"Content-Length: {len(msg)}\r\n"
                                "\r\n"
                            ).encode("utf-8") + msg
                c.sendall(response)
        except OSError:
            print("\033[33mTCP Socket refused to create connection! Please check if address already in use\033[0m", file=sys.stderr)


def author(out_type : int, out_f:str = "output", host:str = "127.0.0.1", port:int = 12345) -> OutputWriter:
    '''
    Writes output based on the specified output type.
    '''
    if out_type==1:
        writer = stdoutWriter(out_f, host, port)
    elif out_type==2:
        writer = FileWriter(out_f, host, port)
        open(out_f+".txt", "w").close() if os.path.isfile(out_f+".txt") else 0
    elif out_type==3:
        writer = TCPWriter(out_f, host, port)
    else:
        raise ValueError("Invalid output type specified.")

    return writer
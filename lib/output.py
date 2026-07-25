from lib.systems import *

class OutputWriter:

    def write(self, sat_objs):
        pass


class stdoutWriter(OutputWriter):

    def write(self, sat_objs:list) -> None:
        for sat_obj in sat_objs:
            if sat_obj.is_visible:
                print(str(sat_obj.id) + ": " + sat_obj.color)
            else:
                print(str(sat_obj.id) + ": NOT PASSING")


class FileWriter(OutputWriter):

    def write(self, sat_objs):
        pass


class TCPWriter(OutputWriter):

    def write(self, sat_objs):
        pass


def write_output(sat_objs, out_type):
    '''
    Writes output based on the specified output type.
    '''
    if out_type==1:
        writer = stdoutWriter()
    elif out_type==2:
        writer = FileWriter()
    elif out_type==3:
        writer = TCPWriter()
    else:
        raise ValueError("Invalid output type specified.")

    writer.write(sat_objs)
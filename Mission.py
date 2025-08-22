from SmfQueue import DataType, SmfQueue
from FrameId import FrameId
from DataCopy import DataCopy # for development test

from time import sleep
import time
from typing import Callable
from syslog import syslog

def debug_msg(msg):
    # type: (str) -> None
    """Print message to console and syslog"""
    print(msg)
    syslog(msg)


"""
======================
@How to define mission

1) Write the command ID and the function name in the '_mission_list' instance variable of the 'ExecuteMission' class.
2) Write the same function name written in '_mission_list' in the 'ExecuteMission' class.
3) Implemental the function actions.

----------------------

@Notes
1) Free to create files, classes, and other functions.
2) 'return' is meaningless
3) The data you want to save in SMF can be saved by executing the following function.
    -> self.smf_data.append(DataType, List[path, ...])
       
      ex) self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png", "./photo/thumb/1.png"])

      NG) self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png"], DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/1.png"])
            -> append same data type to one argument

      NG) self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png"])
          self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/1.png"])
            -> append same data type at once
    

======================
"""


class Mission:
    def request_to_use_smf(self, processer):
        processer._is_smf_copy_allowed = None
        processer._status = processer._SMF_COPY_REQ
        timeout = 60.0
        interval = 0.1
        waited = 0.0
        while processer._is_smf_copy_allowed is None and waited < timeout:
            time.sleep(interval)
            waited += interval
        return processer._is_smf_copy_allowed is True


    def __init__(self, command_id, parameter):
        # type: (int, bytes) -> None
        self._command_id = command_id  # type: int
        self._parameter = parameter  # type: bytes
        self.smf_data = SmfQueue()  # type: SmfQueue
        self._mission_list = {  # type: dict
            0x00: self.example_00, 
            0x01: self.example_01,
        }
    

    def execute_mission(self):
        # type: () -> None
        mission = self._mission_list.get(self._command_id)
        if mission:
            debug_msg("Execute command ID: {0:#02X}".format(self._command_id))
            debug_msg("parameter         : {0:#016X}".format(int.from_bytes(self._parameter)))
            mission()
        else:
            debug_msg("Invalid command ID: {0:#02X}".format(self._command_id))



    # sample code. It waits for the time of the 0th byte of the parameter.
    def example_00(self):
        debug_msg("Start example mission")
        debug_msg("parameter: {0:#016X}".format(int.from_bytes(self._parameter, 'big')))

        time = self._parameter[0]                 # XX __ __ __ __ __ __ __

        debug_msg("count {0} sec".format(time))

        for _ in range(time):
            print(".", end="", flush=True)
            sleep(1)
        print()
        debug_msg("End example mission")


    # sample code. It takes a photo of the number in the lowest 4 bits of the 0th byte of the parameter.       
    def example_01(self):
        debug_msg("Start CAM mission")
        debug_msg("parameter: {0:#016X}".format(int.from_bytes(self._parameter, 'big')))

        number_of_shots = self._parameter[0] & 0X0F              # _X __ __ __ __ __ __ __
        debug_msg("Take {0} photos".format(number_of_shots + 1))

        #definisions
        photo_path_thumb = "./photo/thumb/"
        photo_list = []  # type: list

        # shot
        for i in range(number_of_shots + 1):
            debug_msg("shot photo:" + photo_path_thumb + "00_" + format(i, '02X') + "_00" + ".png")
            photo_list.append(photo_path_thumb + "00_" + format(i, '02X') + "_00" + ".png")
            sleep(1)

        # order to copy to SMF
        debug_msg("order to copy data")
        debug_msg("\t-> data type: {0}".format(DataType.EXAMPLE_SUN_PHOTO_FULL.name))
        for i in range(number_of_shots + 1):
            debug_msg("\t\t-> photo: {0}".format(photo_list[i]))
        self.smf_data.append(DataType.EXAMPLE_SUN_PHOTO_FULL, photo_list)

        debug_msg("End CAM mission")



if __name__ == "__main__":
    command_id = 0x02  # type: int
    parameter = b'\x00\x00\x00\x00\x00\x00\x00\x00'  # type: bytes
    is_do_copy_to_smf = True  # type: bool


    print("\r\nThis is Mission.py run for development test.")
    print("Please run main.py for actual operation.\r\n")

    print("command ID: {0:#02X}".format(command_id))
    print("parameter: {0:#016X}\r\n".format(int.from_bytes(parameter)))

    mission = Mission(command_id, parameter)
    print("_______________________")
    print("_____Start mission_____")
    mission.execute_mission()
    print("_____End mission_______")
    print("_______________________\r\n")

    if is_do_copy_to_smf:
        data_copy = DataCopy()
        data_copy.copy_data()
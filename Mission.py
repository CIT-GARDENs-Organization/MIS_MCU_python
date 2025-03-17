from time import sleep
from typing import Callable

from DataCopy import DataType, SmfData


"""
======================
@How to define function

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
      ex) self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png", "./photo/thumb/1.png"], DataType.EXAMPLE_PHOTO_FULL, ["./photo/full/0.png", "./photo/full/1.png"], )

      NG) self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png"], DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/1.png"])
            -> append same data type to one argument

      NG) self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png"])
          self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/1.png"])
            -> append same data type at once
    

======================
"""


class MissionExecute:
    def __init__(self, command_id: int, parameter: bytes, smf_data: SmfData) -> None:
        self._command_id: int = command_id
        self.parameter: bytes = parameter
        self.smf_data: SmfData = smf_data

        self._mission_list: dict[int, Callable] = {
            0x00: self.example_00, 
            0x01: self.example_01,
            0x02: self.example_02, 
        }
    
    def execute_mission(self) -> None:
        mission = self._mission_list.get(self._command_id)
        if mission:
            print(f"Execute command ID: {self._command_id:#02X}")
            return mission(self.parameter)
        else:
            print(f" Invalid command ID: {self._command_id:#02X}")


    # sample code. It waits for the time of the 0th byte of the parameter.
    def example_00(self, parameter: bytes):
        print("Start example mission", flush=True)
        print(f"parameter: {int.from_bytes(parameter, 'big'):#016X}")

        time = parameter[0]                 # XX __ __ __ __ __ __ __

        print(f"count {time} sec")

        for _ in range(time):
            print(".", end="", flush=True)
            sleep(1)
        print()
        print("End example mission end", flush=True)


    # sample code. It takes a photo of the number in the lowest 4 bits of the 0th byte of the parameter.       
    def example_01(self, parameter: bytes):
        print("Start CAM mission", flush=True)
        print(f"parameter: {int.from_bytes(parameter, 'big'):#016X}")

        number_of_shots = parameter[0] & 0X0F              # _X __ __ __ __ __ __ __
        print(f"Take {number_of_shots} photos")

        #definisions
        photo_path_thumb = "./photo/thumb/"
        photo_list: list = []

        # shot
        for i in range(number_of_shots):
            print(f"shot photo:  {i}.png", flush=True)
            photo_list.append(photo_path_thumb + str(i) + ".png")
            sleep(1)

        # order to copy to SMF
        print("order to copy data")
        print(f"\t-> data type: {DataType.EXAMPLE_PHOTO_THUMB.name}")
        for i in range(number_of_shots):
            print(f"\t\t-> photo: {photo_list[i]}", flush=True)
        self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, photo_list)

        print("End CAM mission")


    # sample code. It wait 0 to 1 byte * msec, then copy one full photo and one thumbnail photo to the SMF.  
    def example_02(self, parameter: bytes):
        print("Start wait and shot", flush=True)
        print(f"parameter: {int.from_bytes(parameter, 'big'):#016X}")

        #definisions
        photo_path_full  = "./photo/full/"
        photo_path_thumb = "./photo/thumb/"
        photo_list_full  = []
        photo_list_thumb = []

        wait_ms = int.from_bytes(parameter[0:1], 'big') / 1000            # XX XX __ __ __ __ __ __
        print(f"Wait {wait_ms} ")
        sleep(wait_ms)

        # shot 
        print(f"shot photo:  0.png", flush=True)
        photo_list_full.append(photo_path_full + "0" + ".png")
        # thumbnailing(0.png)         
        photo_list_thumb.append(photo_path_thumb + "0" + ".png")
        sleep(1)

        # order to copy to SMF
        print("order to copy data")

        print(f"\t-> data type: {DataType.EXAMPLE_PHOTO_FULL.name}")
        print(f"\t\t-> photo: {photo_list_full}", flush=True)
        self.smf_data.append(DataType.EXAMPLE_PHOTO_FULL, photo_list_full)

        print(f"\t-> data type: {DataType.EXAMPLE_PHOTO_THUMB.name}")
        print(f"\t\t-> photo: {photo_list_thumb}", flush=True)
        self.smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, photo_list_thumb)

        print("Start wait and shot")
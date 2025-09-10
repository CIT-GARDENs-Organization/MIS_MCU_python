from SmfQueue import DataType, SmfQueue
from DataCopy import DataCopy # for development test
from Status import DeviceStatus
from time import sleep
from typing import Callable



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
    def __init__(self, command_id: int, parameter: bytes) -> None:
        self._command_id: int = command_id
        self._parameter: bytes = parameter
        self.smf_data: SmfQueue = SmfQueue()
        self.status = DeviceStatus()
        self._mission_list: dict[int, Callable] = {
            0x00: self.example_00, 
            0x01: self.example_01,
            0x02: self.example_02,
        }
    

    def execute_mission(self) -> None:
        mission = self._mission_list.get(self._command_id)
        if mission:
            print(f"Execute command ID: {self._command_id:#02X}")
            print(f"parameter         : {int.from_bytes(self._parameter):#016X}")
            mission()
        else:
            print(f"Invalid command ID: {self._command_id:#02X}")



    # sample code. It waits for the time of the 0th byte of the parameter.
    def example_00(self):
        print("Start example mission", flush=True)
        print(f"parameter: {int.from_bytes(self._parameter, 'big'):#016X}")

        time = self._parameter[0]                 # XX __ __ __ __ __ __ __

        print(f"count {time} sec")

        for _ in range(time):
            print(".", end="", flush=True)
            sleep(1)
        print()
        print("End example mission", flush=True)


    # sample code. It takes a photo of the number in the lowest 4 bits of the 0th byte of the parameter.       
    def example_01(self):
        print("Start CAM mission", flush=True)
        print(f"parameter: {int.from_bytes(self._parameter, 'big'):#016X}")

        number_of_shots = self._parameter[0] & 0X0F              # _X __ __ __ __ __ __ __
        print(f"Take {number_of_shots + 1} photos")

        #definisions
        photo_path_thumb = "./photo/thumb/"
        photo_list: list = []

        # shot
        for i in range(number_of_shots + 1):
            print(f"shot photo:" + photo_path_thumb + "00_" + format(i, '02X') + "_00" + ".png", flush=True)
            photo_list.append(photo_path_thumb + "00_" + format(i, '02X') + "_00" + ".png")
            sleep(1)

        # order to copy to SMF
        print("order to copy data")
        print(f"\t-> data type: {DataType.EXAMPLE_SUN_PHOTO_FULL.name}")
        for i in range(number_of_shots + 1):
            print(f"\t\t-> photo: {photo_list[i]}", flush=True)
        self.smf_data.append(DataType.EXAMPLE_SUN_PHOTO_FULL, photo_list)

        print("End CAM mission")

    # sample code. It waits for the time of the 0th byte of the parameter.
    def example_02(self):
        print("Start example mission", flush=True)
        print(f"parameter: {int.from_bytes(self._parameter, 'big'):#016X}")

        print(f"request to copy data to SMF")


        self.status.request_smf()
        print("waiting for allow...")
        while not self.status.is_can_use_smf():
            sleep(1)
            print(".", end="", flush=True)

        print("\nSMF Access start", flush=True)
        self.status.start_use_smf()
        for _ in range(25):
            print(".", end="", flush=True)
            sleep(1)
        
        print("\nSMF Access end", flush=True)
        self.status.end_use_smf()

        print("End example mission", flush=True)


if __name__ == "__main__":
    command_id: int = 0x02
    parameter: bytes = b'\x00\x00\x00\x00\x00\x00\x00\x00'
    is_do_copy_to_smf: bool = True


    print("\r\nThis is Mission.py run for development test.")
    print("Please run main.py for actual operation.\r\n")

    print(f"command ID: {command_id:#02X}")
    print(f"parameter: {int.from_bytes(parameter):#016X}\r\n")

    mission = Mission(command_id, parameter)
    print("_______________________")
    print("_____Start mission_____")
    mission.execute_mission()
    print("_____End mission_______")
    print("_______________________\r\n")

    if is_do_copy_to_smf:
        data_copy = DataCopy()
        data_copy.copy_data()
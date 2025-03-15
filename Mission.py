from collections import deque
from time import sleep

from DataCopy import DataType


class ExecuteMission():
    def __init__(self, command_id: int, parameter: bytes, smf_data: deque) -> None:
        self.command_id: int = command_id
        self.parameter: bytes = parameter
        self.smf_data: deque = smf_data

        """
        Mission functions names
        """
        self._mission: dict[int, callable] = {
            0x00: self.example_00, 
            0x01: self.example_01,
        }
    
    def execute_mission(self) -> None:
        mission = self._mission.get(self.command_id)
        if mission:
            print(f"Execute command ID: 0x{self.command_id:02X}")
            return mission(self.parameter)
        else:
            print(f" Invalid command ID: 0x{self.command_id:02X}")
    

    """
    How to copy data to SMF

    smf_data.append({DataType.XX: [path]})

    ex) smf_data.append({DataType.PHOTO_THUMB: ["./photo/thumbnail/1.png", "./photo/thumbnail/2.png", "./photo/thumbnail/3.png"]})
    ex) smf_data.append({DataType.PHOTO_THUMB: ["./photo/thumbnail/1.png"], DataType.PHOTO_FULL: ["./photo/full/1.png"]})   

    
    NG) smf_data.append(DataType.PHOTO_FULL: "./photo/full/1.png") 
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                          ^                                        ^ argument must be "dict". '{' and '}' is missing

    NG) smf_data.append({DataType.PHOTO_FULL: "./photo/full/1.png"}) 
                                                 ~~~~~~~~~~~~~~~~~~
                                                 ^                ^  dict value must be "list". '[' and ']' is missing

    NG) smf_data.append({DataType.PHOTO_FULL: "./photo/full/1.png"}, DataType.PHOTO_FULL: ["./photo/full/1.png"])
                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                           ^^^^^^^^^^^^^^^^^^^                       ^ ^^^^^^^^^^^^^^^^^^^          Same data type must be "only one argument"

    NG) smf_data.append({DataType.PHOTO_FULL: "./photo/full/1.png"})
        smf_data.append({DataType.PHOTO_FULL: "./photo/full/2.png"})
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  Same data type must be append to smf_data "at once"

    """ 


    def example_00(self, parameter: bytes):
        print("Mission executing for 15 sec", flush=True, end="")
        for _ in range(15):
            print(".", end="", flush=True)
            sleep(1)
        print()
        
    def example_01(self, parameter: bytes):
        print("Mission executing for 15 sec", flush=True, end="")
        for _ in range(15):
            print(".", end="", flush=True)
            sleep(1)
        self.smf_data.append({DataType.PHOTO_THUMB: ["./photo/thumbnail/1.png", "./photo/thumbnail/2.png", "./photo/thumbnail/3.png"]})
        self.smf_data.append({DataType.PHOTO_FULL: ["./photo/full/1.png"]})

        print("\nMade the data to copy to SMF")

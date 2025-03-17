from ast import Tuple
from collections import deque
from enum import Enum
from typing import List, Tuple

class DataType(Enum):
    """
    Data types and addresses (based on Memory Map)
    Put an underscore at the initial of the size data name
    """
    EXAMPLE_PHOTO_THUMB_SIZE    = 0x00000000
    EXAMPLE_PHOTO_THUMB         = 0x00001000
    EXAMPLE_PHOTO_FULL_SIZE     = 0x00001500
    EXAMPLE_PHOTO_FULL          = 0x00002000
    EXAMPLE_SENSOR_DATA_SIZE    = 0x0000D000
    EXAMPLE_SENSOR_DATA         = 0x0000F000
    EXAMPLE_ERROR_LOG           = 0x00010000
    EXAMPLE_RESERVED            = 0x00020000


class SmfData:
    def __init__(self) -> None:
        self._smf_data: deque[Tuple[DataType, List[str]]] = deque()
    
    def append(self, data_type: DataType, path_list: list) -> None:
        if not isinstance(data_type, DataType):
            raise TypeError("first argument must be 'DataType'")
        if not isinstance(path_list, list):
            raise TypeError("\t->second argument must be 'list'")
        if not all(isinstance(p, str) for p in path_list):
            raise("\t->second argument list elements must be 'str'")
        self._smf_data.append((data_type, path_list), )
    
    def pop(self) -> Tuple[DataType, List[str]]:
        data_type, path_list = self._smf_data.popleft()
        return data_type, path_list

    def is_empty(self) -> bool:
        return not self._smf_data
    


class DataCopy:
    def __init__(self, smf_data: SmfData):
        self._smf_data: SmfData = smf_data

    def copy_data(self) -> None:
        print(f"Start copy to SMF")

        while not self._smf_data.is_empty():
            data_type, path_list = self._smf_data.pop()
            print(f"\t-> Data type: {data_type.name}")
            for path in path_list:
                print(f"\t\t-> {path}")

        print(f"End copy to SMF")
    
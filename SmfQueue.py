from ast import Tuple
from collections import deque
from enum import Enum
from typing import List, Tuple

class DataType(Enum):
#   DATA_TYPE_NAME            = (size_area ,  body_area, data_type_flag)
    EXAMPLE_EARTH_PHOTO_THUMB = (0x00000000, 0x00001000, 0b00010000)
    EXAMPLE_EARTH_PHOTO_FULL  = (0x00000000, 0x00000800, 0b00010001)
    EXAMPLE_SUN_PHOTO_THUMB   = (0x00030000, 0x00003800, 0b00010010)
    EXAMPLE_SUN_PHOTO_FULL    = (0x00002000, 0x00002800, 0b00010011)
    

class SmfQueue:
    """
    Queue of photos to be saved in SMF passed
    from Mission class to DataCopy class
    """
    
    # Singleton pattern
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_smf_data"):
            self._smf_data: deque[Tuple[DataType, List[str]]] = deque()
            self._data_type_flags: List[int] = []
    
    def append(self, data_type: DataType, path_list: List[str]) -> None:
        if not isinstance(data_type, DataType):
            raise TypeError("[WARN] first argument must be 'DataType'")
        if not isinstance(path_list, list):
            raise TypeError("[WARN] second argument must be 'list'")
        if not all(isinstance(path, str) for path in path_list):
            raise TypeError("[WARN] second argument list elements must be 'str'")
        self._smf_data.append((data_type, path_list), )
        self._data_type_flags.append(data_type.value[2])
    
    def pop(self) -> Tuple[DataType, deque[str]]:
        data_type, path_list = self._smf_data.popleft()
        return data_type, path_list

    def is_empty(self) -> bool:
        return not self._smf_data

    def get_data_type_flags(self) -> List[int]:
        return self._data_type_flags
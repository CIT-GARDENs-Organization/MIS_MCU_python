from collections import deque


class DataType:
    """
    Data types and addresses (based on Memory Map) 
    """
    PHOTO_THUMB     = 0x00001000
    PHOTO_FULL      = 0x00002000
    SENSOR_DATA     = 0x0000F000


class DataCopy:

    def __init__(self, smf_data_queue: deque):
        self.smf_data_queue = smf_data_queue

    def copy_data(self) -> None:
        while len(self.smf_data_queue) > 0:
            smf_data_dict: dict = self.smf_data_queue.popleft()
            for key, smf_data_list in smf_data_dict.items():
                print(f"copy to address 0x{key:08X}")
                for smf_data in smf_data_list:
                    print(f"\t -> {smf_data}")

        print("Data copy to SMF END")
    
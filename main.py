from time import sleep
from re import fullmatch
from serial import Serial
from serial import SerialException
import serial.tools.list_ports
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Literal
from select import select
from collections import deque
from gc import collect
import sys

from Mission import ExecuteMission
from DataCopy import DataCopy




USE_LINUX: bool = False
SELF_DEVICE_ID: int = 0x06
SERIAL_PORT: str | None = None


# Command Data class
@dataclass(frozen=True)
class Command:
    frame_id: int
    content: bytes

######################
# ----- Manegrer ----#

class ProcessManeger():
    # My status
    #OFF = b'\x00'
    #BOOTING = b'\x01'  commentout numbers used by BOSS PIC only
    _IDLE =         b'\x02'
    _BUSY=          b'\x03'
    _SMF_COPY_REQ = b'\x04'
    _COPYING =      b'\x05'
    FINISHED =      b'\x06'

    # Definision of "is SMF available" parameter
    _SMF_COPY_ALLOW = 0x00
    _SMF_COPY_DENY = 0x01

    smf_copy_queue = deque()

    def __init__(self):
        self._status = self.__class__._IDLE

    def process_command(self, command: Command) -> Literal["Shutdown"] | None:
        match command.frame_id:
            case FrameId.UPLINK_COMMAND:
                print("\t-> UPLINK_COMMAND")
                self._respond_ack()
                if self._status == self.__class__._IDLE:
                    execute_mission_thread = threading.Thread(target=self._execute_mission, args=(command.content, ), daemon=True)
                    execute_mission_thread.start()

            case FrameId.STATUS_CHECK:
                print("\t-> STATUS_CHECK")
                self._respond_status_check()
            
            case FrameId.IS_SMF_AVAILABLER:
                print("\t-> IS_SMF_AVAILABLER")
                self._respond_ack()
                if command.content[0] == self.__class__._SMF_COPY_ALLOW:
                    print(f"\t\t-> allowed")
                    copy_to_smf_thread = threading.Thread(target=self._copy_to_smf, daemon=True)
                    copy_to_smf_thread.start()
                elif command.content[0] == self.__class__._SMF_COPY_DENY:
                    print(f"\t\t-> denyed")

        return self._status

    def _execute_mission(self, content: bytes) -> None:
        print(f"\nStart Mission thread")
        self._status = self.__class__._BUSY
        command_id = content[0]
        parameter = content[1:]
        exec_mission = ExecuteMission(command_id, parameter, self.__class__.smf_copy_queue)
        exec_mission.execute_mission()
        self._status = self.__class__._SMF_COPY_REQ if len(self.__class__.smf_copy_queue) > 0 else self.__class__.FINISHED
        del exec_mission
        print(f"\nFinished Mission thread")
      
    def _respond_status_check(self) -> None:
        DataHandle.transmit_command(FrameId.MIS_MCU_STATUS, self._status)


    def _copy_to_smf(self) -> None:
        print(f"\nStart Data copy thread")
        self._status = self.__class__._BUSY
        data_copy = DataCopy(self.__class__.smf_copy_queue)
        data_copy.copy_data()     
        self._status = self.FINISHED
        del data_copy
        print(f"\nFinished Data copy thread")


    def _respond_ack(self) -> None:
        DataHandle.transmit_command(FrameId.ACK)

# -----          ----#
######################


#########################
# ----- Data Handle ----#
#                          [[[ Data format ]]]
#
#| Signal ------------------------------------------------------- |
#|         | Data ------------------------------------- |         |
#|         |     | Frame ------------------------------ |         |
#|         |     | Payload ---------------------- |     |         |
#|         |     |           | Command ---------- |     |         |
#| (Noise) | SFD | Device ID | Frame ID | Content | CRC | (Noise) |
#|                                      /         \
#|                                    CMD ID | Parameter



class FrameId:
    #receive
    UPLINK_COMMAND = 0x0
    UPLINK_COMMAND_CONTENT_LENGTH = 9
    STATUS_CHECK = 0x1
    STATUS_CHECK_CONTENT_LENGTH = 0
    IS_SMF_AVAILABLER = 0x2
    IS_SMF_AVAILABLER_CONTENT_LENGTH = 1

    frame_ids_content_length = {UPLINK_COMMAND:     UPLINK_COMMAND_CONTENT_LENGTH, 
                                STATUS_CHECK:       STATUS_CHECK_CONTENT_LENGTH, 
                                IS_SMF_AVAILABLER:  IS_SMF_AVAILABLER_CONTENT_LENGTH, 
                                }

    #transmit
    MIS_MCU_STATUS = 0x1
    ACK = 0xF


    @staticmethod
    def get_frame_id(payload_or_frame: bytes) -> int:
        return (payload_or_frame[0] & 0x0F)

    @classmethod
    def check_frame_id(cls, frame_id: int) -> bool:
        if (frame_id in cls.frame_ids_content_length) == True:
            return True
        else:
            print(f"\t-> Invalid frame ID received")
            print(f"\t\t->received: 0x{frame_id:X}")
            return False    


class DeviceId:
    BOSS_PIC_DEVICE_ID = 0x4

    @staticmethod
    def get_device_id(payload_or_frame: bytes) -> int:
        return (payload_or_frame[0] & 0xF0) >> 4

    @classmethod
    def check_devicve_id(cls, device_id: int) -> bool:
        if device_id == SELF_DEVICE_ID:
            return True
        else:
            print(f"\t-> Invalid device ID received")
            print(f"\t\t-> received: 0x{device_id:X}")
            print(f"\t\t   My device ID: 0x{SELF_DEVICE_ID:X}")
            return False


class DataHandle:
    SFD = 0xAA

    transmit_queue = deque()

    @staticmethod
    def calc_crc(payload: bytes) -> int:
        crc = payload[0]
        for dt in payload[1:]:
            crc ^= dt
        return crc
    
    @classmethod
    def check_crc(cls, frame: bytes) -> bool:
        received_crc = frame[-1]
        payload = DataHandle.get_payload(frame)
        collect_crc = cls.calc_crc(payload)
        if received_crc == collect_crc:
            return True
        else:
            print(f"\t-> CRC error !")
            print(f"\t\t-> received crc: {received_crc:02X}")
            print(f"\t\t   collect crc : {collect_crc:02X}")
            return False

    @staticmethod
    def get_content_length(frame_id: int) -> int:
        return FrameId.frame_ids_content_length.get(frame_id)
    
    @classmethod
    def make_frame(cls, signal: bytes) -> bytes | None:
        index = signal.find(cls.SFD)
        if index == -1:
            print(f"don't find SFD")
            return None
        data = signal[index+1:]
        if data == b'':
            print(f"signal ends with SFD")
            return None
        frame_id = FrameId.get_frame_id(data)
        if FrameId.check_frame_id(frame_id) == False:
            return None
        content_length = cls.get_content_length(frame_id)
        frame = data[:content_length+2] # slice to CRC
        return frame

    def get_payload(frame: bytes) -> bytes: 
        return frame[:-1] # trim CRC

    @staticmethod
    def get_content(frame: bytes) -> bytes:
        return frame[1:-1] # trim Device ID and Frame ID
    
    @classmethod
    def transmit_command(cls, frame_id: int, content: bytes = b'') -> None:
        command: bytes = ((DeviceId.BOSS_PIC_DEVICE_ID << 4) | frame_id).to_bytes(1, 'big') + content
        crc = cls.calc_crc(command)
        data = cls.SFD.to_bytes(1, 'big') + command + crc.to_bytes(1, 'big')
        cls.transmit_queue.append(data)
        
    @classmethod
    def make_command(cls, receive_signal: bytes) -> Command | None:
        frame = cls.make_frame(receive_signal)
        if frame is None:
            return None
        if cls.check_crc(frame) == False:
            return None
        if DeviceId.check_devicve_id(DeviceId.get_device_id(frame)) == False:
            return None
        frame_id = FrameId.get_frame_id(frame)
        if FrameId.check_frame_id(frame_id) == False:
            return None
        command = Command(frame_id, cls.get_content(frame))

        return command

# -----             ----#
#########################


###########################
# ----- Communication ----#

class Communication():
    # Affects CPU utilization (Windows only)
    _READ_SLEEP_SEC = 0.1

    def __init__(self):
        self._ser: serial = None
        self.is_finish: bool = False
        
    def connect_port(self) -> None:
        self._ser = Serial(SERIAL_PORT, baudrate=9600, bytesize=8, stopbits=1, parity="N")

    # for development
    def select_port(self) -> None:
        print('Select using port')
        while True:
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                input('No port found. Press any key to retry.')
                continue
            for i, port in enumerate(ports):
                print(f'{i:X}) {port.device}  ', end='\t')
            print()
            while True:
                choice_str = input('> ')
                if fullmatch(f'^[0-{len(ports)-1}]{{1}}$', choice_str):
                    choice = int(choice_str)
                    try:
                        self._ser = Serial(ports[choice].device, baudrate=9600, bytesize=8, stopbits=1, parity="N")
                        return
                    except SerialException as e:
                        print(e)

    def read(self, read_queue: Queue) -> None:
        while self.is_finish == False:
            r, _, _ = select([self._ser], [], [], None)
            if r:
                read_queue.put(self._ser.read(self._ser.in_waiting))

    def read_debug(self, read_queue: Queue) -> None: # for windows
        while self.is_finish == False:
            if self._ser.in_waiting > 0:
                read_queue.put(self._ser.read(self._ser.in_waiting))
            sleep(self.__class__._READ_SLEEP_SEC)
                
    def transmit(self, data: bytes) -> None:
        self._ser.write(data)

    def close(self) -> None:
        if self._ser:
            self._ser.close()
        
# -----               ----#
###########################


def main():
    print("==================")
    print("= Software start =")
    print("==================")
    WHILE_TRUE_SLEEP_SEC = 1.0

    com = Communication()
    if SERIAL_PORT:
        com.connect_port()
    else:
        com.select_port() # for development

    read_queue = Queue()
    if USE_LINUX:
        read_thread = threading.Thread(target=com.read, args=(read_queue, ), daemon=True)
    else:
        read_thread = threading.Thread(target=com.read_debug, args=(read_queue, ), daemon=True)
    read_thread.start()

    maneger = ProcessManeger()
    
    transmit_queue = DataHandle.transmit_queue

    break_flag = False

    while True:
        if not read_queue.empty():
            receive_data: bytes = read_queue.get()
            print(f"\n===\nData received < <= <== <=== [{int.from_bytes(receive_data):X}]")
            command = DataHandle.make_command(receive_data)
            read_queue.task_done()

            if command:
                if maneger.process_command(command) == ProcessManeger.FINISHED:
                    break_flag = True

        if len(transmit_queue) > 0:
            transmit_data = transmit_queue.popleft()
            print(f"Data transmit ===> ==> => > [{int.from_bytes(transmit_data):X}]")
            com.transmit(transmit_data)
            
        if break_flag == True:
            break

        sleep(WHILE_TRUE_SLEEP_SEC)



    print("software will be quit")
    com.is_finish = True
    read_thread.join()
    com.close()
    


if __name__ == '__main__':
    main()
    collect()
    sys.exit(0)
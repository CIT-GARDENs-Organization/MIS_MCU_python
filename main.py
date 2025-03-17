from time import sleep
from re import fullmatch
from serial import Serial
from serial import SerialException
import serial.tools.list_ports
from threading import Thread
from dataclasses import dataclass
from typing import  Tuple
from select import select
from collections import deque
from gc import collect
import sys

from Mission import MissionExecute
from DataCopy import DataCopy, SmfData


USE_WINDOWS: bool = False
SELF_DEVICE_ID: int = 0x00
SERIAL_PORT: str | None = None



#                          [[[ Data format ]]] (memo)
#
#| Signal ------------------------------------------------------- |
#|         | Data ------------------------------------- |         |
#|         |     | Frame ------------------------------ |         |
#|         |     | Payload ---------------------- |     |         |
#|         |     |           | Command ---------- |     |         |
#| (Noise) | SFD | Device ID | Frame ID | Content | CRC | (Noise) |
#|                                      /         \
#|                                    CMD ID | Parameter

@dataclass(frozen=True)
class Command:
    frame_id: int
    content: bytes

class FrameId:

    #receive
    UPLINK_COMMAND = 0x0
    _UPLINK_COMMAND_CONTENT_LENGTH = 9
    STATUS_CHECK = 0x1
    _STATUS_CHECK_CONTENT_LENGTH = 0
    IS_SMF_AVAILABLER = 0x2
    _IS_SMF_AVAILABLER_CONTENT_LENGTH = 1

    frame_ids_content_length = {UPLINK_COMMAND:     _UPLINK_COMMAND_CONTENT_LENGTH, 
                                STATUS_CHECK:       _STATUS_CHECK_CONTENT_LENGTH, 
                                IS_SMF_AVAILABLER:  _IS_SMF_AVAILABLER_CONTENT_LENGTH, 
                                }

    #transmit
    MIS_MCU_STATUS = 0x1
    ACK = 0xF


    @classmethod
    def check_frame_id(cls, frame_id: int) -> bool:
        if (frame_id in cls.frame_ids_content_length) == True:
            return True
        else:
            print(f"\t-> Invalid frame ID received")
            print(f"\t\t->received: {frame_id:#1X}")
            return False 


class DeviceId:
    BOSS_PIC_DEVICE_ID: int = 0x4
    _DEVICE_ID: int = SELF_DEVICE_ID


    @classmethod
    def check_devicve_id(cls, device_id: int) -> bool:
        if device_id == cls._DEVICE_ID:
            return True
        else:
            print(f"\t-> Invalid device ID received")
            print(f"\t\t-> received: {device_id:#1X}")
            print(f"\t\t   My device ID: {cls._DEVICE_ID:#1X}")
            return False
       

class DataHandler:
    _SFD = 0xAA

    @classmethod
    def make_receive_command(cls, receive_signal: bytes) -> Command | None:
        frame_and_frame_id = cls._get_frame_and_frame_id(receive_signal)
        if not frame_and_frame_id:
            return None
        
        frame, frame_id = frame_and_frame_id
        if not cls._check_crc(frame):
            return None
        
        device_id = (frame[0] & 0xF0) >> 4
        if not DeviceId.check_devicve_id(device_id):
            return None
        
        content = frame[1:-1] # trim Device ID, Frame ID and CRC
        return Command(frame_id, content)
    
    @classmethod
    def make_transmit_command(cls, frame_id: int, content: bytes = b'') -> bytes:
        command: bytes = ((DeviceId.BOSS_PIC_DEVICE_ID << 4) | frame_id).to_bytes(1, 'big') + content
        crc: int = cls._calc_crc(command)
        data: bytes = cls._SFD.to_bytes(1, 'big') + command + crc.to_bytes(1, 'big')
        return data

    @classmethod
    def _get_frame_and_frame_id(cls, signal: bytes) -> Tuple[bytes, int] | None:
        index = signal.find(cls._SFD)
        if index == -1:
            print(f"don't find SFD")
            return None
        
        data = signal[index+1:]
        if data == b'':
            print(f"signal ends with SFD")
            return None
        
        frame_id = data[0] & 0x0F
        content_length = FrameId.frame_ids_content_length.get(frame_id)
        if content_length == None:
            print("\tInvalid frame ID received")
            print(f"\t\t-> received frame ID: {frame_id:#02X}")
            return None
        
        frame = data[:content_length+2] # trim after CRC        
        return frame, frame_id

    @staticmethod
    def _calc_crc(payload: bytes) -> int:
        crc = payload[0]
        for dt in payload[1:]:
            crc ^= dt
        return crc
    
    @classmethod
    def _check_crc(cls, frame: bytes) -> bool:
        received_crc: int       = frame[-1]
        receive_payload: bytes  = frame[:-1]
        collect_crc             = cls._calc_crc(receive_payload)
        if received_crc == collect_crc:
            return True
        else:
            print(f"\t-> CRC error !")
            print(f"\t\t-> received crc: {received_crc:02X}")
            print(f"\t\t   collect crc : {collect_crc:02X}")
            return False
         

class SerialCommunication():
    # Affects CPU utilization (Windows only)
    _READ_SLEEP_SEC = 0.5

    def __init__(self, receive_queue: deque):
        self._ser: Serial
        self._receive_queue: deque = receive_queue
        self.is_finish: bool = False
        
    def connect_port(self) -> None:
        self._ser = Serial(SERIAL_PORT, baudrate=9600, bytesize=8, stopbits=1, parity="N")

    # for development function
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

    def read(self) -> None:
        while self.is_finish == False:
            r, _, _ = select([self._ser], [], [], None)
            if r:
                self._receive_queue.append(self._ser.read(self._ser.in_waiting))

    # for development function
    def read_windows(self) -> None:
        while self.is_finish == False:
            if self._ser.in_waiting > 0:
                self._receive_queue.append(self._ser.read(self._ser.in_waiting))
            sleep(self.__class__._READ_SLEEP_SEC)

    def transmit(self, data: bytes) -> None:
        self._ser.write(data)

    def close(self) -> None:
        if self._ser:
            self._ser.close()
    

class CommandProcesser:
    
    _WHILE_SLEEP_SEC = 0.2

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

    def __init__(self):
        self._is_finished: bool = False
        self._receive_queue: deque = deque()
        self._transmit_data: bytes = b''
        self._com = SerialCommunication(self._receive_queue)
        self._smf_data: SmfData = SmfData()
        self._status: bytes = self.__class__._IDLE

    def run(self):
        if SERIAL_PORT: # for development
            self._com.connect_port()
        else:
            self._com.select_port()
        if USE_WINDOWS: # for development
            read_thread = Thread(target=self._com.read_windows, daemon=True)
        else:
            read_thread = Thread(target=self._com.read, daemon=True)
        read_thread.start()

        while not self._is_finished:
            if len(self._receive_queue) > 0:
                receive_signal: bytes = self._receive_queue.popleft()
                command: Command | None = DataHandler.make_receive_command(receive_signal)

                if command:
                    self._process_command(command)

                    if len(self._transmit_data) > 0:
                        self._com.transmit(self._transmit_data)
                        self._transmit_data = b''

            sleep(self.__class__._WHILE_SLEEP_SEC)
        
        self._com.is_finish = True
        read_thread.join()
        self._com.close()

    def _process_command(self, command: Command) -> None:
        match command.frame_id:
            case FrameId.UPLINK_COMMAND:
                print("\t-> UPLINK_COMMAND")
                self._transmit_data = DataHandler.make_transmit_command(FrameId.ACK)
                if self._status == self.__class__._IDLE:
                    execute_mission_thread = Thread(target=self._execute_mission, args=(command.content, ), daemon=True)
                    execute_mission_thread.start()

            case FrameId.STATUS_CHECK:
                print("\t-> STATUS_CHECK")
                print(f"\t\t-> My status: {int.from_bytes(self._status):02X}")
                self._transmit_data = DataHandler.make_transmit_command(FrameId.MIS_MCU_STATUS, self._status)
                if self._status == self.FINISHED:
                    self._is_finished = True
            
            case FrameId.IS_SMF_AVAILABLER:
                print("\t-> IS_SMF_AVAILABLER")
                self._transmit_data = DataHandler.make_transmit_command(FrameId.ACK)
                if command.content[0] == self.__class__._SMF_COPY_ALLOW:
                    print(f"\t\t-> allowed")
                    copy_to_smf_thread = Thread(target=self._copy_to_smf, daemon=True)
                    copy_to_smf_thread.start()

                elif command.content[0] == self.__class__._SMF_COPY_DENY:
                    print(f"\t\t-> denyed")

    def _execute_mission(self, content: bytes) -> None:
        print(f"\nStart Mission thread")
        command_id = content[0]
        parameter = content[1:]

        self._status = self.__class__._BUSY

        exec_mission = MissionExecute(command_id, parameter, self._smf_data)
        try:
            exec_mission.execute_mission()
        except:
            print("Error in mission thread")

        if self._smf_data.is_empty():
            self._status = self.__class__.FINISHED
        else:
            self._status = self.__class__._SMF_COPY_REQ

        del exec_mission
        print(f"\nFinished Mission thread")
      
    def _copy_to_smf(self) -> None:
        print(f"\nStart data copy thread")

        self._status = self.__class__._BUSY

        data_copy = DataCopy(self._smf_data)
        try:
            data_copy.copy_data()
        except:
            print("Error in data copy thread")   

        self._status = self.FINISHED

        del data_copy
        print(f"\nFinished data copy thread")


if __name__ == '__main__':
    processer = CommandProcesser()
    processer.run()
    collect()
    sys.exit(0)

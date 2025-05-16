from Mission import Mission
from DataCopy import DataCopy
from SmfQueue import SmfQueue

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
import sys


USE_WINDOWS: bool       = False
SELF_DEVICE_ID: int     = 0x06
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


class FrameId():
    #Receives
    UPLINK_COMMAND = 0x0
    _UPLINK_COMMAND_CONTENT_LENGTH = 9
    STATUS_CHECK = 0x1
    _STATUS_CHECK_CONTENT_LENGTH = 0
    IS_SMF_AVAILABLE = 0x2
    _IS_SMF_AVAILABLE_CONTENT_LENGTH = 1
    frame_ids_content_length = {UPLINK_COMMAND:     _UPLINK_COMMAND_CONTENT_LENGTH, 
                                STATUS_CHECK:       _STATUS_CHECK_CONTENT_LENGTH, 
                                IS_SMF_AVAILABLE:  _IS_SMF_AVAILABLE_CONTENT_LENGTH, 
                                }

    #Transmits
    MIS_MCU_STATUS = 0x3
    ACK = 0xF
       

class DataHandler:
    """
    The class role is Converting Signals and Commands
    """
    _SFD = 0xAA
    _BOSS_PIC_DEVICE_ID: int = 0x5

    @classmethod
    def make_receive_command(cls, receive_signal: bytes) -> Command | None:
        frame_and_frame_id = cls._get_frame_and_frame_id(receive_signal)
        if not frame_and_frame_id:
            return None
        
        frame, frame_id = frame_and_frame_id
        if not cls._check_crc(frame):
            return None
        
        device_id = (frame[0] & 0xF0) >> 4
        if not cls._check_devicve_id(device_id):
            return None
        
        content = frame[1:-1] # trim Device ID, Frame ID and CRC
        return Command(frame_id, content)
    
    @classmethod
    def make_transmit_signal(cls, command: Command) -> bytes:
        command: bytes = ((cls._BOSS_PIC_DEVICE_ID << 4) | command.frame_id).to_bytes(1, 'big') + command.content
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

    @classmethod
    def _check_devicve_id(cls, device_id: int) -> bool:
        if device_id == SELF_DEVICE_ID:
            return True
        else:
            print(f"\t-> Invalid device ID received")
            print(f"\t\t-> received: {device_id:#1X}")
            print(f"\t\t   My device ID: {SELF_DEVICE_ID:#1X}")
            return False


class SerialCommunication:
    """
    Receive and transmit signal via UART
    """
    # Affects CPU utilization (Windows only)
    _READ_SLEEP_SEC = 0.5

    def __init__(self):
        self._ser: Serial
        self.receive_queue: deque[bytes] = deque()
        self.is_finished: bool = False # this flag operated from MainProcesser class
        
    def connect_port(self) -> None:
        if SERIAL_PORT:
            self._ser = Serial(SERIAL_PORT, baudrate=9600, bytesize=8, stopbits=1, parity="N")

        else: # for development
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
        if not USE_WINDOWS:
            while self.is_finished == False:
                r, _, _ = select([self._ser], [], [], None) # `select` is only available in Linux and mac environments
                if r:
                    sleep(0.2) # wait for receive all data
                    self.receive_queue.append(self._ser.read(self._ser.in_waiting))

        else: # for Windows environment
            while self.is_finished == False:
                if self._ser.in_waiting > 0:
                    sleep(0.2) # wait for receive all data
                    self.receive_queue.append(self._ser.read(self._ser.in_waiting))
                sleep(self.__class__._READ_SLEEP_SEC)


    def transmit(self, data: bytes) -> None:
        self._ser.write(data)

    def close(self) -> None:
        if self._ser:
            self._ser.close()


class MainProcesser:
    _LOOP_SLEEP_SEC = 0.2

#   _OFF          = b'\x00'
#   _BOOTING      = b'\x01'  commentout numbers used by BOSS PIC only
    _IDLE         = b'\x02'
    _BUSY         = b'\x03'
    _SMF_COPY_REQ = b'\x04'
    _COPYING      = b'\x05'
    _FINISHED     = b'\x06'

    # Definision of `is SMF available` parameter
    _SMF_COPY_ALLOW = 0x00
    _SMF_COPY_DENY = 0x01

    def __init__(self):
        self._is_finished: bool = False
        self._com = SerialCommunication()
        self._status: bytes = self.__class__._IDLE


    def run(self):
        self._com.connect_port()
        read_thread = Thread(target=self._com.read, daemon=True)
        read_thread.start()

        # Main loop
        while True:
            if len(self._com.receive_queue) > 0:
                receive_signal: bytes = self._com.receive_queue.popleft()
                command = DataHandler.make_receive_command(receive_signal)

                if command:
                    self._handle_command(command)
                    if self._is_finished:
                        break

                else:
                    continue
                
            sleep(self.__class__._LOOP_SLEEP_SEC)
        
        self._com.is_finished = True
        read_thread.join()
        self._com.close()


    def _handle_command(self, command: Command) -> None:
        if command.frame_id == FrameId.UPLINK_COMMAND:
            self._handle_uplink_command_frame(command.content)
        elif command.frame_id == FrameId.STATUS_CHECK:
            self._handle_status_check_frame(command.content)
        elif command.frame_id == FrameId.IS_SMF_AVAILABLE:
            self._handle_is_smf_available_frame(command.content)
        else:
            print(f"Frame : Invalid frame ID received")
            print(f"\t-> received: {command.frame_id:#02X}")


    def _handle_uplink_command_frame(self, content: bytes) -> None:
        print(f"Frame : Uplink command")

        self._transmit_ack()
        if self._status == self.__class__._BUSY:
            print(f"\t-> MIS MCU is busy. cant execute this mission")

        elif self._status == self.__class__._IDLE:
            self._status = self.__class__._BUSY

            command_id: int = content[0]
            parameter: bytes = content[1:]

            mission_thread = Thread(target=self._uplink_command_frame_thread, 
                                    args=(command_id, parameter, ), 
                                    daemon=True, 
                                    name=f"Mission thread{command_id:#02X}")
            
            try:
                mission_thread.start()
            except Exception as e:
                print(f"Error in mission thread: {e}")

    def _uplink_command_frame_thread(self, command_id: int, parameter: bytes) -> None:
        print("\r\n________________________________")
        print("_____ Start mission thread _____\r\n")
        mission = Mission(command_id, parameter)
        mission.execute_mission() # do anything mission
        if SmfQueue().is_empty():
            self._status = self.__class__._FINISHED
        else:
            self._status = self.__class__._SMF_COPY_REQ
        print("\r\n______ End mission thread ______")   
        print("________________________________\r\n")



    def _handle_status_check_frame(self, content: bytes) -> None:
        print(f"Frame : STATUS_CHECK")

        print(f"\t-> My status: {int.from_bytes(self._status):#02X}")
        self._transmit_status()
        if self._status == self.__class__._FINISHED:
            print(f"\t\t-> Finished")
            self._is_finished = True


    def _handle_is_smf_available_frame(self, content: bytes) -> None:
        print(f"Frame : IS SMF AVAILABLE")
        self._transmit_ack()

        # Allowed
        if content[0] == self.__class__._SMF_COPY_ALLOW:
            print("\t\t-> allowd")

            self._status = self.__class__._COPYING
            data_copy_thread = Thread(target=self._is_smf_available_frame_thread, 
                                      daemon=True, 
                                      name="Data copy thread")
            data_copy_thread.start()
  
        # Denyed
        elif content[0] == self.__class__._SMF_COPY_DENY:
            print("\t\t-> denyed")
            print("\t\t   retry next status check time")


    def _is_smf_available_frame_thread(self) -> None:
        data_copy = DataCopy()
        data_copy.copy_data()
        self._status = self.__class__._FINISHED


    def _transmit_ack(self):
        command = Command(FrameId.ACK, b'')
        data = DataHandler.make_transmit_signal(command)
        self._com.transmit(data)
    

    def _transmit_status(self):
        if self._status != self.__class__._FINISHED:
            content = self._status + b'\x00\x00\x00'
            command = Command(FrameId.MIS_MCU_STATUS, content)
            data = DataHandler.make_transmit_signal(command)
        else: # finished
            flags = SmfQueue().get_data_type_flags()
            if len(flags) > 3:
                print(f"Data type flags is too long, data is copied to SMF but not to SCF")
            padded_flags = (flags[:3] + [0x00] * (3 - len(flags)))
            content = self._status + bytes(padded_flags)
            command = Command(FrameId.MIS_MCU_STATUS, content)
            data = DataHandler.make_transmit_signal(command)      

        self._com.transmit(data)



if __name__ == '__main__':
    processer = MainProcesser()
    processer.run()
    sys.exit(0)

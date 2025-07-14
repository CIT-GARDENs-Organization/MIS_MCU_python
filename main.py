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
import os
from syslog import syslog

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
            syslog(f"SFD not found in signal")
            return None
        
        data = signal[index+1:]
        if data == b'':
            print(f"signal ends with SFD")
            syslog(f"Signal ends with SFD")
            return None
        
        frame_id = data[0] & 0x0F
        content_length = FrameId.frame_ids_content_length.get(frame_id)
        if content_length == None:
            print("\tInvalid frame ID received")
            print(f"\t\t-> received frame ID: {frame_id:#02X}")
            syslog(f"Invalid frame ID received: {frame_id:#02X}")
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
            syslog(f"CRC error - received: {received_crc:02X}, expected: {collect_crc:02X}")
            return False

    @classmethod
    def _check_devicve_id(cls, device_id: int) -> bool:
        if device_id == SELF_DEVICE_ID:
            return True
        else:
            print(f"\t-> Invalid device ID received")
            print(f"\t\t-> received: {device_id:#1X}")
            print(f"\t\t   My device ID: {SELF_DEVICE_ID:#1X}")
            syslog(f"Invalid device ID received: {device_id:#1X}, expected: {SELF_DEVICE_ID:#1X}")
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
            print(f"Connecting to specified port: {SERIAL_PORT}")
            syslog(f"Connecting to specified port: {SERIAL_PORT}")
            self._ser = Serial(SERIAL_PORT, baudrate=9600, bytesize=8, stopbits=1, parity="N")
            print(f"Successfully connected to {SERIAL_PORT}")
            syslog(f"Successfully connected to {SERIAL_PORT}")

        else: # for development
            print('Select using port')
            syslog('Select using port')
            while True:
                ports = list(serial.tools.list_ports.comports())
                if not ports:
                    print('No port found. Press any key to retry.')
                    syslog('No port found. Press any key to retry.')
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
                            print(f"Attempting to connect to {ports[choice].device}")
                            syslog(f"Attempting to connect to {ports[choice].device}")
                            self._ser = Serial(ports[choice].device, baudrate=9600, bytesize=8, stopbits=1, parity="N")
                            print(f"Successfully connected to {ports[choice].device}")
                            syslog(f"Successfully connected to {ports[choice].device}")
                            return
                        except SerialException as e:
                            print(e)
                            syslog(f"Serial connection error: {e}")


    def read(self) -> None:
        print("Serial read thread started")
        syslog("Serial read thread started")
        if not USE_WINDOWS:
            while True:
                r, _, _ = select([self._ser], [], [], None) # `select` is only available in Linux and mac environments
                if r:
                    sleep(0.2) # wait for receive all data
                    data = self._ser.read(self._ser.in_waiting)
                    if data:
                        print(f"Serial data received: {len(data)} bytes")
                        syslog(f"Serial data received: {len(data)} bytes")
                        self.receive_queue.append(data)

        else: # for Windows environment
            while True:
                if self._ser.in_waiting > 0:
                    sleep(0.2) # wait for receive all data
                    data = self._ser.read(self._ser.in_waiting)
                    if data:
                        print(f"Serial data received: {len(data)} bytes")
                        syslog(f"Serial data received: {len(data)} bytes")
                        self.receive_queue.append(data)
                sleep(self.__class__._READ_SLEEP_SEC)


    def transmit(self, data: bytes) -> None:
        print(f"Transmitting data: {len(data)} bytes - {data.hex()}")
        syslog(f"Transmitting data: {len(data)} bytes - {data.hex()}")
        self._ser.write(data)

    def close(self) -> None:
        if self._ser:
            print("Closing serial port")
            syslog("Closing serial port")
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
    _SMF_COPY_ALLOW = 0x01
    _SMF_COPY_DENY = 0x00

    def __init__(self):
        self._com = SerialCommunication()
        self._status: bytes = self.__class__._IDLE


    def run(self):
        print("Starting MainProcesser")
        syslog("Starting MainProcesser")
        self._com.connect_port()
        read_thread = Thread(target=self._com.read, daemon=True)
        read_thread.start()
        print("Serial read thread started")
        syslog("Serial read thread started")

        # Main loop
        print("Entering main loop")
        syslog("Entering main loop")
        while True:
            if len(self._com.receive_queue) > 0:
                receive_signal: bytes = self._com.receive_queue.popleft()
                print(f"Received size: {len(receive_signal)},  signal: {receive_signal.hex()}")
                syslog(f"Received size: {len(receive_signal)},  signal: {receive_signal.hex()}")
                command = DataHandler.make_receive_command(receive_signal)

                if command:
                    self._handle_command(command)
                    if self._is_finished:
                        break

                else:
                    continue
                
            sleep(self.__class__._LOOP_SLEEP_SEC)

        print("Main processer finish")
        syslog("Main processer finish")
        return


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
            syslog(f"Invalid frame ID received: {command.frame_id:#02X}")


    def _handle_uplink_command_frame(self, content: bytes) -> None:
        print(f"Frame : Uplink command")
        syslog(f"Frame : Uplink command")

        self._transmit_ack()
        if self._status == self.__class__._BUSY:
            print(f"\t-> MIS MCU is busy. cant execute this mission")
            syslog(f"MIS MCU is busy. cant execute this mission")

        elif self._status == self.__class__._IDLE:
            self._status = self.__class__._BUSY
            print(f"\t-> Status changed to BUSY")
            syslog(f"Status changed to BUSY")

            command_id: int = content[0]
            parameter: bytes = content[1:]
            print(f"\t-> Command ID: {command_id:#02X}, Parameter: {parameter.hex()}")
            syslog(f"Command ID: {command_id:#02X}, Parameter: {parameter.hex()}")

            mission_thread = Thread(target=self._uplink_command_frame_thread, 
                                    args=(command_id, parameter, ), 
                                    daemon=True, 
                                    name=f"Mission thread{command_id:#02X}")
            mission_thread.start()
            print(f"\t-> Mission thread started")
            syslog(f"Mission thread started")

    def _uplink_command_frame_thread(self, command_id: int, parameter: bytes) -> None:
        print("\r\n________________________________")
        print("_____ Start mission thread _____\r\n")
        syslog("Start mission thread")
        mission = Mission(command_id, parameter)
        try:
            mission.execute_mission() # do anything mission
            print("Mission executed successfully")
            syslog("Mission executed successfully")
        except Exception as e:
            print(f"Error in mission thread: {e}")
            syslog(f"Error in mission thread: {e}")
        finally:
            if SmfQueue().is_empty():
                self._status = self.__class__._FINISHED
                print("No SMF data to copy, status set to FINISHED")
                syslog("No SMF data to copy, status set to FINISHED")
            else:
                self._status = self.__class__._SMF_COPY_REQ
                print("SMF data available, status set to SMF_COPY_REQ")
                syslog("SMF data available, status set to SMF_COPY_REQ")
        print("\r\n______ End mission thread ______")   
        print("________________________________\r\n")
        syslog("End mission thread")



    def _handle_status_check_frame(self, content: bytes) -> None:
        print(f"Frame : STATUS_CHECK")
        syslog(f"Frame : STATUS_CHECK")

        print(f"\t-> My status: {int.from_bytes(self._status):#02X}")
        syslog(f"Current status: {int.from_bytes(self._status):#02X}")
        self._transmit_status()
        if self._status == self.__class__._FINISHED:
            print(f"\t\t-> Finished")
            syslog(f"Status is FINISHED, setting finish flag")
            self._is_finished = True


    def _handle_is_smf_available_frame(self, content: bytes) -> None:
        print(f"Frame : IS SMF AVAILABLE")
        syslog(f"Frame : IS SMF AVAILABLE")
        self._transmit_ack()

        # Allowed
        if content[0] == self.__class__._SMF_COPY_ALLOW:
            print("\t\t-> allowd")
            syslog("SMF copy allowed, starting data copy thread")

            self._status = self.__class__._COPYING
            data_copy_thread = Thread(target=self._is_smf_available_frame_thread, 
                                      daemon=True, 
                                      name="Data copy thread")
            data_copy_thread.start()
            print("\t\t-> Data copy thread started")
            syslog("Data copy thread started")
  
        # Denyed
        elif content[0] == self.__class__._SMF_COPY_DENY:
            print("\t\t-> denyed")
            print("\t\t   retry next status check time")
            syslog("SMF copy denied, will retry next status check time")


    def _is_smf_available_frame_thread(self) -> None:
        print("Starting data copy process")
        syslog("Starting data copy process")
        data_copy = DataCopy()
        try:
            data_copy.copy_data()
            print("Data copy completed successfully")
            syslog("Data copy completed successfully")
        except Exception as e:
            print(f"Error in data copy thread: {e}")
            syslog(f"Error in data copy thread: {e}")
        finally:
            self._status = self.__class__._FINISHED
            print("Data copy thread finished, status set to FINISHED")
            syslog("Data copy thread finished, status set to FINISHED")

    def _transmit_ack(self):
        print("Transmitting ACK")
        syslog("Transmitting ACK")
        command = Command(FrameId.ACK, b'')
        data = DataHandler.make_transmit_signal(command)
        self._com.transmit(data)
    

    def _transmit_status(self):
        print("Transmitting status")
        syslog("Transmitting status")
        if self._status != self.__class__._FINISHED:
            content = self._status + b'\x00\x00\x00'
            command = Command(FrameId.MIS_MCU_STATUS, content)
            data = DataHandler.make_transmit_signal(command)
        else: # finished
            flags = SmfQueue().get_data_type_flags()
            if len(flags) > 3:
                print(f"Data type flags is too long, data is copied to SMF but not to SCF")
                syslog(f"Data type flags is too long, data is copied to SMF but not to SCF")
            padded_flags = (flags[:3] + [0x00] * (3 - len(flags)))
            content = self._status + bytes(padded_flags)
            command = Command(FrameId.MIS_MCU_STATUS, content)
            data = DataHandler.make_transmit_signal(command)
            print(f"Status transmitted with flags: {flags}")
            syslog(f"Status transmitted with flags: {flags}")

        self._com.transmit(data)



if __name__ == '__main__':
    print("Program started")
    syslog("Program started")
    processer = MainProcesser()
    processer.run()
    print("Program finished")
    syslog("Program finished")
    os.system("sudo shutdown -h now")

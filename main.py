from MySerial import SerialCommunication
from Mission import Mission
from DataCopy import DataCopy
from SmfQueue import SmfQueue
from FrameId import FrameId
from syslog import syslog
from time import sleep
from threading import Thread
from typing import Tuple, Optional
import os

SELF_DEVICE_ID = 0x06  # type: int

def debug_msg(msg):
    # type: (str) -> None
    """Print message to console and syslog"""
    print(msg)
    syslog(msg)



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

class Command:
    def __init__(self, frame_id, content):
        # type: (int, bytes) -> None
        self.frame_id = frame_id  # type: int
        self.content = content  # type: bytes


class DataHandler:
    """
    The class role is Converting Signals and Commands
    """
    _SFD = 0xAA
    _BOSS_PIC_DEVICE_ID = 0x5  # type: int

    @classmethod
    def make_receive_command(cls, receive_signal):
        # type: (bytes) -> Optional[Command]
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
    def make_transmit_signal(cls, command):
        # type: (Command) -> bytes
        command_bytes = ((cls._BOSS_PIC_DEVICE_ID << 4) | command.frame_id).to_bytes(1, 'big') + command.content  # type: bytes
        crc = cls._calc_crc(command_bytes)  # type: int
        data = cls._SFD.to_bytes(1, 'big') + command_bytes + crc.to_bytes(1, 'big')  # type: bytes
        return data

    @classmethod
    def _get_frame_and_frame_id(cls, signal):
        # type: (bytes) -> Optional[Tuple[bytes, int]]
        index = signal.find(cls._SFD)
        if index == -1:
            debug_msg("don't find SFD")
            debug_msg("SFD not found in signal")
            return None
        
        data = signal[index+1:]
        if data == b'':
            debug_msg("signal ends with SFD")
            debug_msg("Signal ends with SFD")
            return None
        
        frame_id = data[0] & 0x0F
        content_length = FrameId.frame_ids_content_length.get(frame_id)
        if content_length == None:
            debug_msg("\tInvalid frame ID received")
            debug_msg("\t\t-> received frame ID: {0:#02X}".format(frame_id))
            debug_msg("Invalid frame ID received: {0:#02X}".format(frame_id))
            return None
        
        frame = data[:content_length+2] # trim after CRC        
        return frame, frame_id

    @staticmethod
    def _calc_crc(payload):
        # type: (bytes) -> int
        crc = payload[0]
        for dt in payload[1:]:
            crc ^= dt
        return crc
    
    @classmethod
    def _check_crc(cls, frame):
        # type: (bytes) -> bool
        received_crc = frame[-1]  # type: int
        receive_payload = frame[:-1]  # type: bytes
        collect_crc = cls._calc_crc(receive_payload)
        if received_crc == collect_crc:
            return True
        else:
            debug_msg("\t-> CRC error !")
            debug_msg("\t\t-> received crc: {0:02X}".format(received_crc))
            debug_msg("\t\t   collect crc : {0:02X}".format(collect_crc))
            debug_msg("CRC error - received: {0:02X}, expected: {1:02X}".format(received_crc, collect_crc))
            return False

    @classmethod
    def _check_devicve_id(cls, device_id):
        # type: (int) -> bool
        if device_id == SELF_DEVICE_ID:
            return True
        else:
            debug_msg("\t-> Invalid device ID received")
            debug_msg("\t\t-> received: {0:#1X}".format(device_id))
            debug_msg("\t\t   My device ID: {0:#1X}".format(SELF_DEVICE_ID))
            debug_msg("Invalid device ID received: {0:#1X}, expected: {1:#1X}".format(device_id, SELF_DEVICE_ID))
            return False


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
        self._status = self.__class__._IDLE  # type: bytes
        self._is_finished = False  # type: bool
        self._is_smf_copy_allowed = None  # type: Optional[bool]


    def run(self):
        # type: () -> None
        debug_msg("Starting MainProcesser")
        self._com.connect_port()
        read_thread = Thread(target=self._com.read, daemon=True)
        read_thread.start()
        debug_msg("Serial read thread started")

        # Main loop
        debug_msg("Entering main loop")
        while True:
            if len(self._com.receive_queue) > 0:
                receive_signal = self._com.receive_queue.popleft()  # type: bytes
                debug_msg("Received size: {0},  signal: {1}".format(len(receive_signal), receive_signal.hex()))
                command = DataHandler.make_receive_command(receive_signal)

                if command:
                    self._handle_command(command)
                    if self._is_finished:
                        break

                else:
                    continue
                
            sleep(self.__class__._LOOP_SLEEP_SEC)

        debug_msg("Main processer finish")
        return


    def _handle_command(self, command):
        # type: (Command) -> None
        if command.frame_id == FrameId.UPLINK_COMMAND:
            self._handle_uplink_command_frame(command.content)
        elif command.frame_id == FrameId.STATUS_CHECK:
            self._handle_status_check_frame(command.content)
        elif command.frame_id == FrameId.IS_SMF_AVAILABLE:
            self._handle_is_smf_available_frame(command.content)
        else:
            debug_msg("Frame : Invalid frame ID received")
            debug_msg("\t-> received: {0:#02X}".format(command.frame_id))
            debug_msg("Invalid frame ID received: {0:#02X}".format(command.frame_id))


    def _handle_uplink_command_frame(self, content):
        # type: (bytes) -> None
        debug_msg("Frame : Uplink command")

        self._transmit_ack()
        if self._status == self.__class__._BUSY:
            debug_msg("\t-> MIS MCU is busy. cant execute this mission")
            debug_msg("MIS MCU is busy. cant execute this mission")

        elif self._status == self.__class__._IDLE:
            self._status = self.__class__._BUSY
            debug_msg("\t-> Status changed to BUSY")
            debug_msg("Status changed to BUSY")

            command_id = content[0]  # type: int
            parameter = content[1:]  # type: bytes
            debug_msg("\t-> Command ID: {0:#02X}, Parameter: {1}".format(command_id, parameter.hex()))
            debug_msg("Command ID: {0:#02X}, Parameter: {1}".format(command_id, parameter.hex()))

            mission_thread = Thread(target=self._uplink_command_frame_thread, 
                                    args=(command_id, parameter, ), 
                                    daemon=True, 
                                    name="Mission thread{0:#02X}".format(command_id))
            mission_thread.start()
            debug_msg("\t-> Mission thread started")
            debug_msg("Mission thread started")

    def _uplink_command_frame_thread(self, command_id, parameter):
        # type: (int, bytes) -> None
        print("\r\n________________________________")
        print("_____ Start mission thread _____\r\n")
        debug_msg("Start mission thread")
        mission = Mission(command_id, parameter)
        try:
            mission.execute_mission() # do anything mission
            debug_msg("Mission executed successfully")
        except Exception as e:
            debug_msg("Error in mission thread: {0}".format(str(e)))
        finally:
            if SmfQueue().is_empty():
                self._status = self.__class__._FINISHED
                debug_msg("No SMF data to copy, status set to FINISHED")
            else:
                self._status = self.__class__._SMF_COPY_REQ
                debug_msg("SMF data available, status set to SMF_COPY_REQ")
        print("\r\n______ End mission thread ______")   
        print("________________________________\r\n")
        debug_msg("End mission thread")



    def _handle_status_check_frame(self, content):
        # type: (bytes) -> None
        debug_msg("Frame : STATUS_CHECK")

        debug_msg("\t-> My status: {0:#02X}".format(int.from_bytes(self._status, "big")))
        debug_msg("Current status: {0:#02X}".format(int.from_bytes(self._status, "big")))
        self._transmit_status()
        if self._status == self.__class__._FINISHED:
            debug_msg("\t\t-> Finished")
            debug_msg("Status is FINISHED, setting finish flag")
            self._is_finished = True


    def _handle_is_smf_available_frame(self, content):
        # type: (bytes) -> None
        debug_msg("Frame : IS SMF AVAILABLE")
        self._transmit_ack()

        # Allowed
        if content[0] == self.__class__._SMF_COPY_ALLOW:
            debug_msg("\t\t-> allowd")
            debug_msg("SMF copy allowed, starting data copy thread")
            self._is_smf_copy_allowed = True
            self._status = self.__class__._COPYING
            data_copy_thread = Thread(target=self._is_smf_available_frame_thread, 
                                      daemon=True, 
                                      name="Data copy thread")
            data_copy_thread.start()
            debug_msg("\t\t-> Data copy thread started")
            debug_msg("Data copy thread started")
        # Denyed
        elif content[0] == self.__class__._SMF_COPY_DENY:
            debug_msg("\t\t-> denyed")
            debug_msg("\t\t   retry next status check time")
            debug_msg("SMF copy denied, will retry next status check time")
            self._is_smf_copy_allowed = False


    def _is_smf_available_frame_thread(self):
        # type: () -> None
        debug_msg("Starting data copy process")
        data_copy = DataCopy()
        try:
            data_copy.copy_data()
            debug_msg("Data copy completed successfully")
        except Exception as e:
            debug_msg("Error in data copy thread: {0}".format(str(e)))
        finally:
            self._status = self.__class__._FINISHED
            debug_msg("Data copy thread finished, status set to FINISHED")

    def _transmit_ack(self):
        # type: () -> None
        debug_msg("Transmitting ACK")
        command = Command(FrameId.ACK, b'')
        data = DataHandler.make_transmit_signal(command)
        self._com.transmit(data)
    

    def _transmit_status(self):
        # type: () -> None
        debug_msg("Transmitting status")
        if self._status != self.__class__._FINISHED:
            content = self._status + b'\x00\x00\x00'
            command = Command(FrameId.MIS_MCU_STATUS, content)
            data = DataHandler.make_transmit_signal(command)
        else: # finished
            flags = SmfQueue().get_data_type_flags()
            if len(flags) > 3:
                debug_msg("Data type flags is too long, data is copied to SMF but not to SCF")
            padded_flags = (flags[:3] + [0x00] * (3 - len(flags)))
            content = self._status + bytes(padded_flags)
            command = Command(FrameId.MIS_MCU_STATUS, content)
            data = DataHandler.make_transmit_signal(command)
            debug_msg("Status transmitted with flags: {0}".format(flags))

        self._com.transmit(data)



if __name__ == '__main__':
    debug_msg("Program started")
    processer = MainProcesser()
    processer.run()
    debug_msg("Program finished")
    os.system("sudo shutdown -h now")

from re import fullmatch
from serial import Serial
from serial import SerialException
import serial.tools.list_ports
from syslog import syslog
from typing import Optional
from select import select
from collections import deque
from time import sleep

USE_WINDOWS = False  # type: bool
SERIAL_PORT = None  # type: Optional[str]

def debug_msg(msg):
    # type: (str) -> None
    """Print message to console and syslog"""
    print(msg)
    syslog(msg)

class SerialCommunication:
    """
    Receive and transmit signal via UART
    """
    
    # Affects CPU utilization (Windows only)
    _READ_SLEEP_SEC = 0.5

    # Singleton pattern
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SerialCommunication, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._ser = None  # type: Optional[Serial]
        self.receive_queue = deque()  # type: deque
        self.is_finished = False  # type: bool
        
    def connect_port(self):
        # type: () -> None
        if SERIAL_PORT:
            debug_msg("Connecting to specified port: {0}".format(SERIAL_PORT))
            self._ser = Serial(SERIAL_PORT, baudrate=9600, bytesize=8, stopbits=1, parity="N")
            debug_msg("Successfully connected to {0}".format(SERIAL_PORT))

        else: # for development
            debug_msg('Select using port')
            while True:
                ports = list(serial.tools.list_ports.comports())
                if not ports:
                    debug_msg('No port found. Press any key to retry.')
                    input('No port found. Press any key to retry.')
                    continue
                for i, port in enumerate(ports):
                    print('{0:X}) {1}  '.format(i, port.device), end='\t')
                print()
                while True:
                    choice_str = input('> ')
                    if fullmatch('^[0-{0}]{{1}}$'.format(len(ports)-1), choice_str):
                        choice = int(choice_str)
                        try:
                            debug_msg("Attempting to connect to {0}".format(ports[choice].device))
                            self._ser = Serial(ports[choice].device, baudrate=9600, bytesize=8, stopbits=1, parity="N")
                            debug_msg("Successfully connected to {0}".format(ports[choice].device))
                            return
                        except SerialException as e:
                            print(str(e))
                            debug_msg("Serial connection error: {0}".format(str(e)))


    def read(self):
        # type: () -> None
        debug_msg("Serial read thread started")
        if not USE_WINDOWS:
            while True:
                r, _, _ = select([self._ser], [], [], None) # `select` is only available in Linux and mac environments
                if r:
                    sleep(0.2) # wait for receive all data
                    data = self._ser.read(self._ser.in_waiting)
                    if data:
                        debug_msg("Serial data received: {0} bytes".format(len(data)))
                        self.receive_queue.append(data)

        else: # for Windows environment
            while True:
                if self._ser.in_waiting > 0:
                    sleep(0.2) # wait for receive all data
                    data = self._ser.read(self._ser.in_waiting)
                    if data:
                        debug_msg("Serial data received: {0} bytes".format(len(data)))
                        self.receive_queue.append(data)
                sleep(self.__class__._READ_SLEEP_SEC)


    def transmit(self, data):
        # type: (bytes) -> None
        debug_msg("Transmitting data: {0} bytes - {1}".format(len(data), data.hex()))
        self._ser.write(data)

    def close(self):
        # type: () -> None
        if self._ser:
            debug_msg("Closing serial port")
            self._ser.close()
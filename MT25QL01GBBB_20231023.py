# -*- coding: utf-8 -*-

# MT25QL01GBBB.py
# 2021.08 Daigo Tanaka, Misaki Hayashi
# This code is for testing(Writing and Reading data) Micron's SPI Flash memory, on the BIRDS OBC board.
# Changelog
# 2021/11/10 多バイト読み込み用関数[READ_DATA_BYTES_SMF]と多バイト書き込み用関数[WRITE_DATA_BYTES_SMF]

import RPi.GPIO as GPIO
import spidev
import time
from time import sleep


class flash:
    READ_ID            = 0x9F
    READ_STATUS_REG    = 0x05
    READ_DATA_BYTES    = 0x13  # 0x03 for 3-byte address
    ENABLE_WRITE       = 0x06
    WRITE_PAGE         = 0x12  # 0x02 for 3-byte address
    ERASE_SECTOR       = 0xDC  # 0xD8 for 3-byte address
    ERASE_4KB_SUBSECTOR  = 0x21
    ERASE_32KB_SUBSECTOR = 0x5C
    DIE_ERASE          = 0xC4

    SUBSECTOR_SIZE_OF_4KB  = 4096
    SUBSECTOR_SIZE_OF_32KB = 0x8000
    SECTOR_SIZE            = 0x10000
    DATA_BUFFER_SIZE       = 256

    def __init__(self, bus=0, CSB=0, baud=1000000):
        self.h = spidev.SpiDev()
        self.h.open(bus, CSB)
        self.h.max_speed_hz = baud
        self.h.mode = 0

    def __del__(self):
        try:
            self.h.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pack_address(self, address):
        # type: (int) -> list
        """4バイトアドレスをビッグエンディアンのバイトリストに変換する。"""
        return [
            (address >> 24) & 0xFF,
            (address >> 16) & 0xFF,
            (address >>  8) & 0xFF,
             address        & 0xFF,
        ]

    def _wait_ready(self, poll_interval=0.0001):
        # type: (float) -> None
        """Flashがビジー状態の間ポーリングで待機する。"""
        while self.read_status_register() & 0x01:
            time.sleep(poll_interval)

    def _write_enable(self):
        # type: () -> None
        self.h.xfer2([self.ENABLE_WRITE])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_chip_id(self):
        # type: () -> list
        cmd = [self.READ_ID, 0x00] + [0xFF] * 19
        chip_id = self.h.xfer2(cmd)[1:]
        time.sleep(0.01)
        print("CHIP ID >>> 0x{:x} 0x{:x}".format(chip_id[0], chip_id[1]))
        return chip_id

    def read_status_register(self):
        # type: () -> int
        rcvdata = self.h.xfer2([self.READ_STATUS_REG, 0x00])
        if rcvdata[1] & 0x01:
            print("busy")
        return rcvdata[1]

    # --- Read ---

    def READ_DATA_BYTE_SMF(self, sector_address):
        # type: (int) -> int
        """指定アドレスから1バイト読み込む。"""
        packet = [self.READ_DATA_BYTES] + self._pack_address(sector_address) + [0x00]
        return self.h.xfer2(packet)[5]

    def READ_DATA_BYTES_SMF(self, sector_address, amount):
        # type: (int, int) -> list
        """指定アドレスから複数バイト読み込む。"""
        packet = [self.READ_DATA_BYTES] + self._pack_address(sector_address) + [0x00] * amount
        return self.h.xfer2(packet)[5:]

    # --- Erase ---

    def SUBSECTOR_4KB_ERASE_OF(self, sector_address):
        # type: (int) -> None
        """4KBサブセクタを消去する。"""
        packet = [self.ERASE_4KB_SUBSECTOR] + self._pack_address(sector_address)
        self._write_enable()
        self.h.xfer2(packet)
        time.sleep(0.02)
        self._wait_ready(poll_interval=0.01)

    def SUBSECTOR_32KB_ERASE_OF(self, sector_address):
        # type: (int) -> None
        """32KBサブセクタを消去する。"""
        packet = [self.ERASE_32KB_SUBSECTOR] + self._pack_address(sector_address)
        self._write_enable()
        self.h.xfer2(packet)
        time.sleep(0.01)
        self._wait_ready(poll_interval=0.005)

    def SECTOR_ERASE(self, sector_address):
        # type: (int) -> None
        """64KBセクタを消去する。"""
        packet = [self.ERASE_SECTOR] + self._pack_address(sector_address)
        self._write_enable()
        self.h.xfer2(packet)
        time.sleep(0.1)
        self._wait_ready(poll_interval=0.05)

    # --- Write ---

    def WRITE_DATA_BYTE_SMF(self, address, write_data):
        # type: (int, int) -> None
        """指定アドレスに1バイト書き込む。"""
        packet = [self.WRITE_PAGE] + self._pack_address(address) + [write_data]
        self._write_enable()
        sleep(0.00001)
        self.h.xfer2(packet)
        time.sleep(0.0001)
        self._wait_ready()

    def WRITE_DATA_BYTES_SMF(self, address, write_data):
        # type: (int, list) -> None
        """指定アドレスに複数バイト書き込む（最大256バイト）。"""
        packet = [self.WRITE_PAGE] + self._pack_address(address) + write_data
        self._write_enable()
        sleep(0.0000001)
        self.h.writebytes2(packet)
        time.sleep(0.0001)
        self._wait_ready()


if __name__ == '__main__':

    Flash = flash()

    pjname = ['i', 'g', 'o', 'm', 'o', 'y']

    try:
        while True:
            print("input command")
            keydata = input()

            if keydata == 'c':
                print("Chip ID")
                sleep(1)
                data = Flash.read_chip_id()
                print(data)

            elif keydata == 'r':
                print("read Start")
                sleep(1)
                for i in range(6):
                    print(Flash.READ_DATA_BYTE_SMF(i))

            elif keydata == 'e':
                Flash.SUBSECTOR_4KB_ERASE_OF(0)
                sleep(1)

            elif keydata == 'w':
                print("write start")
                for counter, w in enumerate(pjname):
                    Flash.WRITE_DATA_BYTE_SMF(counter, ord(w))

            elif keydata == 'b':
                print("read Start")
                sleep(1)
                for i in range(3):
                    print(Flash.READ_DATA_BYTE_SMF(i))

            elif keydata == 't':
                print("How many bytes will you want to read?")
                keynum = int(input())
                sleep(1)
                data = Flash.READ_DATA_BYTES_SMF(0, keynum)
                print([chr(b) for b in data])

            elif keydata == 'y':
                sleep(1)
                Flash.WRITE_DATA_BYTES_SMF(0, [ord(c) for c in pjname])

    except KeyboardInterrupt:
        pass

    GPIO.cleanup()

import argparse
import ctypes
import serial
from pymodbus.client.sync import ModbusSerialClient
from time import sleep

'''
This script helps with setting the te485.

It can set communitcation from spinel to modbus. This is required to make it
work with UniPI.
'''


class TE485Modbus(object):
    def connect(self):
        self.mb = ModbusSerialClient(
            method='rtu',
            port='/dev/extcomm/0/0',
            stopbits=1,
            bytesize=8,
            parity=serial.PARITY_NONE,
            baudrate=19200,
            timeout=0.1,
        )

    def set_sensitivity(self, sensitivity):
        ''' Set the sensitivity of the load cell

            0x00 ......... 2 mV/V
            0x01 ......... 5 mV/V
            0x02 ....... 10 mV/V

            The greater the the sensitivity of the load cell means the
            amplifier/adc has to be less sensitive and thus a same change will
            cause smaller cange on the adc output.
        '''
        # Set sensitivity
        self.mb.write_register(address=0, value=0xFF, unit=0x31)
        self.mb.write_register(address=16, value=sensitivity, unit=0x31)

    def calibrate(self, raw_zero, raw_full, full_cal_value):
        # Set upper limit value.
        self.mb.write_register(address=0, value=0xFF, unit=0x31)
        self.mb.write_register(address=20, value=full_cal_value, unit=0x31)

        # Calibrate zero
        self.mb.write_register(address=0, value=0xFF, unit=0x31)
        self.mb.write_register(address=18, value=raw_zero, unit=0x31)

        # Calibrate full.
        self.mb.write_register(address=0, value=0xFF, unit=0x31)
        self.mb.write_register(address=19, value=raw_full, unit=0x31)
        sleep(1)

    def read(self):
        r = self.mb.read_input_registers(0, count=3, unit=0x31)
        status, cal, raw = r.registers
        cal = ctypes.c_short(cal).value
        raw = ctypes.c_short(raw).value
        return status, cal, raw


def set_te485_sensitivity():
    parser = argparse.ArgumentParser(
        description="Set the TE485 sensitivity through modbus."
    )
    parser.add_argument(
        'sensitivity',
        type=int,
        help="""
            0 ......... 2 mV/V
            1 ......... 5 mV/V
            2 ....... 10 mV/V
    """,
    )
    args = parser.parse_args()

    te485 = TE485Modbus()
    te485.set_sensitivity(args.sensitivity)


def csume(s):
    csum = 0
    for b in s:
        csum += b
        yield b
    yield 0xFF & (255 - csum)
    yield 0x0D


def trans(s):
    for w in s.split(' '):
        yield int(w, 16)


def swich_to_modbus():
    sp = serial.Serial(
        '/dev/extcomm/0/0',
        baudrate=9600,
        parity=serial.PARITY_NONE,
        bytesize=8,
        stopbits=1,
        xonxoff=0,
        rtscts=0,
        timeout=1,
    )

    # Read identification on broadcast address.
    sp.write(b'*B$?\r')
    sp.read_until(b'\r')
    # b'*B10TE485; v0672.01.07; f66 97; iBipolar\r'

    # Enable writing command (the next one)
    sp.write(b'*B1E\r')
    sp.readline()
    # b'*B10\r'

    # Switch to Modbus
    sp.write(bytes(csume(trans('2A 61 00 06 31 02 ed 02'))))
    sp.readline()
    # b'*a\x00\x051\x02\x00<\r'

    # TODO switch also to 19200 bauds as that is the default UniPi rs485
    # baudrate.

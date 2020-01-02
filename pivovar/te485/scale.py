from __future__ import print_function
from time import sleep
import ctypes
from six.moves import input
import requests
from urllib.parse import urljoin

full_cal_value = 1.0


class Scale(object):
    def calibrate(self, raw_zero, raw_full, full_value):
        self.raw_zero = raw_zero
        self.raw_full = raw_full
        self.full_value = full_value

    def load(self, raw):
        return (
            (raw - self.raw_zero)
            * self.full_value
            / (self.raw_full - self.raw_zero)
        )

    def __str__(self):
        return (
            'Scale(raw_zero: {:d}, raw_full: {:d}, full_value: {})'
        ).format(self.raw_zero, self.raw_full, self.full_value)


def evok_read(evok_baseurl):
    register_url = urljoin(evok_baseurl, '/rest/register')
    raw = requests.get(f'{register_url}/UART_49_3_2_inp').json()['value']
    cal = requests.get(f'{register_url}/UART_49_3_1_inp').json()['value']
    status = requests.get(f'{register_url}/UART_49_3_0_inp').json()['value']

    cal = ctypes.c_short(cal).value
    raw = ctypes.c_short(raw).value
    return status, cal, raw


def calibrate(scale, evok_baseurl):
    input('Load to 0% and press Enter')
    _, _, raw_zero = evok_read(evok_baseurl)
    input('Load to 100% and press Enter')
    _, _, raw_full = evok_read(evok_baseurl)
    scale.calibrate(raw_zero, raw_full, full_cal_value)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Read from TE485 through EVOK."
    )
    parser.add_argument('evok_baseurl', help="URL to evok")
    args = parser.parse_args()

    evok_baseurl = args.evok_baseurl

    scale = Scale()
    calibrate(scale, evok_baseurl)

    while True:
        status, cal, raw = evok_read(evok_baseurl)
        load = scale.load(raw)
        print(
            f'load: {load:.3f} status: {status:b} cal: {cal} raw: {raw}; '
            f'{scale}'
        )
        print(('.' * 40) + ('|' * 40))
        print('=' * int(40 * load))
        sleep(0.1)


if __name__ == '__main__':
    main()

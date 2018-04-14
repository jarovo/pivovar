from __future__ import print_function
import atexit
import logging
import subprocess
import time
import signal

import pivovar.config as cfg
from pivovar import phases


def log_time(arg):
    logging.debug("From print_time", arg, time.time())


class UniPi(object):
    def __init__(self):
        from pymodbus.client.sync import ModbusTcpClient
        tun = SSHTunnel(cfg.TUNNEL_REMOTE_ADDR, 'pi', cfg.TUNNEL_LOCAL_PORT,
                        cfg.TUNNEL_REMOTE_BIND_PORT, cfg.MODBUS_ADDR)
        tun.connect()
        atexit.register(tun.disconnect)
        signal.signal(signal.SIGINT, lambda x, y: tun.disconnect())

        logging.info('Connecting to modbus. %s:%s',
                     cfg.MODBUS_ADDR,
                     cfg.MODBUS_PORT)
        time.sleep(1)
        self.modbus = ModbusTcpClient(cfg.MODBUS_ADDR, cfg.MODBUS_PORT)

    def set_output(self, output, state):
        logging.debug("Setting output %s to %s", output, state)
        self.modbus.write_coil(output, state)

    def temp(self):
        return cfg.REQ_TEMP


class SSHTunnel(object):
    def __init__(self, remote_address, user, local_port, remote_port,
                 remote_bind_address):
        self.remote_address = remote_address
        self.user = user
        self.local_port = local_port
        self.remote_port = remote_port
        self.remote_bind_address = remote_bind_address
        self.tunproc = None

    def connect(self):
        if self.tunproc:
            raise Exception('Already connected.')

        logging.debug('Starting ssh port forwarding for modbus connection.')

        args = ("ssh", "-N", "-L",
                "{0.local_port}:{0.remote_bind_address}:{0.remote_port}"
                .format(self),
                "{0.user}@{0.remote_address}"
                .format(self))
        self.tunproc = subprocess.Popen(args, stdin=None)

        logging.debug('Started ssh port forwarding for modbus connection.')

    def disconnect(self):
        self.tunproc.terminate()
        logging.debug('Stopped ssh port forwarding for modbus connection.')


def main():
    logging.basicConfig(level=logging.INFO)
    backend = UniPi()
    phases.wash_the_keg(backend)


if __name__ == '__main__':
    main()

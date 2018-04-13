from __future__ import print_function
import atexit
import logging
import subprocess
import time
import signal

import sshtunnel

import pivovar.config as cfg

sched = None
backend = None
server = None


def log_time(arg):
    logging.debug("From print_time", arg, time.time())


def delay(seconds):
    time.sleep(seconds)


def create_modbus_tunnel():
    global server
    if server:
        return
    server = sshtunnel.SSHTunnelForwarder(
        cfg.TUNNEL_REMOTE_ADDR,
        ssh_username="pi",
        ssh_password="raspberry",
        remote_bind_address=('127.0.0.1', cfg.TUNNEL_REMOTE_BIND_PORT),
        local_bind_address=('0.0.0.0', cfg.TUNNEL_LOCAL_PORT)
    )
    logging.debug('Starting paramiko port forwarding for modbus connection.')
    server.start()
    logging.debug('Started paramiko port forwarding for modbus connection.')
    # import ipdb
    # ipdb.set_trace


def close_modbus_tunnel():
    server.stop()
    logging.debug('Stopped ssh port forwarding for modbus connection.')


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
        # TODO(jhenner) Really do the setting of the output.

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


def reset():
    for rly, state in cfg.RESET_RLY_STATES.items():
        backend.set_output(rly, state)


def temp_ready():
    return backend.temp() >= cfg.REQ_TEMP


def prewash():
    reset()
    backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)


def draining():
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


def wash_with_lye():
    backend.set_output(cfg.LYE_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.ON)
    delay(50)
    backend.set_output(cfg.LYE_RLY, cfg.OFF)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.OFF)


def wash_with_water(rly):
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    backend.set_output(rly, cfg.ON)
    delay(30)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(rly, cfg.OFF)

    # TODO(jhenner) Discuss the validity of this step.
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)


def wash_with_cold_water():
    wash_with_water(cfg.COLD_WATER_RLY)


def wash_with_hot_water():
    wash_with_water(cfg.HOT_WATER_RLY)


def drying():
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(20)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)


def filling_with_co2():
    backend.set_output(cfg.CO2_RLY, cfg.ON)


def wash_the_keg():
    while not temp_ready():
        logging.debug(
            'Waiting for water (temp %d) to get to required temperature: %d.',
            backend.temp(),
            cfg.REQ_TEMP)
        delay(10)
    prewash()
    wash_with_lye()
    wash_with_cold_water()
    wash_with_hot_water()
    drying()
    filling_with_co2()


def main():
    logging.basicConfig(level=logging.DEBUG)
    global backend
    backend = UniPi()
    reset()
    wash_the_keg()


if __name__ == '__main__':
    main()

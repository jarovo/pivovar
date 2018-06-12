from __future__ import print_function
from abc import ABCMeta
import atexit
import logging
import subprocess
import time
import signal

from jsonrpclib import Server
from jsonrpclib.jsonrpc import ProtocolError

import pivovar.config as cfg
from pivovar import phases


def log_time(arg):
    logging.debug("From print_time", arg, time.time())


class UniPi(object):
    __metaclass__ = ABCMeta

    ALL_RLYS = (cfg.AIR_RLY, cfg.PUMP_RLY, cfg.LYE_OR_WATER_RLY, cfg.CO2_RLY,
                cfg.COLD_WATER_RLY, cfg.DRAIN_OR_RECIRCULATION_RLY,
                cfg.DRAIN_RLY)

    def __init__(self):
        pass

    def set_output(self, output, state):
        logging.debug("Setting output '%s' to '%s'", output, state)


class UniPiModbus(UniPi):
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
        UniPi.set_output(self, output, state)
        self.write_coil(output, state)

    def set_register(self, address, value):
        logging.debug("Setting register %s to 0x%x", address, value)
        self.modbus.write_register(address, value)


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


class UniPiJSONRPC(UniPi):
    def __init__(self):
        UniPi.__init__(self)
        self.server = Server(cfg.UNIPI_JSONRPC_ADDRESS)
        self.check()

    def set_output(self, output, state):
        UniPi.set_output(self, output, state)
        return self.server.relay_set(output, state)

    def get_output(self, output):
        ret = self.server.relay_get(output)

        # For user LEDs, the returned entity is a direct value, not a list.
        if isinstance(ret, list):
            return ret[0]
        else:
            return ret

    def get_input(self, input):
        return self.server.input_get(input)[0]

    def temp(self):
        return self.server.sensor_get(cfg.TEMP_SENSOR)[0]

    def check(self):
        failed = False
        for rly in (cfg.ALL_RLYS + cfg.PHASE_SIGNALS +
                    (cfg.MOTOR_VALVE_TRANSITIONING,)):
            logging.info('Checking whether output named "%s" exists.', rly)
            try:
                self.get_output(rly)
            except ProtocolError:
                logging.error('Output "%s" not configured in UniPi!', rly)
                failed = True

        for inp in (cfg.KEG_PRESENT,):
            logging.info('Checking input named "%s" exists.', inp)
            try:
                self.get_input(inp)
            except ProtocolError:
                logging.error('Input "%s" not configured in UniPi!', inp)
                failed = True

        logging.info('Checking sensor named "%s" exists.', cfg.TEMP_SENSOR)
        try:
            self.server.sensor_get(cfg.TEMP_SENSOR)
        except ProtocolError:
                logging.error('Sensor "%s" not found!', cfg.TEMP_SENSOR)
                failed = True

        if failed:
            raise Exception('Failed to find some inputs or outputs! '
                            'Check the logs for more details.')


def main():
    logging.basicConfig(level=logging.DEBUG)
    backend = UniPiJSONRPC()
    phases.wash_the_kegs(backend)


if __name__ == '__main__':
    main()

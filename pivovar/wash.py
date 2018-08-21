from __future__ import print_function

from abc import ABCMeta
import atexit
from datetime import datetime
import logging
import subprocess
import time
from threading import Thread
import signal
from flask import Flask, request, render_template, url_for, jsonify

import pivovar.config as cfg
from pivovar import phases
from pivovar.jsonrpc import Client, ProtocolError


logger = logging.getLogger('keg_wash')
app = Flask(__name__)


def log_time(arg):
    logger.debug("From print_time", arg, time.time())


class UniPi(object):
    __metaclass__ = ABCMeta

    ALL_RLYS = (cfg.AIR_RLY, cfg.PUMP_RLY, cfg.LYE_OR_WATER_RLY, cfg.CO2_RLY,
                cfg.COLD_WATER_RLY, cfg.DRAIN_OR_RECIRCULATION_RLY,
                cfg.DRAIN_RLY)

    def __init__(self):
        pass

    def set_output(self, output, state):
        logger.debug("Setting output '%s' to '%s'", output, state)


class UniPiModbus(UniPi):
    def __init__(self):
        from pymodbus.client.sync import ModbusTcpClient
        tun = SSHTunnel(cfg.TUNNEL_REMOTE_ADDR, 'pi', cfg.TUNNEL_LOCAL_PORT,
                        cfg.TUNNEL_REMOTE_BIND_PORT, cfg.MODBUS_ADDR)
        tun.connect()
        atexit.register(tun.disconnect)
        signal.signal(signal.SIGINT, lambda x, y: tun.disconnect())

        logger.info('Connecting to modbus. %s:%s',
                    cfg.MODBUS_ADDR, cfg.MODBUS_PORT)
        time.sleep(1)
        self.modbus = ModbusTcpClient(cfg.MODBUS_ADDR, cfg.MODBUS_PORT)

    def set_output(self, output, state):
        UniPi.set_output(self, output, state)
        self.write_coil(output, state)

    def set_register(self, address, value):
        logger.debug("Setting register %s to 0x%x", address, value)
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

        logger.debug('Starting ssh port forwarding for modbus connection.')

        args = ("ssh", "-N", "-L",
                "{0.local_port}:{0.remote_bind_address}:{0.remote_port}"
                .format(self),
                "{0.user}@{0.remote_address}"
                .format(self))
        self.tunproc = subprocess.Popen(args, stdin=None)

        logger.debug('Started ssh port forwarding for modbus connection.')

    def disconnect(self):
        self.tunproc.terminate()
        logger.debug('Stopped ssh port forwarding for modbus connection.')


class UniPiJSONRPC(UniPi):
    def __init__(self, address):
        UniPi.__init__(self)
        self.server = Client(address)
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
        for rly in cfg.ALL_RLYS:
            logger.info('Checking whether output named "%s" exists.', rly)
            try:
                self.get_output(rly)
            except ProtocolError:
                logger.error('Output "%s" not configured in UniPi!', rly)
                failed = True

        for inp in (cfg.KEG_PRESENT,):
            logger.info('Checking input named "%s" exists.', inp)
            try:
                self.get_input(inp)
            except ProtocolError:
                logger.error('Input "%s" not configured in UniPi!', inp)
                failed = True

        logger.info('Checking sensor named "%s" exists.', cfg.TEMP_SENSOR)
        try:
            self.server.sensor_get(cfg.TEMP_SENSOR)
        except ProtocolError:
                logger.error('Sensor "%s" not found!', cfg.TEMP_SENSOR)
                failed = True

        if failed:
            raise Exception('Failed to find some inputs or outputs! '
                            'Check the logs for more details.')


class WashMachine(object):
    def __init__(self):
        self.current_phase = 'starting'
        self.phases = [str(phase) for phase in phases.phases]
        self.logger = logging.getLogger('keg_wash')
        self.real_temps = []
        self.required_temp = cfg.REQ_TEMP

    def phase_started(self, name):
        self.logger.info('Staring phase: %s', name)
        self.current_phase = name

    def phase_finished(self, name):
        self.logger.info('Phase finished: %s', name)
        self.current_phase = 'idle'

    def add_temp(self, time, temp):
        self.real_temps.append((time, temp))
        DAY = int(60*60*24/cfg.REAL_TEMP_UPDATE_SECONDS)
        self.real_temps = self.real_temps[-DAY:]
        logger.info('Wash machine water temp now is %0.1f', temp)


wash_machine = WashMachine()


@app.route('/')
def index():
    return render_template(
        'index.html',
        real_temps_url=url_for('real_temps'),
        washing_machine=wash_machine)


@app.route('/real_temps', methods=['GET'])
def real_temps():
    if request.method == 'GET':
        return jsonify({
            'datetime': [item[0].strftime('%y-%m-%d %H:%M:%S')
                         for item in wash_machine.real_temps],
            'temps': [str(item[1]) for item in wash_machine.real_temps]})


def temps_update(wash_machine, backend):
    while True:
        wash_machine.add_temp(datetime.now(), backend.temp())
        time.sleep(cfg.REAL_TEMP_UPDATE_SECONDS)


def main():
    logging.basicConfig(level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser(description='Keg washing control.')
    parser.add_argument('--unipi_jsonrpc', type=str,
                        default='http://127.0.0.1/rpc',
                        help='Address to of unipi JSON RPC server.')
    args = parser.parse_args()
    backend = UniPiJSONRPC(args.unipi_jsonrpc)
    wash_thread = Thread(target=phases.wash_the_kegs, args=(backend,))
    phases.add_phases_listener(wash_machine)

    temps_update_thread = Thread(target=temps_update,
                                 args=(wash_machine, backend))
    temps_update_thread.start()

    wash_thread.start()
    app.run(debug=True)


if __name__ == '__main__':
    main()

from __future__ import print_function

import argparse
from datetime import datetime
import logging
import os
import time
from threading import Thread
from flask import Flask
from flask_restful import Resource, Api
from flask_cors import CORS

import pivovar.config as cfg
from pivovar import phases
from pivovar.unipi import UniPiJSONRPC


logger = logging.getLogger('keg_wash')
app = Flask(__name__)
api = Api(app)
CORS(app)


def log_time(arg):
    logger.debug("From print_time", arg, time.time())


class WashMachine(object):
    MAX_TEMP_SAMPLES_COUNT = int(60*60*24 / cfg.REAL_TEMP_UPDATE_SECONDS)

    def __init__(self):
        self.current_phase = 'starting'
        self.logger = logging.getLogger('keg_wash')
        self.real_temps = []
        self.required_temp = cfg.REQ_TEMP

    def phase_started(self, name):
        self.current_phase = name

    def phase_finished(self, name):
        self.current_phase = 'idle'

    def add_temp(self, time, temp):
        self.real_temps.append((time, temp))
        self.real_temps = self.real_temps[-self.MAX_TEMP_SAMPLES_COUNT:]
        logger.info('Wash machine water temp now is %0.1f', temp)

    @property
    def phases(self):
        return [p for p in phases.phases.keys()]


wash_machine = WashMachine()


class RealTemps(Resource):
    def get(self):
        return {
            'datetime': [
                item[0].strftime('%Y-%m-%d %H:%M:%S') for item in
                wash_machine.real_temps
            ],
            'temps': [str(item[1]) for item in wash_machine.real_temps]}


class Phases(Resource):
    def get(self):
        return wash_machine.phases


class CurrentPhase(Resource):
    def get(self):
        return wash_machine.current_phase


api.add_resource(Phases, '/phases')
api.add_resource(RealTemps, '/real_temps')
api.add_resource(CurrentPhase, '/current_phase')


def temps_update(wash_machine, backend):
    while True:
        wash_machine.add_temp(datetime.now(), backend.temp(cfg.TEMP_SENSOR))
        time.sleep(cfg.REAL_TEMP_UPDATE_SECONDS)


def init():
    parser = argparse.ArgumentParser(description='Keg washing control.')
    parser.add_argument('--unipi_jsonrpc', type=str,
                        default='http://127.0.0.1/rpc',
                        help='Address to of unipi JSON RPC server.')
    args = parser.parse_args()
    backend = UniPiJSONRPC(args.unipi_jsonrpc)

    wash_thread = Thread(name='washing machine',
                         target=phases.wash_the_kegs,
                         args=(backend,))
    phases.add_phases_listener(wash_machine)

    temps_update_thread = Thread(name='temps updater',
                                 target=temps_update,
                                 args=(wash_machine, backend))

    temps_update_thread.daemon = True
    temps_update_thread.start()

    wash_thread.daemon = True
    wash_thread.start()


def main():
    logging.basicConfig(level=logging.DEBUG)
    use_debug = True
    if use_debug and not os.environ.get('WERKZEUG_RUN_MAIN'):
        logger.debug('Startup: pid %d is the werkzeug reloader' % os.getpid())
    else:
        logger.debug('Startup: pid %d is the active werkzeug' % os.getpid())
        init()
    app.run(port=5001, debug=use_debug)


if __name__ == '__main__':
    main()

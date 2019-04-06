from __future__ import print_function

import argparse
from datetime import datetime
import logging
import os
import time
from threading import Thread
from flask import Flask
from flask_restplus import Resource, fields
from flask_restplus import Api
from flask_cors import CORS

import pivovar.config as cfg
from pivovar import phases
from pivovar.unipi import UniPiJSONRPC


logger = logging.getLogger('keg_wash')
app = Flask(__name__)
CORS(app)


class DefaultConfig(object):
    PORT = 5001
    INSTANCE_CONFIG_FILE = 'wash.cfg'


cfg.configure_app(app)
api = Api(app)

ERROR_SLEEP_TIME = 1


def log_time(arg):
    logger.debug("From print_time", arg, time.time())


class WashMachine(object):
    MAX_TEMP_SAMPLES_COUNT = int(60*60*24 / cfg.REAL_TEMP_UPDATE_SECONDS)

    def __init__(self):
        self.current_phase = 'starting'
        self.logger = logging.getLogger('keg_wash')
        self.temp_log = []
        self.required_temp = cfg.REQ_TEMP

    def phase_started(self, name):
        self.current_phase = name

    def phase_finished(self, name):
        self.current_phase = 'idle'

    def add_temp(self, time, temp):
        self.temp_log.append((time, temp))
        self.temp_log = self.temp_log[-self.MAX_TEMP_SAMPLES_COUNT:]
        logger.info(
            'Added wash machine water temperature %0.1f into the temp_log',
            temp)

    @property
    def phases(self):
        return [p for p in phases.phases.keys()]


wash_machine = WashMachine()


washing_machine_model = api.model('Washing machine', {
    'current_phase': fields.String,
    'phases': fields.List(fields.String),
    'required_temp': fields.Float,
})


@api.route('/temp_log')
class RealTemps(Resource):
    def get(self):
        return {
            'datetime': [
                item[0].strftime('%Y-%m-%d %H:%M:%S') for item in
                wash_machine.temp_log
            ],
            'temps': [str(item[1]) for item in wash_machine.temp_log]}


@api.route('/wash_machine')
class WashMachineResource(Resource):
    @api.marshal_with(washing_machine_model)
    def get(self, **kwargs):
        return wash_machine


def temps_update(wash_machine, backend):
    while True:
        try:
            sensor = backend.checked_sensor(cfg.TEMP_SENSOR)
            wash_machine.add_temp(datetime.now(), sensor.value)
            time.sleep(cfg.REAL_TEMP_UPDATE_SECONDS)
        except Exception as exc:
            logger.exception('Error happened in the temps update: %s', exc)
            time.sleep(ERROR_SLEEP_TIME)


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
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    use_debug = True
    if use_debug and not os.environ.get('WERKZEUG_RUN_MAIN'):
        logger.debug('Startup: pid %d is the werkzeug reloader' % os.getpid())
    else:
        logger.debug('Startup: pid %d is the active werkzeug' % os.getpid())
        init()
    app.run(port=app.config['PORT'], debug=use_debug)


if __name__ == '__main__':
    main()

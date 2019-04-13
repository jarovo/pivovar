from __future__ import print_function

import argparse
import logging
import os
from threading import Thread
from flask import Flask
from flask_restplus import Resource, fields
from flask_restplus import Api
from flask_cors import CORS

import pivovar.config as cfg
from pivovar import wash_machine
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


wash_machine = wash_machine.WashMachine()


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


def init():
    parser = argparse.ArgumentParser(description='Keg washing control.')
    parser.add_argument('--unipi_jsonrpc', type=str,
                        default='http://127.0.0.1/rpc',
                        help='Address to of unipi JSON RPC server.')
    args = parser.parse_args()
    backend = UniPiJSONRPC(args.unipi_jsonrpc)
    wash_machine.backend = backend

    wash_thread = Thread(name='washing machine',
                         target=wash_machine.wash_the_kegs)

    temps_update_thread = Thread(name='temps updater',
                                 target=wash_machine.temps_update)

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

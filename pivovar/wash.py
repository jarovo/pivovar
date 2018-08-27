from __future__ import print_function

from datetime import datetime
import logging
import time
from threading import Thread
from flask import Flask, request, render_template, url_for, jsonify

import pivovar.config as cfg
from pivovar import phases
from pivovar.unipi import UniPiJSONRPC


logger = logging.getLogger('keg_wash')
app = Flask(__name__)


def log_time(arg):
    logger.debug("From print_time", arg, time.time())


class WashMachine(object):
    MAX_TEMP_SAMPLES_COUNT = int(60*60*24 / cfg.REAL_TEMP_UPDATE_SECONDS)

    def __init__(self):
        self.current_phase = 'starting'
        self.phases = [str(phase) for phase in phases.phases]
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
            'datetime': [item[0].strftime('%Y-%m-%d %H:%M:%S')
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
    temps_update_thread.daemon = True
    temps_update_thread.start()

    wash_thread.daemon = True
    wash_thread.start()
    app.run(debug=True)


if __name__ == '__main__':
    main()

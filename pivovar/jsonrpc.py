import requests
import json

import logging


logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# The methods are defined here:
# https://github.com/UniPiTechnology/evok/blob/master/evok/rpc_handler.py
# Return value signatures can be inhered from
# https://github.com/UniPiTechnology/evok/blob/master/evok/neuron.py
# or
# https://github.com/UniPiTechnology/evok/blob/master/evok/owclient.py


class ProtocolError(Exception):
    pass


class Client(object):
    def __init__(self, url):
        self.counter = 0
        self.url = url
        self.session = requests.Session()

    def _jsonrpc_args_method(self, method, *args):
        self.counter += 1
        resp = self.session.post(
            self.url,
            data=json.dumps(
                {
                    'id': self.counter,
                    'jsonrpc': '2.0',
                    'method': method,
                    'params': args,
                }
            ),
        ).json()

        error = resp.get('error')
        if error:
            exc = ProtocolError(error['message'], error['code'])
            raise exc
        else:
            return resp['result']

    def relay_get(self, relay):
        return self._jsonrpc_args_method("relay_get", relay)

    def relay_set(self, relay, value):
        return self._jsonrpc_args_method("relay_set", relay, value)

    def sensor_get(self, sensor):
        return self._jsonrpc_args_method("sensor_get", sensor)

    def sensor_get_value(self, sensor):
        return self._jsonrpc_args_method("sensor_get_value", sensor)

    def owbus_get(self, circuit):
        return self._jsonrpc_args_method('owbus_get', circuit)

    def owbus_set(self, circuit, scan_interval):
        return self._jsonrpc_args_method('owbus_set', circuit, scan_interval)

    def owbus_list(self, circuit):
        return self._jsonrpc_args_method("owbus_list", circuit)

    def owbus_scan(self, circuit):
        return self._jsonrpc_args_method("owbus_scan", circuit)

    def input_get(self, input):
        return self._jsonrpc_args_method("input_get", input)

    def input_get_value(self, input):
        return self._jsonrpc_args_method("input_get_value", input)

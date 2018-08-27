from abc import ABCMeta
import logging

from pivovar import config as cfg
from pivovar.jsonrpc import Client, ProtocolError


logger = logging.getLogger('unipi')


class UniPi(object):
    __metaclass__ = ABCMeta

    ALL_RLYS = (cfg.AIR_RLY, cfg.PUMP_RLY, cfg.LYE_OR_WATER_RLY, cfg.CO2_RLY,
                cfg.COLD_WATER_RLY, cfg.DRAIN_OR_RECIRCULATION_RLY,
                cfg.DRAIN_RLY)

    def __init__(self):
        pass

    def set_output(self, output, state):
        logger.debug("Setting output '%s' to '%s'", output, state)


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

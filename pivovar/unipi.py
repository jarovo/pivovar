from abc import ABCMeta
import logging
from collections import namedtuple

from pivovar import config as cfg
from pivovar import PivovarError
from pivovar.jsonrpc import Client

logger = logging.getLogger('unipi')


OneWireSensor = namedtuple('OneWireSensor', 'value lost time interval')


class UniPi(object):
    __metaclass__ = ABCMeta

    ALL_RLYS = (cfg.AIR_RLY, cfg.PUMP_RLY, cfg.LYE_OR_WATER_RLY, cfg.CO2_RLY,
                cfg.COLD_WATER_RLY, cfg.DRAIN_OR_RECIRCULATION_RLY,
                cfg.DRAIN_RLY)

    ALL_OUTPUTS = (cfg.ERROR_LAMP, cfg.READY_LAMP, cfg.WAITING_FOR_INPUT_LAMP)

    def __init__(self):
        pass

    def set_output(self, output, state):
        logger.debug("Setting output '%s' to '%s'", output, state)


class UniPiJSONRPC(UniPi):
    def __init__(self, address):
        UniPi.__init__(self)
        self.server = Client(address)

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
        return self.server.input_get_value(input)

    def sensor(self, sensor_name):
        return OneWireSensor(*self.server.sensor_get(sensor_name))

    def checked_sensor(self, sensor_name):
        sensor = self.sensor(sensor_name)
        if sensor.lost:
            raise LostSensor('Sensor {} has been lost.'.format(sensor_name),
                             sensor)
        return sensor

    def temp(self, sensor_name):
        return self.checked_sensor(sensor_name).value

    def signal_error(self, error=True):
        try:
            self.set_output(cfg.ERROR_LAMP, bool(error))
        except Exception as exc:
            logger.exception("Couldn't switch the error lamp %s: %s",
                             ("on" if error else "off"), exc)


class LostSensor(PivovarError):
    pass

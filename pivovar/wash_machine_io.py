from abc import ABCMeta, abstractmethod
from collections import namedtuple
import logging
import re
from pivovar import PivovarError
from pivovar.jsonrpc import ProtocolError
import pivovar.config as cfg
import time


logger = logging.getLogger('wash_machine_io')
OneWireSensor = namedtuple('OneWireSensor', 'value lost time interval')


class UniPiIO(object):
    def __init__(self, device, name):
        self._device = device
        self.name = name

    def _get_unipi_jsonrpc(self):
        return self._device.unipi_jsonrpc

    @abstractmethod
    def is_defined(self):
        pass

    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)


class UniPiReadable(UniPiIO):
    __metaclass__ = ABCMeta

    @abstractmethod
    def read_state(self):
        pass

    def is_defined(self):
        logger.info('Checking whether %s exists.', self)
        try:
            self.read_state()
            return True
        except ProtocolError:
            logger.error('IO alias %s not configured in UniPi!', self)
            return False


class Switchable(UniPiReadable):
    def _set(self, value):
        logger.debug("Setting %s to '%s'", self, value)
        self._get_unipi_jsonrpc().relay_set(self.name, value)

    def turn_on(self):
        self._set(True)

    def turn_off(self):
        self._set(False)

    def read_state(self):
        return self._get_unipi_jsonrpc().relay_get(self.name)[0]


class TemperatureSensor(UniPiIO):
    def _get(self):
        return OneWireSensor(*self._get_unipi_jsonrpc().sensor_get(self.name))

    def is_lost(self):
        return self._get().lost

    def read_temperature(self):
        if self.is_lost():
            raise LostSensor('Sensor {} has been lost.'.format(self))
        return self._get().value

    def is_defined(self):
        logger.info('Checking %s exists.', self)
        try:
            return not self.is_lost()
        except ProtocolError:
            logger.error('Sensor "%s" not found!', cfg.TEMP_SENSOR)
            return False


class Input(UniPiReadable):
    def read_state(self):
        return self._get_unipi_jsonrpc().input_get_value(self.name)


class MotorValve(Switchable):
    def __init__(self, _device, name):
        super(MotorValve, self).__init__(_device, name)
        self.valve_transition_time = cfg.MOTOR_VALVE_TRANSITION_SECONDS

    def turn_on(self, wait=True):
        super(MotorValve, self).turn_on()
        if wait:
            self.wait_for_valve_to_switch()

    def turn_off(self, wait=True):
        super(MotorValve, self).turn_off()
        if wait:
            self.wait_for_valve_to_switch()

    def wait_for_valve_to_switch(self):
        time.sleep(self.valve_transition_time)


class DrainOrRecirculation(MotorValve):
    def turn_to_drain(self, wait=True):
        self.turn_off(wait)

    def turn_to_recirculation(self, wait=True):
        self.turn_on(wait)


class WaterOrLye(MotorValve):
    def turn_to_water(self, wait=True):
        self.turn_off(wait)

    def turn_to_lye(self, wait=True):
        self.turn_on(wait)


class IOGroup(object):
    def __init__(self):
        self.all = []

    @classmethod
    def from_aliases(cls, device, io_cls, aliases):
        self = cls()
        for name in aliases:
            io = io_cls(device, name)
            self._add(remove_al_prefix_if_exists(name), io)
        return self

    def _add(self, name, io):
        setattr(self, name, io)
        self.all.append(io)


def remove_al_prefix_if_exists(s):
    return re.match(r'^(al_)?(.*)', s).group(2)


class LostSensor(PivovarError):
    pass

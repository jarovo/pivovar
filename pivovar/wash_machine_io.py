import attr
from abc import ABCMeta, abstractmethod
from collections import namedtuple
import logging
import re
from pivovar import PivovarError
from pivovar.jsonrpc import ProtocolError
import time


logger = logging.getLogger('wash_machine_io')
OneWireSensor = namedtuple('OneWireSensor', 'value lost time interval')


@attr.s
class UniPiIO(object):
    _device = attr.ib()
    conf_key = attr.ib()

    @property
    def name(self):
        return self.conf_key.split('.')[-1]

    def _get_unipi_jsonrpc(self):
        return self._device.unipi_jsonrpc

    @abstractmethod
    def is_defined(self):
        pass

    def __strr__(self):
        return '{}({}, {})'.format(self.__class__.__name__, self._device.name,
                                   self.name)

    def _read_config(self, section):
        pass


@attr.s
class UniPiReadable(UniPiIO):
    __metaclass__ = ABCMeta
    alias = attr.ib(default=None)

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

    def __strr__(self):
        return '{}({}, {}, {})'.format(self.__class__.__name__,
                                       self._device.name,
                                       self.name, self.alias)

    def _read_config(self, section):
        super(UniPiReadable, self)._read_config(section)
        self.alias = section.get(self.conf_key + '.alias', self.alias)


class Switchable(UniPiReadable):
    def _set(self, value):
        logger.debug("Setting %s to '%s'", self, value)
        self._get_unipi_jsonrpc().relay_set(self.alias, value)

    def turn_on(self):
        self._set(True)

    def turn_off(self):
        self._set(False)

    def read_state(self):
        try:
            return self._get_unipi_jsonrpc().relay_get(self.alias)[0]
        except ProtocolError as exc:
            raise PivovarError("Couldn't read {}: {}".format(self, exc))


@attr.s
class TemperatureSensor(UniPiIO):
    address = attr.ib(type=str)

    def _get(self):
        return OneWireSensor(*self._get_unipi_jsonrpc().sensor_get(
            self.address))

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
            logger.error('Sensor "%s" not found!', self)
            return False

    def _read_config(self, section):
        super(TemperatureSensor, self)._read_config(section)
        self.address = section.get(self.conf_key + '.address', self.address)

    def __str__(self):
        return '{}({}, {}, {})'.format(self.__class__.__name__,
                                       self._device.name,
                                       self.name,
                                       self.address)


class Input(UniPiReadable):
    def read_state(self):
        return self._get_unipi_jsonrpc().input_get_value(self.alias)


@attr.s
class MotorValve(Switchable):
    transition_time = attr.ib(type=float, default=3.)

    def turn_on(self, wait=True):
        super(MotorValve, self).turn_on()
        if wait:
            self.wait_for_valve_to_switch()

    def turn_off(self, wait=True):
        super(MotorValve, self).turn_off()
        if wait:
            self.wait_for_valve_to_switch()

    def wait_for_valve_to_switch(self):
        time.sleep(self.transition_time)

    def _read_config(self, section):
        super(MotorValve, self)._read_config(section)
        self.transition_time = section.getfloat(
            self.conf_key + '.transition_time', self.transition_time)


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
    def __init__(self, conf_key):
        self.all = []
        self.conf_key = conf_key

    @classmethod
    def from_aliases(cls, device, conf_key, io_cls, aliases):
        self = cls(conf_key)
        for alias in aliases:
            name = remove_al_prefix_if_exists(alias)
            io = io_cls(device, '{}.{}'.format(conf_key, name), alias)
            self._add(io)
        return self

    def _add(self, io):
        setattr(self, io.name, io)
        self.all.append(io)


def remove_al_prefix_if_exists(s):
    return re.match(r'^(al_)?(.*)', s).group(2)


class LostSensor(PivovarError):
    pass

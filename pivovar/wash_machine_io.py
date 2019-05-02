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
class StructureNode(object):
    name = attr.ib(type=str)

    def __attrs_post_init__(self):
        self.parent = None

    def _to_root(self):
        elm = self
        while elm:
            yield elm
            elm = elm.parent

    @property
    def conf_key(self):
        return '.'.join(o.name for o in reversed(list(self._to_root())))


@attr.s
class UniPiIO(StructureNode):
    _facility = attr.ib()

    def _get_unipi_jsonrpc(self):
        return self._facility.unipi_jsonrpc

    @abstractmethod
    def is_defined(self):
        pass

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
                                       self._facility.name,
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


@attr.s
class IOGroup(StructureNode):
    def __attrs_post_init__(self):
        StructureNode.__attrs_post_init__(self)
        self.leafs = []
        self.groups = []

    def all_leafs(self):
        for l in self.leafs:
            yield l
        for g in self.traverse_groups():
            for l in g.all_leafs():
                yield l

    def traverse_groups(self):
        for g in self.groups:
            for s in g.traverse_groups():
                yield s

    @classmethod
    def from_aliases(cls, name, facility, io_cls, aliases):
        self = cls(name)
        for alias in aliases:
            sub_name = remove_al_prefix_if_exists(alias)
            io = io_cls(sub_name, facility, alias)
            self._add(io)
        return self

    def _add(self, io):
        setattr(self, io.name, io)
        io.parent = io.parent if io.parent else self
        self.leafs.append(io)

    def _add_group(self, io):
        setattr(self, io.name, io)
        self.groups.append(io)
        io.parent = io.parent if io.parent else self


def remove_al_prefix_if_exists(s):
    return re.match(r'^(al_)?(.*)', s).group(2)


class LostSensor(PivovarError):
    pass

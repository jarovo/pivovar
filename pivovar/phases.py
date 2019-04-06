import logging
import time
from functools import wraps

import pivovar.config as cfg
from pivovar.jsonrpc import ProtocolError


logger = logging.getLogger('phases')
ERROR_SLEEP_TIME = .3


class Listeners(set):
    def notify_phase_started(self, phase):
        logger.info('Staring phase: %s', phase)
        for listener in self:
            listener.phase_started(phase)

    def notify_phase_finished(self, phase):
        logger.info('Phase finished: %s', phase)
        for listener in self:
            listener.phase_finished(phase)


def add_phases_listener(listener):
    _phase_listeners.add(listener)


_phase_listeners = Listeners()
phases = {}


def phase(name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwds):
            _phase_listeners.notify_phase_started(name)
            ret = f(*args, **kwds)
            _phase_listeners.notify_phase_finished(name)
            return ret
        phases[name] = wrapper
        return wrapper
    return decorator


def delay(ticks):
    time.sleep(ticks * cfg.TICK)


def turn_motor_valve(backend, relay, state):
    backend.set_output(relay, state)
    time.sleep(cfg.MOTOR_VALVE_TRANSITION_SECONDS)


def temp_ok(temp):
    return float(temp) >= cfg.REQ_TEMP


def system_flush(backend, ticks):
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(ticks)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)


def pulse(backend, rly, count, duration, duty_cycle=0.5):
    i = 0
    period = float(duration) / count
    t_on = period * duty_cycle
    t_off = period * (1 - duty_cycle)
    while True:
        i += 1
        backend.set_output(rly, cfg.ON)
        delay(t_on)
        backend.set_output(rly, cfg.OFF)
        if i >= count:
            break
        delay(t_off)


@phase("reset")
def reset(backend):
    backend.set_output(cfg.WAITING_FOR_INPUT_LAMP, False)
    for rly in backend.ALL_RLYS:
        if backend.get_output(rly):
            backend.set_output(rly, False)
    time.sleep(cfg.MOTOR_VALVE_TRANSITION_SECONDS)


@phase('check')
def check(backend):
    failed = []
    for output in backend.ALL_OUTPUTS:
        logger.info('Checking whether output named "%s" exists.', output)
        try:
            backend.get_output(output)
        except ProtocolError:
            logger.error('Output "%s" not configured in UniPi!', output)
            failed.append('output ' + output)

    for rly in backend.ALL_RLYS:
        logger.info('Checking whether relay named "%s" exists.', rly)
        try:
            backend.get_output(rly)
        except ProtocolError:
            logger.error('Relay "%s" not configured in UniPi!', rly)
            failed.append('relay ' + rly)

    for inp in (cfg.KEG_PRESENT,):
        logger.info('Checking input named "%s" exists.', inp)
        try:
            backend.get_input(inp)
        except ProtocolError:
            logger.error('Input "%s" not configured in UniPi!', inp)
            failed.append('input ' + rly)

    logger.info('Checking sensor named "%s" exists.', cfg.TEMP_SENSOR)
    try:
        backend.checked_sensor(cfg.TEMP_SENSOR)
    except ProtocolError:
        logger.error('Sensor "%s" not found!', cfg.TEMP_SENSOR)
        failed.append('temp_sensor ' + rly)

    if failed:
        raise Exception('Failed to find some inputs or outputs! (%s)'
                        .format(', '.join(failed)))


@phase('waiting for keg')
def wait_for_keg(backend):
    logging.info('Waiting for keg.')
    backend.set_output(cfg.WAITING_FOR_INPUT_LAMP, True)
    while not backend.get_input(cfg.KEG_PRESENT):
        time.sleep(.01)


@phase('heating')
def heating(backend):
    actual_temp = backend.temp(cfg.TEMP_SENSOR)
    backend.set_output(cfg.WAITING_FOR_INPUT_LAMP, True)
    while not temp_ok(actual_temp):
        logging.info(
            'Waiting for water (actual temperature %.2f) to get to required '
            'temperature: %.2f.',
            actual_temp,
            cfg.REQ_TEMP)
        time.sleep(cfg.HEATING_SLEEP_SECONDS)
        actual_temp = backend.temp(cfg.TEMP_SENSOR)
    logging.info(
        'Water ready (actual temperature %.2f. Required %.2f)',
        actual_temp, cfg.REQ_TEMP)


@phase('prewashing')
def prewash(backend):
    pulse(backend, cfg.COLD_WATER_RLY, 5, 30, 0.8)


@phase('draining')
def drain(backend):
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(5)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)


@phase('washing with lye')
def wash_with_lye(backend):
    turn_motor_valve(backend, cfg.LYE_OR_WATER_RLY, cfg.LYE)
    backend.set_output(cfg.PUMP_RLY, cfg.ON)
    delay(50)
    backend.set_output(cfg.PUMP_RLY, cfg.OFF)
    turn_motor_valve(backend, cfg.LYE_OR_WATER_RLY, cfg.WATER)


@phase('washing with cold water')
def rinse_with_cold_water(backend):
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY,
                     cfg.RECIRCULATION)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    system_flush(backend, 1)


@phase('washing with hot water')
def wash_with_hot_water(backend):
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY,
                     cfg.RECIRCULATION)
    backend.set_output(cfg.PUMP_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.PUMP_RLY, cfg.OFF)
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.OFF)


@phase('drying')
def dry(backend):
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


@phase('filling with CO2')
def fill_with_co2(backend):
    backend.set_output(cfg.CO2_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.CO2_RLY, cfg.OFF)


def wash_the_kegs(backend):
    while True:
        wash_cycle = (
            check,
            wait_for_keg,
            heating,
            prewash,
            drain,
            wash_with_lye,
            rinse_with_cold_water,
            wash_with_hot_water,
            dry,
            fill_with_co2
        )
        for phase in wash_cycle:
            while True:
                try:
                    backend.signal_error(False)
                    reset(backend)
                    phase(backend)
                    break
                except Exception as exc:
                    logger.exception('Exception happened in phase %s: %s',
                                     phase, exc)
                    backend.signal_error(True)
                    time.sleep(ERROR_SLEEP_TIME)

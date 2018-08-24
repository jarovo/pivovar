import logging
import time
from functools import wraps

import pivovar.config as cfg


logger = logging.getLogger('phases')


class listeners(set):
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


_phase_listeners = listeners()
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


@phase("reset")
def reset(backend):
    for rly in backend.ALL_RLYS:
        if backend.get_output(rly):
            backend.set_output(rly, False)
    time.sleep(cfg.MOTOR_VALVE_TRANSITION_SECONDS)


def temp_ready(backend):
    return backend.temp() >= cfg.REQ_TEMP


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


@phase('waiting for keg')
def wait_for_keg(backend):
    logging.info('Waiting for keg.')
    while not backend.get_input(cfg.KEG_PRESENT):
        time.sleep(.01)


@phase('heating')
def heating(backend):
    while not temp_ready(backend):
        logging.info(
            'Waiting for water (actual temperature %.2f) to get to required '
            'temperature: %.2f.',
            backend.temp(),
            cfg.REQ_TEMP)
        time.sleep(cfg.HEATING_SLEEP_SECONDS)
    logging.info(
        'Water ready (actual temperature %.2f. Required %.2f)',
        backend.temp(), cfg.REQ_TEMP)


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


def wash_the_keg(backend):
    wash_cycle = (
        prewash,
        drain,
        wash_with_lye,
        rinse_with_cold_water,
        wash_with_hot_water,
        dry,
        fill_with_co2
    )
    for phase in wash_cycle:
        reset(backend)
        phase(backend)


def wash_the_kegs(backend):
    while True:
        wait_for_keg(backend)
        heating(backend),
        logging.info('Keg present and hot water is ready. '
                     'The washing process can start now.')
        wash_the_keg(backend)
        reset(backend)

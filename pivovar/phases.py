import logging
import time

import pivovar.config as cfg

phase_logger = logging.getLogger('phase')


def delay(ticks):
    time.sleep(ticks * cfg.TICK)


def turn_motor_valve(backend, relay, state):
    backend.set_output(cfg.MOTOR_VALVE_TRANSITIONING, cfg.ON)
    backend.set_output(relay, state)
    time.sleep(cfg.MOTOR_VALVE_TRANSITION_SECONDS)
    backend.set_output(cfg.MOTOR_VALVE_TRANSITIONING, cfg.OFF)


def reset(backend):
    phase_logger.info('Reset.')
    for output in cfg.PHASE_SIGNALS:
        backend.set_output(output, False)
    for rly in backend.ALL_RLYS:
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


def heating(backend):
    phase_logger.info('Heating.')
    while not temp_ready(backend):
        logging.info(
            'Waiting for water (actual temperature %.2f) to get to required '
            'temperature: %.2f.',
            backend.temp(),
            cfg.REQ_TEMP)
        time.sleep(15)
    logging.info(
        'Water ready (actual temperature %.2f. Required %.2f)',
        backend.temp(), cfg.REQ_TEMP)


def prewash(backend):
    phase_logger.info('Prewashing.')
    backend.set_output(cfg.PHASE_SIGNALS[0], cfg.ON)

    backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)


def drain(backend):
    phase_logger.info('Draining.')
    backend.set_output(cfg.PHASE_SIGNALS[1], cfg.ON)

    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(30)


def wash_with_lye(backend):
    phase_logger.info('Washing with lye.')
    backend.set_output(cfg.PHASE_SIGNALS[2], cfg.ON)

    turn_motor_valve(backend, cfg.LYE_OR_WATER_RLY, cfg.LYE)
    backend.set_output(cfg.PUMP_RLY, cfg.ON)
    delay(50)
    backend.set_output(cfg.PUMP_RLY, cfg.OFF)
    turn_motor_valve(backend, cfg.LYE_OR_WATER_RLY, cfg.WATER)


def rinse_with_cold_water(backend):
    phase_logger.info('Washing with cold water.')
    backend.set_output(cfg.PHASE_SIGNALS[3], cfg.ON)

    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY,
                     cfg.RECIRCULATION)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    system_flush(backend, 1)


def wash_with_hot_water(backend):
    phase_logger.info('Washing with hot water.')
    backend.set_output(cfg.PHASE_SIGNALS[4], cfg.ON)

    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY,
                     cfg.RECIRCULATION)
    backend.set_output(cfg.PUMP_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.PUMP_RLY, cfg.OFF)
    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.OFF)


def dry(backend):
    phase_logger.info('Drying.')
    backend.set_output(cfg.PHASE_SIGNALS[5], cfg.ON)

    turn_motor_valve(backend, cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


def fill_with_co2(backend):
    phase_logger.info('Filling with CO2.')
    backend.set_output(cfg.PHASE_SIGNALS[6], cfg.ON)

    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(cfg.CO2_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.CO2_RLY, cfg.OFF)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


def wash_the_keg(backend):
    wash_cycle = (
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
        reset(backend)
        phase(backend)

import logging
import time

import pivovar.config as cfg

phase_logger = logging.getLogger('phase')


def delay(seconds):
    time.sleep(seconds)


def reset(backend):
    phase_logger.info('Reset')
    for rly, state in cfg.RESET_RLY_STATES.items():
        backend.set_output(rly, state)
    for out in range(0, 4) + range(8, 12):
        backend.set_output(out, cfg.OFF)


def temp_ready(backend):
    return backend.temp() >= cfg.REQ_TEMP


def prewash(backend):
    phase_logger.info('Prewash')
    backend.set_output(0, cfg.ON)
    reset(backend)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)


def draining(backend):
    phase_logger.info('Draining')
    backend.set_output(1, cfg.ON)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


def wash_with_lye(backend):
    phase_logger.info('Wash with lye.')
    backend.set_output(2, cfg.ON)
    backend.set_output(cfg.LYE_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.ON)
    delay(50)
    backend.set_output(cfg.LYE_RLY, cfg.OFF)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.OFF)


def wash_with_water(backend, rly):
    backend.set_output(3, cfg.ON)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    backend.set_output(rly, cfg.ON)
    delay(30)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(rly, cfg.OFF)

    # TODO(jhenner) Discuss the validity of this step.
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)


def wash_with_cold_water(backend):
    phase_logger.info('Wash with cold water.')
    backend.set_output(8, cfg.ON)
    wash_with_water(backend, cfg.COLD_WATER_RLY)


def wash_with_hot_water(backend):
    phase_logger.info('Wash with hot water')
    backend.set_output(9, cfg.ON)
    wash_with_water(backend, cfg.HOT_WATER_RLY)


def drying(backend):
    phase_logger.info('Drying.')
    backend.set_output(10, cfg.ON)
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(20)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)


def filling_with_co2(backend):
    phase_logger.info('Filling with CO2')
    backend.set_output(11, cfg.ON)
    backend.set_output(cfg.CO2_RLY, cfg.ON)
    delay(10)


def wash_the_keg(backend):
    reset(backend)
    while not temp_ready(backend):
        logging.info(
            'Waiting for water (temp %d) to get to required temperature: %d.',
            backend.temp(),
            cfg.REQ_TEMP)
        delay(10)

    wash_cycle = (
        prewash,
        wash_with_lye,
        wash_with_cold_water,
        wash_with_hot_water,
        drying,
        filling_with_co2
    )
    for phase in wash_cycle:
        reset(backend)
        phase(backend)
    reset(backend)

import logging
import time

import pivovar.config as cfg

phase_logger = logging.getLogger('phase')

phase_signals = (0, 1, 2, 3, 9, 10, 11)


def delay(seconds):
    time.sleep(seconds)


def reset(backend):
    phase_logger.info('Reset.')
    backend.set_register(cfg.RELAYS_REG_ADDR, 0x00)
    backend.set_register(cfg.ULED_REG_ADDR, 0x00)
    backend.set_register(cfg.DIGITAL_OUTPUT_REG_ADDR, 0x00)


def temp_ready(backend):
    return backend.temp() >= cfg.REQ_TEMP


def prewash(backend):
    phase_logger.info('Prewashing.')
    backend.set_output(phase_signals[0], cfg.ON)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)


def drain(backend):
    phase_logger.info('Draining.')
    backend.set_output(phase_signals[1], cfg.ON)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


def wash_with_lye(backend):
    phase_logger.info('Washing with lye.')
    backend.set_output(phase_signals[2], cfg.ON)
    backend.set_output(cfg.LYE_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.ON)
    delay(50)
    backend.set_output(cfg.LYE_RLY, cfg.OFF)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.OFF)


def wash_with_water(backend, rly):
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    backend.set_output(rly, cfg.ON)
    delay(30)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(rly, cfg.OFF)

    # TODO(jhenner) Discuss the validity of this step.
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)


def wash_with_cold_water(backend):
    phase_logger.info('Washing with cold water.')
    backend.set_output(phase_signals[3], cfg.ON)
    wash_with_water(backend, cfg.COLD_WATER_RLY)


def wash_with_hot_water(backend):
    phase_logger.info('Washing with hot water.')
    backend.set_output(phase_signals[4], cfg.ON)
    wash_with_water(backend, cfg.HOT_WATER_RLY)


def dry(backend):
    phase_logger.info('Drying.')
    backend.set_output(phase_signals[5], cfg.ON)
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(20)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)


def fill_with_co2(backend):
    phase_logger.info('Filling with CO2.')
    backend.set_output(phase_signals[6], cfg.ON)
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
        drain,
        wash_with_lye,
        wash_with_cold_water,
        wash_with_hot_water,
        dry,
        fill_with_co2
    )
    for phase in wash_cycle:
        reset(backend)
        phase(backend)
    reset(backend)

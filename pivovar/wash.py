from __future__ import print_function
import time
import logging
import pivovar.config as cfg

sched = None
backend = None


def log_time(arg):
    logging.debug("From print_time", arg, time.time())


def delay(seconds):
    time.sleep(seconds)


class UniPi(object):
    def __init__(self):
        from pymodbus.client.sync import ModbusTcpClient
        self.modbus = ModbusTcpClient('')

    def set_output(self, output, state):
        logging.debug("Setting output %s to %s", output, state)
        self.modbus.write_coil(output, state)
        # TODO(jhenner) Really do the setting of the output.

    def temp(self):
        raise NotImplementedError()


def reset():
    for rly, state in cfg.RESET_RLY_STATES.items():
        backend.set_output(rly, state)


def temp_ready():
    backend.temp() >= cfg.REQ_TEMP


def prewash():
    reset()
    backend.set_output(cfg.WATER_PUMP_RLY, cfg.ON)
    delay(30)
    backend.set_output(cfg.WATER_PUMP_RLY, cfg.OFF)


def draining():
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)


def wash_with_lye():
    backend.set_output(cfg.LYE_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.ON)
    delay(50)
    backend.set_output(cfg.LYE_RLY, cfg.OFF)
    delay(10)
    backend.set_output(cfg.LYE_RECIRCULATION_RLY, cfg.OFF)


def wash_with_water(rly):
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    backend.set_output(rly, cfg.ON)
    delay(30)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(rly, cfg.OFF)

    # TODO(jhenner) Discuss the validity of this step.
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)


def wash_with_cold_water():
    wash_with_water(cfg.COLD_WATER_RLY)


def wash_with_hot_water():
    wash_with_water(cfg.HOT_WATER_RLY)


def drying():
    backend.set_output(cfg.AIR_RLY, cfg.ON)
    delay(10)
    backend.set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(20)
    backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
    backend.set_output(cfg.AIR_RLY, cfg.OFF)


def filling_with_co2():
    backend.set_output(cfg.CO2_RLY, cfg.ON)


def wash_the_keg():
    while not temp_ready():
        delay(10)
        logging.debug(
            'Waiting for water (temp %d) to get to required temperature: %d.',
            backend.temp(),
            cfg.REQ_TEMP)
    prewash()
    wash_with_lye()
    wash_with_cold_water()
    wash_with_hot_water()
    drying()
    filling_with_co2()


def main():
    global backend
    backend = UniPi()
    logging.basicConfig(level=logging.DEBUG)
    reset()
    wash_the_keg()


if __name__ == '__main__':
    main()

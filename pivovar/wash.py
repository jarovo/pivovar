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
    def __init__():
        from pymodbus.client.sync import ModbusTcpClient
        self.modbus = ModbusTcpClient('')

    def set_output(output, state):
        logging.debug("Setting output %s to %s", output, state)
        self.modbus.write_coil(output, state)
        # TODO(jhenner) Really do the setting of the output.

    def temp():
        raise NotImplementedError()


def reset():
    for rly, state in cfg.RESET_RLY_STATES:
        set_output(rly,state)


def temp_ready():
    while backend.temp() < cfg.REQ_TEMP:
        sched.schedule(5, wait_for_temp, (period,))
        s.run()


def prewash():
    reset()
    set_output(cfg.WATER_PUMP_RLY, cfg.ON)
    delay(30)
    set_output(cfg.WATER_PUMP_RLY, cfg.OFF)

def draining():
    set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(10)
    set_output(cfg.DRAIN_RLY, cfg.OFF)

def wash_with_lye():
    set_output(cfg.LYE_RLY, cfg.ON)
    delay(10)
    set_output(cfg.LYE_RECIRCULATION_RLY, cfg.ON)
    delay(50)
    set_output(cfg.LYE_RLY, cfg.OFF)
    delay(10)
    set_output(cfg.LYE_RECIRCULATION_RLY, cfg.OFF)

def wash_with_water(rly):
    set_output(cfg.DRAIN_RLY, cfg.ON)
    set_output(rly, cfg.ON)
    delay(30)
    set_output(cfg.DRAIN_RLY, cfg.OFF)
    set_output(rly, cfg.OFF)
    set_output(cfg.DRAIN_RLY, cfg.ON)  # TODO(jhenner) Discuss the validity of this.

def wash_with_cold_water():
    wash_with_water(cfg.COLD_WATER_RLY)

def wash_with_hot_water():
    wash_with_water(cfg.HOT_WATER_RLY)

def drying():
    set_output(cfg.AIR_RLY, cfg.ON)
    delay(10)
    set_output(cfg.DRAIN_RLY, cfg.ON)
    delay(20)
    set_output(cfg.DRAIN_RLY, cfg.OFF)
    set_output(cfg.AIR_RLY, cfg.OFF)

def filling_with_co2():
    set_output(cfg.CO2_RLY, cfg.ON)


def wash_the_keg():
    while not temp_ready():
        sleep(10)
    prewash()
    wash_with_lye()
    wash_with_cold_water()
    wash_with_hot_water()
    drying()
    filling_with_co2()

def main():
    backend = UniPi()
    logging.basicConfig(level=logging.DEBUG)
    run_keg_wash()
    set_output(HEATER_OUTPUT, OFF)
    run_keg_wash()



if __name__ == '__main__':
    main()

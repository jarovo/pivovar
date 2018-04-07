from __future__ import print_function
import time
import logging
import pivovar.config as cfg

sched = None
backend = None

def log_time(arg):
    logging.debug("From print_time", arg, time.time())


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
    time.sleep(30)
    set_output(cfg.WATER_PUMP_RLY, cfg.OFF)

def rinsing():
    set_output(cfg.DRAIN_RLY, cfg.ON)

def wash_with_lye():
    raise NotImplementedError()

def drain_lye():
    raise NotImplementedError()

def hot_wash():
    raise NotImplementedError()

def drying():
    raise NotImplementedError()

def filling_with_co2():
    raise NotImplementedError()


def wash_the_keg():
    reset()
    while not temp_ready():
        sleep(10)
    reset()
    prewash()

    reset()
    wash_with_lye()

    reset()
    drain_lye()

    reset()
    hot_wash()

    reset()
    drying()

    reset()
    filling_with_co2()

def main():
    backend = UniPi()
    logging.basicConfig(level=logging.DEBUG)
    run_keg_wash()
    set_output(HEATER_OUTPUT, OFF)
    run_keg_wash()



if __name__ == '__main__':
    main()

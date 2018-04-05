from __future__ import print_function
import sched, time
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


class Scheduler(object):
    def __init__(self):
        self._scheduler = sched.scheduler(time.time, time.sleep)

    def schedule(delay, prio, action):
        logging.debug("Scheduled action %s after %d seconds.", action, delay)
        self._scheduler.enter(delay, prio, action, ())


def temp_ready():
    while backend.temp() < cfg.REQ_TEMP:
        sched.schedule(5, wait_for_temp, (period,))
        s.run()


def prewash():
    sched.schedule(0, lambda: set_output(WATER_PUMP_RLY, ON))
    sched.schedule(10, lambda: set_output(WATER_PUMP_RLY, OFF))

def lye_wash():
    raise NotImplementedError()

def lye_drain():
    raise NotImplementedError()

def hot_wash():
    raise NotImplementedError()

def drying():
    raise NotImplementedError()

def co2_fill():
    raise NotImplementedError()


def wash_the_keg():
    while not temp_ready():
        sleep(10)

    prewash()
    lye_wash()
    lye_drain()
    hot_wash()
    drying()
    co2_fill()

def main():
    sched = Scheduler()
    backend = UniPi()
    logging.basicConfig(level=logging.DEBUG)
    run_keg_wash()
    set_output(HEATER_OUTPUT, OFF)
    run_keg_wash()



if __name__ == '__main__':
    main()

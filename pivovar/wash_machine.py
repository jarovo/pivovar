import logging
import time
from functools import wraps
from datetime import datetime

import pivovar.config as cfg
from pivovar.jsonrpc import ProtocolError


logger = logging.getLogger('phases')
ERROR_SLEEP_TIME = 1.


def phase(name):
    def decorator(f):
        @wraps(f)
        def wrapper(self, *args, **kwds):
            self.phase_started(name)
            ret = f(self, *args, **kwds)
            self.phase_finished(name)
            return ret
        wrapper.phase_name = name
        return wrapper
    return decorator


class WashMachine(object):
    MAX_TEMP_SAMPLES_COUNT = int(60*60*24 / cfg.REAL_TEMP_UPDATE_SECONDS)

    def __init__(self):
        self.current_phase = 'starting'
        self.errors = set()
        self.logger = logging.getLogger('keg_wash')
        self.temp_log = []
        self.required_temp = cfg.REQ_TEMP
        self.backend = None

        self.wash_cycle = (
           self.check,
           self.wait_for_keg,
           self.heating,
           self.prewash,
           self.drain,
           self.wash_with_lye,
           self.rinse_with_cold_water,
           self.wash_with_hot_water,
           self.dry,
           self.fill_with_co2
        )

    @staticmethod
    def keep_running():
        return True

    @property
    def phases(self):
        return [v.phase_name for v in vars(type(self)).values()
                if getattr(v, 'phase_name', None)]

    def phase_started(self, name):
        self.current_phase = name

    def phase_finished(self, name):
        self.current_phase = 'idle'

    def add_temp(self, time, temp):
        if temp is None:
            self.temp_log.append((time, None))
            logger.info(
                'Added missing value of wash machine water temperature'
                'into the temp_log')
        else:
            self.temp_log.append((time, temp))
            logger.info(
                'Added wash machine water temperature %0.1f into the temp_log',
                temp)

        self.temp_log = self.temp_log[-self.MAX_TEMP_SAMPLES_COUNT:]

    def temps_update(self):
        while True:
            try:
                sensor = self.backend.checked_sensor(cfg.TEMP_SENSOR)
            except Exception as exc:
                logger.exception('Error happened in the temps update: %s', exc)
                self.add_temp(datetime.now(), None)
            else:
                self.add_temp(datetime.now(), sensor.value)
            time.sleep(cfg.REAL_TEMP_UPDATE_SECONDS)

    def is_keg_present(self):
        return self.backend.get_input(cfg.KEG_PRESENT)

    def is_total_stop_pressed(self):
        return self.backend.get_input(cfg.TOTAL_STOP)

    def is_fuse_blown(self):
        return not self.backend.get_input(cfg.FUSE_OK)

    def wait_until_inputs_ok(self):
        previous_is_total_stop_pressed = False
        previous_is_fuse_blown = False

        while True:
            retry = False
            if self.is_total_stop_pressed():
                if not previous_is_total_stop_pressed:
                    logging.info(
                        'TOTAL_STOP is pressed. Stopping the processes.')
                previous_is_total_stop_pressed = True
                retry = True

            if self.is_fuse_blown():
                if not previous_is_fuse_blown:
                    logging.info(
                        'No voltage on peripherals fuse. Is it blown?')
                previous_is_fuse_blown = True
                retry = True

            if not retry:
                break
            time.sleep(.1)

    def delay(self, ticks):
        time.sleep(ticks * cfg.TICK)
        self.wait_until_inputs_ok()

    def turn_motor_valve(self, relay, state):
        self.backend.set_output(relay, state)
        time.sleep(cfg.MOTOR_VALVE_TRANSITION_SECONDS)

    @staticmethod
    def is_temp_ok(temp):
        return float(temp) >= cfg.REQ_TEMP

    def system_flush(self, ticks):
        backend = self.backend
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
        backend.set_output(cfg.DRAIN_RLY, cfg.ON)
        backend.set_output(cfg.AIR_RLY, cfg.ON)
        self.delay(ticks)
        backend.set_output(cfg.AIR_RLY, cfg.OFF)

    def pulse(self, rly, count, duration, duty_cycle=0.5):
        i = 0
        period = float(duration) / count
        t_on = period * duty_cycle
        t_off = period * (1 - duty_cycle)
        while True:
            i += 1
            self.backend.set_output(rly, cfg.ON)
            self.delay(t_on)
            self.backend.set_output(rly, cfg.OFF)
            if i >= count:
                break
            self.delay(t_off)

    @phase("reset")
    def reset(self):
        backend = self.backend
        backend.set_output(cfg.WAITING_FOR_INPUT_LAMP, False)
        wait_for_motor_valve = False
        for rly in backend.ALL_RLYS:
            if backend.get_output(rly):
                backend.set_output(rly, False)
                if rly in cfg.MOTOR_VALVES:
                    wait_for_motor_valve = True
        if wait_for_motor_valve:
            time.sleep(cfg.MOTOR_VALVE_TRANSITION_SECONDS)
        self.wait_until_inputs_ok()

    @phase('check')
    def check(self):
        backend = self.backend
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
            failed.append('temp_sensor ' + cfg.TEMP_SENSOR)

        if failed:
            raise Exception('Failed to find some inputs or outputs! ({})'
                            .format(', '.join(failed)))

    @phase('waiting for keg')
    def wait_for_keg(self):
        backend = self.backend
        logging.info('Waiting for keg.')
        backend.set_output(cfg.WAITING_FOR_INPUT_LAMP, True)
        while not self.is_keg_present():
            time.sleep(.01)
            self.wait_until_inputs_ok()

    @phase('heating')
    def heating(self):
        backend = self.backend
        actual_temp = backend.temp(cfg.TEMP_SENSOR)
        backend.set_output(cfg.WAITING_FOR_INPUT_LAMP, True)
        while not self.is_temp_ok(actual_temp):
            logging.info(
                'Waiting for water (actual temperature %.2f) '
                'to get to required temperature: %.2f.',
                actual_temp,
                cfg.REQ_TEMP)
            time.sleep(cfg.HEATING_SLEEP_SECONDS)
            actual_temp = backend.temp(cfg.TEMP_SENSOR)
        logging.info(
            'Water ready (actual temperature %.2f. Required %.2f)',
            actual_temp, cfg.REQ_TEMP)
        self.wait_until_inputs_ok()

    @phase('prewashing')
    def prewash(self):
        self.pulse(cfg.COLD_WATER_RLY, 5, 30, 0.8)

    @phase('draining')
    def drain(self):
        backend = self.backend
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
        backend.set_output(cfg.DRAIN_RLY, cfg.ON)
        backend.set_output(cfg.AIR_RLY, cfg.ON)
        self.delay(5)
        backend.set_output(cfg.DRAIN_RLY, cfg.OFF)
        backend.set_output(cfg.AIR_RLY, cfg.OFF)

    @phase('washing with lye')
    def wash_with_lye(self):
        backend = self.backend
        self.turn_motor_valve(cfg.LYE_OR_WATER_RLY, cfg.LYE)
        backend.set_output(cfg.PUMP_RLY, cfg.ON)
        self.delay(50)
        backend.set_output(cfg.PUMP_RLY, cfg.OFF)
        self.turn_motor_valve(cfg.LYE_OR_WATER_RLY, cfg.WATER)

    @phase('washing with cold water')
    def rinse_with_cold_water(self):
        backend = self.backend
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY,
                              cfg.RECIRCULATION)
        backend.set_output(cfg.COLD_WATER_RLY, cfg.ON)
        self.delay(30)
        backend.set_output(cfg.COLD_WATER_RLY, cfg.OFF)
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
        self.system_flush(1)

    @phase('washing with hot water')
    def wash_with_hot_water(self):
        backend = self.backend
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY,
                              cfg.RECIRCULATION)
        backend.set_output(cfg.PUMP_RLY, cfg.ON)
        self.delay(30)
        backend.set_output(cfg.PUMP_RLY, cfg.OFF)
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.OFF)

    @phase('drying')
    def dry(self):
        backend = self.backend
        self.turn_motor_valve(cfg.DRAIN_OR_RECIRCULATION_RLY, cfg.DRAIN)
        backend.set_output(cfg.AIR_RLY, cfg.ON)
        self.delay(30)
        backend.set_output(cfg.AIR_RLY, cfg.OFF)
        backend.set_output(cfg.DRAIN_RLY, cfg.OFF)

    @phase('filling with CO2')
    def fill_with_co2(self):
        backend = self.backend
        backend.set_output(cfg.CO2_RLY, cfg.ON)
        self.delay(10)
        backend.set_output(cfg.CO2_RLY, cfg.OFF)

    def wash_the_kegs(self):
        backend = self.backend
        while self.keep_running():
            for phase in self.wash_cycle:
                while True:
                    try:
                        backend.signal_error(False)
                        self.reset()
                        phase()
                        break
                    except Exception as exc:
                        logger.exception('Exception happened in phase %s: %s',
                                         phase.phase_name, exc)
                        backend.signal_error(True)
                        time.sleep(ERROR_SLEEP_TIME)

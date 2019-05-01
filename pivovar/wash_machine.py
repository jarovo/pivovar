import attr
import logging
import time
from functools import wraps
from datetime import datetime
from itertools import chain

from pivovar import config as cfg
import pivovar.wash_machine_io as wm_io
from pivovar.jsonrpc import Client


logger = logging.getLogger('phases')
ERROR_SLEEP_TIME = 1.


def N_(message):
    return message


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


def setdeepattr(o, path, val):
    path = path.split('.')
    for name in path[:-1]:
        o = getattr(o, name)
    setattr(o, path[-1], val)


@attr.s
class WashMachine(object):
    ALL_RLYS = ('al_air', 'al_pump', 'al_water_or_lye', 'al_co2',
                'al_cold_water', 'al_drain_or_recirculation', 'al_drain')

    ALL_OUTPUTS = ('al_error_lamp', 'al_ready_lamp',
                   'al_waiting_for_input_lamp')

    ALL_INPUTS = ('al_total_stop', 'al_fuse_ok', 'al_keg_present',
                  'al_keg_50l', 'al_aux_wash')

    name = attr.ib(type=str)
    required_water_temp = attr.ib(type=float, default=80.)
    unipi_jsonrpc_url = attr.ib(type=str, default='http://localhost/rpc')

    def __attrs_post_init__(self):
        self._unipi_jsonrpc = None
        self.current_phase = 'starting'
        self.errors = set()
        self.logger = logging.getLogger('keg_wash')
        self.temp_log = []
        # TODO Solve the problems of double init
        self.real_temp_update_seconds = 15
        self.tick_secs = 1.
        self.heating_sleep_seconds = 5

        self.wash_cycle = [
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
        ]

        self.rly = None
        self.inp = None
        self.out = None
        self.water_temp = None
        self.mv = None

    @property
    def unipi_jsonrpc(self):
        if not self._unipi_jsonrpc:
            self._unipi_jsonrpc = Client(self.unipi_jsonrpc_url)
        return self._unipi_jsonrpc

    @classmethod
    def from_config(cls, section_name):
        wm_config = cfg[section_name]
        self = cls(wm_config.name)
        self.init_io()

        self.unipi_jsonrpc_url = wm_config.get('unipi_jsonrpc_url')
        self.required_water_temp = wm_config.getfloat('required_water_temp')
        self.heating_sleep_seconds = wm_config.getfloat(
            'heating_sleep_seconds')
        self.realtime_temp_update_seconds = wm_config.getfloat(
            'realtime_temp_update_seconds')
        self.tick_secs = wm_config.getfloat('tick_secs')

        # TODO Resolve use of this
        # for k, v in wm_config.items():
        #     if k.startswith('io.'):
        #         setdeepattr(self, k[len('io.'):], v)

        for io in self.all_io:
            io._read_config(wm_config)
        return self

    @property
    def temp_samples_count_limit(self):
        return int(60*60*24 / self.real_temp_update_seconds)

    def init_io(self):
        self.rly = wm_io.IOGroup.from_aliases(
                self, 'io.rly', wm_io.Switchable, self.ALL_RLYS)
        self.inp = wm_io.IOGroup.from_aliases(
                self, 'io.inp', wm_io.Input, self.ALL_INPUTS)
        self.out = wm_io.IOGroup.from_aliases(
                self, 'io.out', wm_io.Switchable, self.ALL_OUTPUTS)

        self.mv = wm_io.IOGroup('io.mv')
        self.mv._add(wm_io.WaterOrLye(
            self, 'io.mv.water_or_lye', None, 'al_lye_or_water'))
        self.mv._add(
            wm_io.DrainOrRecirculation(
                self, 'io.mv.drain_or_recirculation',
                None, 'al_drain_or_recirculation'))

        self.water_temp = wm_io.TemperatureSensor(self, 'io.water_temp', None)

        self.all_io = list(chain(self.rly.all,
                                 self.inp.all,
                                 self.out.all,
                                 self.mv.all,
                                 [self.water_temp]))

    @staticmethod
    def keep_running():
        return True

    @staticmethod
    def keep_repeating():
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

        self.temp_log = self.temp_log[-self.temp_samples_count_limit:]

    def temps_update(self):
        while self.keep_running():
            try:
                temp = self.water_temp.read_temperature()
            except Exception as exc:
                logger.exception('Error happened in the temps update: %s', exc)
                self.add_temp(datetime.now(), None)
            else:
                self.add_temp(datetime.now(), temp)
            time.sleep(self.real_temp_update_seconds)

    def is_keg_present(self):
        return self.inp.keg_present.read_state()

    def is_total_stop_pressed(self):
        return self.inp.total_stop.read_state()

    def is_fuse_blown(self):
        return not self.inp.fuse_ok.read_state()

    def is_50l_keg_selected(self):
        return self.inp.keg_50l.read_state()

    def is_aux_wash_selected(self):
        return self.inp.aux_wash.read_state()

    def main_phase_delay_coef(self):
        if self.is_aux_wash_selected():
            return 5

        if self.is_50l_keg_selected():
            return 1
        else:
            return .75

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
        time.sleep(ticks * self.tick_secs)
        self.wait_until_inputs_ok()

    def is_temp_ok(self, temp):
        return float(temp) >= self.required_water_temp

    def system_flush(self, ticks):
        self.mv.drain_or_recirculation.turn_to_drain()
        self.rly.drain.turn_on()
        self.rly.air.turn_on()
        self.delay(ticks)
        self.rly.air.turn_off()

    def pulse(self, io, count, duration, duty_cycle=0.5):
        i = 0
        period = float(duration) / count
        t_on = period * duty_cycle
        t_off = period * (1 - duty_cycle)
        while True:
            i += 1
            io.turn_on()
            self.delay(t_on)
            io.turn_off()
            if i >= count:
                break
            self.delay(t_off)

    @phase(N_("reset"))
    def reset(self):
        self.out.waiting_for_input_lamp.turn_off()
        rlys_to_switch = (rly for rly in self.rly.all if rly.read_state())
        for rly in rlys_to_switch:
            rly.turn_off()

        valves_to_switch = [mv for mv in self.mv.all if mv.read_state()]
        if any(valves_to_switch):
            for mv in self.mv.all:
                mv.turn_off(wait=False)

            wait_time = max(mv.transition_time for mv
                            in valves_to_switch)
            time.sleep(wait_time)

    @phase(N_('check'))
    def check(self):
        failed = []
        for io in self.all_io:
            if not io.is_defined():
                failed.append(io)

        if failed:
            raise Exception('Failed to find some IO!:\n    {}'
                            .format('\n    '.join(str(io) for io in failed)))

    @phase(N_('waiting for keg'))
    def wait_for_keg(self):
        logging.info('Waiting for keg.')
        self.out.waiting_for_input_lamp.turn_on()
        while not self.is_keg_present():
            time.sleep(.01)
            self.wait_until_inputs_ok()

    @phase(N_('heating'))
    def heating(self):
        actual_temp = self.water_temp.read_temperature()
        self.out.waiting_for_input_lamp.turn_on()
        while not self.is_temp_ok(actual_temp):
            logging.info(
                'Waiting for water (actual temperature %.2f) '
                'to get to required temperature: %.2f.',
                actual_temp,
                self.required_water_temp)
            time.sleep(self.heating_sleep_seconds)
            actual_temp = self.water_temp.read_temperature()
        logging.info(
            'Water ready (actual temperature %.2f. Required %.2f)',
            actual_temp, self.required_water_temp)
        self.wait_until_inputs_ok()

    @phase(N_('prewashing'))
    def prewash(self):
        self.pulse(self.rly.cold_water, 5, 30, 0.8)

    @phase(N_('draining'))
    def drain(self):
        self.mv.drain_or_recirculation.turn_to_drain()
        self.rly.drain.turn_on()
        self.rly.air.turn_on()
        self.delay(5 * self.main_phase_delay_coef())
        self.rly.air.turn_off()
        self.rly.drain.turn_off()

    @phase(N_('washing with lye'))
    def wash_with_lye(self):
        self.mv.water_or_lye.turn_to_lye()
        self.rly.pump.turn_on()
        self.delay(50 * self.main_phase_delay_coef())
        self.rly.pump.turn_off()
        self.mv.water_or_lye.turn_to_water()

    @phase(N_('washing with cold water'))
    def rinse_with_cold_water(self):
        self.mv.drain_or_recirculation.turn_to_recirculation()
        self.rly.cold_water.turn_on()
        self.delay(30 * self.main_phase_delay_coef())
        self.rly.cold_water.turn_off()
        self.mv.drain_or_recirculation.turn_to_drain()
        self.system_flush(1)

    @phase(N_('washing with hot water'))
    def wash_with_hot_water(self):
        self.mv.drain_or_recirculation.turn_to_recirculation()
        self.rly.pump.turn_on()
        self.delay(30 * self.main_phase_delay_coef())
        self.rly.pump.turn_off()
        self.mv.drain_or_recirculation.turn_to_drain()

    @phase(N_('drying'))
    def dry(self):
        self.mv.drain_or_recirculation.turn_to_drain()
        self.rly.air.turn_on()
        self.delay(30 * self.main_phase_delay_coef())
        self.rly.air.turn_off()
        self.rly.drain.turn_off()

    @phase(N_('filling with CO2'))
    def fill_with_co2(self):
        self.rly.co2.turn_on()
        self.delay(10 * self.main_phase_delay_coef())
        self.rly.co2.turn_off()

    def wash_the_kegs(self):
        while self.keep_running():
            for phase in self.wash_cycle:
                while self.keep_repeating():
                    try:
                        self.signal_error(False)
                        self.reset()
                        phase()
                        break
                    except Exception as exc:
                        logger.exception('Exception happened in phase %s: %s',
                                         phase.phase_name, exc)
                        self.signal_error(True)
                        time.sleep(ERROR_SLEEP_TIME)

    def signal_error(self, error=True):
        try:
            if error:
                self.out.error_lamp.turn_on()
            else:
                self.out.error_lamp.turn_off()
        except Exception as exc:
            logger.exception("Couldn't switch the error lamp: %s", exc)

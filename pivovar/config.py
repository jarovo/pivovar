# Washing machine temperature related config
REQ_TEMP = 24.0
""" Temperature of hot water to wait for. """
TEMP_SENSOR = '287DD88304000063'
HEATING_SLEEP_SECONDS = 3

# Relays
AIR_RLY = 'al_air'
PUMP_RLY = 'al_pump'
LYE_OR_WATER_RLY = 'al_lye_or_water'
CO2_RLY = 'al_co2'
COLD_WATER_RLY = 'al_cold_water'
DRAIN_OR_RECIRCULATION_RLY = 'al_drain_or_recirculation'
DRAIN_RLY = 'al_drain'

# Digital outputs
ERROR_LAMP = 'al_error_lamp'
READY_LAMP = 'al_ready_lamp'
WAITING_FOR_INPUT_LAMP = 'al_waiting_for_input_lamp'

# Digital inputs
FUSE_OK = 'al_fuse_ok'
TOTAL_STOP = 'al_total_stop'
KEG_PRESENT = 'al_keg_present'
KEG_50L = 'al_keg_50l'
AUX_WASH = 'al_aux_wash'

# Define relay constants.
ON = LYE = RECIRCULATION = True
OFF = WATER = DRAIN = False

# Define registers.
RELAYS_REG_ADDR = 101
ULED_REG_ADDR = 20
DIGITAL_OUTPUT_REG_ADDR = 1

# Connection related parameters.
MODBUS_ADDR = 'localhost'
MODBUS_PORT = 5020
TUNNEL_REMOTE_ADDR = '192.168.2.2'
TUNNEL_LOCAL_PORT = 5020
TUNNEL_REMOTE_BIND_PORT = 502
DEFAULT_PRIO = 10

MOTOR_VALVES = 'al_lye_or_water', 'al_drain_or_recirculation'
MOTOR_VALVE_TRANSITION_SECONDS = 3
MOTOR_VALVE_TRANSITIONING = 'al_motor_valve_transitioning'
""" Modbus coil to turn on in each program phase."""


""" Seconds per single 'tick'. """


REAL_TEMP_UPDATE_SECONDS = 15
TICK = 1


def configure_app(app):
    import os
    config_name = os.getenv('FLASK_CONFIGURATION', 'DefaultConfig')
    # object-based default configuratiok
    app.config.from_object('{}.{}'.format(app.name, config_name))
    # instance-folders configuration
    app.config.from_pyfile(app.config['INSTANCE_CONFIG_FILE'], silent=True)

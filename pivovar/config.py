REQ_TEMP = 24.0
""" Temperature of hot water to wait for. """
TEMP_SENSOR = '287DD88304000063'
HEATING_SLEEP_SECONDS = 3

AIR_RLY = 'al_air'
PUMP_RLY = 'al_pump'
LYE_OR_WATER_RLY = 'al_lye_or_water'
CO2_RLY = 'al_co2'
COLD_WATER_RLY = 'al_cold_water'
DRAIN_OR_RECIRCULATION_RLY = 'al_drain_or_recirculation'
DRAIN_RLY = 'al_drain'

ALL_RLYS = (AIR_RLY, PUMP_RLY, LYE_OR_WATER_RLY, CO2_RLY, COLD_WATER_RLY,
            DRAIN_OR_RECIRCULATION_RLY, DRAIN_RLY)

KEG_PRESENT = 'al_keg_present'

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

UNIPI_JSONRPC_ADDRESS = 'http://192.168.2.241/rpc'

MOTOR_VALVE_TRANSITION_SECONDS = 3
MOTOR_VALVE_TRANSITIONING = 'al_motor_valve_transitioning'
""" Modbus coil to turn on in each program phase."""


""" Seconds per single 'tick'. """


PHASE_SIGNALS = ('al_prewashing', 'al_draining', 'al_washing_with_lye',
                 'al_washing_with_cold_water', 'al_washing_with_hot_water',
                 'al_drying', 'al_filling_with_co2')

TICK = 1

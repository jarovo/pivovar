REQ_TEMP = 80
""" Temperature of hot water to wait for. """

(
    AIR_RLY,
    PUMP_RLY,
    LYE_OR_WATER_RLY,
    CO2_RLY,
    COLD_WATER_RLY,
    DRAIN_OR_RECIRCULATION_RLY,
    DRAIN_RLY
) = range(100, 107)

# Define relay constants.
ON = LYE = RECIRCULATION = 1
OFF = WATER = DRAIN = 0

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

TICK = 1
MOTOR_VALVE_TRANSITION_SECONDS = 3
""" Seconds per single 'tick'. """

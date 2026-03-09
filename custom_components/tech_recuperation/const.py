"""Constants for the Tech Recuperation integration."""

from homeassistant.const import Platform

DOMAIN = "tech_recuperation"

# eMODUL API
API_BASE_URL = "https://emodul.eu/api/v1"

# Polling interval in seconds
SCAN_INTERVAL = 30

# Temperature values from the API are multiplied by 10 (e.g., 215 = 21.5 C)
TEMPERATURE_DIVISOR = 10

# --- Tile types ---
TILE_TYPE_TEMP_SENSOR = 1
TILE_TYPE_UNIVERSAL_STATUS = 6
TILE_TYPE_RELAY = 11
TILE_TYPE_FAN = 22
TILE_TYPE_DATE = 41
TILE_TYPE_SOFTWARE_VERSION = 50

# --- Menu element types ---
MENU_TYPE_NUMBER = 1
MENU_TYPE_ON_OFF = 10
MENU_TYPE_YES_NO = 20
MENU_TYPE_MULTI_TABLE_SCHEDULE = 100

# --- Schedule constants ---
SCHEDULE_NUM_ROWS = 5
SCHEDULE_MIN_TIME = 0  # 00:00
SCHEDULE_MAX_TIME = 1439  # 23:59

# Day ID to element ID mapping (for schedule POST requests)
# dayId: 0=Sunday, 1=Monday, ..., 6=Saturday
DAY_ELEMENT_IDS: dict[int, int] = {
    0: 10006,  # Sunday
    1: 10000,  # Monday
    2: 10001,  # Tuesday
    3: 10002,  # Wednesday
    4: 10003,  # Thursday
    5: 10004,  # Friday
    6: 10005,  # Saturday
}

# Day names for service calls (lowercase)
DAY_NAME_TO_ID: dict[str, int] = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}

# Gear values
GEAR_OFF = 0
GEAR_1 = 1
GEAR_2 = 2
GEAR_3 = 3
GEAR_OPTIONS = ["off", "gear_1", "gear_2", "gear_3"]
GEAR_NAME_TO_VALUE: dict[str, int] = {
    "off": 0,
    "gear_1": 1,
    "gear_2": 2,
    "gear_3": 3,
}
GEAR_VALUE_TO_NAME: dict[int, str] = {v: k for k, v in GEAR_NAME_TO_VALUE.items()}

# --- Known menu IDs ---
MENU_ID_RECUPERATION_ONOFF = 1049
MENU_ID_RECUPERATION_PARAM = 1051  # Number value 0-30 (unknown purpose)
MENU_ID_PARTY_MODE_TRIGGER = 1053  # Yes/No dialog to activate party mode
MENU_ID_PARTY_MODE_DURATION = 1054  # Number 15-720 minutes
MENU_ID_SCHEDULE_PARENT = 30010  # Parent group for all schedule elements

# --- Temperature sensor txtId mapping ---
TEMP_SENSOR_NAMES: dict[int, str] = {
    795: "Outdoor Air",   # Fresh air from outside
    1841: "Extract Air",  # Air extracted from rooms
    1840: "Supply Air",   # Air supplied to rooms (after heat exchange)
    1842: "Exhaust Air",  # Air exhausted to outside (after heat exchange)
    6158: "Temperature 5",
    6157: "Temperature 6",
}

# txtIds that are temperature sensors (for auto-detection)
TEMP_SENSOR_TXTIDS = {795, 1840, 1841, 1842, 6157, 6158}

# Configuration keys
CONF_USER_ID = "user_id"
CONF_TOKEN = "token"
CONF_MODULE_UDID = "module_udid"
CONF_MODULE_NAME = "module_name"

# Service names
SERVICE_SET_DAY_SCHEDULE = "set_day_schedule"
SERVICE_SET_GEAR_NOW = "set_gear_now"
SERVICE_SET_GEAR_UNTIL = "set_gear_until"
SERVICE_RESTORE_DAY_SCHEDULE = "restore_day_schedule"

# Attributes
ATTR_SCHEDULE = "schedule"
ATTR_GEAR = "gear"
ATTR_DAY = "day"
ATTR_SLOTS = "slots"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]

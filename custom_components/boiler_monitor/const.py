"""Constants for Boiler Monitor."""
from __future__ import annotations

DOMAIN = "boiler_monitor"
VERSION = "1.1.3"

# Config (entities) — set in config flow
CONF_NAME = "name"
CONF_BURNER = "burner_entity"
CONF_BURNER_ON_STATE = "burner_on_state"
CONF_FLOW_TEMP = "flow_temp_entity"
CONF_RETURN_TEMP = "return_temp_entity"
CONF_OUTDOOR_TEMP = "outdoor_temp_entity"
CONF_INDOOR_TEMPS = "indoor_temp_entities"
CONF_SEASON_ENTITY = "season_entity"
CONF_SEASON_STATE = "season_state"
CONF_FLOW_SETPOINT = "flow_setpoint_entity"
CONF_THERMOREG = "thermoregulation_entity"
CONF_PRESSURE = "pressure_entity"

# Options (tuning) — editable later
CONF_SHORT_CYCLE_MIN = "short_cycle_minutes"
CONF_RETURN_THRESHOLD = "return_threshold"
CONF_RETURN_HOT_MINUTES = "return_hot_minutes"
CONF_EFFECT_DELAY_MIN = "effect_check_minutes"
CONF_MIN_RISE = "min_temp_rise"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_CSV_LOG = "csv_log"
CONF_MIN_BURN_SECONDS = "min_burn_seconds"
CONF_PRESSURE_MIN = "pressure_min"
CONF_PRESSURE_MAX = "pressure_max"

DEFAULT_BURNER_ON_STATE = "on"
DEFAULT_SEASON_STATE = "on"
DEFAULT_SHORT_CYCLE_MIN = 10
DEFAULT_RETURN_THRESHOLD = 53.0
DEFAULT_RETURN_HOT_MINUTES = 15
DEFAULT_EFFECT_DELAY_MIN = 45
DEFAULT_MIN_RISE = 0.2
DEFAULT_NOTIFY_SERVICE = ""
DEFAULT_CSV_LOG = True
DEFAULT_MIN_BURN_SECONDS = 20
DEFAULT_PRESSURE_MIN = 1.0
DEFAULT_PRESSURE_MAX = 2.5

# Retention
CYCLE_RETENTION_HOURS = 7 * 24
DAILY_RETENTION_DAYS = 60
SAMPLE_INTERVAL_SECONDS = 60

STORAGE_VERSION = 1

EVENT_SHORT_CYCLE = f"{DOMAIN}_short_cycle"
EVENT_CONDENSATION_LOST = f"{DOMAIN}_condensation_lost"
EVENT_INEFFECTIVE = f"{DOMAIN}_heating_ineffective"
EVENT_CYCLE_END = f"{DOMAIN}_cycle_end"
EVENT_PRESSURE = f"{DOMAIN}_pressure_problem"
EVENT_REGULATION = f"{DOMAIN}_regulation_changed"

MODE_CURVE = "weather_compensation"
MODE_FIXED = "fixed"

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"

STATUS_HEATING = "heating"
STATUS_IDLE = "idle"
STATUS_OFF_SEASON = "off_season"
STATUS_UNAVAILABLE = "unavailable"

CARD_URL = f"/{DOMAIN}/boiler-monitor-card.js"

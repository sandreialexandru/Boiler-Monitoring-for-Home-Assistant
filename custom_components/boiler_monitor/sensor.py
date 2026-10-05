"""Sensors for Boiler Monitor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_FLOW_TEMP,
    CONF_INDOOR_TEMPS,
    CONF_OUTDOOR_TEMP,
    CONF_RETURN_TEMP,
    DOMAIN,
    STATUS_HEATING,
    STATUS_IDLE,
    STATUS_OFF_SEASON,
    STATUS_UNAVAILABLE,
)
from .entity import BoilerEntity
from .monitor import BoilerMonitor

M = SensorStateClass.MEASUREMENT


@dataclass(frozen=True, kw_only=True)
class BoilerSensorDescription(SensorEntityDescription):
    stat: str


SENSORS: tuple[BoilerSensorDescription, ...] = (
    BoilerSensorDescription(key="cycles_today", stat="cycles_today", translation_key="cycles_today", icon="mdi:counter", native_unit_of_measurement="cycles"),
    BoilerSensorDescription(key="short_cycles_today", stat="short_cycles_today", translation_key="short_cycles_today", icon="mdi:sync-alert", native_unit_of_measurement="cycles"),
    BoilerSensorDescription(key="cycles_per_hour", stat="cycles_per_hour", translation_key="cycles_per_hour", icon="mdi:repeat", state_class=M, native_unit_of_measurement="cycles/h", suggested_display_precision=2),
    BoilerSensorDescription(key="avg_burn", stat="avg_burn_min", translation_key="avg_burn", icon="mdi:fire", device_class=SensorDeviceClass.DURATION, state_class=M, native_unit_of_measurement=UnitOfTime.MINUTES, suggested_display_precision=1),
    BoilerSensorDescription(key="avg_off", stat="avg_off_min", translation_key="avg_off", icon="mdi:fire-off", device_class=SensorDeviceClass.DURATION, state_class=M, native_unit_of_measurement=UnitOfTime.MINUTES, suggested_display_precision=1),
    BoilerSensorDescription(key="last_burn", stat="last_burn_min", translation_key="last_burn", icon="mdi:timer-outline", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.MINUTES, suggested_display_precision=1),
    BoilerSensorDescription(key="duty_cycle", stat="duty_cycle", translation_key="duty_cycle", icon="mdi:percent", state_class=M, native_unit_of_measurement=PERCENTAGE, suggested_display_precision=1),
    BoilerSensorDescription(key="burn_time_today", stat="burn_hours_today", translation_key="burn_time_today", icon="mdi:fire-circle", device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.TOTAL_INCREASING, native_unit_of_measurement=UnitOfTime.HOURS, suggested_display_precision=2),
    BoilerSensorDescription(key="condensing_ratio", stat="condensing_ratio", translation_key="condensing_ratio", icon="mdi:water-percent", state_class=M, native_unit_of_measurement=PERCENTAGE, suggested_display_precision=0),
    BoilerSensorDescription(key="delta_t", stat="delta_t", translation_key="delta_t", icon="mdi:thermometer-lines", device_class=SensorDeviceClass.TEMPERATURE, state_class=M, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=1),
    BoilerSensorDescription(key="heating_rate", stat="heating_rate", translation_key="heating_rate", icon="mdi:home-thermometer", state_class=M, native_unit_of_measurement="°C/h", suggested_display_precision=2),
    BoilerSensorDescription(key="balance_point", stat="balance_point", translation_key="balance_point", icon="mdi:scale-balance", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=1),
    BoilerSensorDescription(key="burn_per_hdd", stat="burn_per_hdd", translation_key="burn_per_hdd", icon="mdi:chart-line", state_class=M, native_unit_of_measurement="h/°C·day", suggested_display_precision=3),
)

STATUS_DESC = SensorEntityDescription(
    key="status",
    translation_key="status",
    icon="mdi:water-boiler",
    device_class=SensorDeviceClass.ENUM,
    options=[STATUS_HEATING, STATUS_IDLE, STATUS_OFF_SEASON, STATUS_UNAVAILABLE],
)

# Needed by entities that don't depend on optional sensors
REQUIRES: dict[str, tuple[str, ...]] = {
    "condensing_ratio": (CONF_RETURN_TEMP,),
    "delta_t": (CONF_FLOW_TEMP, CONF_RETURN_TEMP),
    "heating_rate": (CONF_INDOOR_TEMPS,),
    "balance_point": (CONF_OUTDOOR_TEMP,),
    "burn_per_hdd": (CONF_OUTDOOR_TEMP,),
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    monitor: BoilerMonitor = entry.runtime_data
    cfg = monitor.cfg
    ents: list[SensorEntity] = [BoilerStatusSensor(monitor, STATUS_DESC)]
    for d in SENSORS:
        if all(cfg.get(k) for k in REQUIRES.get(d.key, ())):
            ents.append(BoilerStatSensor(monitor, d))
    async_add_entities(ents)


class BoilerStatSensor(BoilerEntity, SensorEntity):
    entity_description: BoilerSensorDescription

    @property
    def native_value(self) -> Any:
        return self.monitor.stats().get(self.entity_description.stat)


class BoilerStatusSensor(BoilerEntity, SensorEntity):
    """Main entity: status + everything the card needs as attributes."""

    _unrecorded_attributes = frozenset(
        {"timeline", "daily", "regression", "entities", "stats", "thresholds"}
    )

    @property
    def native_value(self) -> str:
        return self.monitor.status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        m = self.monitor
        cfg = m.cfg
        reg = er.async_get(self.hass)
        entities = {}
        for e in reg.entities.get_entries_for_config_entry_id(m.entry.entry_id):
            key = e.unique_id.removeprefix(f"{m.entry.entry_id}_")
            entities[key] = e.entity_id
        return {
            "monitor": DOMAIN,
            "stats": m.stats(),
            "flow": m.flow_temp(),
            "return": m.return_temp(),
            "outdoor": m.outdoor_temp(),
            "indoor": None if (v := m.indoor_avg()) is None else round(v, 2),
            "short_cycling": m.short_cycling,
            "condensation_lost": m.condensation_lost,
            "heating_ineffective": m.heating_ineffective,
            "thresholds": {
                "short_cycle_min": round(m.short_cycle_s / 60, 1),
                "return": m.return_threshold,
            },
            "sources": {
                "burner": cfg.get("burner_entity"),
                "flow": cfg.get(CONF_FLOW_TEMP),
                "return": cfg.get(CONF_RETURN_TEMP),
                "outdoor": cfg.get(CONF_OUTDOOR_TEMP),
            },
            "timeline": m.timeline(24),
            "daily": m.daily(30),
            "regression": m.regression(),
            "entities": entities,
        }

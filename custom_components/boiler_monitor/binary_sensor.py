"""Problem binary sensors for Boiler Monitor."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_INDOOR_TEMPS, CONF_RETURN_TEMP
from .entity import BoilerEntity
from .monitor import BoilerMonitor


@dataclass(frozen=True, kw_only=True)
class BoilerBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[BoilerMonitor], bool]
    requires: str | None = None


BINARY: tuple[BoilerBinaryDescription, ...] = (
    BoilerBinaryDescription(
        key="burner", translation_key="burner", icon="mdi:fire",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda m: m.burner_on and m.season_active,
    ),
    BoilerBinaryDescription(
        key="short_cycling", translation_key="short_cycling", icon="mdi:sync-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda m: m.short_cycling,
    ),
    BoilerBinaryDescription(
        key="condensation_lost", translation_key="condensation_lost", icon="mdi:water-off",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda m: m.condensation_lost, requires=CONF_RETURN_TEMP,
    ),
    BoilerBinaryDescription(
        key="heating_ineffective", translation_key="heating_ineffective", icon="mdi:home-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda m: m.heating_ineffective, requires=CONF_INDOOR_TEMPS,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    monitor: BoilerMonitor = entry.runtime_data
    async_add_entities(
        BoilerBinary(monitor, d) for d in BINARY if not d.requires or monitor.cfg.get(d.requires)
    )


class BoilerBinary(BoilerEntity, BinarySensorEntity):
    entity_description: BoilerBinaryDescription

    @property
    def is_on(self) -> bool:
        return bool(self.entity_description.value_fn(self.monitor))

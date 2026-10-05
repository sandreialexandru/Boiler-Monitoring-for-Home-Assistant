"""Base entity for Boiler Monitor."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, EntityDescription

from .const import DOMAIN, SIGNAL_UPDATE, VERSION
from .monitor import BoilerMonitor


class BoilerEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, monitor: BoilerMonitor, description: EntityDescription) -> None:
        self.monitor = monitor
        self.entity_description = description
        entry = monitor.entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=monitor.name,
            manufacturer="Boiler Monitor",
            model="Burner & condensation monitor",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self.monitor.entry.entry_id),
                self.async_write_ha_state,
            )
        )

"""Boiler Monitor — advanced burner/condensation monitoring for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import CARD_URL, DOMAIN, VERSION
from .monitor import BoilerMonitor

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type BoilerConfigEntry = ConfigEntry[BoilerMonitor]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card and services once."""
    await _register_card(hass)

    async def _reset(call: ServiceCall) -> None:
        ids = call.data.get("entry_id")
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.state is ConfigEntryState.LOADED and (not ids or entry.entry_id in ids):
                await entry.runtime_data.async_reset()

    hass.services.async_register(
        DOMAIN,
        "reset_statistics",
        _reset,
        schema=vol.Schema({vol.Optional("entry_id"): vol.All(cv.ensure_list, [cv.string])}),
    )
    return True


async def _register_card(hass: HomeAssistant) -> None:
    """Serve the card JS and load it on every dashboard (no manual resource)."""
    path = Path(__file__).parent / "frontend" / "boiler-monitor-card.js"
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(path), False)]
        )
    except (AttributeError, ImportError):  # pragma: no cover - test env without http
        _LOGGER.debug("HTTP not available, card not registered")
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    except ImportError:  # pragma: no cover
        pass


async def async_setup_entry(hass: HomeAssistant, entry: BoilerConfigEntry) -> bool:
    monitor = BoilerMonitor(hass, entry)
    await monitor.async_start()
    entry.runtime_data = monitor
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))
    return True


async def _reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BoilerConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.async_stop()
    return ok

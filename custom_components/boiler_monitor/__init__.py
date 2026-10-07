"""Boiler Monitor — advanced burner/condensation monitoring for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant, ServiceCall
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
    """Serve the card JS and make every dashboard load it.

    1. The file is served by the integration at CARD_URL.
    2. It is added as a Lovelace **resource** (storage mode). Resources are
       fetched every time a dashboard loads, so the card is found even after
       the browser / companion app cache expires.
    3. Only when that is impossible (YAML-mode dashboards, where resources
       are read-only) it is registered as an extra frontend module instead.
       Extra modules run very early, before Home Assistant may swap in the
       scoped custom-element registry, which made the card intermittently
       "not exist" - so they are a fallback, not the default.
    The ?v=<version> query string busts caches on every update.
    """
    path = Path(__file__).parent / "frontend" / "boiler-monitor-card.js"
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(path), False)]
        )
    except RuntimeError:
        pass  # already registered (integration reloaded)
    except (AttributeError, ImportError):  # pragma: no cover - no http in tests
        _LOGGER.debug("HTTP not available, card not registered")
        return

    url = f"{CARD_URL}?v={VERSION}"

    def _extra_module() -> None:
        try:
            from homeassistant.components.frontend import add_extra_js_url

            add_extra_js_url(hass, url)
        except ImportError:  # pragma: no cover
            pass

    async def _add_resource(_event: Event | None = None) -> None:
        try:
            if not await _ensure_lovelace_resource(hass, url):
                _extra_module()
        except Exception as err:  # noqa: BLE001 - never block setup
            _LOGGER.warning("Could not add the Boiler Monitor card as a dashboard resource: %s", err)
            _extra_module()

    if hass.state is CoreState.running:
        await _add_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _add_resource)


def _lovelace_resources(hass: HomeAssistant):
    data = hass.data.get("lovelace")
    if data is None:
        return None
    res = getattr(data, "resources", None)
    if res is None and isinstance(data, dict):
        res = data.get("resources")
    # ResourceYAMLCollection (YAML mode) has no create/update
    return res if res is not None and hasattr(res, "async_create_item") else None


async def _ensure_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Create or update the card resource (storage-mode dashboards).

    Returns False when resources can't be managed (YAML mode).
    """
    resources = _lovelace_resources(hass)
    if resources is None:
        _LOGGER.info(
            "Lovelace is in YAML mode: add %s (type: module) to your resources "
            "if the Boiler Monitor card does not show up", url
        )
        return False
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    mine = [i for i in resources.async_items() if str(i.get("url", "")).split("?")[0] == CARD_URL]
    if mine:
        first, *dupes = mine
        if first.get("url") != url or first.get("type") != "module":
            await resources.async_update_item(first["id"], {"res_type": "module", "url": url})
        for d in dupes:
            await resources.async_delete_item(d["id"])
        return True
    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.info("Added the Boiler Monitor card to the dashboard resources (%s)", url)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the dashboard resource when the last boiler is deleted."""
    if hass.config_entries.async_entries(DOMAIN):
        return
    resources = _lovelace_resources(hass)
    if resources is None:
        return
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    for item in list(resources.async_items()):
        if str(item.get("url", "")).split("?")[0] == CARD_URL:
            await resources.async_delete_item(item["id"])


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

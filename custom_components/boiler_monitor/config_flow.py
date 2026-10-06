"""Config & options flow for Boiler Monitor."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector as sel

from .const import (
    CONF_BURNER,
    CONF_BURNER_ON_STATE,
    CONF_CSV_LOG,
    CONF_EFFECT_DELAY_MIN,
    CONF_FLOW_SETPOINT,
    CONF_FLOW_TEMP,
    CONF_INDOOR_TEMPS,
    CONF_MIN_BURN_SECONDS,
    CONF_MIN_RISE,
    CONF_NAME,
    CONF_NOTIFY_SERVICE,
    CONF_OUTDOOR_TEMP,
    CONF_PRESSURE,
    CONF_PRESSURE_MAX,
    CONF_PRESSURE_MIN,
    CONF_RETURN_HOT_MINUTES,
    CONF_RETURN_TEMP,
    CONF_RETURN_THRESHOLD,
    CONF_SEASON_ENTITY,
    CONF_SEASON_STATE,
    CONF_SHORT_CYCLE_MIN,
    CONF_THERMOREG,
    DEFAULT_BURNER_ON_STATE,
    DEFAULT_CSV_LOG,
    DEFAULT_EFFECT_DELAY_MIN,
    DEFAULT_MIN_BURN_SECONDS,
    DEFAULT_MIN_RISE,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_PRESSURE_MAX,
    DEFAULT_PRESSURE_MIN,
    DEFAULT_RETURN_HOT_MINUTES,
    DEFAULT_RETURN_THRESHOLD,
    DEFAULT_SEASON_STATE,
    DEFAULT_SHORT_CYCLE_MIN,
    DOMAIN,
)

TEMP_SENSOR = sel.EntitySelector(
    sel.EntitySelectorConfig(domain="sensor", device_class="temperature")
)


def _opt(key: str, src: dict[str, Any]) -> vol.Optional:
    """Optional field that can be cleared (suggested value, no default)."""
    return vol.Optional(key, description={"suggested_value": src.get(key)})


def entities_schema(src: dict[str, Any], with_name: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_name:
        fields[vol.Required(CONF_NAME, default=src.get(CONF_NAME, "Centrala"))] = str
    fields.update(
        {
            vol.Required(CONF_BURNER, default=src.get(CONF_BURNER, vol.UNDEFINED)): sel.EntitySelector(
                sel.EntitySelectorConfig(
                    domain=["binary_sensor", "switch", "input_boolean", "climate", "sensor"]
                )
            ),
            vol.Required(
                CONF_BURNER_ON_STATE,
                default=src.get(CONF_BURNER_ON_STATE, DEFAULT_BURNER_ON_STATE),
            ): sel.TextSelector(),
            _opt(CONF_FLOW_TEMP, src): TEMP_SENSOR,
            _opt(CONF_RETURN_TEMP, src): TEMP_SENSOR,
            _opt(CONF_FLOW_SETPOINT, src): TEMP_SENSOR,
            _opt(CONF_THERMOREG, src): sel.EntitySelector(
                sel.EntitySelectorConfig(domain=["switch", "binary_sensor", "input_boolean"])
            ),
            _opt(CONF_OUTDOOR_TEMP, src): TEMP_SENSOR,
            _opt(CONF_INDOOR_TEMPS, src): sel.EntitySelector(
                sel.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=True)
            ),
            _opt(CONF_PRESSURE, src): sel.EntitySelector(
                sel.EntitySelectorConfig(domain="sensor", device_class="pressure")
            ),
            _opt(CONF_SEASON_ENTITY, src): sel.EntitySelector(sel.EntitySelectorConfig()),
            vol.Optional(
                CONF_SEASON_STATE, default=src.get(CONF_SEASON_STATE, DEFAULT_SEASON_STATE)
            ): sel.TextSelector(),
        }
    )
    return vol.Schema(fields)


def _num(lo: float, hi: float, step: float, unit: str) -> sel.NumberSelector:
    return sel.NumberSelector(
        sel.NumberSelectorConfig(
            min=lo, max=hi, step=step, unit_of_measurement=unit, mode=sel.NumberSelectorMode.BOX
        )
    )


def options_schema(src: dict[str, Any]) -> vol.Schema:
    g = src.get
    return vol.Schema(
        {
            vol.Required(CONF_SHORT_CYCLE_MIN, default=g(CONF_SHORT_CYCLE_MIN, DEFAULT_SHORT_CYCLE_MIN)): _num(1, 60, 1, "min"),
            vol.Required(CONF_RETURN_THRESHOLD, default=g(CONF_RETURN_THRESHOLD, DEFAULT_RETURN_THRESHOLD)): _num(30, 70, 0.5, "°C"),
            vol.Required(CONF_RETURN_HOT_MINUTES, default=g(CONF_RETURN_HOT_MINUTES, DEFAULT_RETURN_HOT_MINUTES)): _num(1, 120, 1, "min"),
            vol.Required(CONF_EFFECT_DELAY_MIN, default=g(CONF_EFFECT_DELAY_MIN, DEFAULT_EFFECT_DELAY_MIN)): _num(10, 240, 5, "min"),
            vol.Required(CONF_MIN_RISE, default=g(CONF_MIN_RISE, DEFAULT_MIN_RISE)): _num(0.1, 3, 0.1, "°C"),
            vol.Required(CONF_MIN_BURN_SECONDS, default=g(CONF_MIN_BURN_SECONDS, DEFAULT_MIN_BURN_SECONDS)): _num(0, 300, 5, "s"),
            vol.Required(CONF_PRESSURE_MIN, default=g(CONF_PRESSURE_MIN, DEFAULT_PRESSURE_MIN)): _num(0.3, 2.0, 0.1, "bar"),
            vol.Required(CONF_PRESSURE_MAX, default=g(CONF_PRESSURE_MAX, DEFAULT_PRESSURE_MAX)): _num(1.5, 3.5, 0.1, "bar"),
            vol.Optional(CONF_NOTIFY_SERVICE, description={"suggested_value": g(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)}): sel.TextSelector(),
            vol.Required(CONF_CSV_LOG, default=g(CONF_CSV_LOG, DEFAULT_CSV_LOG)): sel.BooleanSelector(),
        }
    )


class BoilerMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_BURNER])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=entities_schema({}, True))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            data = {CONF_NAME: entry.data.get(CONF_NAME, entry.title), **user_input}
            return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reconfigure", data_schema=entities_schema(dict(entry.data), False)
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BoilerMonitorOptionsFlow()


class BoilerMonitorOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=options_schema(dict(self.config_entry.options))
        )

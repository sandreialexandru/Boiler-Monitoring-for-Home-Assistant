"""Behavioural tests: simulate a boiler and check what the integration sees."""
from datetime import timedelta

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.boiler_monitor.const import DOMAIN

BURNER = "switch.releu_centrala"
DATA = {
    "name": "Centrala",
    "burner_entity": BURNER,
    "burner_on_state": "on",
    "flow_temp_entity": "sensor.tur",
    "return_temp_entity": "sensor.retur",
    "outdoor_temp_entity": "sensor.exterior",
    "indoor_temp_entities": ["sensor.living", "sensor.dormitor"],
}
OPTIONS = {
    "short_cycle_minutes": 10,
    "return_threshold": 53,
    "return_hot_minutes": 15,
    "effect_check_minutes": 45,
    "min_temp_rise": 0.2,
    "min_burn_seconds": 20,
    "notify_service": "notify.mobile_app_telefon",
    "csv_log": True,
}


def temps(hass, flow=60, ret=45, out=2, liv=21.0, dor=20.0):
    hass.states.async_set("sensor.tur", flow, {"device_class": "temperature"})
    hass.states.async_set("sensor.retur", ret, {"device_class": "temperature"})
    hass.states.async_set("sensor.exterior", out, {"device_class": "temperature"})
    hass.states.async_set("sensor.living", liv, {"device_class": "temperature"})
    hass.states.async_set("sensor.dormitor", dor, {"device_class": "temperature"})


async def advance(hass, freezer, minutes):
    """Move time forward minute by minute so the 60 s sampler runs."""
    for _ in range(int(minutes)):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()


async def setup(hass, data=DATA, options=OPTIONS):
    entry = MockConfigEntry(domain=DOMAIN, data=data, options=options, unique_id=data["burner_entity"])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def burner(hass, on: bool):
    hass.states.async_set(BURNER, "on" if on else "off")
    await hass.async_block_till_done()


def st(hass, eid):
    return hass.states.get(eid)


async def test_config_flow(hass: HomeAssistant):
    hass.states.async_set(BURNER, "off")
    res = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert res["type"] is FlowResultType.FORM
    res = await hass.config_entries.flow.async_configure(
        res["flow_id"], {"name": "Centrala", "burner_entity": BURNER, "burner_on_state": "on"}
    )
    assert res["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    # Minimal config: only burner. Optional-sensor entities must not exist.
    assert st(hass, "sensor.centrala_status").state == "idle"
    assert st(hass, "sensor.centrala_cycles_today") is not None
    assert st(hass, "sensor.centrala_flow_return_dt") is None
    assert st(hass, "binary_sensor.centrala_condensation_lost") is None

    # Options flow
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    res = await hass.config_entries.options.async_init(entry.entry_id)
    res = await hass.config_entries.options.async_configure(res["flow_id"], {**OPTIONS, "short_cycle_minutes": 7})
    assert res["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert hass.states.get("sensor.centrala_status").attributes["thresholds"]["short_cycle_min"] == 7


async def test_cycles_and_short_cycle(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass)
    await burner(hass, False)
    await setup(hass)

    # Normal cycle: 20 min on, 25 min off
    await burner(hass, True)
    assert st(hass, "sensor.centrala_status").state == "heating"
    assert st(hass, "binary_sensor.centrala_burner").state == "on"
    await advance(hass, freezer, 20)
    await burner(hass, False)
    await advance(hass, freezer, 25)
    await burner(hass, True)
    await advance(hass, freezer, 10)
    await burner(hass, False)
    assert st(hass, "binary_sensor.centrala_short_cycling").state == "off"
    sc = lambda: [c for c in notify if c.data["data"]["tag"].endswith("short_cycle")]
    assert sc() == []

    # Short cycle: restart after only 4 minutes
    await advance(hass, freezer, 4)
    await burner(hass, True)
    await hass.async_block_till_done()
    assert st(hass, "binary_sensor.centrala_short_cycling").state == "on"
    assert len(sc()) == 1
    assert "4.0 min" in sc()[0].data["message"]

    # Second short cycle within the hour: event yes, push throttled
    await advance(hass, freezer, 5)
    await burner(hass, False)
    await advance(hass, freezer, 3)
    await burner(hass, True)
    assert len(sc()) == 1
    assert st(hass, "sensor.centrala_short_cycles_today").state == "2"
    assert st(hass, "sensor.centrala_cycles_today").state == "4"

    await advance(hass, freezer, 6)
    await burner(hass, False)
    attrs = st(hass, "sensor.centrala_status").attributes
    s = attrs["stats"]
    # burns: 20, 10, 5, 6 -> avg 10.25
    assert s["avg_burn_min"] == pytest.approx(10.2, abs=0.1)
    # offs: 25, 4, 3 -> avg 10.67
    assert s["avg_off_min"] == pytest.approx(10.7, abs=0.1)
    assert s["burn_hours_today"] == pytest.approx(41 / 60, abs=0.02)
    assert len(attrs["timeline"]) == 4
    assert [x[2] for x in attrs["timeline"]] == [0, 0, 1, 1]
    assert float(st(hass, "sensor.centrala_flow_return_dt").state) == 15

    # Short-cycling flag clears after an hour without short cycles
    await advance(hass, freezer, 61)
    assert st(hass, "binary_sensor.centrala_short_cycling").state == "off"


async def test_glitch_ignored(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass)
    await burner(hass, False)
    await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 15)
    await burner(hass, False)
    await advance(hass, freezer, 30)
    # 5-second relay chatter
    await burner(hass, True)
    freezer.tick(timedelta(seconds=5))
    await burner(hass, False)
    assert st(hass, "sensor.centrala_cycles_today").state == "1"
    # Real restart 30 min after the *real* stop is not a short cycle
    await advance(hass, freezer, 1)
    await burner(hass, True)
    assert st(hass, "sensor.centrala_short_cycles_today").state == "0"


async def test_restart_no_false_short_cycle(hass: HomeAssistant, freezer):
    """The blueprint's problem: after restart last_changed resets."""
    freezer.move_to("2026-11-10 08:00:00+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass)
    await burner(hass, False)
    entry = await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 15)
    await burner(hass, False)
    await advance(hass, freezer, 30)

    # Restart integration (like an HA restart): stored stop time survives
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_cycles_today").state == "1"
    await advance(hass, freezer, 2)
    await burner(hass, True)
    assert st(hass, "sensor.centrala_short_cycles_today").state == "0"
    assert not [c for c in notify if "short" in c.data["title"]]
    # off time measured from the real stop (32 min), not from the restart
    tl = st(hass, "sensor.centrala_status").attributes["timeline"]
    assert len(tl) == 2

    # Restart while burning -> partial cycle, never a short cycle
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    await advance(hass, freezer, 10)
    await burner(hass, False)
    assert st(hass, "sensor.centrala_short_cycles_today").state == "0"


async def test_condensation(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass, ret=45)
    await burner(hass, False)
    await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 30)  # 30 min condensing
    temps(hass, flow=75, ret=58)
    await hass.async_block_till_done()
    await advance(hass, freezer, 14)
    assert st(hass, "binary_sensor.centrala_condensation_lost").state == "off"
    await advance(hass, freezer, 2)
    assert st(hass, "binary_sensor.centrala_condensation_lost").state == "on"
    assert any("condensation" in c.data["title"] for c in notify)
    ratio = float(st(hass, "sensor.centrala_condensing_ratio_24h").state)
    assert 60 < ratio < 70  # ~30 of ~46 burning minutes
    # Return drops below threshold-1 -> clears
    temps(hass, flow=60, ret=51)
    await hass.async_block_till_done()
    assert st(hass, "binary_sensor.centrala_condensation_lost").state == "off"


async def test_heating_effect(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass, liv=20.0, dor=20.0)
    await burner(hass, False)
    await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 20)
    temps(hass, liv=20.1, dor=20.0)  # +0.05 avg
    await advance(hass, freezer, 26)
    assert st(hass, "binary_sensor.centrala_heating_ineffective").state == "on"
    assert any("without effect" in c.data["title"] for c in notify)
    await burner(hass, False)
    await advance(hass, freezer, 20)
    await burner(hass, True)
    temps(hass, liv=20.6, dor=20.6)  # +0.55 over 45 min
    await advance(hass, freezer, 46)
    assert st(hass, "binary_sensor.centrala_heating_ineffective").state == "off"
    rate = float(st(hass, "sensor.centrala_heating_rate").state)
    assert 0.6 < rate < 0.8


async def test_season_gating(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    temps(hass)
    hass.states.async_set("input_boolean.iarna", "off")
    await burner(hass, False)
    await setup(hass, {**DATA, "season_entity": "input_boolean.iarna", "season_state": "on"})
    assert st(hass, "sensor.centrala_status").state == "off_season"
    await burner(hass, True)  # DHW in summer: ignored
    await advance(hass, freezer, 5)
    await burner(hass, False)
    assert st(hass, "sensor.centrala_cycles_today").state == "0"
    hass.states.async_set("input_boolean.iarna", "on")
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_status").state == "idle"
    await burner(hass, True)
    assert st(hass, "sensor.centrala_cycles_today").state == "1"


async def test_climate_burner(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    hass.states.async_set("climate.ariston", "heat", {"hvac_action": "idle"})
    await setup(hass, {"name": "Ariston", "burner_entity": "climate.ariston", "burner_on_state": "heating"}, {})
    assert st(hass, "sensor.ariston_status").state == "idle"
    hass.states.async_set("climate.ariston", "heat", {"hvac_action": "heating"})
    await hass.async_block_till_done()
    assert st(hass, "sensor.ariston_status").state == "heating"


async def test_outdoor_regression(hass: HomeAssistant, freezer):
    """5 days with colder days burning more -> balance point appears."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass)
    await burner(hass, False)
    await setup(hass)
    # outdoor temp, burn minutes per hour
    for out, burn_per_h in [(0, 30), (5, 20), (10, 10), (2, 26), (8, 14)]:
        temps(hass, out=out)
        for _h in range(24):
            await burner(hass, True)
            await advance(hass, freezer, burn_per_h)
            await burner(hass, False)
            await advance(hass, freezer, 60 - burn_per_h)
    attrs = st(hass, "sensor.centrala_status").attributes
    reg = attrs["regression"]
    assert reg is not None and reg["n"] >= 4
    assert reg["slope"] == pytest.approx(-0.8, abs=0.1)  # -2 min/h per °C = -0.8 h/day
    assert float(st(hass, "sensor.centrala_balance_point").state) == pytest.approx(15, abs=1)
    assert st(hass, "sensor.centrala_burn_hours_per_degree_day_7d").state not in ("unknown", None)
    assert len(attrs["daily"]) >= 5


async def test_reset_service(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:00+02:00")
    temps(hass)
    await burner(hass, False)
    await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 10)
    await burner(hass, False)
    await hass.services.async_call(DOMAIN, "reset_statistics", {}, blocking=True)
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_cycles_today").state == "0"


async def test_csv_log(hass: HomeAssistant, freezer):
    import os
    freezer.move_to("2026-11-10 08:00:00+02:00")
    path0 = hass.config.path("boiler_monitor", "centrala.csv")
    if os.path.exists(path0):
        os.remove(path0)
    temps(hass)
    await burner(hass, False)
    await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 10)
    await burner(hass, False)
    await hass.async_block_till_done()
    path = hass.config.path("boiler_monitor", "centrala.csv")
    lines = await hass.async_add_executor_job(lambda: open(path).read().splitlines())
    assert lines[0].startswith("time;event")
    assert lines[1].split(";")[1] == "START"
    assert lines[2].split(";")[1:3] == ["STOP", "10.0"]
    await hass.async_add_executor_job(os.remove, path)


async def test_dump_card_fixture(hass: HomeAssistant, freezer):
    """Generate realistic attributes for the card preview (not an assertion test)."""
    import json, os, random
    out = os.environ.get("CARD_FIXTURE")
    if not out:
        pytest.skip("CARD_FIXTURE not set")
    random.seed(4)
    freezer.move_to("2026-10-22 00:00:30+03:00")
    temps(hass)
    await burner(hass, False)
    ariston(hass, thermo="on")
    await setup(hass, ARISTON, {**OPTIONS, "notify_service": ""})
    outs = [9, 7, 6, 8, 4, 3, 5, 2, 1, 3, 6, 4, 2, 0]
    for day, o in enumerate(outs):
        for h in range(24):
            hour_out = o + (3 if 11 <= h <= 17 else -1)
            tgt = round(38 + 1.4 * (12 - hour_out) + random.uniform(-0.5, 0.5), 1)
            ariston(hass, setpoint=tgt, thermo="on", pressure=round(1.62 - 0.004 * day, 2))
            temps(hass, out=hour_out, flow=round(tgt - 1.5 + random.uniform(-2, 1), 1), ret=44 + (h % 5), liv=20.8, dor=20.4)
            burn = max(2, int(36 - 2.6 * hour_out + random.randint(-4, 4)))
            if day == len(outs) - 1 and h == 15:
                break
            if h in (6, 7) and day >= 12:  # morning short-cycling
                for _ in range(3):
                    await burner(hass, True); await advance(hass, freezer, 4)
                    await burner(hass, False); await advance(hass, freezer, 3)
                await burner(hass, True); await advance(hass, freezer, burn // 2)
                await burner(hass, False); await advance(hass, freezer, 60 - 21 - burn // 2)
                continue
            await burner(hass, True); await advance(hass, freezer, burn // 2)
            await burner(hass, False); await advance(hass, freezer, 30 - burn // 2)
            await burner(hass, True); await advance(hass, freezer, burn - burn // 2)
            await burner(hass, False); await advance(hass, freezer, 30 - (burn - burn // 2))
    temps(hass, out=3, flow=66, ret=55, liv=20.9, dor=20.5)
    await burner(hass, True)
    await advance(hass, freezer, 17)
    s = st(hass, "sensor.centrala_status")
    attrs = dict(s.attributes)
    attrs["friendly_name"] = "Centrala Status"
    open(out, "w").write(json.dumps({"state": s.state, "attributes": attrs, "now": dt_util.utcnow().timestamp()}, default=str))


async def test_condensing_at_threshold(hass: HomeAssistant, freezer):
    """Return exactly at the threshold still counts as condensing."""
    freezer.move_to("2026-11-10 08:00:00+02:00")
    temps(hass, ret=44.0)
    await burner(hass, False)
    await setup(hass, options={**OPTIONS, "return_threshold": 45, "notify_service": ""})
    await burner(hass, True)
    await advance(hass, freezer, 10)
    temps(hass, ret=45.0)
    await hass.async_block_till_done()
    await advance(hass, freezer, 10)
    s = st(hass, "sensor.centrala_condensing_ratio_24h")
    assert float(s.state) == 100
    assert s.attributes["return_threshold"] == 45
    assert s.attributes["return_max_while_burning_24h"] == 45.0
    assert s.attributes["burning_minutes_sampled_24h"] == 20
    temps(hass, ret=45.5)
    await hass.async_block_till_done()
    await advance(hass, freezer, 5)
    s = st(hass, "sensor.centrala_condensing_ratio_24h")
    assert float(s.state) == 80
    assert s.attributes["condensing_minutes_24h"] == 20


ARISTON = {
    **DATA,
    "flow_setpoint_entity": "sensor.ariston_ch_flow_setpoint_temp",
    "thermoregulation_entity": "switch.ariston_automatic_thermoregulation",
    "pressure_entity": "sensor.ariston_heating_circuit_pressure",
}


def ariston(hass, setpoint=55.0, thermo="off", pressure=1.7):
    hass.states.async_set("sensor.ariston_ch_flow_setpoint_temp", setpoint, {"device_class": "temperature"})
    hass.states.async_set("switch.ariston_automatic_thermoregulation", thermo)
    hass.states.async_set("sensor.ariston_heating_circuit_pressure", pressure, {"device_class": "pressure", "unit_of_measurement": "bar"})


async def test_fixed_flow_deviation_and_logging(hass: HomeAssistant, freezer):
    import os
    freezer.move_to("2026-11-10 08:00:00+02:00")
    path = hass.config.path("boiler_monitor", "centrala.csv")
    if os.path.exists(path):
        os.remove(path)
    temps(hass, flow=50)
    ariston(hass, setpoint=55, thermo="off")
    await burner(hass, False)
    await setup(hass, ARISTON, {**OPTIONS, "notify_service": ""})
    assert st(hass, "sensor.centrala_regulation_mode").state == "fixed"
    await burner(hass, True)
    # First 5 minutes (warm-up) are ignored for flow-vs-target
    temps(hass, flow=30)
    await advance(hass, freezer, 4)
    temps(hass, flow=52)
    await advance(hass, freezer, 20)
    dev = float(st(hass, "sensor.centrala_flow_vs_target_24h").state)
    assert dev == pytest.approx(-3.0, abs=0.2)
    attrs = st(hass, "sensor.centrala_status").attributes
    assert attrs["flow_target"] == 55 and attrs["regulation_mode"] == "fixed"
    # Fixed setpoint changed by the user -> logged
    ariston(hass, setpoint=50, thermo="off")
    await hass.async_block_till_done()
    # Thermoregulation switched on -> mode change logged + event
    events = []
    hass.bus.async_listen("boiler_monitor_regulation_changed", lambda e: events.append(e))
    ariston(hass, setpoint=48, thermo="on")
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_regulation_mode").state == "weather_compensation"
    assert events and events[0].data["mode"] == "weather_compensation"
    await hass.async_block_till_done()
    lines = await hass.async_add_executor_job(lambda: open(path).read())
    assert "SETPOINT;" in lines and "from=55.0;to=50.0" in lines
    assert "MODE;" in lines and "mode=weather_compensation" in lines


async def test_weather_compensation_curve(hass: HomeAssistant, freezer):
    """Target follows outdoor -> curve points + slope."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass)
    ariston(hass, thermo="on")
    await burner(hass, False)
    await setup(hass, ARISTON, {**OPTIONS, "notify_service": ""})
    # 12 hours, outdoor from 10 to -1, curve: target = 40 + 1.5 * (10 - out)
    for h in range(12):
        out = 10 - h
        temps(hass, out=out)
        ariston(hass, setpoint=40 + 1.5 * (10 - out), thermo="on")
        await hass.async_block_till_done()
        await advance(hass, freezer, 60)
    attrs = st(hass, "sensor.centrala_status").attributes
    pts = attrs["curve_points"]
    assert len(pts) >= 10 and all(p[3] == 1 for p in pts)
    fit = attrs["curve_fit"]
    assert fit["slope"] == pytest.approx(1.5, abs=0.05)
    assert fit["at_0"] == pytest.approx(55, abs=0.5)
    assert float(st(hass, "sensor.centrala_heating_curve_slope").state) == pytest.approx(1.5, abs=0.05)


async def test_pressure_alert_and_trend(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-01 00:00:30+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass)
    ariston(hass, pressure=1.6)
    await burner(hass, False)
    await setup(hass, ARISTON, OPTIONS)
    assert st(hass, "binary_sensor.centrala_pressure_problem").state == "off"
    # Slow leak: 1.6 -> ~1.3 over 4 days
    for day in range(4):
        ariston(hass, pressure=round(1.6 - 0.1 * day, 2))
        await hass.async_block_till_done()
        await advance(hass, freezer, 24 * 60)
    change = float(st(hass, "sensor.centrala_pressure_change_7d").state)
    assert change == pytest.approx(-0.3, abs=0.05)
    # Drop below minimum -> alert, works even out of season logic
    ariston(hass, pressure=0.8)
    await hass.async_block_till_done()
    assert st(hass, "binary_sensor.centrala_pressure_problem").state == "on"
    assert any("pressure" in c.data["title"] for c in notify)
    ariston(hass, pressure=1.4)
    await hass.async_block_till_done()
    assert st(hass, "binary_sensor.centrala_pressure_problem").state == "off"


async def test_card_resource_registration(hass: HomeAssistant):
    """The card is added to (and kept up to date in) the dashboard resources."""
    from homeassistant.setup import async_setup_component
    from custom_components.boiler_monitor import _ensure_lovelace_resource, _lovelace_resources
    from custom_components.boiler_monitor.const import CARD_URL

    assert await async_setup_component(hass, "lovelace", {})
    res = _lovelace_resources(hass)
    assert res is not None
    await _ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.0.0")
    await _ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.0.0")
    items = [i for i in res.async_items() if i["url"].startswith(CARD_URL)]
    assert len(items) == 1 and items[0]["type"] == "module"
    # New version -> same resource updated, not duplicated
    await _ensure_lovelace_resource(hass, f"{CARD_URL}?v=9.9.9")
    items = [i for i in res.async_items() if i["url"].startswith(CARD_URL)]
    assert len(items) == 1 and items[0]["url"].endswith("v=9.9.9")

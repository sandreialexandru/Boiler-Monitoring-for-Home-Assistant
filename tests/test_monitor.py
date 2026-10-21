"""Behavioural tests: simulate a boiler and check what the integration sees."""
from datetime import timedelta

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
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
    base = {"name": "Centrala", "burner_entity": BURNER, "burner_on_state": "on"}
    # Indoor sensors and an outdoor source (sensor or weather) are required
    with pytest.raises(InvalidData):  # indoor sensors are a required field
        await hass.config_entries.flow.async_configure(res["flow_id"], base)
    res = await hass.config_entries.flow.async_configure(res["flow_id"], {**base, "indoor_temp_entities": []})
    assert res["errors"] == {"indoor_temp_entities": "indoor_required", "base": "outdoor_required"}
    res = await hass.config_entries.flow.async_configure(
        res["flow_id"], {**base, "indoor_temp_entities": ["sensor.living"]}
    )
    assert res["errors"] == {"base": "outdoor_required"}
    hass.states.async_set("weather.acasa", "sunny", {"temperature": 7.5, "temperature_unit": "°C"})
    hass.states.async_set("sensor.living", 21.0, {"device_class": "temperature"})
    res = await hass.config_entries.flow.async_configure(
        res["flow_id"], {**base, "indoor_temp_entities": ["sensor.living"], "weather_entity": "weather.acasa"}
    )
    assert res["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    # Minimal config: burner + indoor + weather. Entities needing other sensors must not exist.
    assert st(hass, "sensor.centrala_status").state == "idle"
    attrs = st(hass, "sensor.centrala_status").attributes
    assert attrs["outdoor"] == 7.5  # taken from the weather entity
    assert attrs["sources"]["outdoor"] == "weather.acasa"
    assert st(hass, "sensor.centrala_balance_point") is not None
    assert st(hass, "sensor.centrala_heating_rate") is not None
    for missing in ("flow_return_dt", "condensing_ratio_24h", "flow_vs_target_24h", "regulation_mode",
                    "pressure_change_7d", "comfort_verdict", "pre_heat_time", "heat_demand_time_today",
                    "flame_share_of_demand_24_h", "heating_curve_slope"):
        assert st(hass, f"sensor.centrala_{missing}") is None, missing
    assert st(hass, "binary_sensor.centrala_pressure_problem") is None
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
    # burns: 20, 10, 5, 6 -> median 8 (one long burn does not dominate)
    assert s["avg_burn_min"] == pytest.approx(8, abs=0.1)
    # offs: 25, 4, 3 -> median 4
    assert s["avg_off_min"] == pytest.approx(4, abs=0.1)
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


async def test_heating_effect_not_judged_when_boiler_idle(hass: HomeAssistant, freezer):
    """Mild weather: a short burn, then nothing. Rooms don't rise, but that is not 'ineffective'."""
    freezer.move_to("2026-11-10 08:00:00+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    temps(hass, out=16, liv=21.0, dor=21.0)
    await burner(hass, False)
    await setup(hass)
    await burner(hass, True)
    await advance(hass, freezer, 5)
    await burner(hass, False)
    await advance(hass, freezer, 50)  # the check fires at 45 min, burner long off
    assert st(hass, "binary_sensor.centrala_heating_ineffective").state == "off"
    assert not any("without effect" in c.data["title"] for c in notify)

    # A real problem: burning all the time, no rise -> on
    await burner(hass, True)
    await advance(hass, freezer, 46)
    assert st(hass, "binary_sensor.centrala_heating_ineffective").state == "on"
    # ...and it does not stay on for days once the boiler stops for good
    await burner(hass, False)
    await advance(hass, freezer, 30)
    assert st(hass, "binary_sensor.centrala_heating_ineffective").state == "on"
    await advance(hass, freezer, 20)
    assert st(hass, "binary_sensor.centrala_heating_ineffective").state == "off"


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
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-22 00:00:30+03:00")
    temps(hass)
    thermostat(hass, target=19.0)
    await burner(hass, False)
    ariston(hass, thermo="on")
    await setup(hass, {**ARISTON, "thermostat_entity": "climate.termostat"}, {**OPTIONS, "notify_service": ""})
    outs = [9, 7, 6, 8, 4, 3, 5, 2, 1, 3, 6, 4, 2, 0]
    room = 19.0
    for day, o in enumerate(outs):
        for h in range(24):
            hour_out = o + (3 if 11 <= h <= 17 else -1)
            tgt = round(38 + 1.4 * (12 - hour_out) + random.uniform(-0.5, 0.5), 1)
            night = h < 5 or h >= 23
            sp = 19.0 if night else 21.0
            thermostat(hass, target=sp, current=room)
            ariston(hass, setpoint=tgt, thermo="on", pressure=round(1.62 - 0.004 * day, 2))
            # curve a bit too low: the house sags when it's cold outside
            steady = sp - (0.18 * (3 - hour_out) if hour_out < 3 else 0) + random.uniform(-0.15, 0.15)
            flow = round(tgt - 1.5 + random.uniform(-2, 1), 1)
            if day == len(outs) - 1 and h == 15:
                break
            if night:
                room = max(19.0, room - 0.4)
                temps(hass, out=hour_out, flow=flow, ret=44, liv=room, dor=room - 0.3)
                await advance(hass, freezer, 60)
                continue
            if h == 5:  # morning warm-up from the night set-back, slower when colder
                per_deg = 16 + (8 - hour_out) * 1.6 + random.uniform(-2, 2)
                await burner(hass, True)
                for _m in range(60):
                    room = min(steady, room + 1 / per_deg)
                    temps(hass, out=hour_out, flow=flow, ret=46, liv=room, dor=room - 0.3)
                    await advance(hass, freezer, 1)
                await burner(hass, False)
                continue
            room = steady
            temps(hass, out=hour_out, flow=flow, ret=44 + (h % 5), liv=room, dor=room - 0.3)
            burn = max(2, int(36 - 2.6 * hour_out + random.randint(-4, 4)))
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
    temps(hass, out=3, flow=66, ret=55, liv=20.4, dor=20.1)
    thermostat(hass, target=21.0, current=20.3)
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
    # The burner never fires here: the target is sampled while idle too
    await setup(hass, ARISTON, {**OPTIONS, "notify_service": "", "target_only_burning": False})
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
    assert await _ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.0.0")
    assert await _ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.0.0")
    items = [i for i in res.async_items() if i["url"].startswith(CARD_URL)]
    assert len(items) == 1 and items[0]["type"] == "module"
    # New version -> same resource updated, not duplicated
    await _ensure_lovelace_resource(hass, f"{CARD_URL}?v=9.9.9")
    items = [i for i in res.async_items() if i["url"].startswith(CARD_URL)]
    assert len(items) == 1 and items[0]["url"].endswith("v=9.9.9")


THERMO = {**DATA, "thermostat_entity": "climate.termostat"}


def thermostat(hass, target=21.0, current=21.0, mode="heat"):
    hass.states.async_set("climate.termostat", mode, {"temperature": target, "current_temperature": current})


async def test_comfort_verdict_slope_low(hass: HomeAssistant, freezer):
    """Cold outside -> house can't reach the setpoint while burning flat out -> slope too low."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    thermostat(hass)
    temps(hass)
    await burner(hass, False)
    await setup(hass, THERMO, {**OPTIONS, "notify_service": ""})
    st0 = st(hass, "sensor.centrala_comfort_verdict")
    assert st0.state == "insufficient_data"
    for h in range(60):
        out = [12, 8, 4, 0, -4][(h // 6) % 5]
        room = 21.0 - (0.25 * (4 - out) if out < 4 else 0.0)   # too cold when it's cold
        duty = 55 if out <= 0 else 25                           # minutes per hour burning
        temps(hass, out=out, liv=room, dor=room)
        await burner(hass, True)
        await advance(hass, freezer, duty)
        await burner(hass, False)
        await advance(hass, freezer, 60 - duty)
    v = st(hass, "sensor.centrala_comfort_verdict")
    assert v.state == "slope_low", v.attributes
    assert v.attributes["gap_cold"] < -0.5
    assert v.attributes["confidence"] in ("low", "medium", "high")
    assert float(st(hass, "sensor.centrala_comfort_gap_24h").state) < 0


async def test_comfort_verdict_offset_high_and_setback_ignored(hass: HomeAssistant, freezer):
    """Short cycles in mild weather -> offset too high; night set-back hours are not counted as 'cold'."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    thermostat(hass)
    temps(hass)
    await burner(hass, False)
    await setup(hass, THERMO, {**OPTIONS, "notify_service": ""})
    for h in range(60):
        out = [14, 10, 6, 2][(h // 6) % 4]
        hour = h % 24
        setback = 0 <= hour < 5
        thermostat(hass, target=18.0 if setback else 21.0)
        temps(hass, out=out, liv=18.0 if setback else 21.2, dor=18.0 if setback else 21.2)
        await hass.async_block_till_done()
        if out >= 10 and not setback:  # mild: on/off every few minutes
            for _ in range(6):
                await burner(hass, True); await advance(hass, freezer, 3)
                await burner(hass, False); await advance(hass, freezer, 7)
        else:
            await burner(hass, True); await advance(hass, freezer, 20)
            await burner(hass, False); await advance(hass, freezer, 40)
    v = st(hass, "sensor.centrala_comfort_verdict")
    assert v.state == "offset_high", v.attributes
    # set-back hours (gap -3) must not drag the cold median down
    assert v.attributes["gap_cold"] > -0.5


async def test_heatup_model_and_preheat_service(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 00:00:30+02:00")
    thermostat(hass, target=21.0)
    temps(hass)
    await burner(hass, False)
    await setup(hass, THERMO, {**OPTIONS, "notify_service": ""})
    # 4 mornings: house at 19 °C after the night, warms 2 °C; slower when colder
    for day, out in enumerate([10, 6, 2, -2]):
        minutes_per_deg = 15 + (10 - out) * 1.5    # 15 at 10 °C ... 33 at -2 °C
        temps(hass, out=out, liv=19.0, dor=19.0)
        await advance(hass, freezer, 120)          # long pause
        await burner(hass, True)
        room = 19.0
        while room < 21.0:
            room = min(21.0, room + 1 / minutes_per_deg)
            temps(hass, out=out, liv=room, dor=room)
            await advance(hass, freezer, 1)
        await burner(hass, False)
        await advance(hass, freezer, 24 * 60 - 120 - int(2 * minutes_per_deg) - 2)
    rate = st(hass, "sensor.centrala_heat_up_time_per_degc")
    assert float(rate.attributes["n"]) == 4
    assert rate.attributes["b"] < 0  # colder -> slower
    # Now: 4 °C outside, house at 19.5 °C, target 21 °C at a given time
    temps(hass, out=4, liv=19.5, dor=19.5)
    await advance(hass, freezer, 1)  # next sample picks up the new values
    expected_rate = 15 + (10 - 4) * 1.5  # 24 min/°C
    assert float(st(hass, "sensor.centrala_heat_up_time_per_degc").state) == pytest.approx(expected_rate, abs=2)
    assert float(st(hass, "sensor.centrala_pre_heat_time").state) == pytest.approx(1.5 * expected_rate, abs=4)
    resp = await hass.services.async_call(
        DOMAIN, "estimate_preheat", {"target_temperature": 21, "at": "07:00"}, blocking=True, return_response=True
    )
    assert resp["minutes"] == pytest.approx(1.5 * expected_rate, abs=4)
    assert resp["start_at"] < resp["at"] and resp["outdoor_source"] == "now"


async def test_preheat_uses_weather_forecast(hass: HomeAssistant, freezer):
    from homeassistant.core import SupportsResponse
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-11-10 22:00:00+02:00")
    thermostat(hass, target=21.0)
    temps(hass, out=8, liv=19.0, dor=19.0)
    await burner(hass, False)
    entry = await setup(hass, {**THERMO, "weather_entity": "weather.home"}, {**OPTIONS, "notify_service": ""})
    # rate = 20 + (-1.5)*out  -> 32 min/°C at -8 °C, 8 min/°C at 8 °C
    entry.runtime_data.heatups = [
        {"ts": 1, "out": o, "rate": 20 - 1.5 * o, "rise": 1, "minutes": 20 - 1.5 * o} for o in (-8, 0, 8)
    ]

    async def forecasts(call):
        start = dt_util.now().replace(minute=0, second=0, microsecond=0)
        return {"weather.home": {"forecast": [
            {"datetime": (start + timedelta(hours=h)).isoformat(), "temperature": 8 - 2 * h} for h in range(24)
        ]}}

    hass.services.async_register("weather", "get_forecasts", forecasts, supports_response=SupportsResponse.ONLY)
    resp = await hass.services.async_call(
        DOMAIN, "estimate_preheat", {"target_temperature": 21, "at": "02:00"}, blocking=True, return_response=True
    )
    # at 02:00 the forecast says 8 - 2*4 = 0 °C -> 20 min/°C, 2 °C to go -> 40 min
    assert resp["outdoor_source"] == "forecast" and resp["outdoor"] == 0
    assert resp["minutes"] == pytest.approx(40, abs=1)
    assert resp["start_at"].startswith("2026-11-11T01:20")


FULL = {**ARISTON, "thermostat_entity": "climate.termostat"}


async def test_comfort_sunny_hours_do_not_blame_the_curve(hass: HomeAssistant, freezer):
    """Mild hours: boiler off, sun warms the house 1 °C above the setpoint -> not offset_high."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    thermostat(hass)
    temps(hass)
    await burner(hass, False)
    await setup(hass, THERMO, {**OPTIONS, "notify_service": ""})
    for h in range(60):
        out = [14, 12, 6, 0][(h // 6) % 4]
        sunny = out >= 12
        room = 22.0 if sunny else 21.0
        temps(hass, out=out, liv=room, dor=room)
        await hass.async_block_till_done()
        if sunny:
            await advance(hass, freezer, 60)
            continue
        await burner(hass, True)
        await advance(hass, freezer, 20)
        await burner(hass, False)
        await advance(hass, freezer, 40)
    v = st(hass, "sensor.centrala_comfort_verdict")
    assert v.state == "ok", v.attributes
    assert v.attributes["rule"] == "ok"
    assert v.attributes["excluded_sunny_hours"] > 0
    assert v.attributes["duty_mild"] == 0


async def test_burner_unavailable_during_burn(hass: HomeAssistant, freezer):
    """Burner entity drops out mid-burn for 2 h: no phantom burn time, hours left out, no false short cycle."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    notify = async_mock_service(hass, "notify", "mobile_app_telefon")
    thermostat(hass)
    temps(hass)
    ariston(hass, setpoint=50, thermo="on")
    await burner(hass, False)
    entry = await setup(hass, FULL)
    m = entry.runtime_data

    async def normal_hours(n):
        for _ in range(n):
            await burner(hass, True)
            await advance(hass, freezer, 20)
            await burner(hass, False)
            await advance(hass, freezer, 40)

    def burn_total():
        m.stats()  # accounts the burn in progress, if any
        return sum(v["burn_s"] for v in m.hours.values())

    await normal_hours(3)
    await burner(hass, True)
    await advance(hass, freezer, 15)
    lost = dt_util.utcnow().timestamp()
    hass.states.async_set(BURNER, "unavailable")
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_status").state == "unavailable"
    assert burn_total() == pytest.approx(3 * 20 * 60 + 15 * 60, abs=1)

    await advance(hass, freezer, 120)
    assert burn_total() == pytest.approx(3 * 20 * 60 + 15 * 60, abs=1)
    cycle = m.cycles[-1]
    assert cycle["partial"] is True and cycle["end"] == pytest.approx(lost, abs=1)

    # Back, still (or again) on: not measured against the partial stop
    back = dt_util.utcnow().timestamp()
    await burner(hass, True)
    assert st(hass, "sensor.centrala_status").state == "heating"
    assert st(hass, "sensor.centrala_short_cycles_today").state == "0"
    assert m.cycles[-1]["short"] is False and m.cycles[-1]["off_s"] is None
    assert not [c for c in notify if c.data["data"]["tag"].endswith("short_cycle")]
    await advance(hass, freezer, 15)
    await burner(hass, False)
    await advance(hass, freezer, 30)
    await normal_hours(2)
    assert st(hass, "sensor.centrala_short_cycles_today").state == "0"

    attrs = st(hass, "sensor.centrala_status").attributes
    first, last = int(lost // 3600 * 3600), int(back // 3600 * 3600)
    gone = set(range(first, last + 1, 3600))
    assert len(gone) == 3
    for name in ("curve_points", "comfort_points"):
        seen = {p[4] for p in attrs[name]}
        assert seen and not (seen & gone), name
        assert first - 3600 in seen and last + 3600 in seen, name


@pytest.mark.parametrize("idle_target", [0, 25])
async def test_curve_target_sampled_only_while_burning(hass: HomeAssistant, freezer, idle_target):
    """The setpoint reports 0 (or its minimum) while the burner is idle -> the slope is still right."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass)
    ariston(hass, setpoint=idle_target, thermo="on")
    await burner(hass, False)
    await setup(hass, ARISTON, {**OPTIONS, "notify_service": ""})
    # 12 hours, outdoor from 10 to -1, curve: target = 40 + 1.5 * (10 - out)
    for h in range(12):
        out = 10 - h
        temps(hass, out=out)
        ariston(hass, setpoint=40 + 1.5 * (10 - out), thermo="on")
        await burner(hass, True)
        await advance(hass, freezer, 30)
        await burner(hass, False)
        ariston(hass, setpoint=idle_target, thermo="on")
        await hass.async_block_till_done()
        await advance(hass, freezer, 30)
    attrs = st(hass, "sensor.centrala_status").attributes
    assert len(attrs["curve_points"]) >= 10
    fit = attrs["curve_fit"]
    assert fit["slope"] == pytest.approx(1.5, abs=0.05)
    assert fit["at_0"] == pytest.approx(55, abs=0.5)


async def test_regression_skips_day_with_burner_unavailable(hass: HomeAssistant, freezer):
    """A day with many hours of unavailable burner is not a complete day for the balance point."""
    from custom_components.boiler_monitor.const import MAX_NA_S_PER_HOUR

    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass)
    await burner(hass, False)
    entry = await setup(hass)
    m = entry.runtime_data
    bad_ts = None
    # outdoor temp, burn minutes per hour
    for day, (out, burn_per_h) in enumerate([(0, 30), (5, 20), (10, 10), (2, 26), (8, 14), (4, 22)]):
        temps(hass, out=out)
        hours = 24
        if day == 2:  # the burner entity is gone for the first 8 hours
            hass.states.async_set(BURNER, "unavailable")
            await hass.async_block_till_done()
            await advance(hass, freezer, 4 * 60)
            bad_ts = dt_util.utcnow()
            await advance(hass, freezer, 4 * 60)
            hours = 16
        for _h in range(hours):
            await burner(hass, True)
            await advance(hass, freezer, burn_per_h)
            await burner(hass, False)
            await advance(hass, freezer, 60 - burn_per_h)
    assert sum(1 for v in m.hours.values() if v.get("na_s", 0) > MAX_NA_S_PER_HOUR) == 8
    bad_date = dt_util.as_local(bad_ts).date().isoformat()
    bad_day = next(d for d in m.daily(30) if d["date"] == bad_date)
    assert bad_day["samples"] >= 20 * 60  # sampled all day, so only the missing burner rules it out
    assert bad_date not in [d["date"] for d in m._complete_days(30)]
    reg = st(hass, "sensor.centrala_status").attributes["regression"]
    assert reg is not None and reg["n"] >= 3
    assert reg["slope"] == pytest.approx(-0.8, abs=0.1)
    assert float(st(hass, "sensor.centrala_balance_point").state) == pytest.approx(15, abs=1)


FLAME = "binary_sensor.flacara"
FLAME_DATA = {**DATA, "flame_entity": FLAME, "thermostat_entity": "climate.termostat"}


async def flame(hass, on: bool):
    hass.states.async_set(FLAME, "on" if on else "off")
    await hass.async_block_till_done()


async def flow(hass, value):
    hass.states.async_set("sensor.tur", value, {"device_class": "temperature"})
    await hass.async_block_till_done()


async def test_flame_entity_demand_vs_flame(hass: HomeAssistant, freezer):
    """Relay = demand, flame = burn. Flame without demand is hot water; pauses during demand are not burn."""
    freezer.move_to("2026-11-10 08:00:30+02:00")
    thermostat(hass, target=22.0, current=20.0)
    temps(hass, flow=30, ret=28, liv=20.0, dor=20.0)
    await flame(hass, False)
    await burner(hass, False)
    await setup(hass, FLAME_DATA, {**OPTIONS, "notify_service": ""})
    status = lambda: st(hass, "sensor.centrala_status").state

    # Domestic hot water: flame without demand is ignored
    await flame(hass, True)
    await advance(hass, freezer, 5)
    await flame(hass, False)
    assert status() == "idle"
    assert st(hass, "sensor.centrala_cycles_today").state == "0"

    await advance(hass, freezer, 70)
    # Demand, the boiler fires 2 min every 7 min (modulation too high for the load)
    await burner(hass, True)
    assert status() == "demand"
    for _ in range(4):
        await flame(hass, True)
        assert status() == "heating"
        await advance(hass, freezer, 2)
        await flame(hass, False)
        assert status() == "demand"
        await advance(hass, freezer, 5)
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert s["cycles_today"] == 4
    assert s["short_cycles_today"] == 3
    assert s["burn_hours_today"] == pytest.approx(8 / 60, abs=0.01)
    assert s["demand_hours_today"] == pytest.approx(28 / 60, abs=0.01)
    assert st(hass, "binary_sensor.centrala_short_cycling").state == "on"

    # A flame the cloud sensor missed: flow jumps, flame stays "off"
    await flow(hass, 31)
    await flow(hass, 42)
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    tl = st(hass, "sensor.centrala_status").attributes["timeline"]
    assert tl[-1][3] == 1  # inferred
    assert tl[-1][1] - tl[-1][0] == pytest.approx(60, abs=2)
    assert st(hass, "sensor.centrala_status").attributes["stats"]["cycles_today"] == 5

    # A jump right after a reported flame is that flame, not a new one
    await flow(hass, 30)
    await advance(hass, freezer, 5)
    await flame(hass, True)
    await advance(hass, freezer, 2)
    await flame(hass, False)
    await flow(hass, 41)
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_status").attributes["stats"]["cycles_today"] == 6

    # Flame share and ignitions per demand hour need enough demand time
    await flow(hass, 30)
    await advance(hass, freezer, 20)
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert 0 < float(st(hass, "sensor.centrala_flame_share_of_demand_24_h").state) < 40
    assert s["starts_per_demand_hour"] > 4
    assert st(hass, "sensor.centrala_status").attributes["demand_timeline"][-1][1] is None


async def test_flame_entity_heatup_spans_the_demand(hass: HomeAssistant, freezer):
    """Warm-up is measured from demand start to the setpoint, not per flame."""
    freezer.move_to("2026-11-10 05:00:30+02:00")
    thermostat(hass, target=21.0, current=19.0)
    temps(hass, out=5, liv=19.0, dor=19.0)
    await flame(hass, False)
    await burner(hass, False)
    await setup(hass, FLAME_DATA, {**OPTIONS, "notify_service": ""})
    await advance(hass, freezer, 90)
    await burner(hass, True)
    room = 19.0
    for _ in range(6):  # 6 x (3 min flame + 7 min pause) = 60 min, +2 °C
        await flame(hass, True)
        for _ in range(3):
            room += 2 / 60
            temps(hass, out=5, liv=room, dor=room)
            await advance(hass, freezer, 1)
        await flame(hass, False)
        for _ in range(7):
            room += 2 / 60
            temps(hass, out=5, liv=room, dor=room)
            await advance(hass, freezer, 1)
    heatups = st(hass, "sensor.centrala_status").attributes["heatups"]
    assert len(heatups) == 1
    assert heatups[0]["minutes"] == pytest.approx(60, abs=3)
    assert heatups[0]["rate"] == pytest.approx(30, abs=3)


async def test_flame_unavailable_at_startup_is_not_a_burn(hass: HomeAssistant, freezer):
    """After a restart the cloud flame entity loads late: no fake burn from the relay."""
    freezer.move_to("2026-11-10 08:00:30+02:00")
    thermostat(hass, target=22.0, current=20.0)
    temps(hass, flow=30, ret=28)
    hass.states.async_set(FLAME, "unavailable")
    await burner(hass, True)
    await setup(hass, FLAME_DATA, {**OPTIONS, "notify_service": ""})
    assert st(hass, "sensor.centrala_status").state == "demand"
    await advance(hass, freezer, 2)
    await flame(hass, False)  # integration loaded
    assert st(hass, "sensor.centrala_status").attributes["stats"]["cycles_today"] == 0
    # A long outage: after 10 min the relay is used alone
    hass.states.async_set(FLAME, "unavailable")
    await advance(hass, freezer, 9)
    assert st(hass, "sensor.centrala_status").state == "demand"
    await advance(hass, freezer, 2)
    assert st(hass, "sensor.centrala_status").state == "heating"


async def test_balance_point_hidden_when_line_is_flat(hass: HomeAssistant, freezer):
    """Burn barely changes with outdoor (e.g. neighbours unheated): no absurd balance point."""
    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass)
    await burner(hass, False)
    await setup(hass)
    for out, burn_per_h in [(10, 20), (12, 21), (11, 19), (13, 20), (10, 21), (12, 20), (11, 21)]:
        temps(hass, out=out)
        for _h in range(24):
            await burner(hass, True)
            await advance(hass, freezer, burn_per_h)
            await burner(hass, False)
            await advance(hass, freezer, 60 - burn_per_h)
    reg = st(hass, "sensor.centrala_status").attributes["regression"]
    assert reg is not None and "balance_point" not in reg
    assert reg["balance_reason"] in ("weak_fit", "out_of_range")
    assert st(hass, "sensor.centrala_balance_point").state == "unknown"


async def test_late_flame_merges_with_inferred_ignition(hass: HomeAssistant, freezer):
    """Flow jump first, flame entity 20 s later: one burn, not two, and no short cycle."""
    freezer.move_to("2026-11-10 08:00:30+02:00")
    thermostat(hass, target=22.0, current=20.0)
    temps(hass, flow=30, ret=28)
    await flame(hass, False)
    await burner(hass, True)
    entry = await setup(hass, FLAME_DATA, {**OPTIONS, "notify_service": ""})
    await advance(hass, freezer, 15)
    await flow(hass, 42)
    for _ in range(2):
        freezer.tick(timedelta(seconds=10))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert len(entry.runtime_data.cycles) == 1 and entry.runtime_data.cycles[0].get("inferred")
    await flame(hass, True)
    await advance(hass, freezer, 3)
    await flame(hass, False)
    cycles = entry.runtime_data.cycles
    assert len(cycles) == 1
    assert not cycles[0].get("inferred") and not cycles[0]["short"]
    assert cycles[0]["end"] - cycles[0]["start"] == pytest.approx(60 + 20 + 180, abs=5)
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert s["cycles_today"] == 1 and s["short_cycles_today"] == 0
    assert s["burn_hours_today"] * 3600 == pytest.approx(260, abs=40)


async def test_units_are_converted(hass: HomeAssistant, freezer):
    """°F temperatures and kPa pressure are handled as °C and bar."""
    freezer.move_to("2026-11-10 08:00:30+02:00")
    data = {**DATA, "pressure_entity": "sensor.presiune", "flow_setpoint_entity": "sensor.cerut"}
    for eid, val in (("sensor.tur", 140), ("sensor.retur", 104), ("sensor.exterior", 32), ("sensor.cerut", 131),
                     ("sensor.living", 69.8), ("sensor.dormitor", 69.8)):
        hass.states.async_set(eid, val, {"device_class": "temperature", "unit_of_measurement": "°F"})
    hass.states.async_set("sensor.presiune", 150, {"device_class": "pressure", "unit_of_measurement": "kPa"})
    await burner(hass, False)
    await setup(hass, data, {**OPTIONS, "notify_service": ""})
    a = st(hass, "sensor.centrala_status").attributes
    assert a["flow"] == pytest.approx(60) and a["return"] == pytest.approx(40)
    assert a["outdoor"] == pytest.approx(0) and a["indoor"] == pytest.approx(21)
    assert a["flow_target"] == pytest.approx(55) and a["pressure"] == pytest.approx(1.5)
    assert a["stats"]["delta_t"] == pytest.approx(20, abs=0.1)
    assert st(hass, "binary_sensor.centrala_pressure_problem").state == "off"


async def test_typical_pause_ignores_the_night(hass: HomeAssistant, freezer):
    """With a flame entity the pause is the median inside the heat demand."""
    freezer.move_to("2026-11-10 06:00:30+02:00")
    thermostat(hass, target=22.0, current=20.0)
    temps(hass, flow=30, ret=28)
    await flame(hass, False)
    await burner(hass, False)
    await setup(hass, FLAME_DATA, {**OPTIONS, "notify_service": ""})
    for _block in range(2):  # two demand periods, 8 h apart
        await burner(hass, True)
        for _ in range(4):
            await flame(hass, True)
            await advance(hass, freezer, 3)
            await flame(hass, False)
            await advance(hass, freezer, 6)
        await burner(hass, False)
        await advance(hass, freezer, 8 * 60)
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert s["avg_off_min"] == pytest.approx(6, abs=0.2)
    assert s["avg_burn_min"] == pytest.approx(3, abs=0.2)


# ---------------------------------------------------------------- 1.9.0: optional boiler data
DHW = "binary_sensor.ariston_dhw"
MOD = "sensor.ariston_modulation"
STARTS = "sensor.boiler_burner_starts"
GAS = "sensor.gas_meter"


async def test_dhw_flame_is_not_heating(hass: HomeAssistant, freezer):
    """A DHW entity: burner on while hot water is active is not a heating burn."""
    freezer.move_to("2026-11-10 08:00:30+02:00")
    temps(hass)
    hass.states.async_set(DHW, "off")
    await burner(hass, False)
    await setup(hass, {**DATA, "dhw_entity": DHW}, {**OPTIONS, "notify_service": ""})
    hass.states.async_set(DHW, "on")
    await burner(hass, True)
    await advance(hass, freezer, 6)
    assert st(hass, "sensor.centrala_status").state == "hot_water"
    assert st(hass, "sensor.centrala_cycles_today").state == "0"
    hass.states.async_set(DHW, "off")
    await burner(hass, False)
    await advance(hass, freezer, 10)
    # a real heating burn afterwards is counted
    await burner(hass, True)
    assert st(hass, "sensor.centrala_status").state == "heating"
    await advance(hass, freezer, 15)
    await burner(hass, False)
    assert st(hass, "sensor.centrala_cycles_today").state == "1"
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert s["burn_hours_today"] == pytest.approx(0.25, abs=0.02)


async def test_modulation_power_and_energy(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:30+02:00")
    temps(hass)
    hass.states.async_set(MOD, 50, {"unit_of_measurement": "%"})
    await burner(hass, False)
    data = {**DATA, "modulation_entity": MOD, "max_power_kw": 24, "min_power_kw": 4}
    await setup(hass, data, {**OPTIONS, "notify_service": ""})
    await burner(hass, True)
    await advance(hass, freezer, 30)          # 12 kW for 30 min = 6 kWh
    hass.states.async_set(MOD, 5)             # below minimum -> 4 kW (pmin)
    await advance(hass, freezer, 30)          # 4 kW for 30 min = 2 kWh
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert s["heat_power_kw"] == pytest.approx(4.0)
    assert s["energy_today_kwh"] == pytest.approx(8.0, abs=0.5)
    assert s["modulation_avg_24h"] == pytest.approx(27.5, abs=3)
    assert s["modulation_low_24h"] == pytest.approx(50, abs=5)
    assert float(st(hass, "sensor.centrala_heat_energy_today").state) == pytest.approx(8.0, abs=0.5)
    await burner(hass, False)
    assert st(hass, "sensor.centrala_status").attributes["stats"]["heat_power_kw"] == 0
    assert st(hass, "sensor.centrala_status").attributes["sources"]["power"] is True


async def test_starts_counter_and_reset(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:30+02:00")
    temps(hass)
    hass.states.async_set(STARTS, 1000)
    await burner(hass, False)
    await setup(hass, {**DATA, "burner_starts_entity": STARTS}, {**OPTIONS, "notify_service": ""})
    await burner(hass, True)
    for v in (1003, 1007):
        await advance(hass, freezer, 30)
        hass.states.async_set(STARTS, v)
        await hass.async_block_till_done()
    hass.states.async_set(STARTS, 2)          # counter replaced / reset
    await hass.async_block_till_done()
    hass.states.async_set(STARTS, 5)
    await hass.async_block_till_done()
    s = st(hass, "sensor.centrala_status").attributes["stats"]
    assert s["boiler_starts_today"] == 10     # 3 + 4 + (reset ignored) + 3
    assert s["boiler_starts_per_hour"] == pytest.approx(10, abs=0.5)  # one hour of demand
    assert st(hass, "sensor.centrala_boiler_starts_today").state == "10"


async def test_gas_meter_and_per_degree_day(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass, out=5)
    hass.states.async_set(GAS, 100.0, {"unit_of_measurement": "m³", "state_class": "total_increasing"})
    await burner(hass, False)
    await setup(hass, {**DATA, "gas_entity": GAS}, {**OPTIONS, "notify_service": ""})
    gas = 100.0
    for _day in range(2):
        for _h in range(24):
            await burner(hass, True)
            await advance(hass, freezer, 15)
            gas += 0.1
            hass.states.async_set(GAS, round(gas, 3), {"unit_of_measurement": "m³"})
            await burner(hass, False)
            await advance(hass, freezer, 45)
    attrs = st(hass, "sensor.centrala_status").attributes
    s = attrs["stats"]
    assert s["gas_today"] is not None
    assert sum(d["gas"] for d in attrs["daily"]) == pytest.approx(4.8, abs=0.05)
    # every full day: 2.4 m³ at 5 °C outdoor
    from custom_components.boiler_monitor.monitor import HDD_BASE
    assert s["gas_per_hdd"] == pytest.approx(2.4 / (HDD_BASE - 5), rel=0.05)
    assert attrs["source_units"]["gas"] == "m³"
    assert st(hass, "sensor.centrala_gas_per_degree_day_7d").attributes["unit_of_measurement"] == "m³/°C·day"


async def test_numeric_burner_threshold(hass: HomeAssistant, freezer):
    """burner_on_state '>60' on a power sensor in W."""
    freezer.move_to("2026-11-10 08:00:30+02:00")
    temps(hass)
    plug = "sensor.priza_centrala_power"
    hass.states.async_set(plug, 8)
    await setup(hass, {**DATA, "burner_entity": plug, "burner_on_state": ">60"}, {**OPTIONS, "notify_service": ""})
    assert st(hass, "sensor.centrala_status").state == "idle"
    hass.states.async_set(plug, 95)
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_status").state == "heating"
    await advance(hass, freezer, 12)
    hass.states.async_set(plug, 10)
    await hass.async_block_till_done()
    assert st(hass, "sensor.centrala_cycles_today").state == "1"


async def test_thermoregulation_from_select(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 08:00:30+02:00")
    temps(hass)
    sel_ent = "select.boiler_heating_mode"
    hass.states.async_set(sel_ent, "manual")
    await burner(hass, False)
    data = {**DATA, "thermoregulation_entity": sel_ent, "thermoregulation_on_state": "Weather"}
    await setup(hass, data, {**OPTIONS, "notify_service": ""})
    assert st(hass, "sensor.centrala_regulation_mode").state == "fixed"
    hass.states.async_set(sel_ent, "weather")
    await hass.async_block_till_done()
    await advance(hass, freezer, 1)
    assert st(hass, "sensor.centrala_regulation_mode").state == "weather_compensation"


async def test_regression_uses_energy_when_power_known(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-10 00:00:30+02:00")
    temps(hass)
    hass.states.async_set(MOD, 50)
    await burner(hass, False)
    data = {**DATA, "modulation_entity": MOD, "max_power_kw": 20}
    await setup(hass, data, {**OPTIONS, "notify_service": ""})
    for out, burn_per_h in [(0, 30), (5, 20), (10, 10), (2, 26), (8, 14)]:
        temps(hass, out=out)
        for _h in range(24):
            await burner(hass, True)
            await advance(hass, freezer, burn_per_h)
            await burner(hass, False)
            await advance(hass, freezer, 60 - burn_per_h)
    attrs = st(hass, "sensor.centrala_status").attributes
    reg = attrs["regression"]
    assert reg["metric"] == "kwh"
    # 10 kW x burn hours: -0.8 h/day per °C -> -8 kWh/day per °C
    assert reg["slope"] == pytest.approx(-8, abs=1)
    assert reg["balance_point"] == pytest.approx(15, abs=1)
    assert attrs["stats"]["energy_per_hdd"] is not None

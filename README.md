# Boiler Monitoring for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/sandreialexandru/Boiler-Monitoring-for-Home-Assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Boiler-Monitoring-for-Home-Assistant/actions/workflows/validate.yml)
![License](https://img.shields.io/github/license/sandreialexandru/Boiler-Monitoring-for-Home-Assistant)

A Home Assistant integration that monitors your gas boiler in depth: burner cycles, short-cycling, condensing efficiency (return temperature), flow/return ΔT, the actual effect on room temperature, and how burn time correlates with outdoor temperature. Use it to tune your weather-compensation curve. It ships with its own Lovelace card in **full** and **compact** modes, which loads automatically.

It works with any boiler. All it needs is an entity that tells it when the burner is firing (or when there is heat demand): a relay, a flame sensor, a `climate` entity or a text sensor. Every other sensor is optional.

<p align="center">
  <img src="docs/images/card-full-light.png" width="420" alt="Full card, light theme">
  &nbsp;
  <img src="docs/images/card-full-dark.png" width="420" alt="Full card, dark theme">
</p>

<p align="center">
  <img src="docs/images/card-compact-light.png" width="420" alt="Compact card, light theme">
  &nbsp;
  <img src="docs/images/card-compact-dark.png" width="420" alt="Compact card, dark theme">
</p>

---

## Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [The card](#the-card)
- [Events, services and CSV log](#events-services-and-csv-log)
- [How the numbers are calculated](#how-the-numbers-are-calculated)
- [Using it to tune your heating curve](#using-it-to-tune-your-heating-curve)
- [Example: ESPHome relay + DS18B20](#example-esphome-relay--ds18b20)
- [FAQ / troubleshooting](#faq--troubleshooting)
- [Development](#development)

## Features

| | |
|---|---|
| 🔥 **Cycle statistics** | cycles today, cycles per hour, average burn and off times, duty cycle, burn time today, last burn |
| 🔁 **Short-cycling detection** | flags any restart sooner than *N* minutes after the previous stop. The off-time is measured from the stored stop time, so a Home Assistant restart never produces a false alarm |
| 💧 **Condensing efficiency** | % of burn time with the return below the condensing threshold, plus an alert when the return stays too hot |
| 🌡️ **Flow/return ΔT** | live, and as a daily average |
| 🏠 **Heating effect** | measures how much the rooms actually warmed after the burner started (°C/h) and alerts when the boiler burns without effect |
| 📈 **Outdoor correlation** | daily burn hours vs outdoor temperature, linear regression, **balance point**, **burn hours per degree-day** |
| ❄️ **Season gating** | optionally pauses all monitoring outside the heating season, so domestic-hot-water starts in summer don't count |
| 🔔 **Alerts** | problem binary sensors, HA events, optional push notifications (tagged, max 1/hour per type) |
| 🗒️ **CSV log** | every START / STOP / SHORT_CYCLE / RETURN_HOT / INEFFECTIVE event, ready for Excel |
| 🧩 **UI-only setup** | config flow, options flow, reconfigure. No YAML, no helpers, no File integration |
| 🌍 **Translations** | English, Romanian |

## Installation

### HACS (recommended)

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/sandreialexandru/Boiler-Monitoring-for-Home-Assistant`, category **Integration**
3. Install **Boiler Monitor** and restart Home Assistant

### Manual

Copy `custom_components/boiler_monitor` into `/config/custom_components/` and restart Home Assistant.

### Add the integration

**Settings → Devices & services → Add integration → Boiler Monitor**

The card is registered automatically, so you don't need to add a dashboard resource. If it doesn't show up in the card picker right away, hard-refresh the browser (Ctrl+F5).

## Configuration

### Step 1: entities (set at creation, change later via ⋮ → **Reconfigure**)

| Field | Required | Description |
|---|---|---|
| Name | ✅ | Used for entity IDs (`sensor.<name>_status`…) |
| Burner / heat-demand entity | ✅ | `switch`, `binary_sensor`, `input_boolean`, `climate` or `sensor` |
| State meaning "burner on" | ✅ | `on` for switches and binary sensors. For a **climate** entity, the `hvac_action` value (`heating`). For a text sensor, the exact state string |
| Flow temperature sensor | – | Enables ΔT |
| Return temperature sensor | – | Enables condensing ratio and the condensation-lost alert |
| Outdoor temperature sensor | – | Enables balance point and burn per degree-day |
| Indoor temperature sensors | – | One or more; their average is used for the heating-effect check |
| Heating-season entity / state | – | e.g. `input_boolean.heating_season` = `on`, `climate.x` = `heat`, or an `input_select` option. Leave it empty to monitor all year |

Entities that need a sensor you didn't configure are simply not created.

> **Which burner entity should I pick?**
> If the boiler is switched by a relay from a thermostat (e.g. Generic Thermostat + ESPHome relay), the relay shows *heat demand*, not the flame. Short-cycling then means the **thermostat** is cycling, and you fix it with hysteresis or `min_cycle_duration`. If your boiler integration exposes the real flame state, use that to see the boiler's own cycling. You can add the integration **twice** (once per source) and compare them side by side.

### Step 2: tuning (⋮ → **Configure**)

| Option | Default | Meaning |
|---|---|---|
| Short-cycle threshold | 10 min | A restart sooner than this after a stop counts as a short cycle |
| Return temperature threshold | 53 °C | Above this, a condensing boiler stops condensing (≈ 55 °C dew point for natural gas; 53 °C leaves a margin) |
| Minutes above threshold before alert | 15 min | How long the return must stay hot (while burning) before *Condensation lost* triggers |
| Heating-effect check delay | 45 min | How long after a start to measure the room temperature rise |
| Minimum expected room rise | 0.2 °C | Below this, *Heating ineffective* triggers |
| Ignore burns shorter than | 20 s | Relay chatter / ignition glitches are discarded entirely |
| Notification service | – | `notify.mobile_app_your_phone` **or** a notify entity. Leave empty for no push |
| Write CSV log | on | `/config/boiler_monitor/<name>.csv` |

## Entities

All entities belong to one device named after your integration. The examples use the name **Centrala**.

### Sensors

| Entity | Unit | Description |
|---|---|---|
| `sensor.centrala_status` | – | `heating` / `idle` / `off_season` / `unavailable`. Its attributes carry everything the card needs |
| `sensor.centrala_cycles_today` | cycles | Burner starts since local midnight |
| `sensor.centrala_short_cycles_today` | cycles | Of which short cycles |
| `sensor.centrala_cycles_per_hour_24h` | cycles/h | Rolling 24 h |
| `sensor.centrala_average_burn_time_24h` | min | Mean burn duration, rolling 24 h |
| `sensor.centrala_average_off_time_24h` | min | Mean pause before each start, rolling 24 h |
| `sensor.centrala_last_burn_duration` | min | |
| `sensor.centrala_duty_cycle_24h` | % | Share of the last 24 h with the burner on |
| `sensor.centrala_burn_time_today` | h | `total_increasing`, so it works with long-term statistics and the statistics-graph card |
| `sensor.centrala_condensing_ratio_24h` | % | Share of burn time with return < threshold *(needs return)* |
| `sensor.centrala_flow_return_dt` | °C | Live flow − return *(needs flow + return)* |
| `sensor.centrala_heating_rate` | °C/h | Room warming rate from the last effect check *(needs indoor)* |
| `sensor.centrala_balance_point` | °C | Outdoor temperature at which the house needs no heating *(needs outdoor, ≥ 3 full days)* |
| `sensor.centrala_burn_hours_per_degree_day_7d` | h/°C·day | Burn hours ÷ heating degree-days over the last 7 full days *(needs outdoor)* |

### Binary sensors

| Entity | Device class | On when |
|---|---|---|
| `binary_sensor.centrala_burner` | heat | Burner on (and in season) |
| `binary_sensor.centrala_short_cycling` | problem | A short cycle happened in the last 60 minutes |
| `binary_sensor.centrala_condensation_lost` | problem | Return above threshold for *N* minutes while burning. Clears when the return drops 1 °C below the threshold or the burner stops |
| `binary_sensor.centrala_heating_ineffective` | problem | The last effect check measured less than the minimum rise |

## The card

### Full card: all options

```yaml
type: custom:boiler-monitor-card
entity: sensor.centrala_status   # the Status sensor of the integration (required)
title: Centrala                  # optional, defaults to the device name
mode: full                       # full | compact
show_timeline: true              # 24 h burner timeline (short cycles in red)
show_daily: true                 # last 14 days: burn hours per day + outdoor avg
show_correlation: true           # burn vs outdoor scatter + regression + balance point
```

### Compact card

```yaml
type: custom:boiler-monitor-card
entity: sensor.centrala_status
mode: compact
```

The compact card shows the status, active alerts as icons, four key numbers and a slim 24 h timeline. It fits a wall tablet or a sidebar.

### What's on the full card

1. **Header**: animated flame while burning, how long the current burn has lasted, a status chip.
2. **Alert chips**: short-cycling, condensation lost, heating ineffective. They only appear when active.
3. **Live temperatures**: flow, return (green while condensing, red above the threshold), ΔT, outdoor, indoor average.
4. **Statistics tiles**: cycles today (with short cycles), cycles/h, average burn, average off, 24 h duty cycle, burn today, condensing %, heating rate.
5. **Last 24 hours**: every burn as a bar, short cycles in red, the current burn pulsing.
6. **Last 14 days**: burn hours per day, with the date and average outdoor temperature underneath. A red cap marks days with short cycles.
7. **Burn vs outdoor**: one dot per full day (newer days are more opaque), the regression line, the balance point (green line), burn per degree-day and R².

Tapping any value opens the more-info dialog of the underlying entity. The card follows your theme (light/dark), works in both masonry and sections views, and has a visual editor.

A complete example dashboard view is in [`examples/dashboard.yaml`](examples/dashboard.yaml).

## Events, services and CSV log

### Events

| Event | Data |
|---|---|
| `boiler_monitor_short_cycle` | `entry_id`, `name`, `off_minutes` |
| `boiler_monitor_condensation_lost` | `entry_id`, `name`, `return` |
| `boiler_monitor_heating_ineffective` | `entry_id`, `name`, `rise` |
| `boiler_monitor_cycle_end` | `entry_id`, `name`, `burn_minutes`, `off_minutes_before`, `short_cycle`, `outdoor` |

Ready-to-use automations (an actionable alert, a logbook entry per cycle, a daily summary) are in [`examples/automations.yaml`](examples/automations.yaml).

### Service

`boiler_monitor.reset_statistics` clears stored cycles and statistics. Pass `entry_id` to limit it to one boiler.

### CSV log

`/config/boiler_monitor/<name>.csv`, separated by `;`:

```
time;event;burn_min;off_min;outdoor;flow;return;indoor_avg;extra
2026-11-10 06:12:04;START;;24.5;1.8;58.2;44.1;20.31;
2026-11-10 06:29:40;STOP;17.6;;1.8;61.0;47.9;20.52;
2026-11-10 06:33:02;START;;3.4;1.8;55.3;46.0;20.55;
2026-11-10 06:33:02;SHORT_CYCLE;;3.4;1.8;55.3;46.0;20.55;
```

## How the numbers are calculated

- **Off-time / short cycles.** When the burner stops, the stop timestamp is stored on disk. At the next start, off-time = now − stored stop. A cycle that was already running when Home Assistant started is marked *partial* and never counts as a short cycle. *(The usual automation approach based on `last_changed` gives false short cycles after every restart.)*
- **Glitches.** Burns shorter than *Ignore burns shorter than* are removed completely: from the counters, from burn time and from off-time calculations.
- **Burn time** is accumulated per hour bucket and split exactly at hour boundaries, so daily totals are correct across midnight.
- **Condensing ratio.** Once a minute, while burning, the integration checks whether the return is below the threshold. Ratio = condensing minutes ÷ sampled burning minutes over the last 24 h.
- **Heating effect.** At burner start it stores the average of the indoor sensors. After the delay it computes rise and rate (°C/h). If the burner cycles faster than the delay, the pending check is **kept**, not restarted, so it measures the whole heating period.
- **Regression / balance point.** For each *complete* past day (≥ 20 h of samples) it computes `burn_hours = a + b · outdoor_avg` by least squares. Balance point = −a / b, the outdoor temperature at which predicted burn time is zero. It needs at least 3 complete days.
- **Burn per degree-day** = Σ burn hours ÷ Σ max(0, 18 °C − outdoor_avg) over the last 7 complete days.
- **Storage.** Cycles are kept for 7 days and hourly aggregates for 60 days, in `.storage/boiler_monitor.<entry_id>`. The large attributes (timeline, daily) are excluded from the recorder, so they don't bloat your database.

## Using it to tune your heating curve

| What you see | Likely cause | What to try |
|---|---|---|
| Many short cycles, short burns (< 10 min) | Boiler minimum output > heat demand; curve too high in mild weather | Lower the curve **parallel shift** / offset; enable or extend the boiler's anti-cycling timer; with a thermostat relay, increase hysteresis or `min_cycle_duration` |
| Condensing ratio < 80 %, *Condensation lost* alerts | Flow temperature too high, or ΔT too small (pump too fast) | Lower the curve **slope**; reduce the pump speed so ΔT reaches ~15–20 °C |
| ΔT < 8 °C | Pump speed too high / bypass open | Lower the pump speed, check the bypass valve |
| *Heating ineffective* | Flow too low for the current outdoor temperature, TRVs closed, air in radiators | Raise the slope slightly, check TRVs, bleed radiators |
| Balance point well above 16 °C | Curve too high overall or high heat loss | Lower the parallel shift. Check the windows (or the boiler's location, e.g. an open balcony) |
| Burn per degree-day | – | Note it before a change and compare 7 days later at similar outdoor temperatures. Lower is better |

Change **one thing at a time** and wait a few days. The 14-day chart and the regression make the effect visible.

## Example: ESPHome relay + DS18B20

A typical DIY setup: a Wemos D1 mini driving the boiler's thermostat contact through a relay, with DS18B20 probes clamped on the flow and return pipes.

```yaml
# ESPHome
one_wire:
  - platform: gpio
    pin: D4

sensor:
  - platform: dallas_temp
    address: 0x1234567890abcdef   # flow pipe
    name: "Boiler flow"
    update_interval: 30s
  - platform: dallas_temp
    address: 0xfedcba0987654321   # return pipe
    name: "Boiler return"
    update_interval: 30s

switch:
  - platform: gpio
    pin: D1
    name: "Boiler relay"
    id: boiler_relay
```

Then configure Boiler Monitor with `switch.boiler_relay` (state `on`), `sensor.boiler_flow` and `sensor.boiler_return`.
Tip: insulate the probe and the pipe together. A bare probe reads several degrees low.

## FAQ / troubleshooting

**The card says "Pick the Boiler Monitor status sensor".** Select the `sensor.<name>_status` entity, not one of the statistics sensors.

**The card isn't in the card picker.** Hard-refresh the browser (Ctrl+F5). In the companion app: Settings → Companion app → Debugging → Reset frontend cache.

**Balance point / per-degree-day stay `unknown`.** They need an outdoor sensor and at least 3 complete days (7 for per-degree-day) of data.

**My boiler also heats domestic hot water.** With a flame sensor, DHW draws look like short cycles. Use the heating-season entity, or point the integration at the heating relay / heat demand instead of the flame.

**Notifications don't arrive.** Check the logs for `notification via … failed`. The field takes either a service (`notify.mobile_app_x`) or an existing notify entity. Push alerts are limited to one per hour per alert type; events and binary sensors are never throttled.

**Where's the data stored?** In `.storage/boiler_monitor.<entry_id>` and, if enabled, in `/config/boiler_monitor/<name>.csv`.

## Development

```bash
python -m venv venv && . venv/bin/activate
pip install -r requirements_test.txt
pytest -q
```

The tests run the integration inside a real Home Assistant core with a simulated boiler. They cover cycles, short cycles, relay glitches, restarts (no false short cycles), condensation, the heating effect, season gating, `climate` entities, the outdoor regression, the CSV log and the reset service.

The card is plain JavaScript (no build step) in `custom_components/boiler_monitor/frontend/boiler-monitor-card.js`.

### Releasing a new version

Releases are published automatically by [`.github/workflows/release.yml`](.github/workflows/release.yml):

1. Bump the version in **all three** places (the workflow refuses to release if they differ):
   - `custom_components/boiler_monitor/manifest.json` → `"version"`
   - `custom_components/boiler_monitor/const.py` → `VERSION`
   - `custom_components/boiler_monitor/frontend/boiler-monitor-card.js` → `CARD_VERSION` (this also busts the browser cache for the card)
2. Optionally add release notes in `docs/release-notes/vX.Y.Z.md`. Without that file, notes are generated from the commits.
3. Push to `main`. The workflow runs the tests, tags `vX.Y.Z`, and publishes the release with `boiler_monitor.zip` attached. HACS then offers the update.

## License

MIT

"""Core monitoring logic for Boiler Monitor.

Everything stateful lives here. Entities are thin views over this object.
State (cycles + hourly buckets) is persisted with Home Assistant's Store,
so statistics and short-cycle detection survive restarts.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
import math
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify

from . import comfort as cmf
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
    CONF_TARGET_ONLY_BURNING,
    CONF_THERMOREG,
    CONF_THERMOSTAT,
    CONF_WEATHER,
    COMFORT_DAYS,
    CYCLE_RETENTION_HOURS,
    DAILY_RETENTION_DAYS,
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
    DEFAULT_TARGET_ONLY_BURNING,
    DOMAIN,
    EVENT_CONDENSATION_LOST,
    EVENT_CYCLE_END,
    EVENT_INEFFECTIVE,
    EVENT_PRESSURE,
    EVENT_REGULATION,
    MODE_CURVE,
    MODE_FIXED,
    EVENT_SHORT_CYCLE,
    MAX_NA_S_PER_HOUR,
    MIN_VALID_FLOW_TARGET,
    SAMPLE_INTERVAL_SECONDS,
    SIGNAL_UPDATE,
    STATUS_HEATING,
    STATUS_IDLE,
    STATUS_OFF_SEASON,
    STATUS_UNAVAILABLE,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

FLOW_SETTLE_S = 300  # ignore the first minutes of a burn for flow-vs-target
CURVE_HOURS = 7 * 24
HDD_BASE = 18.0  # °C, base temperature for heating degree-days
ALERT_THROTTLE_S = 3600
BAD_STATES = (STATE_UNAVAILABLE, STATE_UNKNOWN, None, "", "none")


def _f(value: Any) -> float | None:
    """Float or None."""
    if value in BAD_STATES:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r(value: float | None, nd: int = 1) -> float | None:
    return None if value is None else round(value, nd)


def _hour_key(ts: float) -> int:
    return int(ts // 3600 * 3600)


def _new_bucket() -> dict[str, float]:
    return {
        "burn_s": 0.0,  # seconds burner on
        "na_s": 0.0,  # seconds with the burner entity unavailable/unknown
        "cycles": 0,  # completed cycles (attributed to start hour)
        "short": 0,  # short cycles
        "cond_s": 0.0,  # sampled seconds burning with return <= threshold
        "smp_s": 0.0,  # sampled seconds burning with a valid return reading
        "out_sum": 0.0,
        "out_n": 0,
        "dt_sum": 0.0,  # flow-return while burning
        "dt_n": 0,
        "tgt_sum": 0.0,  # flow target (setpoint); only while burning unless the option is off
        "tgt_n": 0,
        "th_n": 0,  # of those, samples with thermoregulation ON
        "fl_sum": 0.0,  # actual flow while burning (after settle time)
        "fl_n": 0,
        "dev_sum": 0.0,  # flow - target while burning (after settle time)
        "dev_n": 0,
        "p_sum": 0.0,  # pressure, sampled all year
        "p_n": 0,
    }


def _add(b: dict[str, float], key: str, val: float) -> None:
    b[key] = b.get(key, 0) + val


def _na_hour(b: dict[str, float]) -> bool:
    """Burner state unknown for too much of this hour to trust its numbers."""
    return b.get("na_s", 0) > MAX_NA_S_PER_HOUR


class BoilerMonitor:
    """Tracks burner cycles and derived statistics for one boiler."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._unsubs: list[CALLBACK_TYPE] = []
        self._effect_unsub: CALLBACK_TYPE | None = None

        self.cycles: list[dict[str, Any]] = []
        self.hours: dict[int, dict[str, float]] = {}
        self.last_alert: dict[str, float] = {}

        self.started_at: float = 0.0
        self._last_tick: float = 0.0
        self._burn_accounted_until: float | None = None
        self._return_hot_since: float | None = None

        # Flags / last results
        self.condensation_lost = False
        self.heating_ineffective = False
        self.last_heating_rate: float | None = None
        self.last_rise: float | None = None
        self.season_active = True
        self.burner_on = False
        self.burner_available = True
        self.pressure_problem = False
        self.heatups: list[dict[str, Any]] = []
        self._heatup: dict[str, Any] | None = None
        self._last_mode: str | None = None
        self._last_setpoint: float | None = None
        self._stats_cache: dict[str, Any] | None = None
        self._csv_buf: list[str] = []
        self._csv_flushing = False

    # ------------------------------------------------------------------ config
    @property
    def cfg(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    def _opt(self, key: str, default: Any) -> Any:
        val = self.cfg.get(key)
        return default if val in (None, "") else val

    @property
    def name(self) -> str:
        return self.cfg.get(CONF_NAME, "Boiler")

    @property
    def short_cycle_s(self) -> float:
        return float(self._opt(CONF_SHORT_CYCLE_MIN, DEFAULT_SHORT_CYCLE_MIN)) * 60

    @property
    def return_threshold(self) -> float:
        return float(self._opt(CONF_RETURN_THRESHOLD, DEFAULT_RETURN_THRESHOLD))

    @property
    def csv_path(self) -> str:
        return self.hass.config.path(DOMAIN, f"{slugify(self.name)}.csv")

    # --------------------------------------------------------------- lifecycle
    async def async_start(self) -> None:
        data = await self._store.async_load() or {}
        self.cycles = data.get("cycles", [])
        self.hours = {int(k): v for k, v in data.get("hours", {}).items()}
        self.last_alert = data.get("last_alert", {})
        self.heatups = data.get("heatups", [])
        last_saved = data.get("saved_at")

        now = dt_util.utcnow().timestamp()
        self.started_at = now
        self._last_tick = now

        # A cycle left open by a crash/restart: close it at the last save time.
        if self.cycles and self.cycles[-1].get("end") is None:
            c = self.cycles[-1]
            c["end"] = max(c["start"], float(last_saved or c["start"]))
            c["partial"] = True

        self._refresh_season()
        self._refresh_burner(now, initial=True)

        cfg = self.cfg
        watched = [cfg[CONF_BURNER]]
        if cfg.get(CONF_SEASON_ENTITY):
            watched.append(cfg[CONF_SEASON_ENTITY])
        self._unsubs.append(
            async_track_state_change_event(self.hass, watched, self._on_state_event)
        )
        regulation = [e for e in (cfg.get(CONF_THERMOREG), cfg.get(CONF_FLOW_SETPOINT)) if e]
        if regulation:
            self._last_mode = self.regulation_mode
            self._last_setpoint = self.flow_target()
            self._unsubs.append(
                async_track_state_change_event(self.hass, regulation, self._on_regulation_event)
            )
        if cfg.get(CONF_PRESSURE):
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [cfg[CONF_PRESSURE]], self._on_pressure_event
                )
            )
        if cfg.get(CONF_RETURN_TEMP):
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [cfg[CONF_RETURN_TEMP]], self._on_return_event
                )
            )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._on_tick, timedelta(seconds=SAMPLE_INTERVAL_SECONDS)
            )
        )

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._effect_unsub:
            self._effect_unsub()
            self._effect_unsub = None
        self._account_burn(dt_util.utcnow().timestamp())
        await self._store.async_save(self._data_to_save())

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "cycles": self.cycles,
            "hours": {str(k): v for k, v in self.hours.items()},
            "last_alert": self.last_alert,
            "heatups": self.heatups,
            "saved_at": dt_util.utcnow().timestamp(),
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._data_to_save, 30)

    async def async_reset(self) -> None:
        self.cycles = [c for c in self.cycles if c.get("end") is None]
        self.hours = {}
        self.last_alert = {}
        self.heatups = []
        self._heatup = None
        self.condensation_lost = self.heating_ineffective = False
        self.last_heating_rate = self.last_rise = None
        await self._store.async_save(self._data_to_save())
        self._notify_entities()

    # ------------------------------------------------------------ state reads
    def _state_val(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        return _f(st.state) if st else None

    def flow_temp(self) -> float | None:
        return self._state_val(self.cfg.get(CONF_FLOW_TEMP))

    def return_temp(self) -> float | None:
        return self._state_val(self.cfg.get(CONF_RETURN_TEMP))

    def outdoor_temp(self) -> float | None:
        return self._state_val(self.cfg.get(CONF_OUTDOOR_TEMP))

    def indoor_avg(self) -> float | None:
        vals = [
            v
            for v in (self._state_val(e) for e in self.cfg.get(CONF_INDOOR_TEMPS) or [])
            if v is not None
        ]
        return sum(vals) / len(vals) if vals else None

    def flow_target(self) -> float | None:
        return self._state_val(self.cfg.get(CONF_FLOW_SETPOINT))

    def pressure(self) -> float | None:
        return self._state_val(self.cfg.get(CONF_PRESSURE))

    @property
    def regulation_mode(self) -> str | None:
        """weather_compensation / fixed, or None when not configured/unknown."""
        ent = self.cfg.get(CONF_THERMOREG)
        if not ent:
            return None
        st = self.hass.states.get(ent)
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return self._last_mode
        return MODE_CURVE if st.state.lower() in ("on", "true", "1") else MODE_FIXED

    def _thermostat(self) -> State | None:
        ent = self.cfg.get(CONF_THERMOSTAT)
        st = self.hass.states.get(ent) if ent else None
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return st

    def thermostat_setpoint(self) -> float | None:
        """Room temperature the thermostat is aiming for (None when off)."""
        st = self._thermostat()
        if st is None or st.state == "off":
            return None
        return _f(st.attributes.get("temperature"))

    def room_temp(self) -> float | None:
        """Indoor average, or the thermostat's own reading when no indoor sensors are set."""
        v = self.indoor_avg()
        if v is not None:
            return v
        st = self._thermostat()
        return _f(st.attributes.get("current_temperature")) if st else None

    def delta_t(self) -> float | None:
        f, r = self.flow_temp(), self.return_temp()
        return None if f is None or r is None else f - r

    def _is_burner_on(self, st: State | None) -> bool | None:
        """True/False, or None when unavailable."""
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        on_state = str(self._opt(CONF_BURNER_ON_STATE, DEFAULT_BURNER_ON_STATE)).strip()
        if st.domain == "climate":
            # Climate entities: look at hvac_action (e.g. "heating")
            action = st.attributes.get("hvac_action")
            target = on_state if on_state != "on" else "heating"
            return str(action).lower() == target.lower()
        return st.state.lower() == on_state.lower()

    def _refresh_season(self) -> None:
        ent = self.cfg.get(CONF_SEASON_ENTITY)
        if not ent:
            self.season_active = True
            return
        st = self.hass.states.get(ent)
        want = str(self._opt(CONF_SEASON_STATE, DEFAULT_SEASON_STATE)).strip().lower()
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return  # keep last known value
        if st.domain == "climate" and want in ("on", "heat"):
            self.season_active = st.state in ("heat", "auto", "heat_cool")
        else:
            self.season_active = st.state.lower() == want

    # --------------------------------------------------------------- handlers
    @callback
    def _on_state_event(self, event: Event) -> None:
        now = dt_util.utcnow().timestamp()
        if event.data["entity_id"] == self.cfg.get(CONF_SEASON_ENTITY):
            was = self.season_active
            self._refresh_season()
            if was and not self.season_active:
                # Season ended: close an open cycle silently.
                self._close_open_cycle(now, log=False)
            elif not was and self.season_active:
                self._refresh_burner(now, initial=True)
        else:
            self._refresh_burner(now)
        self._notify_entities()

    @callback
    def _on_return_event(self, event: Event) -> None:
        now = dt_util.utcnow().timestamp()
        self._check_return_hot(now)
        self._notify_entities()

    @callback
    def _on_regulation_event(self, event: Event) -> None:
        now = dt_util.utcnow().timestamp()
        mode = self.regulation_mode
        target = self.flow_target()
        if mode is not None and mode != self._last_mode:
            self._csv(now, "MODE", extra=f"mode={mode};target={target}")
            self.hass.bus.async_fire(
                EVENT_REGULATION,
                {"entry_id": self.entry.entry_id, "name": self.name, "mode": mode, "target": target},
            )
            self._last_mode = mode
        # In fixed mode the setpoint is a user setting -> log changes.
        # With weather compensation it moves with the outdoor temperature.
        if (
            target is not None
            and self._last_setpoint is not None
            and abs(target - self._last_setpoint) >= 0.5
            and mode != MODE_CURVE
        ):
            self._csv(now, "SETPOINT", extra=f"from={self._last_setpoint};to={target}")
        if target is not None:
            self._last_setpoint = target
        self._notify_entities()

    @callback
    def _on_pressure_event(self, event: Event) -> None:
        self._check_pressure(dt_util.utcnow().timestamp())
        self._notify_entities()

    def _check_pressure(self, now: float) -> None:
        p = self.pressure()
        if p is None:
            return
        lo = float(self._opt(CONF_PRESSURE_MIN, DEFAULT_PRESSURE_MIN))
        hi = float(self._opt(CONF_PRESSURE_MAX, DEFAULT_PRESSURE_MAX))
        if not self.pressure_problem and (p < lo or p > hi):
            self.pressure_problem = True
            kind = "low" if p < lo else "high"
            self._csv(now, "PRESSURE", extra=f"{kind}={p}")
            self.hass.bus.async_fire(
                EVENT_PRESSURE,
                {"entry_id": self.entry.entry_id, "name": self.name, "pressure": p, "kind": kind},
            )
            self._notify(
                "pressure",
                f"⚠️ {self.name}: pressure {'low' if kind == 'low' else 'high'}",
                f"Heating circuit pressure is {p:.2f} bar "
                f"(allowed {lo:.1f}–{hi:.1f} bar).",
            )
        elif self.pressure_problem and lo + 0.05 <= p <= hi - 0.05:
            self.pressure_problem = False

    @callback
    def _on_tick(self, _now: datetime) -> None:
        now = dt_util.utcnow().timestamp()
        dt = min(now - self._last_tick, SAMPLE_INTERVAL_SECONDS * 2)
        self._last_tick = now
        self._sample_pressure(now)
        self._check_pressure(now)
        if not self.burner_available:
            _add(self._bucket(now), "na_s", dt)
        if self.season_active:
            self._sample(now, dt)
            self._check_heatup(now)
            self._account_burn(now)
            self._check_return_hot(now)
        self._prune(now)
        self._save()
        self._notify_entities()

    # ----------------------------------------------------------- cycle logic
    def _open_cycle(self) -> dict[str, Any] | None:
        if self.cycles and self.cycles[-1].get("end") is None:
            return self.cycles[-1]
        return None

    def _last_closed_cycle(self) -> dict[str, Any] | None:
        for c in reversed(self.cycles):
            if c.get("end") is not None:
                return c
        return None

    def _refresh_burner(self, now: float, initial: bool = False) -> None:
        st = self.hass.states.get(self.cfg[CONF_BURNER])
        on = self._is_burner_on(st)
        was_available = self.burner_available
        self.burner_available = on is not None
        if on is None:
            # We no longer know what the burner does: stop counting. A burn in
            # progress ends here as partial, so only the observed part counts.
            self.burner_on = False
            self._close_lost_cycle(now)
            return
        prev = self.burner_on
        self.burner_on = on
        if not self.season_active:
            return
        if on and self._open_cycle() is None:
            # Coming back already on: the real start was not observed.
            self._start_cycle(now, partial=initial or not was_available)
        elif not on and self._open_cycle() is not None and (prev or initial):
            self._stop_cycle(now)

    def _start_cycle(self, now: float, partial: bool = False) -> None:
        last = self._last_closed_cycle()
        # Off-time is measured from the *recorded* stop of the previous cycle
        # (persisted), never from last_changed, so a restart cannot fake a
        # short cycle. A cycle whose real start/stop was not observed
        # (partial) is never used.
        off_s: float | None = None
        if not partial and last is not None and not last.get("partial"):
            off_s = now - last["end"]

        short = off_s is not None and off_s < self.short_cycle_s
        # For heat-up detection, a burner that has been off since HA started also counts
        heat_off = off_s
        if heat_off is None and not partial and last is None:
            heat_off = now - self.started_at
        self._maybe_open_heatup(now, heat_off)
        cycle = {
            "start": now,
            "end": None,
            "off_s": _r(off_s, 0),
            "short": short,
            "partial": partial,
            "outdoor": _r(self.outdoor_temp()),
            "indoor_start": _r(self.indoor_avg(), 2),
            "ret_start": _r(self.return_temp()),
        }
        self.cycles.append(cycle)
        self._burn_accounted_until = now
        b = self._bucket(now)
        b["cycles"] += 1
        if short:
            b["short"] += 1

        self._csv(now, "START", off_min=_r(off_s / 60 if off_s else None))
        if short:
            self._alert_short_cycle(off_s or 0)

        # Thermal-effect check. If one is already pending (burner cycling
        # faster than the check delay) keep it, so the rise is measured over
        # the whole heating period instead of being restarted every cycle.
        if (
            self._effect_unsub is None
            and self.cfg.get(CONF_INDOOR_TEMPS)
            and cycle["indoor_start"] is not None
        ):
            delay = float(self._opt(CONF_EFFECT_DELAY_MIN, DEFAULT_EFFECT_DELAY_MIN)) * 60
            self._effect_unsub = async_call_later(
                self.hass, delay, self._make_effect_check(cycle, now)
            )
        self._save()

    def _stop_cycle(self, now: float) -> None:
        cycle = self._open_cycle()
        if cycle is None:
            return
        self._account_burn(now)
        burn_s = now - cycle["start"]
        min_burn = float(self._opt(CONF_MIN_BURN_SECONDS, DEFAULT_MIN_BURN_SECONDS))
        if burn_s < min_burn and not cycle.get("partial"):
            # Relay glitch: drop it entirely so it does not distort statistics.
            self.cycles.pop()
            b = self._bucket(cycle["start"])
            b["cycles"] = max(0, b["cycles"] - 1)
            if cycle.get("short"):
                b["short"] = max(0, b["short"] - 1)
            b["burn_s"] = max(0.0, b["burn_s"] - burn_s)
            self._burn_accounted_until = None
            if self._heatup and self._heatup["start"] == cycle["start"]:
                self._heatup = None  # it was a glitch, not a heat-up
            return
        cycle["end"] = now
        self._close_heatup(now)
        cycle["ret_end"] = _r(self.return_temp())
        cycle["flow_end"] = _r(self.flow_temp())
        cycle["indoor_end"] = _r(self.indoor_avg(), 2)
        self._burn_accounted_until = None
        self._csv(now, "STOP", burn_min=_r(burn_s / 60))
        self.hass.bus.async_fire(
            EVENT_CYCLE_END,
            {
                "entry_id": self.entry.entry_id,
                "name": self.name,
                "burn_minutes": round(burn_s / 60, 1),
                "off_minutes_before": _r((cycle.get("off_s") or 0) / 60)
                if cycle.get("off_s") is not None
                else None,
                "short_cycle": cycle.get("short", False),
                "outdoor": cycle.get("outdoor"),
            },
        )
        self._save()

    def _close_open_cycle(self, now: float, log: bool = True) -> None:
        if self._open_cycle() is not None:
            if log:
                self._stop_cycle(now)
            else:
                self._account_burn(now)
                self._open_cycle()["end"] = now  # type: ignore[index]
                self._burn_accounted_until = None

    def _close_lost_cycle(self, now: float) -> None:
        """Burner entity became unavailable mid-burn: close the cycle as partial."""
        cycle = self._open_cycle()
        if cycle is None:
            return
        self._account_burn(now)
        cycle["end"] = now
        # Partial: the real stop was not observed, so it is not used for the
        # average burn time nor for the off-time of the next cycle.
        cycle["partial"] = True
        self._burn_accounted_until = None
        self._close_heatup(now)
        self._csv(now, "UNAVAILABLE", burn_min=_r((now - cycle["start"]) / 60))
        self._save()

    def _make_effect_check(self, cycle: dict[str, Any], started: float) -> Callable:
        @callback
        def _check(_now: datetime) -> None:
            self._effect_unsub = None
            if not self.season_active:
                return
            now = dt_util.utcnow().timestamp()
            cur = self.indoor_avg()
            start = cycle.get("indoor_start")
            if cur is None or start is None:
                return
            rise = cur - start
            hours = max((now - started) / 3600, 1e-6)
            self.last_rise = round(rise, 2)
            self.last_heating_rate = round(rise / hours, 2)
            cycle["rise"] = self.last_rise
            min_rise = float(self._opt(CONF_MIN_RISE, DEFAULT_MIN_RISE))
            was = self.heating_ineffective
            self.heating_ineffective = rise < min_rise
            if self.heating_ineffective and not was:
                self._csv(now, "INEFFECTIVE", extra=f"rise={rise:.2f}")
                self.hass.bus.async_fire(
                    EVENT_INEFFECTIVE,
                    {"entry_id": self.entry.entry_id, "name": self.name, "rise": round(rise, 2)},
                )
                self._notify(
                    "ineffective",
                    f"⚠️ {self.name}: heating without effect",
                    f"Since the burner started {round((now - started) / 60)} min ago, "
                    f"the rooms rose only {rise:.2f}°C (expected ≥ {min_rise}°C).",
                )
            self._notify_entities()

        return _check

    def _check_return_hot(self, now: float) -> None:
        if not self.season_active:
            return
        ret = self.return_temp()
        thr = self.return_threshold
        if ret is None:
            return
        if ret > thr and self.burner_on:
            if self._return_hot_since is None:
                self._return_hot_since = now
            dur = float(self._opt(CONF_RETURN_HOT_MINUTES, DEFAULT_RETURN_HOT_MINUTES)) * 60
            if not self.condensation_lost and now - self._return_hot_since >= dur:
                self.condensation_lost = True
                self._csv(now, "RETURN_HOT")
                self.hass.bus.async_fire(
                    EVENT_CONDENSATION_LOST,
                    {"entry_id": self.entry.entry_id, "name": self.name, "return": ret},
                )
                self._notify(
                    "return_hot",
                    f"⚠️ {self.name}: condensation lost",
                    f"Return is {ret:.1f}°C, above {thr:.0f}°C for "
                    f"{round((now - self._return_hot_since) / 60)} min. "
                    "Curve may be too steep or flow restricted.",
                )
        elif ret < thr - 1 or not self.burner_on:
            # 1°C hysteresis before clearing
            self._return_hot_since = None
            self.condensation_lost = False

    def _alert_short_cycle(self, off_s: float) -> None:
        now = dt_util.utcnow().timestamp()
        self.hass.bus.async_fire(
            EVENT_SHORT_CYCLE,
            {"entry_id": self.entry.entry_id, "name": self.name, "off_minutes": round(off_s / 60, 1)},
        )
        self._csv(now, "SHORT_CYCLE", off_min=round(off_s / 60, 1))
        n1h = sum(1 for c in self.cycles if c.get("short") and c["start"] >= now - 3600)
        self._notify(
            "short_cycle",
            f"⚠️ {self.name}: short-cycling",
            f"Burner restarted after only {off_s / 60:.1f} min off "
            f"(threshold {self.short_cycle_s / 60:.0f} min). "
            f"{n1h} short cycle(s) in the last hour.",
        )

    # ------------------------------------------------------- bucket helpers
    def _bucket(self, ts: float) -> dict[str, float]:
        key = _hour_key(ts)
        if key not in self.hours:
            self.hours[key] = _new_bucket()
        return self.hours[key]

    def _account_burn(self, now: float) -> None:
        """Add burn time since last accounting, split across hour buckets."""
        if self._burn_accounted_until is None or self._open_cycle() is None:
            return
        t = self._burn_accounted_until
        while t < now:
            nxt = min(now, _hour_key(t) + 3600)
            self._bucket(t)["burn_s"] += nxt - t
            t = nxt
        self._burn_accounted_until = now

    def _sample(self, now: float, dt: float) -> None:
        b = self._bucket(now)
        out = self.outdoor_temp()
        if out is not None:
            _add(b, "out_sum", out)
            _add(b, "out_n", 1)
        burning = self.burner_on and self._open_cycle() is not None
        if burning:
            ret = self.return_temp()
            if ret is not None:
                b["smp_s"] = b.get("smp_s", 0.0) + dt
                if ret <= self.return_threshold:
                    b["cond_s"] = b.get("cond_s", 0.0) + dt
                # Highest return seen while burning (diagnostics; max, not sum)
                b["ret_max"] = max(b.get("ret_max", ret), ret)
            d = self.delta_t()
            if d is not None:
                _add(b, "dt_sum", d)
                _add(b, "dt_n", 1)
            cyc = self._open_cycle()
            flow, target = self.flow_temp(), self.flow_target()
            if flow is not None and cyc is not None and now - cyc["start"] >= FLOW_SETTLE_S:
                _add(b, "fl_sum", flow)
                _add(b, "fl_n", 1)
                if target is not None:
                    _add(b, "dev_sum", flow - target)
                    _add(b, "dev_n", 1)
        room = self.room_temp()
        if room is not None:
            _add(b, "in_sum", room)
            _add(b, "in_n", 1)
        sp = self.thermostat_setpoint()
        if sp is not None:
            _add(b, "sp_sum", sp)
            _add(b, "sp_n", 1)
            b["sp_min"] = min(b.get("sp_min", sp), sp)
            b["sp_max"] = max(b.get("sp_max", sp), sp)
        # Some boilers report 0 / the minimum / a frozen value while idle,
        # which would bend the fitted curve.
        target = self.flow_target()
        only_burning = self._opt(CONF_TARGET_ONLY_BURNING, DEFAULT_TARGET_ONLY_BURNING)
        if (
            target is not None
            and target >= MIN_VALID_FLOW_TARGET
            and (burning or not only_burning)
        ):
            _add(b, "tgt_sum", target)
            _add(b, "tgt_n", 1)
            if self.regulation_mode == MODE_CURVE:
                _add(b, "th_n", 1)

    # ------------------------------------------------------------- heat-up
    def _maybe_open_heatup(self, now: float, off_s: float | None) -> None:
        """Start measuring how fast the house warms up (after a long pause)."""
        if self._heatup is not None or off_s is None or off_s < cmf.HEATUP_MIN_OFF_S:
            return
        room = self.room_temp()
        if room is None:
            return
        sp = self.thermostat_setpoint()
        if sp is not None and sp - room < cmf.HEATUP_MIN_GAP:
            return
        self._heatup = {"start": now, "in0": round(room, 2), "sp": sp, "out": _r(self.outdoor_temp())}

    def _check_heatup(self, now: float) -> None:
        ev = self._heatup
        if ev is None:
            return
        room = self.room_temp()
        if ev["sp"] is not None and room is not None and room >= ev["sp"] - 0.1:
            self._close_heatup(now)
        elif now - ev["start"] > cmf.HEATUP_MAX_S:
            self._close_heatup(now)

    def _close_heatup(self, now: float) -> None:
        ev, self._heatup = self._heatup, None
        if ev is None:
            return
        room = self.room_temp()
        if room is None:
            return
        rise = room - ev["in0"]
        dur = now - ev["start"]
        if rise < cmf.HEATUP_MIN_RISE or dur < cmf.HEATUP_MIN_S:
            return
        minutes = dur / 60
        self.heatups.append(
            {
                "ts": int(ev["start"]),
                "end": int(now),
                "out": ev["out"],
                "in0": ev["in0"],
                "in1": round(room, 2),
                "sp": ev["sp"],
                "rise": round(rise, 2),
                "minutes": round(minutes, 1),
                "rate": round(minutes / rise, 1),
            }
        )
        cut = now - 60 * 86400
        self.heatups = [e for e in self.heatups if e["ts"] >= cut][-cmf.HEATUP_KEEP :]
        self._csv(now, "HEATUP", extra=f"rise={rise:.2f};min={minutes:.0f};rate={minutes / rise:.1f}")
        self._save()

    def heatup_model(self) -> dict[str, Any] | None:
        return cmf.heatup_model(self.heatups)

    async def async_estimate_preheat(self, target: float | None, at: datetime | None) -> dict[str, Any]:
        """When to start heating to reach `target` °C at time `at`."""
        now = dt_util.now()
        if target is None:
            target = self.thermostat_setpoint()
        room = self.room_temp()
        model = self.heatup_model()
        outdoor = self.outdoor_temp()
        source = "now"
        if at is not None and self.cfg.get(CONF_WEATHER):
            fc = await self._forecast_temp(at)
            if fc is not None:
                outdoor, source = fc, "forecast"
        minutes = cmf.preheat_minutes(model, room, target, outdoor)
        res: dict[str, Any] = {
            "target": target,
            "indoor": None if room is None else round(room, 2),
            "outdoor": outdoor,
            "outdoor_source": source,
            "rate_min_per_degree": cmf.heatup_rate(model, outdoor),
            "minutes": minutes,
            "events": model["n"] if model else 0,
        }
        if at is not None and minutes is not None:
            start = at - timedelta(minutes=minutes)
            res["at"] = at.isoformat()
            res["start_at"] = start.isoformat()
            res["start_now"] = start <= now
        return res

    async def _forecast_temp(self, at: datetime) -> float | None:
        ent = self.cfg.get(CONF_WEATHER)
        try:
            resp = await self.hass.services.async_call(
                "weather", "get_forecasts", {"entity_id": ent, "type": "hourly"},
                blocking=True, return_response=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("%s: hourly forecast not available: %s", self.name, err)
            return None
        items = (resp or {}).get(ent, {}).get("forecast") or []
        best, best_d = None, None
        for it in items:
            t = dt_util.parse_datetime(str(it.get("datetime", "")))
            temp = _f(it.get("temperature"))
            if t is None or temp is None:
                continue
            d = abs((t - at).total_seconds())
            if best_d is None or d < best_d:
                best, best_d = temp, d
        return best if best_d is not None and best_d <= 3 * 3600 else None

    # ------------------------------------------------------------- comfort
    def comfort_points(self) -> list[list[Any]]:
        now = dt_util.utcnow().timestamp()
        return cmf.comfort_points(self.hours, now - COMFORT_DAYS * 86400, MAX_NA_S_PER_HOUR)

    def comfort(self) -> dict[str, Any]:
        return cmf.comfort_verdict(self.comfort_points())

    def _sample_pressure(self, now: float) -> None:
        p = self.pressure()
        if p is not None:
            b = self._bucket(now)
            _add(b, "p_sum", p)
            _add(b, "p_n", 1)

    def _prune(self, now: float) -> None:
        cut_c = now - CYCLE_RETENTION_HOURS * 3600
        if self.cycles and self.cycles[0]["start"] < cut_c:
            self.cycles = [c for c in self.cycles if c["start"] >= cut_c or c.get("end") is None]
        cut_h = now - DAILY_RETENTION_DAYS * 86400
        for k in [k for k in self.hours if k < cut_h]:
            del self.hours[k]

    # ------------------------------------------------------------- flags
    @property
    def short_cycling(self) -> bool:
        now = dt_util.utcnow().timestamp()
        return any(c.get("short") and c["start"] >= now - 3600 for c in self.cycles)

    # ----------------------------------------------------------- statistics
    @property
    def status(self) -> str:
        if not self.burner_available:
            return STATUS_UNAVAILABLE
        if not self.season_active:
            return STATUS_OFF_SEASON
        return STATUS_HEATING if self.burner_on else STATUS_IDLE

    def _window_cycles(self, now: float, seconds: float) -> list[dict[str, Any]]:
        return [c for c in self.cycles if c["start"] >= now - seconds]

    def _sum_hours(self, start: float, end: float, field: str) -> float:
        return sum(v.get(field, 0) for k, v in self.hours.items() if start <= k < end)

    def _comfort_stats(self, now: float) -> dict[str, Any]:
        pts = self.comfort_points()
        recent = [p[1] for p in pts if p[4] >= _hour_key(now) - 23 * 3600]
        verdict = cmf.comfort_verdict(pts)
        model = self.heatup_model()
        out = self.outdoor_temp()
        return {
            "comfort_verdict": verdict["verdict"],
            "comfort_confidence": verdict.get("confidence"),
            "comfort_gap_24h": round(sum(recent) / len(recent), 2) if recent else None,
            "heatup_rate": cmf.heatup_rate(model, out),
            "preheat_minutes": cmf.preheat_minutes(model, self.room_temp(), self.thermostat_setpoint(), out),
            "thermostat_setpoint": self.thermostat_setpoint(),
        }

    def _avg_hours(self, start: float, end: float, sum_f: str, n_f: str) -> float | None:
        n = self._sum_hours(start, end, n_f)
        return _r(self._sum_hours(start, end, sum_f) / n) if n else None

    def curve_points(self, hours: int = CURVE_HOURS) -> list[list[Any]]:
        """Per hour: [outdoor avg, target avg, actual flow avg (burning) | None, mode 1=curve 0=fixed, hour start ts]."""
        now = dt_util.utcnow().timestamp()
        out = []
        for k in sorted(self.hours):
            if k < now - hours * 3600:
                continue
            v = self.hours[k]
            if not v.get("tgt_n") or not v.get("out_n") or _na_hour(v):
                continue
            out.append(
                [
                    round(v["out_sum"] / v["out_n"], 1),
                    round(v["tgt_sum"] / v["tgt_n"], 1),
                    round(v["fl_sum"] / v["fl_n"], 1) if v.get("fl_n") else None,
                    1 if v.get("th_n", 0) * 2 >= v["tgt_n"] else 0,
                    k,  # hour start (epoch seconds, UTC)
                ]
            )
        return out

    def curve_fit(self) -> dict[str, float] | None:
        """Linear fit target = a + b*outdoor over weather-compensated hours."""
        pts = [(p[0], p[1]) for p in self.curve_points() if p[3] == 1]
        if len(pts) < 6:
            return None
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        if max(p[0] for p in pts) - min(p[0] for p in pts) < 3:
            return None  # outdoor range too narrow for a meaningful slope
        sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
        b = sxy / sxx
        a = my - b * mx
        syy = sum((p[1] - my) ** 2 for p in pts)
        return {
            "slope": round(-b, 2),  # °C of flow per °C colder outside (positive)
            "intercept": round(a, 2),
            "raw_slope": round(b, 3),
            "at_0": round(a, 1),
            "at_minus_10": round(a - 10 * b, 1),
            "r2": round((sxy * sxy) / (sxx * syy), 2) if syy > 0 else 1.0,
            "n": n,
        }

    def pressure_change(self) -> float | None:
        """Mean of the last 24 h minus mean of the oldest day in the last 7 days."""
        now = dt_util.utcnow().timestamp()
        keys = sorted(k for k, v in self.hours.items() if v.get("p_n") and k >= now - 7 * 86400)
        if not keys or keys[-1] - keys[0] < 2 * 86400:
            return None
        def mean(ks: list[int]) -> float | None:
            n = sum(self.hours[k]["p_n"] for k in ks)
            return sum(self.hours[k]["p_sum"] for k in ks) / n if n else None
        old = mean([k for k in keys if k < keys[0] + 86400])
        new = mean([k for k in keys if k >= now - 86400])
        return None if old is None or new is None else round(new - old, 2)

    def _max_hours(self, start: float, end: float, field: str) -> float | None:
        vals = [v[field] for k, v in self.hours.items() if start <= k < end and field in v]
        return max(vals) if vals else None

    def stats(self) -> dict[str, Any]:
        """All derived statistics (cached until the next update signal)."""
        if self._stats_cache is None:
            self._stats_cache = self._compute_stats()
        return self._stats_cache

    def _compute_stats(self) -> dict[str, Any]:
        now = dt_util.utcnow().timestamp()
        self._account_burn(now)
        day = 86400
        win = self._window_cycles(now, day)
        closed = [c for c in win if c.get("end") is not None]
        burns = [c["end"] - c["start"] for c in closed if not c.get("partial")]
        offs = [c["off_s"] for c in win if c.get("off_s") is not None]

        h_start = _hour_key(now) - 23 * 3600
        burn_24 = self._sum_hours(h_start, now + 1, "burn_s")
        smp = self._sum_hours(h_start, now + 1, "smp_s")
        cond = self._sum_hours(h_start, now + 1, "cond_s")
        span = now - max(h_start, self.earliest_ts() or h_start)

        today_start = dt_util.start_of_local_day().timestamp()
        today = [c for c in self.cycles if c["start"] >= today_start]
        open_c = self._open_cycle()
        last = self._last_closed_cycle()

        reg = self.regression()
        hdd = self.burn_per_hdd(7)

        return {
            "cycles_today": len(today),
            "short_cycles_today": sum(1 for c in today if c.get("short")),
            "cycles_24h": len(win),
            "cycles_per_hour": _r(len(win) / max(min(span, day) / 3600, 1), 2),
            "avg_burn_min": _r(sum(burns) / len(burns) / 60) if burns else None,
            "avg_off_min": _r(sum(offs) / len(offs) / 60) if offs else None,
            "duty_cycle": _r(100 * burn_24 / max(min(span, day), 60)),
            "burn_hours_today": round(
                self._sum_hours(_hour_key(today_start), now + 1, "burn_s") / 3600, 2
            ),
            "last_burn_min": _r((last["end"] - last["start"]) / 60) if last else None,
            "current_burn_min": _r((now - open_c["start"]) / 60) if open_c else None,
            "condensing_ratio": _r(100 * cond / smp) if smp >= 300 else None,
            "condensing_minutes": round(cond / 60),
            "flow_target": _r(self.flow_target()),
            "flow_deviation": self._avg_hours(h_start, now + 1, "dev_sum", "dev_n"),
            "regulation_mode": self.regulation_mode,
            "curve_slope": (cf := self.curve_fit()) and cf.get("slope"),
            "pressure": _r(self.pressure(), 2),
            "pressure_change_7d": self.pressure_change(),
            **self._comfort_stats(now),
            "burning_sampled_minutes": round(smp / 60),
            "return_max_24h": _r(self._max_hours(h_start, now + 1, "ret_max")),
            "delta_t": _r(self.delta_t()),
            "heating_rate": self.last_heating_rate,
            "balance_point": reg.get("balance_point") if reg else None,
            "burn_per_hdd": hdd,
        }

    def earliest_ts(self) -> float | None:
        cands = []
        if self.hours:
            cands.append(min(self.hours))
        if self.cycles:
            cands.append(self.cycles[0]["start"])
        return min(cands) if cands else None

    def daily(self, days: int = 30) -> list[dict[str, Any]]:
        """Per local day aggregates (oldest first)."""
        agg: dict[str, dict[str, float]] = {}
        for k, v in self.hours.items():
            d = dt_util.as_local(dt_util.utc_from_timestamp(k)).date().isoformat()
            a = agg.setdefault(d, {**_new_bucket(), "ok_n": 0})
            for f in _new_bucket():
                a[f] += v.get(f, 0)
            if not _na_hour(v):
                a["ok_n"] += v.get("out_n", 0)
        out = []
        for d in sorted(agg)[-days:]:
            a = agg[d]
            out.append(
                {
                    "date": d,
                    "burn_h": round(a["burn_s"] / 3600, 2),
                    "cycles": int(a["cycles"]),
                    "short": int(a["short"]),
                    "outdoor": _r(a["out_sum"] / a["out_n"]) if a["out_n"] else None,
                    "cond_pct": _r(100 * a["cond_s"] / a["smp_s"]) if a["smp_s"] >= 300 else None,
                    "delta_t": _r(a["dt_sum"] / a["dt_n"]) if a["dt_n"] else None,
                    "samples": int(a["out_n"]),
                    # samples from hours in which the burner state was known
                    "samples_ok": int(a["ok_n"]),
                }
            )
        return out

    def _complete_days(self, days: int) -> list[dict[str, Any]]:
        today = dt_util.now().date().isoformat()
        # A day counts if it is in the past and has at least ~20h of samples,
        # not counting hours in which the burner entity was mostly unavailable.
        return [
            d
            for d in self.daily(days)
            if d["date"] != today and d["outdoor"] is not None and d["samples_ok"] >= 20 * 60 * 60 / SAMPLE_INTERVAL_SECONDS
        ]

    def regression(self, days: int = 30) -> dict[str, float] | None:
        """Linear fit burn_h = a + b*outdoor over complete days."""
        pts = [(d["outdoor"], d["burn_h"]) for d in self._complete_days(days)]
        if len(pts) < 3:
            return None
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        if sxx < 1:
            return None
        sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
        b = sxy / sxx
        a = my - b * mx
        syy = sum((p[1] - my) ** 2 for p in pts)
        r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else 0.0
        res = {"slope": round(b, 3), "intercept": round(a, 3), "r2": round(r2, 2), "n": n}
        if b < 0:
            res["balance_point"] = round(-a / b, 1)
        return res

    def burn_per_hdd(self, days: int = 7) -> float | None:
        ds = self._complete_days(days + 1)[-days:]
        hdd = sum(max(0.0, HDD_BASE - d["outdoor"]) for d in ds)
        burn = sum(d["burn_h"] for d in ds)
        return round(burn / hdd, 3) if hdd >= 1 else None

    def timeline(self, hours: int = 24) -> list[list[Any]]:
        now = dt_util.utcnow().timestamp()
        out = []
        for c in self.cycles:
            end = c.get("end")
            if (end or now) < now - hours * 3600:
                continue
            out.append([int(c["start"]), int(end) if end else None, 1 if c.get("short") else 0])
        return out

    # ------------------------------------------------------------- outputs
    def _notify(self, kind: str, title: str, message: str) -> None:
        svc = str(self._opt(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)).strip()
        if not svc:
            return
        now = dt_util.utcnow().timestamp()
        if now - self.last_alert.get(kind, 0) < ALERT_THROTTLE_S:
            return
        self.last_alert[kind] = now
        tag = f"{DOMAIN}_{slugify(self.name)}_{kind}"
        if svc.startswith("notify.") and self.hass.states.get(svc) is not None:
            domain, service = "notify", "send_message"
            data: dict[str, Any] = {"entity_id": svc, "title": title, "message": message}
        else:
            if "." not in svc:
                svc = f"notify.{svc}"
            domain, service = svc.split(".", 1)
            data = {"title": title, "message": message, "data": {"tag": tag}}

        async def _send() -> None:
            try:
                await self.hass.services.async_call(domain, service, data, blocking=True)
            except Exception as err:  # noqa: BLE001 - never break monitoring
                _LOGGER.warning("%s: notification via %s.%s failed: %s", self.name, domain, service, err)

        self.hass.async_create_task(_send())

    def _csv(self, now: float, event: str, **kw: Any) -> None:
        if not self._opt(CONF_CSV_LOG, DEFAULT_CSV_LOG):
            return
        ts = dt_util.as_local(dt_util.utc_from_timestamp(now)).strftime("%Y-%m-%d %H:%M:%S")
        vals = [
            ts,
            event,
            kw.get("burn_min", ""),
            kw.get("off_min", ""),
            _r(self.outdoor_temp()),
            _r(self.flow_temp()),
            _r(self.return_temp()),
            _r(self.indoor_avg(), 2),
            kw.get("extra", ""),
        ]
        self._csv_buf.append(";".join("" if v is None else str(v) for v in vals) + "\n")
        if not self._csv_flushing:
            self._csv_flushing = True
            self.hass.async_create_task(self._csv_flush())

    async def _csv_flush(self) -> None:
        """Write buffered lines in order (one writer at a time)."""
        path = self.csv_path

        def _write(lines: list[str]) -> None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            new = not os.path.exists(path)
            with open(path, "a", encoding="utf-8") as fh:
                if new:
                    fh.write("time;event;burn_min;off_min;outdoor;flow;return;indoor_avg;extra\n")
                fh.writelines(lines)

        try:
            while self._csv_buf:
                lines, self._csv_buf = self._csv_buf, []
                try:
                    await self.hass.async_add_executor_job(_write, lines)
                except OSError as err:
                    _LOGGER.warning("%s: cannot write CSV %s: %s", self.name, path, err)
        finally:
            self._csv_flushing = False

    @callback
    def _notify_entities(self) -> None:
        self._stats_cache = None
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

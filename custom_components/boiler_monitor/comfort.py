"""Comfort-vs-outdoor analysis and heat-up model (pure functions, no Home Assistant imports).

Comfort
-------
Every hour bucket stores the average indoor temperature, the thermostat setpoint
(min / max / average) and the burner time. From that we build one point per
"steady" hour: (outdoor, indoor - setpoint, duty, short cycles). Hours in which
the setpoint changed, and the hour right after a setpoint increase (recovery
from a night set-back), are left out: in those hours the house is *supposed* to
be below the setpoint.

A well-tuned curve keeps the house at the setpoint in any weather. With an
on/off thermostat in front of the boiler, a curve that is too *high* is hidden
in the indoor temperature (the thermostat cuts it off) and shows up as short
cycles / overshoot instead; a curve that is too *low* shows up as the house not
reaching the setpoint in cold weather while the burner runs nearly all the time.
The verdict combines both signals.

Heat-up
-------
A heat-up event starts when the burner comes on after at least an hour off and
the rooms are clearly below the setpoint; it ends when the rooms reach the
setpoint (or the burner stops / 4 h pass). Each event gives minutes per °C at
the outdoor temperature of the moment. A straight line through the events
(minutes per °C vs outdoor) predicts how long the house needs to warm up.
"""
from __future__ import annotations

from math import nan
from statistics import median
from typing import Any

# --- comfort -----------------------------------------------------------------
MIN_HOURS = 24  # steady hours needed before giving a verdict
MIN_SPREAD = 4.0  # °C of outdoor spread (10th..90th percentile) needed
GAP_COLD = -0.5  # house this much below setpoint in cold weather = too cold
GAP_WARM = 0.7  # house this much above setpoint = overshoot
DUTY_FLAT_OUT = 0.8  # burner on ≥80 % of the hour = running flat out
SHORT_PER_HOUR = 0.3  # short cycles per hour in mild weather = curve too high
MIN_DUTY_FOR_OVERSHOOT = 0.1  # mild-weather overshoot only blames the curve if the burner ran this much

VERDICT_OK = "ok"
VERDICT_SLOPE_LOW = "slope_low"
VERDICT_SLOPE_HIGH = "slope_high"
VERDICT_OFFSET_LOW = "offset_low"
VERDICT_OFFSET_HIGH = "offset_high"
VERDICT_INSUFFICIENT = "insufficient_data"
VERDICTS = [
    VERDICT_OK,
    VERDICT_SLOPE_LOW,
    VERDICT_SLOPE_HIGH,
    VERDICT_OFFSET_LOW,
    VERDICT_OFFSET_HIGH,
    VERDICT_INSUFFICIENT,
]

# --- heat-up -----------------------------------------------------------------
HEATUP_MIN_OFF_S = 3600  # burner off at least this long before an event
HEATUP_MIN_GAP = 0.5  # rooms at least this far below setpoint at the start
HEATUP_MIN_RISE = 0.4  # °C rise needed for a valid event
HEATUP_MIN_S = 300
HEATUP_MAX_S = 4 * 3600
HEATUP_KEEP = 200


def _quantile(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if not s:
        return 0.0
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def linfit(pts: list[tuple[float, float]]) -> dict[str, float] | None:
    """Least squares y = a + b*x. None when x has no spread."""
    n = len(pts)
    if n < 2:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx <= 1e-9:
        return None
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    b = sxy / sxx
    return {
        "a": my - b * mx,
        "b": b,
        "r2": (sxy * sxy) / (sxx * syy) if syy > 0 else 1.0,
        "n": n,
    }


def comfort_points(
    hours: dict[int, dict[str, float]], since: float, max_na_s: float | None = None
) -> list[list[Any]]:
    """[outdoor, gap, duty, short_cycles, hour_ts, indoor, setpoint] per steady hour.

    Hours with the burner unavailable for more than max_na_s seconds are left out.
    """
    out: list[list[Any]] = []
    prev: dict[str, float] | None = None
    prev_changed = False
    for k in sorted(hours):
        v = hours[k]
        if k < since:
            prev = v
            continue
        sp_n, in_n, out_n = v.get("sp_n", 0), v.get("in_n", 0), v.get("out_n", 0)
        changed = sp_n > 0 and (v.get("sp_max", 0) - v.get("sp_min", 0)) > 0.2
        raised = (
            prev is not None
            and prev.get("sp_n")
            and sp_n
            and v["sp_sum"] / sp_n - prev["sp_sum"] / prev["sp_n"] > 0.2
        )
        skip = changed or raised or prev_changed
        prev_changed = bool(changed or raised)
        prev = v
        if skip or not (sp_n and in_n and out_n):
            continue
        if max_na_s is not None and v.get("na_s", 0) > max_na_s:
            continue  # burner state unknown: the duty of this hour means nothing
        sp = v["sp_sum"] / sp_n
        indoor = v["in_sum"] / in_n
        out.append(
            [
                round(v["out_sum"] / out_n, 1),
                round(indoor - sp, 2),
                round(min(1.0, v.get("burn_s", 0) / 3600), 2),
                int(v.get("short", 0)),
                k,
                round(indoor, 2),
                round(sp, 1),
            ]
        )
    return out


def comfort_verdict(points: list[list[Any]]) -> dict[str, Any]:
    """Turn comfort points into a verdict + the numbers behind it."""
    n = len(points)
    # House above the setpoint with the burner off all hour: sun or other free
    # heat, not the curve. These hours say nothing about the gap.
    used = [p for p in points if not (p[2] == 0 and p[1] > 0)]
    res: dict[str, Any] = {
        "verdict": VERDICT_INSUFFICIENT,
        "confidence": None,
        "n": n,
        "rule": None,
        "excluded_sunny_hours": n - len(used),
    }
    if n < MIN_HOURS:
        res["reason"] = "hours"
        return res
    outs = [p[0] for p in points]
    p10, p33, p67, p90 = (_quantile(outs, q) for q in (0.1, 0.33, 0.67, 0.9))
    spread = p90 - p10
    res["spread"] = round(spread, 1)
    if spread < MIN_SPREAD:
        res["reason"] = "spread"
        return res

    cold = [p for p in points if p[0] <= p33]
    mild = [p for p in points if p[0] >= p67]
    # None when every hour of that third was a sunny one (no rule fires on it)
    gaps_cold = [p[1] for p in used if p[0] <= p33]
    gaps_mild = [p[1] for p in used if p[0] >= p67]
    gap_cold = median(gaps_cold) if gaps_cold else None
    gap_mild = median(gaps_mild) if gaps_mild else None
    duty_cold = sum(p[2] for p in cold) / len(cold)
    duty_mild = sum(p[2] for p in mild) / len(mild)
    short_mild = sum(p[3] for p in mild) / len(mild)
    fit = linfit([(p[0], p[1]) for p in used])
    trend = fit["b"] if fit else 0.0  # °C of indoor gap per °C outdoor

    res.update(
        gap_cold=None if gap_cold is None else round(gap_cold, 2),
        gap_mild=None if gap_mild is None else round(gap_mild, 2),
        duty_cold=round(duty_cold, 2),
        duty_mild=round(duty_mild, 2),
        short_mild=round(short_mild, 2),
        trend=round(trend, 3),
        cold_below=round(p33, 1),
        mild_above=round(p67, 1),
        fit_a=round(fit["a"], 3) if fit else None,
        fit_b=round(fit["b"], 4) if fit else None,
    )

    # A missing gap is NaN here, so every comparison on it is False.
    gc = nan if gap_cold is None else gap_cold
    gm = nan if gap_mild is None else gap_mild
    if gc < GAP_COLD and gm < GAP_COLD:
        verdict, rule = VERDICT_OFFSET_LOW, "cold_all_weather"
    elif gc < GAP_COLD and duty_cold >= DUTY_FLAT_OUT:
        # can't keep up when it's cold, fine when mild
        verdict, rule = VERDICT_SLOPE_LOW, "flat_out_cold"
    elif short_mild >= SHORT_PER_HOUR:
        verdict, rule = VERDICT_OFFSET_HIGH, "short_cycles_mild"
    elif gm > GAP_WARM and duty_mild >= MIN_DUTY_FOR_OVERSHOOT:
        # too much heat in mild weather, and the boiler is the one providing it
        verdict, rule = VERDICT_OFFSET_HIGH, "overshoot_mild"
    elif gc > GAP_WARM and duty_cold < 0.5:
        verdict, rule = VERDICT_SLOPE_HIGH, "overshoot_cold"
    elif trend > 0.08 and gc < -0.3:
        verdict, rule = VERDICT_SLOPE_LOW, "trend_low"
    elif trend < -0.08 and gc > 0.3:
        verdict, rule = VERDICT_SLOPE_HIGH, "trend_high"
    else:
        verdict, rule = VERDICT_OK, "ok"
    res["verdict"] = verdict
    res["rule"] = rule
    res["confidence"] = (
        "high" if n >= 72 and spread >= 8 else "medium" if n >= 48 or spread >= 6 else "low"
    )
    return res


# --- heat-up -----------------------------------------------------------------
def heatup_model(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """minutes per °C as a function of outdoor temperature."""
    pts = [(e["out"], e["rate"]) for e in events if e.get("out") is not None]
    if not pts:
        return None
    rates = [p[1] for p in pts]
    model: dict[str, Any] = {
        "n": len(pts),
        "median": round(median(rates), 1),
        "min": round(min(rates), 1),
        "max": round(max(rates), 1),
    }
    outs = [p[0] for p in pts]
    fit = linfit(pts) if len(pts) >= 3 and max(outs) - min(outs) >= 3 else None
    if fit and fit["b"] <= 0:  # colder outside must not be faster
        model.update(a=round(fit["a"], 3), b=round(fit["b"], 4), r2=round(fit["r2"], 2))
    return model


def heatup_rate(model: dict[str, Any] | None, outdoor: float | None) -> float | None:
    """Predicted minutes per °C at this outdoor temperature."""
    if not model:
        return None
    if outdoor is None or "a" not in model:
        return model["median"]
    rate = model["a"] + model["b"] * outdoor
    # stay within a sane band around what was actually observed
    return round(min(max(rate, model["min"] * 0.5), model["max"] * 1.5), 1)


def preheat_minutes(
    model: dict[str, Any] | None, indoor: float | None, target: float | None, outdoor: float | None
) -> float | None:
    if indoor is None or target is None:
        return None
    if indoor >= target:
        return 0.0
    rate = heatup_rate(model, outdoor)
    return None if rate is None else round((target - indoor) * rate)


# --- curve advice -------------------------------------------------------------
# What flow temperature would keep the rooms exactly at the thermostat setting
# with the burner running most of the time (the point of weather compensation)?
#
# Per steady hour, radiator output ~ duty * (water - room)^n, and it equals the
# losses ~ (room - outdoor). With the room at the setpoint and the burner on for
# ADVICE_DUTY of the hour, the water would need to be
#     E_need = E * ((duty / ADVICE_DUTY) * (setpoint - out) / (room - out))^(1/n)
# above the setpoint, where E = mean water - room in that hour. Fitting the
# needed flow over the outdoor temperature gives the recommended curve.
RADIATOR_N = 1.3
ADVICE_DUTY = 0.9  # leave the thermostat a little room to switch
ADVICE_MIN_DUTY = 0.15  # the burner must have run in the hour to know the water temperature
ADVICE_MIN_HOURS = 12
ADVICE_MIN_SPREAD = 4.0  # °C of outdoor range needed to change the slope as well
ADVICE_MIN_DIFF = 3.0  # °C room-outdoor / water-room below which the ratio is noise


def curve_advice(points: list[dict[str, float]]) -> dict[str, Any] | None:
    """points: dicts with out, room, sp, duty, flow (actual, while burning),
    dt (flow-return, may be None) and now (current flow target, may be None)."""
    need: list[tuple[float, float]] = []
    now: list[tuple[float, float]] = []
    for p in points:
        out, room, sp, duty, flow = p["out"], p["room"], p["sp"], p["duty"], p["flow"]
        if duty < ADVICE_MIN_DUTY or flow is None:
            continue
        half = (p.get("dt") or 0.0) / 2
        e = flow - half - room
        if e < ADVICE_MIN_DIFF or room - out < ADVICE_MIN_DIFF or sp - out < ADVICE_MIN_DIFF:
            continue
        factor = (min(duty, 1.0) / ADVICE_DUTY) * (sp - out) / (room - out)
        factor = min(max(factor, 0.3), 3.0)
        need.append((out, sp + e * factor ** (1 / RADIATOR_N) + half))
        now.append((out, p["now"] if p.get("now") is not None else flow))
    if len(need) < ADVICE_MIN_HOURS:
        return None
    outs = [p[0] for p in need]
    spread = _quantile(outs, 0.9) - _quantile(outs, 0.1)
    fit_now = linfit(now)
    fit_need = linfit(need)
    mean_out = sum(outs) / len(outs)
    slope_known = spread >= ADVICE_MIN_SPREAD and fit_now is not None and fit_need is not None
    if not slope_known:
        # too little weather spread for a slope: keep the current one, shift the level
        b_now = fit_now["b"] if fit_now and spread >= ADVICE_MIN_SPREAD else 0.0
        a_now = sum(p[1] for p in now) / len(now) - b_now * mean_out
        shift = sum(n[1] - (a_now + b_now * n[0]) for n in need) / len(need)
        fit_now = {"a": a_now, "b": b_now}
        fit_need = {"a": a_now + shift, "b": b_now}

    def line(fit: dict[str, float]) -> dict[str, float]:
        return {
            "slope": round(-fit["b"], 2),
            "at_0": round(fit["a"], 1),
            "at_minus_10": round(fit["a"] - 10 * fit["b"], 1),
            "at_mean": round(fit["a"] + fit["b"] * mean_out, 1),
        }

    cur, rec = line(fit_now), line(fit_need)
    slope_factor = (
        round(fit_need["b"] / fit_now["b"], 2) if slope_known and fit_now["b"] < -0.05 else None
    )
    return {
        "n": len(need),
        "spread": round(spread, 1),
        "mean_outdoor": round(mean_out, 1),
        "slope_known": slope_known,
        "now": cur,
        "recommended": rec,
        "delta_at_0": round(rec["at_0"] - cur["at_0"], 1),
        "delta_at_mean": round(rec["at_mean"] - cur["at_mean"], 1),
        "slope_factor": slope_factor,
        "confidence": "high" if len(need) >= 72 and spread >= 8 else "medium" if len(need) >= 36 else "low",
    }


# --- heat loss ----------------------------------------------------------------
HEATLOSS_MIN_DIFF = 3.0  # °C indoor-outdoor for a day to count
HEATLOSS_FIT_MIN_DAYS = 5
HEATLOSS_FIT_MIN_R2 = 0.5


def heat_loss(days: list[dict[str, float]], recent: int = 7) -> dict[str, Any] | None:
    """days: dicts with kwh (heat delivered that day), indoor, outdoor (averages).

    W per °C of indoor-outdoor difference: total heat / total (24 h x difference)
    over the last `recent` days. That includes free heat (people, appliances,
    sun); a fit over all days separates the two when the data allows it.
    """
    pts = [
        (d["indoor"] - d["outdoor"], d["kwh"])
        for d in days
        if d.get("indoor") is not None
        and d.get("outdoor") is not None
        and d["indoor"] - d["outdoor"] >= HEATLOSS_MIN_DIFF
    ]
    if not pts:
        return None
    last = pts[-recent:]
    kh = sum(24 * p[0] for p in last)
    res: dict[str, Any] = {
        "w_per_k": round(1000 * sum(p[1] for p in last) / kh) if kh else None,
        "days": len(last),
        "avg_diff": round(sum(p[0] for p in last) / len(last), 1),
        "kwh_per_day": round(sum(p[1] for p in last) / len(last), 1),
    }
    fit = linfit(pts) if len(pts) >= HEATLOSS_FIT_MIN_DAYS else None
    if fit and fit["b"] > 0 and fit["r2"] >= HEATLOSS_FIT_MIN_R2:
        # kWh/day = 24*H*diff - 24*gains  ->  H = b/24, gains = -a/24
        res["fit_w_per_k"] = round(1000 * fit["b"] / 24)
        res["free_gains_w"] = round(max(0.0, -1000 * fit["a"] / 24))
        res["fit_r2"] = round(fit["r2"], 2)
        res["fit_days"] = fit["n"]
    return res

/*
 * Boiler Monitor card — companion card for the boiler_monitor integration.
 * Served automatically by the integration; no manual resource needed.
 *
 *   type: custom:boiler-monitor-card
 *   entity: sensor.centrala_status
 *   mode: full            # full | compact
 *   title: Centrala       # optional
 *   show_timeline: true   # full mode only
 *   show_daily: true
 *   show_correlation: true
 *   show_curve: true      # heating curve / fixed flow chart (needs a flow setpoint sensor)
 *   show_comfort: true    # comfort vs outdoor + tuning verdict (needs a thermostat)
 *   show_heatup: true     # how fast the house warms up + pre-heat time
 */
const CARD_VERSION = "1.7.0";

const I18N = {
  en: {
    heating: "Heating", idle: "Idle", off_season: "Off season", unavailable: "Unavailable", demand: "Demand, flame off",
    demand_today: "Demand today", flame_share: "Flame / demand", starts_dh: "Ignitions / demand h",
    tt_demand: "Heat demand", tt_inferred: "seen from the flow jump (flame sensor missed it)", tt_flame: "Flame",
    tab_now: "Now", tab_history: "History", tab_curve: "Curve", tab_comfort: "Comfort",
    h_cond: "Condensing", h_cycle: "Ignitions", h_press: "Pressure", h_comfort: "Comfort",
    g_burns: "Burns · 24 h", g_time: "Today", g_eff: "Efficiency",
    l_flow: "flow", l_ret: "return", l_tgt: "target", l_flame: "flame", l_dem: "demand",
    st_label: "Status", st_burn: "burning", st_dem: "demand, flame off", st_idle: "off", tl_hint: "Drag to zoom · double-tap to zoom in · tap for values",
    no_hist: "Loading temperatures…",
    burning_for: "burning for", min: "min", h: "h",
    flow: "Flow", ret: "Return", dt: "ΔT", outdoor: "Outdoor", indoor: "Indoor",
    cycles_today: "Cycles today", cycles_h: "Cycles / h", avg_burn: "Avg burn", avg_off: "Avg off",
    duty: "Duty 24h", burn_today: "Burn today", cond: "Condensing", rate: "Heating rate",
    short: "short", last24: "Last 24 hours", days: "Last 14 days", corr: "Burn vs outdoor",
    balance: "Balance point", bp_unreliable: "Balance point: not reliable yet", per_hdd: "min per degree-day", not_enough: "Needs ≥ 3 full days of data",
    a_short: "Short-cycling", a_cond: "Condensation lost", a_ineff: "Heating ineffective",
    no_entity: "Pick the Boiler Monitor status sensor", burn_h: "burn time",
    target: "Target", m_curve: "curve", m_fixed: "fixed", pressure: "Pressure", a_press: "Pressure problem",
    curve_title: "Heating curve", fixed_title: "Fixed flow temperature",
    mode_curve: "Weather compensation", mode_fixed: "Fixed flow",
    slope: "Slope", at0: "at 0 °C", atm10: "at −10 °C", fixed_at: "Fixed flow",
    dev24: "actual vs target (24h)", leg_target: "target", leg_actual: "actual (burning)",
    need_curve: "Needs ≥ 6 hours with outdoor temperatures at least 3 °C apart",
    no_points: "No data yet",
    tt_burn: "Burn time", tt_cycles: "Cycles", tt_outdoor: "Outdoor", tt_cond: "Condensing", tt_dt: "Avg ΔT",
    tt_target: "Target", tt_actual: "Actual flow", tt_diff: "Actual − target", tt_mode: "Mode",
    z_in: "Zoom in", z_out: "Zoom out", z_reset: "Reset zoom", more: "more",
    z_hint: "Drag to zoom · double-click to zoom in · pinch on touch",
comfort_title: "Comfort vs outdoor", heat_title: "Warming up the house",
    v_ok: "Curve looks right", v_slope_low: "Slope too low", v_slope_high: "Slope too high",
    v_offset_low: "Offset too low", v_offset_high: "Offset too high", v_insufficient_data: "Not enough data yet",
    a_ok: "The house stays at the set temperature in cold and mild weather alike. Nothing to change.",
    a_slope_low: "When it's cold outside the house stays below the set temperature even though the burner runs almost non-stop. Raise the curve slope a little (+0.1 to +0.2).",
    a_slope_high: "When it's cold the house overshoots the set temperature. Lower the curve slope a little (−0.1 to −0.2).",
    a_offset_low: "The house stays below the set temperature in every weather. Raise the offset (parallel shift) by 1–2 °C.",
    a_offset_high: "In mild weather the boiler gives more heat than needed (short cycles or overshoot). Lower the offset by 1–2 °C.",
    af_slope_low: "When it's cold the house can't reach the set temperature. Raise the fixed flow temperature, or switch automatic thermoregulation on.",
    af_slope_high: "When it's cold the house overshoots. Lower the fixed flow temperature a little.",
    af_offset_low: "The house stays below the set temperature in every weather. Raise the fixed flow temperature by a few degrees.",
    af_offset_high: "In mild weather the water is hotter than needed (short cycles or overshoot). Lower the fixed flow temperature, or switch automatic thermoregulation on so it drops when it's mild.",
    a_insufficient_data: "Needs at least {h} steady hours spread over different outdoor temperatures (now {n} h, {s} °C apart).",
    conf_low: "low confidence", conf_medium: "medium confidence", conf_high: "high confidence",
    gap_cold_l: "in cold weather", gap_mild_l: "in mild weather", duty_cold_l: "burner on when cold",
    vs_set: "vs set", leg_zone: "comfort zone (±0.5 °C)",
    tt_indoor: "Indoor", tt_setpoint: "Set", tt_gap: "Indoor − set", tt_duty: "Burner on", tt_shorts: "Short cycles",
    heat_none: "No warm-up measured yet. It is measured each time heating starts after at least 1 h off, with the rooms clearly below the set temperature.",
    heat_rate_l: "per °C at {o} °C outside", heat_pre_l: "to reach {t} °C now", heat_reached: "already at {t} °C",
    heat_events: "{n} warm-ups measured", tt_rise: "Rose", tt_took: "Took", tt_rate: "Per °C",
    tt_running: "running", tt_short: "short cycle", tt_from: "Off before", tt_noburn: "not burning this hour",
  },
  ro: {
    heating: "Încălzește", idle: "În așteptare", off_season: "În afara sezonului", unavailable: "Indisponibil", demand: "Cerere, flacără stinsă",
    demand_today: "Cerere azi", flame_share: "Flacără / cerere", starts_dh: "Aprinderi / h cerere",
    tt_demand: "Cerere de căldură", tt_inferred: "văzută din saltul turului (senzorul de flacără a ratat-o)", tt_flame: "Flacără",
    tab_now: "Acum", tab_history: "Istoric", tab_curve: "Curbă", tab_comfort: "Confort",
    h_cond: "Condensare", h_cycle: "Aprinderi", h_press: "Presiune", h_comfort: "Confort",
    g_burns: "Arderi · 24 h", g_time: "Azi", g_eff: "Eficiență",
    l_flow: "tur", l_ret: "retur", l_tgt: "tur cerut", l_flame: "flacără", l_dem: "cerere",
    st_label: "Stare", st_burn: "arde", st_dem: "cerere, flacără stinsă", st_idle: "oprită", tl_hint: "Trage pentru zoom · dublu-tap pentru mărire · tap pentru valori",
    no_hist: "Se încarcă temperaturile…",
    burning_for: "arde de", min: "min", h: "h",
    flow: "Tur", ret: "Retur", dt: "ΔT", outdoor: "Exterior", indoor: "Interior",
    cycles_today: "Cicluri azi", cycles_h: "Cicluri / h", avg_burn: "Ardere medie", avg_off: "Pauză medie",
    duty: "Funcționare 24h", burn_today: "Ardere azi", cond: "Condensare", rate: "Rată încălzire",
    short: "scurte", last24: "Ultimele 24 de ore", days: "Ultimele 14 zile", corr: "Ardere vs exterior",
    balance: "Punct de echilibru", bp_unreliable: "Punct de echilibru: încă nesigur", per_hdd: "min pe grad-zi", not_enough: "Necesită ≥ 3 zile complete de date",
    a_short: "Short-cycling", a_cond: "Condensare pierdută", a_ineff: "Încălzire ineficientă",
    no_entity: "Alege senzorul de stare Boiler Monitor", burn_h: "timp de ardere",
    target: "Cerut", m_curve: "curbă", m_fixed: "fix", pressure: "Presiune", a_press: "Problemă presiune",
    curve_title: "Curba de încălzire", fixed_title: "Temperatură de tur fixă",
    mode_curve: "Compensare climatică", mode_fixed: "Tur fix",
    slope: "Panta", at0: "la 0 °C", atm10: "la −10 °C", fixed_at: "Tur fix",
    dev24: "real vs cerut (24h)", leg_target: "cerut", leg_actual: "real (în ardere)",
    need_curve: "Necesită ≥ 6 ore cu temperaturi exterioare diferite cu cel puțin 3 °C",
    no_points: "Încă nu sunt date",
    tt_burn: "Timp de ardere", tt_cycles: "Cicluri", tt_outdoor: "Exterior", tt_cond: "Condensare", tt_dt: "ΔT mediu",
    tt_target: "Tur cerut", tt_actual: "Tur real", tt_diff: "Real − cerut", tt_mode: "Mod",
    z_in: "Mărește", z_out: "Micșorează", z_reset: "Resetează zoom-ul", more: "încă",
    z_hint: "Trage pentru zoom · dublu-clic pentru mărire · ciupire pe ecran tactil",
comfort_title: "Confort vs exterior", heat_title: "Încălzirea casei",
    v_ok: "Curba pare bună", v_slope_low: "Panta prea mică", v_slope_high: "Panta prea mare",
    v_offset_low: "Offset prea mic", v_offset_high: "Offset prea mare", v_insufficient_data: "Încă nu sunt destule date",
    a_ok: "Casa stă la temperatura setată și pe frig, și pe vreme blândă. Nu e nimic de schimbat.",
    a_slope_low: "Când e frig afară, casa rămâne sub temperatura setată deși arzătorul merge aproape continuu. Crește puțin panta curbei (+0,1 … +0,2).",
    a_slope_high: "Când e frig, casa depășește temperatura setată. Scade puțin panta curbei (−0,1 … −0,2).",
    a_offset_low: "Casa rămâne sub temperatura setată pe orice vreme. Crește offset-ul (deplasarea paralelă) cu 1–2 °C.",
    a_offset_high: "Pe vreme blândă centrala dă mai multă căldură decât trebuie (cicluri scurte sau depășire). Scade offset-ul cu 1–2 °C.",
    af_slope_low: "Când e frig, casa nu ajunge la temperatura setată. Crește temperatura de tur fixă sau pornește termoreglarea automată.",
    af_slope_high: "Când e frig, casa depășește temperatura setată. Scade puțin temperatura de tur fixă.",
    af_offset_low: "Casa rămâne sub temperatura setată pe orice vreme. Crește temperatura de tur fixă cu câteva grade.",
    af_offset_high: "Pe vreme blândă apa e mai caldă decât trebuie (cicluri scurte sau depășire). Scade turul fix sau pornește termoreglarea automată, ca să scadă singur când e blând.",
    a_insufficient_data: "Necesită cel puțin {h} ore stabile, la temperaturi exterioare diferite (acum {n} h, diferență {s} °C).",
    conf_low: "încredere mică", conf_medium: "încredere medie", conf_high: "încredere mare",
    gap_cold_l: "pe frig", gap_mild_l: "pe vreme blândă", duty_cold_l: "arzător pornit pe frig",
    vs_set: "față de setat", leg_zone: "zona de confort (±0,5 °C)",
    tt_indoor: "Interior", tt_setpoint: "Setat", tt_gap: "Interior − setat", tt_duty: "Arzător pornit", tt_shorts: "Cicluri scurte",
    heat_none: "Încă nu s-a măsurat nicio încălzire. Se măsoară de fiecare dată când încălzirea pornește după cel puțin 1 h de pauză, cu camerele clar sub temperatura setată.",
    heat_rate_l: "pe °C la {o} °C afară", heat_pre_l: "până la {t} °C, de acum", heat_reached: "deja la {t} °C",
    heat_events: "{n} încălziri măsurate", tt_rise: "A crescut", tt_took: "A durat", tt_rate: "Pe °C",
    tt_running: "în curs", tt_short: "ciclu scurt", tt_from: "Pauză înainte", tt_noburn: "nu a ars în ora asta",
  },
};

const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(Number(v)) ? "–" : Number(v).toFixed(d));
// Durations: never decimal hours. < 60 min -> "45 min"; otherwise "2 h 05 min".
const durText = (min) => {
  if (min === null || min === undefined || Number.isNaN(Number(min))) return "–";
  const m = Math.round(Number(min));
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min`;
};
// Same, split for tiles: [value html, unit]
const durTile = (min) => {
  if (min === null || min === undefined || Number.isNaN(Number(min))) return ["–", "min"];
  const m = Math.round(Number(min));
  if (m < 60) return [String(m), "min"];
  return [`${Math.floor(m / 60)}<small>h</small> ${String(m % 60).padStart(2, "0")}`, "min"];
};
// Compact, for small labels: "45m", "5h48"
const durShort = (min) => {
  if (min === null || min === undefined || Number.isNaN(Number(min))) return "–";
  const m = Math.round(Number(min));
  return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}`;
};
// "Nice" axis ticks for a range.
const niceTicks = (a, b, target = 5) => {
  const span = Math.max(b - a, 1e-6);
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const n = raw / mag;
  const step = (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
  const out = [];
  for (let v = Math.ceil(a / step - 1e-9) * step; v <= b + 1e-9; v += step) out.push(Math.round(v * 1e6) / 1e6);
  return { ticks: out, step };
};
const tickFmt = (v, step) => (step < 1 ? v.toFixed(1) : String(Math.round(v)));

// Tooltip content: title + rows of [label, value]; stored escaped in data-tip.
const tipHtml = (title, rows) =>
  `<b>${title}</b>` + rows.filter((r) => r && r[1] != null && r[1] !== "").map(([l, v]) => `<div><span>${l}</span><span>${v}</span></div>`).join("");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

class BoilerMonitorCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: "boiler_monitor" } } },
        { name: "title", selector: { text: {} } },
        { name: "tabs", selector: { boolean: {} } },
        {
          name: "mode",
          selector: { select: { mode: "dropdown", options: [
            { value: "full", label: "Full / Complet" },
            { value: "compact", label: "Compact" },
          ] } },
        },
        {
          type: "grid", name: "", schema: [
            { name: "show_timeline", selector: { boolean: {} } },
            { name: "show_daily", selector: { boolean: {} } },
            { name: "show_correlation", selector: { boolean: {} } },
            { name: "show_curve", selector: { boolean: {} } },
            { name: "show_comfort", selector: { boolean: {} } },
            { name: "show_heatup", selector: { boolean: {} } },
          ],
        },
      ],
    };
  }

  static getStubConfig(hass) {
    const ent = Object.keys(hass.states).find((e) => hass.states[e].attributes?.monitor === "boiler_monitor");
    return { entity: ent || "", mode: "full" };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { mode: "full", tabs: true, show_timeline: true, show_daily: true, show_correlation: true, show_curve: true, show_comfort: true, show_heatup: true, ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._lastState = undefined;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config?.entity];
    if (st === this._lastState && this.shadowRoot?.childElementCount) return;
    this._lastState = st;
    this._render();
  }

  getCardSize() {
    return this._config?.mode === "compact" ? 2 : 9;
  }

  getGridOptions() {
    return this._config?.mode === "compact" ? { columns: 12, rows: 2, min_rows: 2 } : { columns: 12, min_columns: 6 };
  }

  get _t() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
    return I18N[lang] || I18N.en;
  }

  get _lang() {
    return (this._hass?.locale?.language || this._hass?.language || "en");
  }

  _fmtDay(iso) {
    try {
      return new Date(`${iso}T12:00:00`).toLocaleDateString(this._lang, { weekday: "short", day: "numeric", month: "short" });
    } catch (e) { return iso; }
  }

  _fmtTs(ts, withDay = true) {
    try {
      const o = { hour: "2-digit", minute: "2-digit" };
      if (withDay) Object.assign(o, { weekday: "short", day: "numeric", month: "short" });
      return new Date(ts * 1000).toLocaleString(this._lang, o);
    } catch (e) { return String(ts); }
  }

  _dayTip(d) {
    const t = this._t;
    return tipHtml(esc(this._fmtDay(d.date)), [
      [t.tt_burn, durText(d.burn_h * 60)],
      [t.tt_demand, d.demand_h != null && this._hasFlame ? durText(d.demand_h * 60) : null],
      [t.tt_cycles, d.cycles != null ? `${d.cycles}${d.short ? ` (${d.short} ${t.short})` : ""}` : null],
      [t.tt_outdoor, d.outdoor != null ? `${fmt(d.outdoor, 1)} °C` : null],
      [t.tt_cond, d.cond_pct != null ? `${fmt(d.cond_pct, 0)} %` : null],
      [t.tt_dt, d.delta_t != null ? `${fmt(d.delta_t, 1)} °C` : null],
    ]);
  }

  // ---------------------------------------------------------------- tooltip
  _showTip(html, clientX, anchor) {
    const card = this.shadowRoot.querySelector("ha-card");
    const tip = this.shadowRoot.querySelector(".tip");
    if (!card || !tip) return;
    tip.innerHTML = html;
    tip.style.display = "block";
    const cr = card.getBoundingClientRect();
    const x = (clientX != null ? clientX : anchor.left + anchor.width / 2) - cr.left;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    const left = Math.min(Math.max(8, x - tw / 2), cr.width - tw - 8);
    let top = anchor.top - cr.top - th - 8;
    if (top < 4) top = anchor.bottom - cr.top + 8;
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  }

  _hideTip() {
    const tip = this.shadowRoot?.querySelector(".tip");
    if (tip) tip.style.display = "none";
    this._pinned = null;
    this.shadowRoot?.querySelectorAll(".hl, .cur").forEach((h) => h.setAttribute("visibility", "hidden"));
  }

  // Hover (mouse) or tap (touch) on elements with data-tip (bars, timeline).
  _wireTips() {
    const root = this.shadowRoot;
    const card = root.querySelector("ha-card");
    if (!card) return;
    this._pinned = null;
    root.querySelectorAll("[data-tip]").forEach((el) => {
      const show = (ev) => this._showTip(el.getAttribute("data-tip"), ev?.clientX, el.getBoundingClientRect());
      el.addEventListener("pointerenter", (ev) => { if (ev.pointerType === "mouse" && !this._pinned) show(ev); });
      el.addEventListener("pointermove", (ev) => { if (ev.pointerType === "mouse" && !this._pinned) show(ev); });
      el.addEventListener("pointerleave", (ev) => { if (ev.pointerType === "mouse" && !this._pinned) this._hideTip(); });
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (this._pinned === el) { this._hideTip(); return; }
        show(ev); this._pinned = el;
      });
    });
    card.addEventListener("click", () => { if (this._pinned) this._hideTip(); });
    root.querySelectorAll(".plot").forEach((el) => this._wirePlot(el));
  }

  // ------------------------------------------------------- zoomable scatter
  // cfg: { full:{x0,x1,y0,y1}, H, xFmt, yFmt, layers(X,Y,dom)->svg, points:[{x,y,cls,op,tip}] }
  _plot(id, cfg) {
    this._plots = this._plots || {};
    this._zoom = this._zoom || {};
    this._plots[id] = cfg;
    return `<div class="plot ${this._zoom[id] ? "zoomed" : ""}" data-plot="${id}">${this._plotInner(id)}</div>`;
  }

  _plotDomain(id) {
    const { full } = this._plots[id];
    const z = this._zoom[id];
    if (!z) return { ...full };
    // keep inside the full range
    const clamp = (lo, hi, a, b) => {
      const w = Math.min(b - a, hi - lo);
      let s0 = Math.max(lo, Math.min(a, hi - w));
      return [s0, s0 + w];
    };
    const [x0, x1] = clamp(full.x0, full.x1, z.x0, z.x1);
    if (this._plots[id].xOnly) return { x0, x1, y0: full.y0, y1: full.y1 };
    const [y0, y1] = clamp(full.y0, full.y1, z.y0, z.y1);
    return { x0, x1, y0, y1 };
  }

  _plotInner(id) {
    const t = this._t;
    const cfg = this._plots[id];
    const W = 320, H = cfg.H || 160, P = { l: 32, r: 10, t: 10, b: 22, ...(cfg.pad || {}) };
    const d = this._plotDomain(id);
    const X = (v) => P.l + ((v - d.x0) / (d.x1 - d.x0)) * (W - P.l - P.r);
    const Y = (v) => H - P.b - ((v - d.y0) / (d.y1 - d.y0)) * (H - P.t - P.b);
    const xt = niceTicks(d.x0, d.x1, 6), yt = niceTicks(d.y0, d.y1, 4);
    let axes = `<line x1="${P.l}" x2="${W - P.r}" y1="${H - P.b}" y2="${H - P.b}" class="ax"/>`;
    const xlist = cfg.xTicks ? cfg.xTicks(d) : xt.ticks.map((x) => [x, cfg.xFmt(tickFmt(x, xt.step))]);
    xlist.forEach(([x, lab]) => {
      axes += `<text x="${X(x)}" y="${H - 6}" class="axl" text-anchor="middle">${lab}</text>`;
      if (cfg.xGrid) axes += `<line x1="${X(x)}" x2="${X(x)}" y1="${P.t}" y2="${H - P.b}" class="grd"/>`;
    });
    yt.ticks.forEach((y) => { axes += `<text x="${P.l - 5}" y="${Y(y) + 3}" class="axl" text-anchor="end">${cfg.yFmt(tickFmt(y, yt.step))}</text><line x1="${P.l}" x2="${W - P.r}" y1="${Y(y)}" y2="${Y(y)}" class="grd"/>`; });
    const r = this._zoom[id] ? 3.6 : 3; // a bit larger when zoomed in
    const dots = cfg.points.map((p) => p.y == null ? "" :
      `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="${p.cls === "hdot" ? r - 0.4 : r}" class="${p.cls}" style="opacity:${p.op ?? 1}"/>`).join("");
    cfg._geo = { W, H, P, d };
    const zoomed = !!this._zoom[id];
    return `<svg class="corr ${zoomed ? "zoomed" : ""}" viewBox="0 0 ${W} ${H}">
        <defs><clipPath id="clip-${id}"><rect x="${P.l}" y="${P.t - 4}" width="${W - P.l - P.r}" height="${H - P.t - P.b + 4}"/></clipPath></defs>
        ${axes}
        <g clip-path="url(#clip-${id})">${cfg.layers ? cfg.layers(X, Y, d) : ""}${dots}
          <circle class="hl" r="7" visibility="hidden"/>
          <line class="cur" y1="${P.t}" y2="${H - P.b}" visibility="hidden"/></g>
        <rect class="sel" visibility="hidden"/>
      </svg>
      <div class="zbtns">
        <button data-z="in" title="${esc(t.z_in)}" aria-label="${esc(t.z_in)}">+</button>
        <button data-z="out" title="${esc(t.z_out)}" aria-label="${esc(t.z_out)}" ${zoomed ? "" : "disabled"}>−</button>
        ${zoomed ? `<button data-z="reset" title="${esc(t.z_reset)}" aria-label="${esc(t.z_reset)}">⟲</button>` : ""}
      </div>`;
  }

  _redrawPlot(id) {
    const el = this.shadowRoot.querySelector(`.plot[data-plot="${id}"]`);
    if (!el) return;
    el.innerHTML = this._plotInner(id);
    el.classList.toggle("zoomed", !!this._zoom[id]);
    this._wirePlot(el);
  }

  _setZoom(id, dom) {
    const cfg = this._plots[id];
    const { full } = cfg;
    if (cfg.xOnly) dom = { ...dom, y0: full.y0, y1: full.y1 };
    const minW = cfg.minW ?? (full.x1 - full.x0) / 25, minH = (full.y1 - full.y0) / 25;
    const cx = (dom.x0 + dom.x1) / 2, cy = (dom.y0 + dom.y1) / 2;
    const w = Math.max(dom.x1 - dom.x0, minW), h = Math.max(dom.y1 - dom.y0, minH);
    const nd = { x0: cx - w / 2, x1: cx + w / 2, y0: cy - h / 2, y1: cy + h / 2 };
    const isFull = w >= full.x1 - full.x0 - 1e-6 && h >= full.y1 - full.y0 - 1e-6;
    if (isFull) delete this._zoom[id]; else this._zoom[id] = nd;
    this._hideTip();
    this._redrawPlot(id);
  }

  _zoomBy(id, factor, cx, cy) {
    const d = this._plotDomain(id);
    const px = cx ?? (d.x0 + d.x1) / 2, py = cy ?? (d.y0 + d.y1) / 2;
    this._setZoom(id, {
      x0: px - (px - d.x0) / factor, x1: px + (d.x1 - px) / factor,
      y0: py - (py - d.y0) / factor, y1: py + (d.y1 - py) / factor,
    });
  }

  _wirePlot(el) {
    const id = el.getAttribute("data-plot");
    if (!this._plots?.[id]) return;
    // Zoom buttons are re-created on every redraw
    el.querySelectorAll("button[data-z]").forEach((b) => b.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const z = b.getAttribute("data-z");
      if (z === "in") this._zoomBy(id, 2);
      else if (z === "out") this._zoomBy(id, 0.5);
      else this._setZoom(id, this._plots[id].full);
    }));
    // Gesture listeners live on the container, which survives redraws of the
    // SVG inside it, so pinch/pan keep working while the chart re-renders.
    if (el._wired) return;
    el._wired = true;

    const cfg = () => this._plots[id];
    const svg = () => el.querySelector("svg");
    const geo = () => cfg()._geo;
    const toSvg = (ev) => {
      const r = svg().getBoundingClientRect(), { W, H } = geo();
      return { sx: ((ev.clientX - r.left) / r.width) * W, sy: ((ev.clientY - r.top) / r.height) * H, k: W / r.width };
    };
    const toData = (sx, sy) => {
      const { W, H, P, d } = geo();
      return {
        x: d.x0 + ((sx - P.l) / (W - P.l - P.r)) * (d.x1 - d.x0),
        y: d.y0 + ((H - P.b - sy) / (H - P.t - P.b)) * (d.y1 - d.y0),
      };
    };
    const sX = (x) => { const { W, P, d } = geo(); return P.l + ((x - d.x0) / (d.x1 - d.x0)) * (W - P.l - P.r); };
    const sY = (y) => { const { H, P, d } = geo(); return H - P.b - ((y - d.y0) / (d.y1 - d.y0)) * (H - P.t - P.b); };

    // All points near the pointer, so overlapping points are listed together
    const showNear = (ev, pin) => {
      const { sx, sy, k } = toSvg(ev);
      if (cfg().hover) {
        const { W, H, P, d } = geo();
        const x = toData(sx, sy).x;
        const html = x >= d.x0 && x <= d.x1 ? cfg().hover(x) : null;
        if (!html) { if (pin || !this._pinned) this._hideTip(); return; }
        const cur = svg().querySelector(".cur");
        cur.setAttribute("x1", sX(x)); cur.setAttribute("x2", sX(x));
        cur.setAttribute("visibility", "visible");
        const r = svg().getBoundingClientRect();
        const ax = r.left + (sX(x) / W) * r.width, ay = r.top + (P.t / H) * r.height;
        this._showTip(html, ax, { left: ax, width: 0, top: ay, bottom: r.top + ((H - P.b) / H) * r.height });
        if (pin) this._pinned = el;
        return;
      }
      const R = 9 * k;
      const hits = cfg().points
        .filter((p) => p.y != null && p.tip)
        .map((p) => ({ p, dist: Math.hypot(sX(p.x) - sx, sY(p.y) - sy) }))
        .filter((o) => o.dist <= R)
        .sort((a, b) => a.dist - b.dist);
      if (!hits.length) { if (pin || !this._pinned) this._hideTip(); return; }
      const tips = [...new Set(hits.map((h) => h.p.tip))];
      const max = 3;
      let html = tips.slice(0, max).join("<hr>");
      if (tips.length > max) html += `<div class="more">+${tips.length - max} ${esc(this._t.more)}</div>`;
      const hl = svg().querySelector(".hl");
      hl.setAttribute("cx", sX(hits[0].p.x)); hl.setAttribute("cy", sY(hits[0].p.y));
      hl.setAttribute("visibility", "visible");
      const r = svg().getBoundingClientRect(), { W, H } = geo();
      const ax = r.left + (sX(hits[0].p.x) / W) * r.width, ay = r.top + (sY(hits[0].p.y) / H) * r.height;
      this._showTip(html, ax, { left: ax, width: 0, top: ay - 6, bottom: ay + 6 });
      if (pin) this._pinned = el;
    };

    const ptrs = new Map();
    let start = null, moved = false, pinch0 = null, lastTap = 0, raf = 0;
    const later = (fn) => { cancelAnimationFrame(raf); raf = requestAnimationFrame(fn); };
    const midData = () => {
      const [a, b] = [...ptrs.values()];
      const p = toSvg({ clientX: (a.clientX + b.clientX) / 2, clientY: (a.clientY + b.clientY) / 2 });
      return toData(p.sx, p.sy);
    };
    el.addEventListener("pointerdown", (ev) => {
      if (ev.target.closest?.("button")) return;
      try { el.setPointerCapture(ev.pointerId); } catch (e) { /* synthetic events */ }
      ptrs.set(ev.pointerId, { clientX: ev.clientX, clientY: ev.clientY });
      moved = false;
      start = { ...toSvg(ev), dom: this._plotDomain(id), type: ev.pointerType };
      if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()];
        pinch0 = { dist: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), dom: this._plotDomain(id), mid: midData() };
      }
    });
    el.addEventListener("pointermove", (ev) => {
      if (!ptrs.has(ev.pointerId)) {
        if (ev.pointerType === "mouse" && !this._pinned && !ev.target.closest?.("button")) showNear(ev, false);
        return;
      }
      ptrs.set(ev.pointerId, { clientX: ev.clientX, clientY: ev.clientY });
      const p = toSvg(ev);
      if (start && Math.hypot(p.sx - start.sx, p.sy - start.sy) > 6 * p.k) moved = true;
      if (!moved || !start) return;
      if (ptrs.size === 2 && pinch0) {
        const [a, b] = [...ptrs.values()];
        const f = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) / Math.max(pinch0.dist, 1);
        const d0 = pinch0.dom, m = pinch0.mid;
        later(() => this._setZoom(id, {
          x0: m.x - (m.x - d0.x0) / f, x1: m.x + (d0.x1 - m.x) / f,
          y0: m.y - (m.y - d0.y0) / f, y1: m.y + (d0.y1 - m.y) / f }));
      } else if (start.type === "mouse") {
        const sel = svg().querySelector(".sel");
        const xo = cfg().xOnly, { H, P } = geo();
        sel.setAttribute("x", Math.min(start.sx, p.sx)); sel.setAttribute("width", Math.abs(p.sx - start.sx));
        sel.setAttribute("y", xo ? P.t : Math.min(start.sy, p.sy));
        sel.setAttribute("height", xo ? H - P.t - P.b : Math.abs(p.sy - start.sy));
        sel.setAttribute("visibility", "visible");
        this._hideTip();
      } else if (this._zoom[id] && ptrs.size === 1) {
        const { W, H, P } = geo(), d0 = start.dom;
        const dx = ((p.sx - start.sx) / (W - P.l - P.r)) * (d0.x1 - d0.x0);
        const dy = ((p.sy - start.sy) / (H - P.t - P.b)) * (d0.y1 - d0.y0);
        later(() => this._setZoom(id, { x0: d0.x0 - dx, x1: d0.x1 - dx, y0: d0.y0 + dy, y1: d0.y1 + dy }));
      }
    });
    const end = (ev) => {
      if (!ptrs.has(ev.pointerId)) return;
      ptrs.delete(ev.pointerId);
      if (ptrs.size < 2) pinch0 = null;
      if (ptrs.size) { start = null; return; } // lifting one finger of a pinch: don't treat as pan/tap
      if (!start) return;
      const p = toSvg(ev);
      if (moved && start.type === "mouse") {
        svg().querySelector(".sel").setAttribute("visibility", "hidden");
        if (Math.abs(p.sx - start.sx) > 8 * p.k && (cfg().xOnly || Math.abs(p.sy - start.sy) > 8 * p.k)) {
          const a = toData(start.sx, start.sy), b = toData(p.sx, p.sy);
          this._setZoom(id, { x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), y0: Math.min(a.y, b.y), y1: Math.max(a.y, b.y) });
        }
      } else if (!moved) {
        const now = Date.now();
        if (now - lastTap < 300) {            // double tap / double click: zoom in here
          lastTap = 0;
          const c = toData(p.sx, p.sy);
          this._zoomBy(id, 2, c.x, c.y);
        } else {
          lastTap = now;
          showNear(ev, true);
        }
      }
      start = null; moved = false;
    };
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", end);
    el.addEventListener("pointerleave", (ev) => { if (ev.pointerType === "mouse" && !ptrs.size && !this._pinned) this._hideTip(); });
    el.addEventListener("click", (ev) => ev.stopPropagation());
    // Ctrl/⌘ + wheel zooms; the plain wheel keeps scrolling the dashboard
    el.addEventListener("wheel", (ev) => {
      if (!ev.ctrlKey && !ev.metaKey) return;
      ev.preventDefault();
      const p = toSvg(ev), c = toData(p.sx, p.sy);
      this._zoomBy(id, ev.deltaY < 0 ? 1.4 : 1 / 1.4, c.x, c.y);
    }, { passive: false });
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  // ------------------------------------------------------------------ render
  _render() {
    if (!this.shadowRoot || !this._config) return;
    const t = this._t;
    const st = this._hass?.states[this._config.entity];
    if (!st || st.attributes?.monitor !== "boiler_monitor") {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="empty">${esc(t.no_entity)}${
        this._config.entity ? `<br><code>${esc(this._config.entity)}</code>` : ""}</div></ha-card>`;
      return;
    }
    const a = st.attributes;
    const s = a.stats || {};
    this._hasFlame = !!a.sources?.flame;
    const status = st.state;
    const title = this._config.title || (a.friendly_name || "").replace(/\s*(Status|Stare)$/i, "");
    const compact = this._config.mode === "compact";

    const alerts = [
      a.short_cycling && { k: "short_cycling", txt: t.a_short, icon: "mdi:sync-alert" },
      a.condensation_lost && { k: "condensation_lost", txt: t.a_cond, icon: "mdi:water-off" },
      a.heating_ineffective && { k: "heating_ineffective", txt: t.a_ineff, icon: "mdi:home-alert" },
      a.pressure_problem && { k: "pressure_problem", txt: `${t.a_press} · ${fmt(a.pressure, 2)} bar`, icon: "mdi:gauge-low" },
    ].filter(Boolean);

    const sub = status === "heating" && s.current_burn_min != null
      ? `${t.burning_for} ${durText(s.current_burn_min)}`
      : (t[status] || status);

    const header = `
      <div class="hdr">
        <div class="flame ${status}" data-ent="${esc(a.entities?.burner || this._config.entity)}">
          <ha-icon icon="${status === "heating" ? "mdi:fire" : status === "off_season" ? "mdi:snowflake-off" : status === "demand" ? "mdi:thermostat" : "mdi:fire-off"}"></ha-icon>
        </div>
        <div class="ttl">
          <div class="name">${esc(title)}</div>
          <div class="sub">${esc(sub)}</div>
        </div>
        ${compact ? alerts.map((x) => `<div class="aicon" title="${esc(x.txt)}" data-ent="${esc(a.entities?.[x.k] || "")}"><ha-icon icon="${x.icon}"></ha-icon></div>`).join("") : ""}
        <div class="chip ${status}">${esc(t[status] || status)}</div>
      </div>
      ${alerts.length && !compact ? `<div class="alerts">${alerts.map((x) => `
        <div class="alert" data-ent="${esc(a.entities?.[x.k] || "")}"><ha-icon icon="${x.icon}"></ha-icon>${esc(x.txt)}</div>`).join("")}</div>` : ""}`;

    let body;
    if (compact) {
      body = `
        <div class="crow">
          ${this._mini("cycles_per_hour", t.cycles_h, fmt(s.cycles_per_hour, 1), "", s.short_cycles_today ? "warn" : "")}
          ${this._mini("avg_burn", t.avg_burn, ...durTile(s.avg_burn_min))}
          ${a.sources?.return ? this._mini("condensing_ratio", t.cond, fmt(s.condensing_ratio, 0), "%", this._condCls(s.condensing_ratio)) : this._mini("duty_cycle", t.duty, fmt(s.duty_cycle, 0), "%")}
          ${a.sources?.flow && a.sources?.return ? this._mini("delta_t", t.dt, fmt(s.delta_t, 1), "°") : this._mini("burn_time_today", t.burn_today, ...durTile(s.burn_hours_today == null ? null : s.burn_hours_today * 60))}
        </div>
        ${this._timeline(a, true)}`;
    } else {
      body = this._fullBody(a, s, t);
    }

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card class="${compact ? "compact" : ""}"><div class="wrap">${header}${body}</div><div class="tip" role="tooltip"></div></ha-card>`;
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", (ev) => {
      ev.stopPropagation();
      this._tab = b.getAttribute("data-tab");
      try { localStorage.setItem(`bm-tab-${this._config.entity}`, this._tab); } catch (e) { /* storage blocked */ }
      this._hideTip();
      this._render();
    }));
    this.shadowRoot.querySelectorAll("[data-ent]").forEach((el) => {
      const id = el.getAttribute("data-ent");
      if (!id) return;
      el.classList.add("click");
      el.addEventListener("click", () => this._moreInfo(id));
    });
    this._wireTips();
  }


  // Full card: tabs (or everything stacked with tabs: false)
  _fullBody(a, s, t) {
    const cfg = this._config;
    const sections = [
      { id: "now", label: t.tab_now, html: this._nowTab(a, s, t) },
      { id: "history", label: t.tab_history, html: [
        cfg.show_daily ? this._daily(a) : "",
        cfg.show_correlation && a.sources?.outdoor ? this._corr(a) : "",
      ].join("") },
      { id: "curve", label: t.tab_curve, html: cfg.show_curve && a.sources?.setpoint && a.sources?.outdoor ? this._curve(a) : "" },
      { id: "comfort", label: t.tab_comfort, html: [
        cfg.show_comfort && a.sources?.thermostat && a.sources?.outdoor ? this._comfort(a) : "",
        cfg.show_heatup && (a.sources?.thermostat || a.room != null) ? this._heatup(a) : "",
      ].join("") },
    ].filter((x) => x.html);
    if (cfg.tabs === false) return sections.map((x) => `<div class="pane">${x.html}</div>`).join("");
    let cur = this._tab;
    if (!cur) { try { cur = localStorage.getItem(`bm-tab-${cfg.entity}`); } catch (e) { cur = null; } }
    if (!sections.some((x) => x.id === cur)) cur = sections[0].id;
    this._tab = cur;
    const bar = `<div class="tabs" role="tablist">${sections.map((x) => `
      <button class="tab ${x.id === cur ? "on" : ""}" data-tab="${x.id}" role="tab" aria-selected="${x.id === cur}">${esc(x.label)}</button>`).join("")}</div>`;
    return `${bar}<div class="pane">${sections.find((x) => x.id === cur).html}</div>`;
  }

  _nowTab(a, s, t) {
    const fl = this._hasFlame;
    // health summary
    const pills = [];
    if (a.sources?.return) {
      const v = s.condensing_ratio;
      pills.push({ ent: a.entities?.condensing_ratio, icon: "mdi:water-percent", l: t.h_cond, v: v == null ? "–" : `${fmt(v, 0)} %`,
        cls: a.condensation_lost ? "bad" : v == null ? "none" : v >= 80 ? "good" : v >= 50 ? "warn" : "bad" });
    }
    const cyc = fl ? s.starts_per_demand_hour : s.cycles_per_hour;
    pills.push({ ent: a.entities?.[fl ? "starts_per_demand_hour" : "cycles_per_hour"], icon: "mdi:repeat", l: t.h_cycle,
      v: cyc == null ? "–" : `${fmt(cyc, 1)}/h`,
      cls: a.short_cycling ? "bad" : cyc == null ? "none" : cyc <= 3 ? "good" : cyc <= 5 ? "warn" : "bad" });
    if (a.sources?.pressure) {
      const p = a.pressure, th = a.thresholds || {};
      const out = p != null && (p < th.pressure_min || p > th.pressure_max);
      pills.push({ ent: a.sources.pressure, icon: "mdi:gauge", l: t.h_press, v: p == null ? "–" : `${fmt(p, 1)} bar`,
        cls: a.pressure_problem || out ? "bad" : p == null ? "none" : "good" });
    }
    if (a.sources?.thermostat) {
      const v = s.comfort_verdict;
      const known = v && v !== "insufficient_data";
      pills.push({ ent: a.entities?.comfort_verdict, icon: "mdi:home-thermometer", l: t.h_comfort,
        v: v === "ok" ? "OK" : known ? (t[`v_${v}`] || v) : "…", cls: v === "ok" ? "good" : known ? "warn" : "none" });
    }
    const health = `<div class="pills">${pills.map((x) => `
      <div class="pill ${x.cls}" data-ent="${esc(x.ent || "")}"><ha-icon icon="${x.icon}"></ha-icon><span>${esc(x.l)}</span><b>${esc(x.v)}</b></div>`).join("")}</div>`;

    // live temperatures
    const temps = [
      a.sources?.flow && { k: a.sources.flow, l: t.flow, v: a.flow, u: "°C" },
      a.sources?.setpoint && { k: a.sources.setpoint, v: a.flow_target, u: "°C",
        l: t.target, sub: a.regulation_mode ? (a.regulation_mode === "fixed" ? t.m_fixed : t.m_curve) : "" },
      a.sources?.return && { k: a.sources.return, l: t.ret, v: a.return, u: "°C",
        cls: a.return != null && a.return > a.thresholds?.return ? "bad" : "good" },
      a.sources?.flow && a.sources?.return && { k: a.entities?.delta_t, l: t.dt, v: s.delta_t, u: "°C" },
      a.sources?.outdoor && { k: a.sources.outdoor, l: t.outdoor, v: a.outdoor, u: "°C" },
      a.indoor != null && { k: "", l: t.indoor, v: a.indoor, u: "°C" },
    ].filter(Boolean);
    const tempsHtml = temps.length ? `<div class="temps">${temps.map((x) => `
      <div class="temp ${x.cls || ""}" data-ent="${esc(x.k || "")}"><span>${esc(x.l)}</span><b>${fmt(x.v, x.d ?? 1)}<small>${x.u}</small></b>${x.sub ? `<em>${esc(x.sub)}</em>` : ""}</div>`).join("")}</div>` : "";

    // tiles, grouped
    const groups = [
      [t.g_burns, [
        ["cycles_today", t.cycles_today, fmt(s.cycles_today, 0), s.short_cycles_today ? `${s.short_cycles_today} ${t.short}` : "", s.short_cycles_today ? "warn" : ""],
        fl ? ["starts_per_demand_hour", t.starts_dh, fmt(s.starts_per_demand_hour, 1), "", (s.starts_per_demand_hour ?? 0) > 4 ? "warn" : ""]
           : ["cycles_per_hour", t.cycles_h, fmt(s.cycles_per_hour, 2), "", (s.cycles_per_hour ?? 0) > 3 ? "warn" : ""],
        ["avg_burn", t.avg_burn, ...durTile(s.avg_burn_min), ""],
        ["avg_off", t.avg_off, ...durTile(s.avg_off_min), ""],
      ]],
      [t.g_time, [
        ["burn_time_today", t.burn_today, ...durTile(s.burn_hours_today == null ? null : s.burn_hours_today * 60), ""],
        fl && ["demand_time_today", t.demand_today, ...durTile(s.demand_hours_today == null ? null : s.demand_hours_today * 60), ""],
        fl ? ["flame_share", t.flame_share, fmt(s.flame_share, 0), "%", ""] : ["duty_cycle", t.duty, fmt(s.duty_cycle, 0), "%", ""],
        a.entities?.heating_rate && ["heating_rate", t.rate, fmt(s.heating_rate, 2), "°C/h", (s.heating_rate ?? 1) <= 0 ? "warn" : ""],
      ].filter(Boolean)],
    ];
    const tiles = groups.map(([label, list]) => `<div class="grp"><div class="gl">${esc(label)}</div><div class="grid">${list.map(([k, l, v, u, cls]) => `
      <div class="tile ${cls}" data-ent="${esc(a.entities?.[k] || "")}">
        <div class="tv">${v}<small>${esc(u)}</small></div><div class="tl">${esc(l)}</div>
      </div>`).join("")}</div></div>`).join("");

    const chart = this._config.show_timeline ? this._tl24(a) : "";
    return `${health}${tempsHtml}${chart}${tiles}`;
  }

  // Flow / return / target temperatures for the last 24 h, from the recorder.
  _fetchHistory(a) {
    const src = a.sources || {};
    const ids = [src.flow, src.return, src.setpoint].filter(Boolean);
    if (!ids.length || !this._hass?.callWS) return;
    const key = ids.join();
    const now = Date.now();
    if (this._histBusy || (this._hist && this._hist.key === key && now - this._hist.at < 5 * 60000)) return;
    this._histBusy = true;
    const conv = (res, id) => (id ? (res?.[id] || []) : [])
      .map((e) => [e.lu ?? e.lc ?? Date.parse(e.last_updated || e.last_changed) / 1000, parseFloat(e.s ?? e.state)])
      .filter((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]));
    this._hass.callWS({
      type: "history/history_during_period",
      start_time: new Date(now - 24 * 3600 * 1000).toISOString(),
      entity_ids: ids, minimal_response: true, no_attributes: true, significant_changes_only: false,
    }).then((res) => {
      this._hist = { at: now, key, flow: conv(res, src.flow), ret: conv(res, src.return), tgt: conv(res, src.setpoint) };
    }).catch(() => {
      this._hist = { at: now, key, flow: [], ret: [], tgt: [] };
    }).finally(() => {
      this._histBusy = false;
      if (this._tab === "now" || this._config.tabs === false) this._render();
    });
  }

  _tl24(a) {
    const t = this._t;
    this._fetchHistory(a);
    const now = Date.now() / 1000, t0 = now - 24 * 3600;
    const H = this._hist || { flow: [], ret: [], tgt: [] };
    const live = (arr, v) => (v == null ? arr : [...arr, [now, v]]);
    const flow = live(H.flow, a.flow), ret = live(H.ret, a.return);
    const segs = (a.timeline || []).map(([st, en, sh, inf]) => ({ s: st, e: en ?? now, sh, inf, live: en == null }));
    const dems = (a.demand_timeline || []).map(([st, en]) => ({ s: st, e: en ?? now }));
    // the boiler reports a meaningless target while idle: keep it only while heating
    const active = dems.length ? dems : segs;
    const inAct = (ts) => active.some((x) => ts >= x.s && ts <= x.e);
    const tgt = live(H.tgt, a.flow_target).filter(([ts, v]) => v >= 10 && v < 90 && inAct(ts));
    const vals = [...flow, ...ret, ...tgt].filter(([ts]) => ts >= t0).map((p) => p[1]);
    let y0 = vals.length ? Math.floor((Math.min(...vals) - 3) / 5) * 5 : 20;
    let y1 = vals.length ? Math.ceil((Math.max(...vals) + 3) / 5) * 5 : 60;
    if (y1 - y0 < 20) y1 = y0 + 20;
    const at = (arr, ts) => { let v = null; for (const p of arr) { if (p[0] > ts) break; v = p[1]; } return v; };
    const line = (arr, X, Y, d, cls) => {
      const pts = arr.filter(([ts], i) => ts >= d.x0 - 1800 && ts <= d.x1 + 1800 || (arr[i + 1] && arr[i + 1][0] >= d.x0));
      if (pts.length < 2) return "";
      return `<polyline class="${cls}" points="${pts.map(([ts, v]) => `${X(ts).toFixed(1)},${Y(v).toFixed(1)}`).join(" ")}"/>`;
    };
    const step = (X, Y, d) => active.map((iv) => {
      const inside = tgt.filter(([ts]) => ts >= iv.s && ts <= iv.e);
      if (!inside.length || iv.e < d.x0 || iv.s > d.x1) return "";
      let path = "", prev = null;
      inside.forEach(([ts, v]) => {
        const x = X(Math.max(ts, iv.s));
        path += prev == null ? `M${x.toFixed(1)},${Y(v).toFixed(1)}` : ` H${x.toFixed(1)} V${Y(v).toFixed(1)}`;
        prev = v;
      });
      path += ` H${X(iv.e).toFixed(1)}`;
      return `<path class="ltgt" d="${path}"/>`;
    }).join("");
    const layers = (X, Y, d) => {
      const top = Y(d.y1), bot = Y(d.y0);
      let out = dems.map((x) => `<rect x="${X(x.s).toFixed(1)}" y="${top}" width="${Math.max(1, X(x.e) - X(x.s)).toFixed(1)}" height="${bot - top}" class="tdem"/>`).join("");
      out += step(X, Y, d) + line(ret, X, Y, d, "lret") + line(flow, X, Y, d, "lflow");
      out += segs.map((x) => `<rect x="${X(x.s).toFixed(1)}" y="${bot - 7}" width="${Math.max(1.2, X(x.e) - X(x.s)).toFixed(1)}" height="6" rx="1" class="seg${x.sh ? " short" : ""}${x.inf ? " inf" : ""}${x.live ? " live" : ""}"/>`).join("");
      return out;
    };
    const tz = -new Date().getTimezoneOffset() * 60;
    const xTicks = (d) => {
      const span = d.x1 - d.x0;
      const st = [300, 600, 900, 1800, 3600, 7200, 10800, 21600].find((v) => span / v <= 6) || 21600;
      const out = [];
      for (let v = Math.ceil((d.x0 + tz) / st) * st - tz; v <= d.x1; v += st) {
        out.push([v, new Date(v * 1000).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit" })]);
      }
      return out;
    };
    const hover = (ts) => {
      const inSeg = segs.find((x) => ts >= x.s && ts <= x.e);
      const inDem = dems.find((x) => ts >= x.s && ts <= x.e);
      const f = at(flow, ts), r = at(ret, ts), g = inAct(ts) ? at(tgt, ts) : null;
      return tipHtml(esc(this._fmtTs(ts, false)), [
        [t.flow, f != null ? `${fmt(f, 1)} °C` : null],
        [t.ret, r != null ? `${fmt(r, 1)} °C` : null],
        [t.target, g != null ? `${fmt(g, 0)} °C` : null],
        [t.st_label, inSeg ? `🔥 ${t.st_burn}${inSeg.sh ? ` · ${t.tt_short}` : ""}` : inDem ? t.st_dem : t.st_idle],
        inSeg ? [t.tt_burn, durText((inSeg.e - inSeg.s) / 60)] : null,
      ]);
    };
    const plot = this._plot("tl24", {
      full: { x0: t0, x1: now, y0, y1 }, H: 190, xOnly: true, minW: 900, xGrid: true,
      pad: { l: 28, r: 6, t: 34 }, xTicks, xFmt: (v) => v, yFmt: (v) => `${v}°`, layers, points: [], hover,
    });
    const hasT = a.sources?.flow || a.sources?.return;
    const legend = `<div class="legend wrapl">
      ${a.sources?.flow ? `<span><i class="lc flow"></i>${esc(t.l_flow)}</span>` : ""}
      ${a.sources?.return ? `<span><i class="lc ret"></i>${esc(t.l_ret)}</span>` : ""}
      ${a.sources?.setpoint ? `<span><i class="lc tgt"></i>${esc(t.l_tgt)}</span>` : ""}
      <span><i class="lb burn"></i>${esc(t.l_flame)}</span>
      ${dems.length ? `<span><i class="lb dem"></i>${esc(t.l_dem)}</span>` : ""}</div>`;
    const note = hasT && !this._hist ? `<div class="muted small">${esc(t.no_hist)}</div>` : "";
    return `<div class="sec">${esc(t.last24)}</div>${plot}${legend}${note}`;
  }

  _condCls(v) {
    if (v == null) return "";
    return v >= 80 ? "good" : v >= 50 ? "" : "bad";
  }

  _mini(key, label, value, unit, cls = "") {
    const ent = this._hass.states[this._config.entity].attributes.entities?.[key] || "";
    return `<div class="mini ${cls}" data-ent="${esc(ent)}"><b>${value}<small>${esc(unit)}</small></b><span>${esc(label)}</span></div>`;
  }

  _timeline(a, small) {
    const now = Date.now() / 1000;
    const span = 24 * 3600;
    const t0 = now - span;
    const W = 1000;
    const H = small ? 14 : 26;
    const tt0 = this._t;
    // Heat demand (relay) as a pale band behind the flames
    const dems = (a.demand_timeline || []).map(([s, e]) => {
      const x1 = Math.max(0, ((s - t0) / span) * W);
      const x2 = Math.min(W, (((e ?? now) - t0) / span) * W);
      if (x2 <= 0) return "";
      const tip = small ? "" : esc(tipHtml(
        `${this._fmtTs(s, false)} – ${e == null ? tt0.tt_running : this._fmtTs(e, false)}`,
        [[tt0.tt_demand, durText(((e ?? now) - s) / 60)],
         [tt0.tt_flame, durText(this._flameIn(a, s, e ?? now) / 60)]]));
      return `<rect x="${x1.toFixed(1)}" y="0" width="${Math.max(1.5, x2 - x1).toFixed(1)}" height="${H}" rx="1.5" class="dem"${tip ? ` data-tip="${tip}"` : ""}/>`;
    }).join("");
    const segs = (a.timeline || []).map(([s, e, sh, inf]) => {
      const x1 = Math.max(0, ((s - t0) / span) * W);
      const x2 = Math.min(W, (((e ?? now) - t0) / span) * W);
      if (x2 <= 0) return "";
      const tt = this._t;
      const tip = small ? "" : esc(tipHtml(
        `${this._fmtTs(s, false)} – ${e == null ? tt.tt_running : this._fmtTs(e, false)}`,
        [[tt.tt_burn, durText(((e ?? now) - s) / 60)], sh ? ["⚠️", tt.tt_short] : null, inf ? ["ℹ️", tt.tt_inferred] : null]));
      const dy = dems ? H * 0.2 : 0;
      return `<rect x="${x1.toFixed(1)}" y="${dy}" width="${Math.max(1.5, x2 - x1).toFixed(1)}" height="${H - 2 * dy}" rx="1.5" class="${sh ? "seg short" : "seg"}${inf ? " inf" : ""}${e == null ? " live" : ""}"${tip ? ` data-tip="${tip}"` : ""}/>`;
    }).join("");
    let ticks = "", labels = "";
    if (!small) {
      const d = new Date();
      d.setMinutes(0, 0, 0);
      for (let i = 0; i <= 24; i++) {
        const ts = d.getTime() / 1000 - i * 3600;
        if (ts < t0) break;
        const h = new Date(ts * 1000).getHours();
        if (h % 6) continue;
        const x = ((ts - t0) / span) * W;
        ticks += `<line x1="${x}" x2="${x}" y1="0" y2="${H}" class="tick"/>`;
        labels += `<span style="left:${(x / W) * 100}%">${String(h).padStart(2, "0")}:00</span>`;
      }
    }
    return `<div class="tlw"><svg class="tl ${small ? "small" : ""}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
      <rect x="0" y="0" width="${W}" height="${H}" rx="3" class="track"/>${dems}${segs}${ticks}</svg>${
      small ? "" : `<div class="tlabs">${labels}</div>`}</div>`;
  }

  _flameIn(a, start, end) {
    return (a.timeline || []).reduce((acc, [s, e]) =>
      acc + Math.max(0, Math.min(e ?? Date.now() / 1000, end) - Math.max(s, start)), 0);
  }

  _daily(a) {
    const t = this._t;
    const days = (a.daily || []).slice(-14);
    if (!days.length) return "";
    const max = Math.max(1, ...days.map((d) => d.burn_h));
    const bars = days.map((d) => {
      const h = (d.burn_h / max) * 100;
      const dd = d.date.slice(8, 10);
      return `<div class="bar" data-tip="${esc(this._dayTip(d))}"><div class="bv">${durShort(d.burn_h * 60)}</div>
        <div class="bcol"><div class="bf ${d.short ? "has-short" : ""}" style="height:${h}%"></div></div>
        <div class="bd">${dd}</div>${d.outdoor != null ? `<div class="bo">${fmt(d.outdoor, 0)}°</div>` : ""}</div>`;
    }).join("");
    return `<div class="sec">${esc(t.days)} <span class="muted">· ${esc(t.burn_h)}</span></div><div class="bars">${bars}</div>`;
  }

  // Heating curve (weather compensation) or fixed flow chart: flow °C vs outdoor °C.
  _curve(a) {
    const t = this._t;
    const s = a.stats || {};
    const mode = a.regulation_mode; // "weather_compensation" | "fixed" | null
    const fixed = mode === "fixed";
    const all = a.curve_points || [];
    const pts = mode ? all.filter((p) => p[3] === (fixed ? 0 : 1)) : all;
    const title = `<div class="sec">${esc(fixed ? t.fixed_title : t.curve_title)}${
      mode ? ` <span class="mchip ${fixed ? "fixed" : "curve"}">${esc(fixed ? t.mode_fixed : t.mode_curve)}</span>` : ""}</div>`;
    if (!pts.length) return `${title}<div class="muted small">${esc(t.no_points)}</div>`;

    const xs = pts.map((p) => p[0]);
    let xmin = Math.floor(Math.min(...xs) - 1), xmax = Math.ceil(Math.max(...xs) + 1);
    if (!fixed) { xmin = Math.min(xmin, -10); xmax = Math.max(xmax, 15); }
    const ys = pts.flatMap((p) => [p[1], p[2]]).filter((v) => v != null);
    if (a.flow_target != null) ys.push(a.flow_target);
    const fit = a.curve_fit;
    if (!fixed && fit) ys.push(fit.intercept + fit.raw_slope * xmin, fit.intercept + fit.raw_slope * xmax);
    let ymin = Math.floor((Math.min(...ys) - 3) / 5) * 5, ymax = Math.ceil((Math.max(...ys) + 3) / 5) * 5;
    if (ymax - ymin < 15) ymax = ymin + 15;

    const n = pts.length;
    const op = (i) => (0.3 + 0.7 * (i + 1) / n).toFixed(2);
    const hourTip = (p) => tipHtml(
      p[4] != null ? esc(`${this._fmtTs(p[4])} – ${this._fmtTs(p[4] + 3600, false)}`) : "",
      [
        [t.tt_outdoor, `${fmt(p[0], 1)} °C`],
        [t.tt_target, `${fmt(p[1], 1)} °C`],
        [t.tt_actual, p[2] != null ? `${fmt(p[2], 1)} °C` : t.tt_noburn],
        p[2] != null ? [t.tt_diff, `${p[2] - p[1] > 0 ? "+" : ""}${fmt(p[2] - p[1], 1)} °C`] : null,
        [t.tt_mode, p[3] === 1 ? t.mode_curve : t.mode_fixed],
      ]);
    const points = [
      ...(fixed ? [] : pts.map((p, i) => ({ x: p[0], y: p[1], cls: "dot", op: op(i), tip: hourTip(p) }))),
      ...pts.filter((p) => p[2] != null).map((p) => ({ x: p[0], y: p[2], cls: "hdot", op: 0.75, tip: hourTip(p) })),
    ];
    const layers = (X, Y, d) => {
      if (fixed && a.flow_target != null) return `<line x1="${X(d.x0)}" x2="${X(d.x1)}" y1="${Y(a.flow_target)}" y2="${Y(a.flow_target)}" class="reg"/>`;
      if (!fixed && fit) {
        const f = (x) => fit.intercept + fit.raw_slope * x;
        return `<line x1="${X(d.x0)}" y1="${Y(f(d.x0))}" x2="${X(d.x1)}" y2="${Y(f(d.x1))}" class="reg"/>`;
      }
      return "";
    };
    const plot = this._plot("curve", {
      full: { x0: xmin, x1: xmax, y0: ymin, y1: ymax }, H: 160,
      xFmt: (v) => `${v}°`, yFmt: (v) => `${v}°`, layers, points,
    });

    const parts = [];
    if (fixed && a.flow_target != null) parts.push(`<span data-ent="${esc(a.sources?.setpoint || "")}"><b>${fmt(a.flow_target, 0)} °C</b> ${esc(t.fixed_at)}</span>`);
    if (!fixed && fit) {
      parts.push(`<span data-ent="${esc(a.entities?.curve_slope || "")}"><b>${fmt(fit.slope, 2)}</b> ${esc(t.slope)}</span>`);
      parts.push(`<span><b>${fmt(fit.at_0, 0)} °C</b> ${esc(t.at0)}</span>`);
      parts.push(`<span><b>${fmt(fit.at_minus_10, 0)} °C</b> ${esc(t.atm10)}</span>`);
    }
    if (s.flow_deviation != null) {
      const d = s.flow_deviation;
      parts.push(`<span data-ent="${esc(a.entities?.flow_deviation || "")}" class="${Math.abs(d) > 5 ? "warnt" : ""}"><b>${d > 0 ? "+" : ""}${fmt(d, 1)} °C</b> ${esc(t.dev24)}</span>`);
    }
    const legend = `<div class="legend">${fixed ? `<span><i class="lline"></i>${esc(t.fixed_at)}</span>` : `<span><i class="ldot"></i>${esc(t.leg_target)}</span>`}<span><i class="lhdot"></i>${esc(t.leg_actual)}</span></div>`;
    const note = !fixed && !fit ? `<div class="muted small">${esc(t.need_curve)}</div>` : "";
    return `${title}${plot}${legend}${note}<div class="cfoot">${parts.join("")}</div>`;
  }

  // Comfort vs outdoor: how far the rooms are from the thermostat setting, per hour, vs outdoor temp.
  _comfort(a) {
    const t = this._t;
    const c = a.comfort || { verdict: "insufficient_data", n: 0 };
    const v = c.verdict || "insufficient_data";
    const fixed = a.regulation_mode === "fixed";
    const tone = v === "ok" ? "good" : v === "insufficient_data" ? "none" : /low$/.test(v) ? "cold" : "warm";
    const icon = { good: "mdi:check-circle", none: "mdi:timer-sand", cold: "mdi:thermometer-chevron-up", warm: "mdi:thermometer-chevron-down" }[tone];
    let advice = (fixed && t[`af_${v}`]) || t[`a_${v}`] || "";
    advice = advice.replace("{h}", 24).replace("{n}", c.n ?? 0).replace("{s}", fmt(c.spread ?? 0, 1));
    const sign = (x) => (x > 0 ? "+" : "") + fmt(x, 1);
    const facts = v === "insufficient_data" ? "" : `<div class="vfacts">
        <span><b>${sign(c.gap_cold)} °C</b> ${esc(t.gap_cold_l)}</span>
        <span><b>${sign(c.gap_mild)} °C</b> ${esc(t.gap_mild_l)}</span>
        <span><b>${fmt((c.duty_cold ?? 0) * 100, 0)} %</b> ${esc(t.duty_cold_l)}</span>
        ${c.confidence ? `<span class="muted">${esc(t[`conf_${c.confidence}`] || c.confidence)} · n=${c.n}</span>` : ""}</div>`;
    const box = `<div class="verdict ${tone}" data-ent="${esc(a.entities?.comfort_verdict || "")}">
        <ha-icon icon="${icon}"></ha-icon><div><b>${esc(t[`v_${v}`] || v)}</b><div class="vtext">${esc(advice)}</div>${facts}</div></div>`;
    const head = `<div class="sec">${esc(t.comfort_title)}</div>`;
    const pts = a.comfort_points || [];
    if (!pts.length) return `${head}${box}`;

    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const xmin = Math.floor(Math.min(...xs) - 1), xmax = Math.ceil(Math.max(...xs) + 1);
    const ymin = Math.floor(Math.min(-1.5, ...ys) - 0.3), ymax = Math.ceil(Math.max(1.5, ...ys) + 0.3);
    const n = pts.length;
    const tip = (p) => tipHtml(esc(`${this._fmtTs(p[4])} – ${this._fmtTs(p[4] + 3600, false)}`), [
      [t.tt_outdoor, `${fmt(p[0], 1)} °C`],
      [t.tt_indoor, `${fmt(p[5], 1)} °C`],
      [t.tt_setpoint, `${fmt(p[6], 1)} °C`],
      [t.tt_gap, `${sign(p[1])} °C`],
      [t.tt_duty, `${fmt(p[2] * 100, 0)} %`],
      p[3] ? [t.tt_shorts, String(p[3])] : null,
    ]);
    const points = pts.map((p, i) => ({
      x: p[0], y: p[1], op: (0.3 + 0.7 * (i + 1) / n).toFixed(2), tip: tip(p),
      cls: p[1] < -0.5 ? "cdot cold" : p[1] > 0.5 ? "cdot warm" : "cdot ok",
    }));
    const layers = (X, Y, d) => {
      let out = `<rect x="${X(d.x0)}" y="${Y(0.5)}" width="${X(d.x1) - X(d.x0)}" height="${Math.max(0, Y(-0.5) - Y(0.5))}" class="zone"/>`;
      out += `<line x1="${X(d.x0)}" x2="${X(d.x1)}" y1="${Y(0)}" y2="${Y(0)}" class="zero"/>`;
      if (c.fit_a != null && c.fit_b != null) {
        const f = (x) => c.fit_a + c.fit_b * x;
        out += `<line x1="${X(d.x0)}" y1="${Y(f(d.x0))}" x2="${X(d.x1)}" y2="${Y(f(d.x1))}" class="reg"/>`;
      }
      return out;
    };
    const plot = this._plot("comfort", {
      full: { x0: xmin, x1: xmax, y0: ymin, y1: ymax }, H: 150,
      xFmt: (v2) => `${v2}°`, yFmt: (v2) => `${v2 > 0 ? "+" : ""}${v2}°`, layers, points,
    });
    const legend = `<div class="legend"><span><i class="lzone"></i>${esc(t.leg_zone)}</span><span><i class="ldot cold"></i>&lt; −0.5</span><span><i class="ldot warm"></i>&gt; +0.5</span></div>`;
    return `${head}${box}${plot}${legend}`;
  }

  // How fast the house warms up: one dot per measured warm-up, minutes per °C vs outdoor.
  _heatup(a) {
    const t = this._t;
    const s = a.stats || {};
    const head = `<div class="sec">${esc(t.heat_title)}</div>`;
    const ev = a.heatups || [];
    const m = a.heatup_model;
    if (!ev.length || !m) return `${head}<div class="muted small">${esc(t.heat_none)}</div>`;
    const parts = [];
    if (s.heatup_rate != null) {
      parts.push(`<span data-ent="${esc(a.entities?.heatup_rate || "")}"><b>${durText(s.heatup_rate)}</b> ${esc(t.heat_rate_l.replace("{o}", fmt(a.outdoor, 0)))}</span>`);
    }
    if (a.thermostat_setpoint != null && s.preheat_minutes != null) {
      parts.push(s.preheat_minutes > 0
        ? `<span data-ent="${esc(a.entities?.preheat_time || "")}"><b>${durText(s.preheat_minutes)}</b> ${esc(t.heat_pre_l.replace("{t}", fmt(a.thermostat_setpoint, 1)))}</span>`
        : `<span class="muted">${esc(t.heat_reached.replace("{t}", fmt(a.thermostat_setpoint, 1)))}</span>`);
    }
    parts.push(`<span class="muted">${esc(t.heat_events.replace("{n}", m.n))}${m.r2 != null ? ` · R² ${fmt(m.r2, 2)}` : ""}</span>`);
    const xs = ev.map((e) => e.out).filter((x) => x != null);
    if (!xs.length) return `${head}<div class="cfoot">${parts.join("")}</div>`;
    const xmin = Math.floor(Math.min(...xs) - 2), xmax = Math.ceil(Math.max(...xs) + 2);
    const ymax = Math.ceil(Math.max(10, ...ev.map((e) => e.rate)) * 1.15 / 5) * 5;
    const points = ev.filter((e) => e.out != null).map((e, i) => ({
      x: e.out, y: e.rate, cls: "dot", op: (0.35 + 0.65 * (i + 1) / ev.length).toFixed(2),
      tip: tipHtml(esc(this._fmtTs(e.ts)), [
        [t.tt_outdoor, `${fmt(e.out, 1)} °C`],
        [t.tt_rise, `${fmt(e.in0, 1)} → ${fmt(e.in1, 1)} °C`],
        [t.tt_took, durText(e.minutes)],
        [t.tt_rate, durText(e.rate)],
      ]),
    }));
    const layers = (X, Y, d) => {
      if (m.a == null || m.b == null) return `<line x1="${X(d.x0)}" x2="${X(d.x1)}" y1="${Y(m.median)}" y2="${Y(m.median)}" class="reg"/>`;
      const f = (x) => m.a + m.b * x;
      return `<line x1="${X(d.x0)}" y1="${Y(f(d.x0))}" x2="${X(d.x1)}" y2="${Y(f(d.x1))}" class="reg"/>`;
    };
    const plot = this._plot("heatup", {
      full: { x0: xmin, x1: xmax, y0: 0, y1: ymax }, H: 130,
      xFmt: (v2) => `${v2}°`, yFmt: (v2) => `${v2}m`, layers, points,
    });
    return `${head}${plot}<div class="cfoot">${parts.join("")}</div>`;
  }

  _corr(a) {
    const t = this._t;
    const n = new Date(); const today = `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-${String(n.getDate()).padStart(2, "0")}`;
    const pts = (a.daily || []).filter((d) => d.outdoor != null && d.date !== today);
    const reg = a.regression;
    const head = `<div class="sec">${esc(t.corr)}</div>`;
    if (pts.length < 3) return `${head}<div class="muted small">${esc(t.not_enough)}</div>`;
    const xs = pts.map((p) => p.outdoor);
    let xmin = Math.min(...xs), xmax = Math.max(...xs);
    if (reg?.balance_point != null && reg.balance_point < 30) xmax = Math.max(xmax, reg.balance_point);
    xmin = Math.floor(xmin - 1); xmax = Math.ceil(xmax + 1);
    const ymax = Math.ceil(Math.max(1, ...pts.map((p) => p.burn_h)) * 1.1);
    const points = pts.map((p, i) => ({ x: p.outdoor, y: p.burn_h, cls: "dot", op: (0.35 + 0.65 * (i + 1) / pts.length).toFixed(2), tip: this._dayTip(p) }));
    const layers = (X, Y, d) => {
      if (!reg) return "";
      const f = (x) => reg.intercept + reg.slope * x;
      let out = `<line x1="${X(d.x0)}" y1="${Y(f(d.x0))}" x2="${X(d.x1)}" y2="${Y(f(d.x1))}" class="reg"/>`;
      if (reg.balance_point != null) out = `<line x1="${X(reg.balance_point)}" x2="${X(reg.balance_point)}" y1="${Y(d.y1) - 4}" y2="${Y(d.y0)}" class="bpl"/>` + out;
      return out;
    };
    const plot = this._plot("corr", {
      full: { x0: xmin, x1: xmax, y0: 0, y1: ymax }, H: 150,
      xFmt: (v) => `${v}°`, yFmt: (v) => `${v}h`, layers, points,
    });
    const perHdd = a.stats?.burn_per_hdd;
    const foot = `<div class="cfoot">
      ${reg?.balance_point != null ? `<span data-ent="${esc(a.entities?.balance_point || "")}"><b>${fmt(reg.balance_point, 1)}°C</b> ${esc(t.balance)}</span>` : reg ? `<span class="muted">${esc(t.bp_unreliable)}</span>` : ""}
      ${perHdd != null ? `<span data-ent="${esc(a.entities?.burn_per_hdd || "")}"><b>${fmt(perHdd * 60, 0)}</b> ${esc(t.per_hdd)}</span>` : ""}
      ${reg ? `<span class="muted">R² ${fmt(reg.r2, 2)} · n=${reg.n}</span>` : ""}</div>`;
    return `${head}${plot}${foot}`;
  }
}

const STYLE = `
  :host { --bm-burn: var(--state-climate-heat-color, #ff8100); --bm-short: var(--error-color, #db4437);
          --bm-good: var(--success-color, #43a047); --bm-warn: var(--warning-color, #ffa600); }
  ha-card { overflow: hidden; position: relative; }
  .tip { display: none; position: absolute; z-index: 5; pointer-events: none; min-width: 150px; max-width: 240px;
         padding: 8px 10px; border-radius: 8px; font-size: 12px; line-height: 1.5;
         background: var(--primary-text-color); color: var(--card-background-color, #fff);
         box-shadow: 0 4px 14px rgba(0,0,0,.25); }
  .tip b { display: block; font-weight: 600; margin-bottom: 2px; }
  .tip div { display: flex; justify-content: space-between; gap: 12px; }
  .tip div span:first-child { opacity: .75; }
  .tip hr { border: 0; border-top: 1px solid currentColor; opacity: .25; margin: 6px 0; }
  .tip .more { opacity: .75; font-style: italic; justify-content: flex-start; }
  .plot { position: relative; }
  .plot { touch-action: pan-y; }
  .plot.zoomed { touch-action: none; }
  .plot svg { cursor: crosshair; user-select: none; -webkit-user-select: none; }
  .plot svg.zoomed { cursor: grab; }
  .hl { fill: none; stroke: var(--primary-text-color); stroke-width: 1.6; pointer-events: none; }
  .sel { fill: color-mix(in srgb, var(--primary-color) 15%, transparent); stroke: var(--primary-color); stroke-width: 1; stroke-dasharray: 3 2; pointer-events: none; }
  .zbtns { position: absolute; top: 2px; right: 2px; display: flex; gap: 4px; }
  .zbtns button { width: 26px; height: 26px; border-radius: 6px; border: 1px solid var(--divider-color);
                  background: var(--card-background-color); color: var(--primary-text-color); font: 15px/1 inherit;
                  cursor: pointer; padding: 0; opacity: .85; }
  .zbtns button:hover { opacity: 1; border-color: var(--primary-color); }
  .zbtns button:disabled { opacity: .35; cursor: default; }
  [data-tip] { cursor: pointer; }
  .bar:hover .bf { opacity: 1; filter: brightness(1.08); }
  .wrap { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .compact .wrap { padding: 12px; gap: 8px; }
  .empty { padding: 16px; color: var(--secondary-text-color); }
  .click { cursor: pointer; }
  .muted { color: var(--secondary-text-color); font-weight: 400; }
  .small { font-size: 12px; }
  .hdr { display: flex; align-items: center; gap: 12px; }
  .flame { width: 42px; height: 42px; border-radius: 50%; display: grid; place-items: center; flex: none;
           background: rgba(var(--rgb-disabled-color, 189,189,189), .2); color: var(--disabled-color, #bdbdbd); }
  .flame.heating { background: color-mix(in srgb, var(--bm-burn) 20%, transparent); color: var(--bm-burn); }
  .flame.heating ha-icon { animation: flick 1.6s ease-in-out infinite; }
  @keyframes flick { 0%,100% { transform: scale(1); } 50% { transform: scale(1.12) translateY(-1px); } }
  @media (prefers-reduced-motion: reduce) { .flame.heating ha-icon { animation: none; } }
  .ttl { flex: 1; min-width: 0; }
  .name { font-size: 16px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sub { font-size: 13px; color: var(--secondary-text-color); }
  .chip { font-size: 12px; padding: 3px 10px; border-radius: 12px; white-space: nowrap;
          background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .chip.heating { background: color-mix(in srgb, var(--bm-burn) 18%, transparent); color: var(--bm-burn); }
  .compact .chip { display: none; }
  .alerts { display: flex; flex-wrap: wrap; gap: 6px; }
  .alert { display: flex; align-items: center; gap: 6px; font-size: 13px; padding: 4px 10px 4px 6px; border-radius: 14px;
           background: color-mix(in srgb, var(--bm-short) 14%, transparent); color: var(--bm-short); }
  .alert ha-icon { --mdc-icon-size: 18px; }
  .temps { display: grid; gap: 6px; grid-template-columns: repeat(auto-fit, minmax(62px, 1fr)); }
  .temps.many { grid-template-columns: repeat(4, 1fr); }
  @container (max-width: 340px) { .temps.many { grid-template-columns: repeat(3, 1fr); } }
  .temp em { font-style: normal; font-size: 10px; color: var(--secondary-text-color); margin-top: -2px; }
  .temp { padding: 6px 8px; border-radius: 10px; background: var(--secondary-background-color);
          display: flex; flex-direction: column; }
  .temp span { font-size: 11px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }
  .temp b { font-size: 18px; font-weight: 500; font-variant-numeric: tabular-nums; }
  .temp small, .tv small, .mini small { font-size: .6em; font-weight: 400; margin-left: 2px; color: var(--secondary-text-color); }
  .temp.bad b { color: var(--bm-short); } .temp.good b { color: var(--bm-good); }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  @container (max-width: 360px) { .grid { grid-template-columns: repeat(2, 1fr); } }
  ha-card { container-type: inline-size; }
  .tile { padding: 8px; border-radius: 10px; border: 1px solid var(--divider-color); }
  .tv { font-size: 20px; font-weight: 500; font-variant-numeric: tabular-nums; line-height: 1.2; }
  .tl { font-size: 11px; color: var(--secondary-text-color); margin-top: 2px; }
  .tile.warn .tv, .mini.warn b { color: var(--bm-warn); }
  .tile.bad .tv, .mini.bad b { color: var(--bm-short); }
  .tile.good .tv, .mini.good b { color: var(--bm-good); }
  .crow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .mini { display: flex; flex-direction: column; align-items: center; text-align: center; }
  .mini b { font-size: 17px; font-weight: 500; font-variant-numeric: tabular-nums; }
  .mini span { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .sec { font-size: 13px; font-weight: 500; margin-bottom: -4px; }
  .tlw { position: relative; }
  svg.tl { width: 100%; height: 26px; display: block; }
  .tlabs { position: relative; height: 14px; margin-top: 2px; }
  .tlabs span { position: absolute; transform: translateX(-50%); font-size: 10px; color: var(--secondary-text-color); }
  .tlabs span:first-child { transform: translateX(-100%); }
  .aicon { color: var(--bm-short); display: grid; place-items: center; }
  .aicon ha-icon { --mdc-icon-size: 20px; }
  svg.tl.small { height: 12px; }
  .track { fill: var(--secondary-background-color); }
  .seg { fill: var(--bm-burn); } .seg.short { fill: var(--bm-short); }
  .dem { fill: color-mix(in srgb, var(--bm-burn) 28%, transparent); }
  .seg.inf { fill-opacity: 0.55; }
  .flame.demand, .chip.demand { background: color-mix(in srgb, var(--bm-burn) 10%, transparent); color: color-mix(in srgb, var(--bm-burn) 70%, var(--secondary-text-color)); }
  .seg.live { animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .55; } }
  .tick { stroke: var(--card-background-color, #fff); stroke-width: 2; vector-effect: non-scaling-stroke; }
  .bars { display: flex; gap: 3px; align-items: stretch; height: 110px; }
  .bar { flex: 1; display: flex; flex-direction: column; align-items: center; min-width: 0; }
  .bv { font-size: 9px; color: var(--secondary-text-color); height: 12px; }
  @container (max-width: 400px) { .bv { visibility: hidden; } }
  .bcol { flex: 1; width: 100%; display: flex; align-items: flex-end; }
  .bf { width: 100%; background: var(--bm-burn); border-radius: 3px 3px 0 0; min-height: 1px; opacity: .85; }
  .bf.has-short { box-shadow: inset 0 3px 0 var(--bm-short); }
  .bd { font-size: 10px; color: var(--secondary-text-color); }
  .bo { font-size: 9px; color: var(--secondary-text-color); }
  svg.corr { width: 100%; height: auto; display: block; }
  .dot { fill: var(--bm-burn); }
  .reg { stroke: var(--primary-color); stroke-width: 2; stroke-dasharray: 5 4; }
  .bpl { stroke: var(--bm-good); stroke-width: 1.5; }
  .ax { stroke: var(--divider-color); } .grd { stroke: var(--divider-color); opacity: .5; }
  .axl { font-size: 10px; fill: var(--secondary-text-color); }
  .hdot { fill: none; stroke: var(--primary-color); stroke-width: 1.6; }
  .legend { display: flex; gap: 14px; font-size: 11px; color: var(--secondary-text-color); margin-top: -4px; }
  .legend span { display: inline-flex; align-items: center; gap: 5px; }
  .ldot { width: 8px; height: 8px; border-radius: 50%; background: var(--bm-burn); display: inline-block; }
  .lhdot { width: 7px; height: 7px; border-radius: 50%; border: 1.6px solid var(--primary-color); display: inline-block; }
  .lline { width: 14px; border-top: 2px dashed var(--primary-color); display: inline-block; }
  .mchip { font-size: 11px; font-weight: 400; padding: 1px 8px; border-radius: 10px; margin-left: 6px;
           background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .mchip.curve { background: color-mix(in srgb, var(--bm-good) 16%, transparent); color: var(--bm-good); }
  .mchip.fixed { background: color-mix(in srgb, var(--primary-color) 14%, transparent); color: var(--primary-color); }
  .warnt b { color: var(--bm-warn); }
  .verdict { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 10px;
             background: var(--secondary-background-color); font-size: 13px; line-height: 1.4; }
  .verdict ha-icon { flex: none; --mdc-icon-size: 22px; margin-top: 1px; }
  .verdict b { font-size: 14px; }
  .verdict .vtext { color: var(--primary-text-color); margin-top: 2px; }
  .verdict.good ha-icon { color: var(--bm-good); }
  .verdict.cold ha-icon { color: var(--primary-color); }
  .verdict.warm ha-icon { color: var(--bm-burn); }
  .verdict.none ha-icon { color: var(--secondary-text-color); }
  .vfacts { display: flex; flex-wrap: wrap; gap: 2px 12px; margin-top: 6px; font-size: 12px; }
  .cdot.ok { fill: var(--bm-good); } .cdot.cold { fill: var(--primary-color); } .cdot.warm { fill: var(--bm-burn); }
  .zone { fill: color-mix(in srgb, var(--bm-good) 10%, transparent); }
  .zero { stroke: var(--secondary-text-color); stroke-width: 1; opacity: .6; }
  .lzone { width: 14px; height: 8px; background: color-mix(in srgb, var(--bm-good) 25%, transparent); display: inline-block; border-radius: 2px; }
  .ldot.cold { background: var(--primary-color); } .ldot.warm { background: var(--bm-burn); }
  .cfoot { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 13px; }
  .tabs { display: flex; gap: 4px; padding: 3px; border-radius: 12px; background: var(--secondary-background-color); }
  .tab { flex: 1; border: 0; background: none; color: var(--secondary-text-color); font: inherit; font-size: 13px;
         padding: 7px 4px; border-radius: 9px; cursor: pointer; white-space: nowrap; }
  .tab.on { background: var(--card-background-color); color: var(--primary-text-color); font-weight: 500;
            box-shadow: 0 1px 3px rgba(0,0,0,.15); }
  .pane { display: flex; flex-direction: column; gap: 12px; }
  .pills { display: grid; gap: 6px; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
  .pill { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 10px; font-size: 13px;
          background: var(--secondary-background-color); }
  .pill ha-icon { --mdc-icon-size: 18px; flex: none; }
  .pill span { color: var(--secondary-text-color); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pill b { font-weight: 500; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .pill.good ha-icon, .pill.good b { color: var(--bm-good); }
  .pill.warn ha-icon, .pill.warn b { color: var(--bm-warn); }
  .pill.bad { background: color-mix(in srgb, var(--bm-short) 12%, transparent); }
  .pill.bad ha-icon, .pill.bad b { color: var(--bm-short); }
  .pill.none ha-icon { color: var(--secondary-text-color); }
  .pane .temps { grid-template-columns: repeat(3, 1fr); }
  @container (min-width: 520px) { .pane .temps { grid-template-columns: repeat(6, 1fr); } }
  .grp .grid { grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); }
  .grp { display: flex; flex-direction: column; gap: 4px; }
  .gl { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--secondary-text-color); }
  .tdem { fill: color-mix(in srgb, var(--bm-burn) 9%, transparent); }
  .tburn { fill: color-mix(in srgb, var(--bm-burn) 14%, transparent); }
  .lflow, .lret { fill: none; stroke-width: 1.6; stroke-linejoin: round; }
  .lflow { stroke: var(--bm-burn); } .lret { stroke: var(--primary-color); }
  .ltgt { fill: none; stroke: var(--secondary-text-color); stroke-width: 1.2; stroke-dasharray: 4 3; }
  .cur { stroke: var(--primary-text-color); stroke-width: 1; opacity: .5; pointer-events: none; }
  .legend.wrapl { flex-wrap: wrap; gap: 4px 12px; }
  .lc { width: 14px; height: 0; border-top: 2px solid; display: inline-block; }
  .lc.flow { border-color: var(--bm-burn); } .lc.ret { border-color: var(--primary-color); }
  .lc.tgt { border-top: 2px dashed var(--secondary-text-color); }
  .lb { width: 12px; height: 8px; border-radius: 2px; display: inline-block; }
  .lb.burn { background: var(--bm-burn); } .lb.dem { background: color-mix(in srgb, var(--bm-burn) 25%, transparent); }
`;

// ---------------------------------------------------------------- register
// Some Home Assistant setups replace window.customElements after page load
// (the scoped-custom-element-registry polyfill). Anything defined before the
// swap is invisible to the new registry, and Lovelace then reports
// "Custom element doesn't exist". So: define now, and keep checking for a few
// seconds and define again on the new registry if it was replaced.
const CARD_TAG = "boiler-monitor-card";
const registerCard = () => {
  try {
    if (!window.customElements.get(CARD_TAG)) {
      window.customElements.define(CARD_TAG, BoilerMonitorCard);
      return true;
    }
  } catch (err) {
    // The native registry may already hold this exact class; that's fine.
    if (!window.customElements.get(CARD_TAG)) {
      try {
        window.customElements.define(CARD_TAG, class extends BoilerMonitorCard {});
        return true;
      } catch (err2) {
        console.warn("boiler-monitor-card: could not register on the current registry", err2);
      }
    }
  }
  return false;
};

if (!window.__boilerMonitorCardLoaded) {
  window.__boilerMonitorCardLoaded = CARD_VERSION;
  registerCard();
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === CARD_TAG)) {
    window.customCards.push({
      type: CARD_TAG,
      name: "Boiler Monitor",
      description: "Burner cycles, condensation and heating-curve insights (boiler_monitor integration).",
      preview: true,
    });
  }
  console.info(`%c BOILER-MONITOR-CARD %c ${CARD_VERSION} `, "background:#ff8100;color:#fff", "");
  let checks = 0;
  const watch = setInterval(() => {
    registerCard();
    if (++checks >= 60) clearInterval(watch); // 30 s
  }, 500);
  window.addEventListener("location-changed", registerCard);
} else {
  registerCard();
}

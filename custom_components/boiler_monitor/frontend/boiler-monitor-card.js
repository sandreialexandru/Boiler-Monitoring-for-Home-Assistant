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
 */
const CARD_VERSION = "1.1.2";

const I18N = {
  en: {
    heating: "Heating", idle: "Idle", off_season: "Off season", unavailable: "Unavailable",
    burning_for: "burning for", min: "min", h: "h",
    flow: "Flow", ret: "Return", dt: "ΔT", outdoor: "Outdoor", indoor: "Indoor",
    cycles_today: "Cycles today", cycles_h: "Cycles / h", avg_burn: "Avg burn", avg_off: "Avg off",
    duty: "Duty 24h", burn_today: "Burn today", cond: "Condensing", rate: "Heating rate",
    short: "short", last24: "Last 24 hours", days: "Last 14 days", corr: "Burn vs outdoor",
    balance: "Balance point", per_hdd: "min per degree-day", not_enough: "Needs ≥ 3 full days of data",
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
    tt_running: "running", tt_short: "short cycle", tt_from: "Off before", tt_noburn: "not burning this hour",
  },
  ro: {
    heating: "Încălzește", idle: "În așteptare", off_season: "În afara sezonului", unavailable: "Indisponibil",
    burning_for: "arde de", min: "min", h: "h",
    flow: "Tur", ret: "Retur", dt: "ΔT", outdoor: "Exterior", indoor: "Interior",
    cycles_today: "Cicluri azi", cycles_h: "Cicluri / h", avg_burn: "Ardere medie", avg_off: "Pauză medie",
    duty: "Funcționare 24h", burn_today: "Ardere azi", cond: "Condensare", rate: "Rată încălzire",
    short: "scurte", last24: "Ultimele 24 de ore", days: "Ultimele 14 zile", corr: "Ardere vs exterior",
    balance: "Punct de echilibru", per_hdd: "min pe grad-zi", not_enough: "Necesită ≥ 3 zile complete de date",
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
    this._config = { mode: "full", show_timeline: true, show_daily: true, show_correlation: true, show_curve: true, ...config };
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
    this.shadowRoot?.querySelectorAll(".hl").forEach((h) => h.setAttribute("visibility", "hidden"));
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
    const [y0, y1] = clamp(full.y0, full.y1, z.y0, z.y1);
    return { x0, x1, y0, y1 };
  }

  _plotInner(id) {
    const t = this._t;
    const cfg = this._plots[id];
    const W = 320, H = cfg.H || 160, P = { l: 32, r: 10, t: 10, b: 22 };
    const d = this._plotDomain(id);
    const X = (v) => P.l + ((v - d.x0) / (d.x1 - d.x0)) * (W - P.l - P.r);
    const Y = (v) => H - P.b - ((v - d.y0) / (d.y1 - d.y0)) * (H - P.t - P.b);
    const xt = niceTicks(d.x0, d.x1, 6), yt = niceTicks(d.y0, d.y1, 4);
    let axes = `<line x1="${P.l}" x2="${W - P.r}" y1="${H - P.b}" y2="${H - P.b}" class="ax"/>`;
    xt.ticks.forEach((x) => { axes += `<text x="${X(x)}" y="${H - 6}" class="axl" text-anchor="middle">${cfg.xFmt(tickFmt(x, xt.step))}</text>`; });
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
          <circle class="hl" r="7" visibility="hidden"/></g>
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
    const { full } = this._plots[id];
    const minW = (full.x1 - full.x0) / 25, minH = (full.y1 - full.y0) / 25;
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
        sel.setAttribute("x", Math.min(start.sx, p.sx)); sel.setAttribute("y", Math.min(start.sy, p.sy));
        sel.setAttribute("width", Math.abs(p.sx - start.sx)); sel.setAttribute("height", Math.abs(p.sy - start.sy));
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
        if (Math.abs(p.sx - start.sx) > 8 * p.k && Math.abs(p.sy - start.sy) > 8 * p.k) {
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
          <ha-icon icon="${status === "heating" ? "mdi:fire" : status === "off_season" ? "mdi:snowflake-off" : "mdi:fire-off"}"></ha-icon>
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
      const temps = [
        a.sources?.flow && { k: a.sources.flow, l: t.flow, v: a.flow, u: "°C" },
        a.sources?.setpoint && { k: a.sources.setpoint, v: a.flow_target, u: "°C",
          l: t.target, sub: a.regulation_mode ? (a.regulation_mode === "fixed" ? t.m_fixed : t.m_curve) : "" },
        a.sources?.return && { k: a.sources.return, l: t.ret, v: a.return, u: "°C",
          cls: a.return != null && a.return > a.thresholds?.return ? "bad" : "good" },
        a.sources?.flow && a.sources?.return && { k: a.entities?.delta_t, l: t.dt, v: s.delta_t, u: "°C" },
        a.sources?.outdoor && { k: a.sources.outdoor, l: t.outdoor, v: a.outdoor, u: "°C" },
        a.indoor != null && { k: "", l: t.indoor, v: a.indoor, u: "°C" },
        a.sources?.pressure && { k: a.sources.pressure, v: a.pressure, u: "bar", d: 2,
          l: s.pressure_change_7d != null && Math.abs(s.pressure_change_7d) >= 0.1
            ? `${t.pressure} ${s.pressure_change_7d < 0 ? "↓" : "↑"}${fmt(Math.abs(s.pressure_change_7d), 1)}` : t.pressure,
          cls: a.pressure != null && (a.pressure < a.thresholds?.pressure_min || a.pressure > a.thresholds?.pressure_max) ? "bad" : "" },
      ].filter(Boolean);

      const tiles = [
        ["cycles_today", t.cycles_today, fmt(s.cycles_today, 0), s.short_cycles_today ? `${s.short_cycles_today} ${t.short}` : "", s.short_cycles_today ? "warn" : ""],
        ["cycles_per_hour", t.cycles_h, fmt(s.cycles_per_hour, 2), "", (s.cycles_per_hour ?? 0) > 3 ? "warn" : ""],
        ["avg_burn", t.avg_burn, ...durTile(s.avg_burn_min), ""],
        ["avg_off", t.avg_off, ...durTile(s.avg_off_min), ""],
        ["duty_cycle", t.duty, fmt(s.duty_cycle, 0), "%", ""],
        ["burn_time_today", t.burn_today, ...durTile(s.burn_hours_today == null ? null : s.burn_hours_today * 60), ""],
        a.sources?.return && ["condensing_ratio", t.cond, fmt(s.condensing_ratio, 0), "%", this._condCls(s.condensing_ratio)],
        a.entities?.heating_rate && ["heating_rate", t.rate, fmt(s.heating_rate, 2), "°C/h", (s.heating_rate ?? 1) <= 0 ? "warn" : ""],
      ].filter(Boolean);

      body = `
        ${temps.length ? `<div class="temps ${temps.length > 5 ? "many" : ""}">${temps.map((x) => `
          <div class="temp ${x.cls || ""}" data-ent="${esc(x.k || "")}"><span>${esc(x.l)}</span><b>${fmt(x.v, x.d ?? 1)}<small>${x.u}</small></b>${x.sub ? `<em>${esc(x.sub)}</em>` : ""}</div>`).join("")}</div>` : ""}
        <div class="grid">${tiles.map(([k, l, v, u, cls]) => `
          <div class="tile ${cls}" data-ent="${esc(a.entities?.[k] || "")}">
            <div class="tv">${v}<small>${esc(u)}</small></div><div class="tl">${esc(l)}</div>
          </div>`).join("")}</div>
        ${this._config.show_timeline ? `<div class="sec">${esc(t.last24)}</div>${this._timeline(a, false)}` : ""}
        ${this._config.show_daily ? this._daily(a) : ""}
        ${this._config.show_curve && a.sources?.setpoint && a.sources?.outdoor ? this._curve(a) : ""}
        ${this._config.show_correlation && a.sources?.outdoor ? this._corr(a) : ""}`;
    }

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card class="${compact ? "compact" : ""}"><div class="wrap">${header}${body}</div><div class="tip" role="tooltip"></div></ha-card>`;
    this.shadowRoot.querySelectorAll("[data-ent]").forEach((el) => {
      const id = el.getAttribute("data-ent");
      if (!id) return;
      el.classList.add("click");
      el.addEventListener("click", () => this._moreInfo(id));
    });
    this._wireTips();
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
    const segs = (a.timeline || []).map(([s, e, sh]) => {
      const x1 = Math.max(0, ((s - t0) / span) * W);
      const x2 = Math.min(W, (((e ?? now) - t0) / span) * W);
      if (x2 <= 0) return "";
      const tt = this._t;
      const tip = small ? "" : esc(tipHtml(
        `${this._fmtTs(s, false)} – ${e == null ? tt.tt_running : this._fmtTs(e, false)}`,
        [[tt.tt_burn, durText(((e ?? now) - s) / 60)], sh ? ["⚠️", tt.tt_short] : null]));
      return `<rect x="${x1.toFixed(1)}" y="0" width="${Math.max(1.5, x2 - x1).toFixed(1)}" height="${H}" rx="1.5" class="${sh ? "seg short" : "seg"}${e == null ? " live" : ""}"${tip ? ` data-tip="${tip}"` : ""}/>`;
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
      <rect x="0" y="0" width="${W}" height="${H}" rx="3" class="track"/>${segs}${ticks}</svg>${
      small ? "" : `<div class="tlabs">${labels}</div>`}</div>`;
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
      ${reg?.balance_point != null ? `<span data-ent="${esc(a.entities?.balance_point || "")}"><b>${fmt(reg.balance_point, 1)}°C</b> ${esc(t.balance)}</span>` : ""}
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
  .cfoot { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 13px; }
`;

if (!customElements.get("boiler-monitor-card")) {
  customElements.define("boiler-monitor-card", BoilerMonitorCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "boiler-monitor-card",
    name: "Boiler Monitor",
    description: "Burner cycles, condensation and heating-curve insights (boiler_monitor integration).",
    preview: true,
  });
  console.info(`%c BOILER-MONITOR-CARD %c ${CARD_VERSION} `, "background:#ff8100;color:#fff", "");
}

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
 */
const CARD_VERSION = "1.0.4";

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
    this._config = { mode: "full", show_timeline: true, show_daily: true, show_correlation: true, ...config };
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
        a.sources?.return && { k: a.sources.return, l: t.ret, v: a.return, u: "°C",
          cls: a.return != null && a.return > a.thresholds?.return ? "bad" : "good" },
        a.sources?.flow && a.sources?.return && { k: a.entities?.delta_t, l: t.dt, v: s.delta_t, u: "°C" },
        a.sources?.outdoor && { k: a.sources.outdoor, l: t.outdoor, v: a.outdoor, u: "°C" },
        a.indoor != null && { k: "", l: t.indoor, v: a.indoor, u: "°C" },
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
        ${temps.length ? `<div class="temps">${temps.map((x) => `
          <div class="temp ${x.cls || ""}" data-ent="${esc(x.k || "")}"><span>${esc(x.l)}</span><b>${fmt(x.v, 1)}<small>${x.u}</small></b></div>`).join("")}</div>` : ""}
        <div class="grid">${tiles.map(([k, l, v, u, cls]) => `
          <div class="tile ${cls}" data-ent="${esc(a.entities?.[k] || "")}">
            <div class="tv">${v}<small>${esc(u)}</small></div><div class="tl">${esc(l)}</div>
          </div>`).join("")}</div>
        ${this._config.show_timeline ? `<div class="sec">${esc(t.last24)}</div>${this._timeline(a, false)}` : ""}
        ${this._config.show_daily ? this._daily(a) : ""}
        ${this._config.show_correlation && a.sources?.outdoor ? this._corr(a) : ""}`;
    }

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card class="${compact ? "compact" : ""}"><div class="wrap">${header}${body}</div></ha-card>`;
    this.shadowRoot.querySelectorAll("[data-ent]").forEach((el) => {
      const id = el.getAttribute("data-ent");
      if (!id) return;
      el.classList.add("click");
      el.addEventListener("click", () => this._moreInfo(id));
    });
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
      return `<rect x="${x1.toFixed(1)}" y="0" width="${Math.max(1.5, x2 - x1).toFixed(1)}" height="${H}" rx="1.5" class="${sh ? "seg short" : "seg"}${e == null ? " live" : ""}"/>`;
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
      const tip = `${d.date}: ${durText(d.burn_h * 60)} · ${d.cycles} cyc${d.short ? ` (${d.short} ${t.short})` : ""}${d.outdoor != null ? ` · ${fmt(d.outdoor, 1)}°C` : ""}${d.cond_pct != null ? ` · ${fmt(d.cond_pct, 0)}%` : ""}`;
      return `<div class="bar" title="${esc(tip)}"><div class="bv">${durShort(d.burn_h * 60)}</div>
        <div class="bcol"><div class="bf ${d.short ? "has-short" : ""}" style="height:${h}%"></div></div>
        <div class="bd">${dd}</div>${d.outdoor != null ? `<div class="bo">${fmt(d.outdoor, 0)}°</div>` : ""}</div>`;
    }).join("");
    return `<div class="sec">${esc(t.days)} <span class="muted">· ${esc(t.burn_h)}</span></div><div class="bars">${bars}</div>`;
  }

  _corr(a) {
    const t = this._t;
    const n = new Date(); const today = `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-${String(n.getDate()).padStart(2, "0")}`;
    const pts = (a.daily || []).filter((d) => d.outdoor != null && d.date !== today);
    const reg = a.regression;
    const head = `<div class="sec">${esc(t.corr)}</div>`;
    if (pts.length < 3) return `${head}<div class="muted small">${esc(t.not_enough)}</div>`;
    const W = 320, H = 150, P = { l: 30, r: 10, t: 10, b: 22 };
    const xs = pts.map((p) => p.outdoor);
    let xmin = Math.min(...xs), xmax = Math.max(...xs);
    if (reg?.balance_point != null && reg.balance_point < 30) xmax = Math.max(xmax, reg.balance_point);
    xmin = Math.floor(xmin - 1); xmax = Math.ceil(xmax + 1);
    const ymax = Math.ceil(Math.max(1, ...pts.map((p) => p.burn_h)) * 1.1);
    const X = (v) => P.l + ((v - xmin) / (xmax - xmin)) * (W - P.l - P.r);
    const Y = (v) => H - P.b - (v / ymax) * (H - P.t - P.b);
    const dots = pts.map((p, i) => `<circle cx="${X(p.outdoor).toFixed(1)}" cy="${Y(p.burn_h).toFixed(1)}" r="3.5"
      class="dot" style="opacity:${(0.35 + 0.65 * (i + 1) / pts.length).toFixed(2)}"><title>${esc(p.date)}: ${fmt(p.outdoor)}°C → ${durText(p.burn_h * 60)}</title></circle>`).join("");
    let line = "", bp = "";
    if (reg) {
      const f = (x) => reg.intercept + reg.slope * x;
      let x1 = xmin, x2 = xmax;
      if (reg.slope !== 0) {
        const xa = (0 - reg.intercept) / reg.slope, xb = (ymax - reg.intercept) / reg.slope;
        x1 = Math.max(xmin, Math.min(xa, xb));
        x2 = Math.min(xmax, Math.max(xa, xb));
      }
      if (x2 > x1) line = `<line x1="${X(x1)}" y1="${Y(f(x1))}" x2="${X(x2)}" y2="${Y(f(x2))}" class="reg"/>`;
      if (reg.balance_point != null && reg.balance_point >= xmin && reg.balance_point <= xmax) {
        bp = `<line x1="${X(reg.balance_point)}" x2="${X(reg.balance_point)}" y1="${P.t}" y2="${H - P.b}" class="bpl"/>`;
      }
    }
    let axes = `<line x1="${P.l}" x2="${W - P.r}" y1="${H - P.b}" y2="${H - P.b}" class="ax"/>`;
    const step = (xmax - xmin) > 16 ? 5 : 2;
    for (let x = Math.ceil(xmin / step) * step; x <= xmax; x += step) {
      axes += `<text x="${X(x)}" y="${H - 6}" class="axl" text-anchor="middle">${x}°</text>`;
    }
    for (let y = 0; y <= ymax; y += Math.max(1, Math.round(ymax / 4))) {
      axes += `<text x="${P.l - 5}" y="${Y(y) + 3}" class="axl" text-anchor="end">${y}h</text><line x1="${P.l}" x2="${W - P.r}" y1="${Y(y)}" y2="${Y(y)}" class="grd"/>`;
    }
    const perHdd = a.stats?.burn_per_hdd;
    const foot = `<div class="cfoot">
      ${reg?.balance_point != null ? `<span data-ent="${esc(a.entities?.balance_point || "")}"><b>${fmt(reg.balance_point, 1)}°C</b> ${esc(t.balance)}</span>` : ""}
      ${perHdd != null ? `<span data-ent="${esc(a.entities?.burn_per_hdd || "")}"><b>${fmt(perHdd * 60, 0)}</b> ${esc(t.per_hdd)}</span>` : ""}
      ${reg ? `<span class="muted">R² ${fmt(reg.r2, 2)} · n=${reg.n}</span>` : ""}</div>`;
    return `${head}<svg class="corr" viewBox="0 0 ${W} ${H}">${axes}${bp}${line}${dots}</svg>${foot}`;
  }
}

const STYLE = `
  :host { --bm-burn: var(--state-climate-heat-color, #ff8100); --bm-short: var(--error-color, #db4437);
          --bm-good: var(--success-color, #43a047); --bm-warn: var(--warning-color, #ffa600); }
  ha-card { overflow: hidden; }
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

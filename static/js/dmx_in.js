// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* DMX-Eingang (Menue "Steuerung" -> "DMX-Eingang ..."): Art-Net und sACN empfangen (app/dmx_in.py, GET/POST /api/dmx-in*).
 * Oben: ein-/ausschalten, Protokolle, Absender, Zeitablauf, Zustand; darunter die LIVE gesehenen Quellen (mit Werte-Anzeige und "Weiterleiten"), die Zuordnungen
 * (Eingang -> Ausgabe: Hoechster gewinnt / Ersetzen), die Ausloeser (Kanal -> Befehl, "Einlernen") und die letzten Ausloeser.
 * Aenderungen werden nach kurzer Pause gespeichert (nur an der Konsole selbst). */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "dmx-in";
  const COMMANDS = ["Go", "Back", "Pause", "Resume", "Stop", "Blackout", "Blackout On", "Blackout Off", "Master {value}", "Fader {value}", "Goto Cue 1"];

  let cfg = null;
  let status = null;
  let learned = null;
  let learnedSeq = 0;
  let learning = "";                                  // Id des Ausloesers, der gerade einlernt
  let saveTimer = null;
  let pollTimer = null;
  let watched = "";                                   // "protokoll|universum|ip": diese Quelle zeigt die Werte-Anzeige
  let recentSeq = 0;
  let builtLang = "";

  async function api(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leer */ }
      return { ok: res.ok && data.ok !== false, data };
    } catch (e) { return { ok: false, data: {} }; }
  }

  function saveSoon() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      const res = await api("POST", "/api/dmx-in/config", cfg);
      if (res.ok) { status = res.data.status; paintStatus(); }
    }, 600);
  }

  const newId = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-3);
  const input = (type, value, cls, attrs) => { const n = document.createElement("input"); n.type = type; n.value = value; if (cls) n.className = cls; Object.assign(n, attrs || {}); return n; };
  const switchBox = (checked, onChange, title) => {
    const label = el("label", "toggle-switch");
    const box = document.createElement("input");
    box.type = "checkbox"; box.checked = !!checked; if (title) box.title = title;
    box.addEventListener("change", () => onChange(box.checked));
    label.append(box, el("span", "toggle-switch__track"));
    return label;
  };
  const select = (options, value, onChange, cls) => {
    const s = document.createElement("select");
    s.className = "settings__select" + (cls ? " " + cls : "");
    options.forEach(([v, text]) => { const o = document.createElement("option"); o.value = v; o.textContent = text; s.appendChild(o); });
    s.value = value;
    s.addEventListener("change", () => onChange(s.value));
    return s;
  };
  const protocols = () => [["any", t("DMXIN_ANY")], ["artnet", "Art-Net"], ["sacn", "sACN"]];
  const delButton = (title, onClick) => {
    const b = el("button", "modal__button osc__del"); b.type = "button"; b.title = title; b.setAttribute("aria-label", title);
    if (typeof Icons !== "undefined") b.appendChild(Icons.svg("trash"));
    b.addEventListener("click", onClick);
    return b;
  };
  const section = (title, hint) => { const box = el("section", "dmxin__section"); box.appendChild(el("h3", "dmxin__h", title)); if (hint) box.appendChild(el("p", "dmxin__hint", hint)); return box; };

  // ---------------------------------------------------------------------------------------------- Zustand
  function paintStatus() {
    const box = $("dmxin-status");
    if (!box || !status) return;
    let text, cls = "";
    if (!cfg.enabled) text = t("DMXIN_STATUS_OFF");
    else {
      const l = status.listening || {};
      const parts = [];
      if (cfg.artnet) parts.push("Art-Net " + (l.artnet ? "✓" : "✗"));
      if (cfg.sacn) parts.push("sACN " + (l.sacn ? "✓" : "✗"));
      const errs = Object.values(status.errors || {});
      if (errs.length) { text = t("DMXIN_STATUS_ERROR", { error: errs.join("; ") }); cls = "osc__err"; }
      else { text = t("DMXIN_STATUS_ON", { parts: parts.join(", ") || "-" }); cls = "osc__ok"; }
      if (status.where === "server") text += " " + t("DMXIN_NO_MERGE");
    }
    box.textContent = text;
    box.className = "osc__status " + cls;
    paintSources();
  }

  function paintSources() {
    const box = $("dmxin-sources");
    if (!box || !status) return;
    box.textContent = "";
    const rows = status.sources || [];
    if (!rows.length) { box.appendChild(el("p", "dmxin__empty", cfg.enabled ? t("DMXIN_NO_SOURCES") : t("DMXIN_ENABLE_FIRST"))); paintViewer(null); return; }
    let watchedRow = null;
    rows.forEach((s) => {
      const key = s.protocol + "|" + s.universe + "|" + s.ip;
      const row = el("div", "dmxin__src" + (s.alive ? "" : " dmxin__src--dead") + (key === watched ? " dmxin__src--on" : ""));
      row.append(el("span", "dmxin__proto", s.protocol === "artnet" ? "Art-Net" : "sACN"), el("span", "dmxin__uni", t("DMXIN_UNIVERSE_N", { n: s.universe })),
                 el("span", "dmxin__from", (s.name ? s.name + " · " : "") + s.ip + (s.priority != null ? " · " + t("DMXIN_PRIO", { n: s.priority }) : "")),
                 el("span", "dmxin__rate", s.alive ? t("DMXIN_RATE", { n: s.pps, c: s.nonzero }) : t("DMXIN_GONE")));
      const view = el("button", "modal__button", t("DMXIN_VIEW")); view.type = "button";
      view.addEventListener("click", () => { watched = watched === key ? "" : key; paintSources(); });
      const fwd = el("button", "modal__button", t("DMXIN_FORWARD")); fwd.type = "button"; fwd.title = t("DMXIN_FORWARD_TIP");
      fwd.addEventListener("click", () => {
        cfg.merge.push({ id: newId(), enabled: true, name: "", protocol: s.protocol, universe: s.universe, target: s.universe >= 1 && s.universe <= 64 ? s.universe : 1, mode: "htp", first: 1, last: 512 });
        saveSoon(); renderLists();
        if (typeof _showToast === "function") _showToast(t("DMXIN_FORWARD_DONE", { n: s.universe }), "info", 3000, true);
      });
      row.append(view, fwd);
      box.appendChild(row);
      if (key === watched) watchedRow = s;
    });
    paintViewer(watchedRow);
  }

  function paintViewer(src) {
    const box = $("dmxin-viewer");
    if (!box) return;
    box.hidden = !src;
    if (!src) return;
    let canvas = box.querySelector("canvas");
    if (!canvas) {
      canvas = document.createElement("canvas"); canvas.width = 512; canvas.height = 128; canvas.className = "dmxin__canvas";
      canvas.addEventListener("mousemove", (e) => { const r = canvas.getBoundingClientRect(); const ch = Math.floor(((e.clientX - r.left) / r.width) * 32) + 32 * Math.floor(((e.clientY - r.top) / r.height) * 16) + 1; canvas.title = t("DMXIN_CHANNEL_N", { n: ch, v: canvas._v ? canvas._v[ch - 1] || 0 : 0 }); });
      box.appendChild(canvas);
    }
    const bytes = src.data ? Uint8Array.from(atob(src.data), (c) => c.charCodeAt(0)) : new Uint8Array(0);
    canvas._v = bytes;
    const g = canvas.getContext("2d");
    g.fillStyle = "#101012"; g.fillRect(0, 0, 512, 128);
    for (let i = 0; i < 512; i++) {
      const v = bytes[i] || 0, x = (i % 32) * 16, y = Math.floor(i / 32) * 8;
      g.fillStyle = v ? `hsl(${40 - v / 255 * 30}, 90%, ${12 + v / 255 * 50}%)` : "#1a1a1d";
      g.fillRect(x + 1, y + 1, 14, 6);
    }
  }

  function paintRecent(items) {
    const box = $("dmxin-recent");
    if (!box) return;
    for (const m of items) { const row = el("div", "osc__row"); row.append(el("span", "osc__t", m.t), el("code", "osc__a", m.text)); box.prepend(row); }
    while (box.children.length > 30) box.lastChild.remove();
    $("dmxin-recent-empty").hidden = box.children.length > 0;
  }

  // ---------------------------------------------------------------------------------------------- Listen
  function mergeRow(m) {
    const row = el("div", "dmxin__row" + (m.enabled ? "" : " osc__row--off"));
    const on = switchBox(m.enabled, (v) => { m.enabled = v; row.classList.toggle("osc__row--off", !v); saveSoon(); }, t("DMXIN_ENABLED"));
    const proto = select(protocols(), m.protocol, (v) => { m.protocol = v; saveSoon(); });
    const uni = input("number", m.universe, "osc__num", { min: 0, max: 63999, title: t("DMXIN_IN_UNIVERSE") });
    uni.addEventListener("change", () => { m.universe = Math.max(0, Math.min(63999, parseInt(uni.value, 10) || 0)); saveSoon(); });
    const target = input("number", m.target, "osc__num", { min: 1, max: 64, title: t("DMXIN_OUT_UNIVERSE") });
    target.addEventListener("change", () => { m.target = Math.max(1, Math.min(64, parseInt(target.value, 10) || 1)); saveSoon(); });
    const mode = select([["htp", t("DMXIN_MODE_HTP")], ["replace", t("DMXIN_MODE_REPLACE")]], m.mode, (v) => { m.mode = v; saveSoon(); });
    const first = input("number", m.first, "osc__num", { min: 1, max: 512, title: t("DMXIN_FIRST") });
    const last = input("number", m.last, "osc__num", { min: 1, max: 512, title: t("DMXIN_LAST") });
    first.addEventListener("change", () => { m.first = Math.max(1, Math.min(512, parseInt(first.value, 10) || 1)); saveSoon(); });
    last.addEventListener("change", () => { m.last = Math.max(1, Math.min(512, parseInt(last.value, 10) || 512)); saveSoon(); });
    const del = delButton(t("DMXIN_DELETE"), async () => {
      if (typeof _askDelete === "function" && !(await _askDelete("other", { title: t("DMXIN_DELETE_MERGE_TITLE"), body: t("DMXIN_DELETE_MERGE_BODY", { a: m.universe, b: m.target }), confirmKey: "FX_DELETE_CONFIRM" }))) return;
      cfg.merge = cfg.merge.filter((x) => x.id !== m.id); saveSoon(); renderLists();
    });
    row.append(on, proto, el("span", "dmxin__lbl", t("DMXIN_IN_UNIVERSE")), uni, el("span", "dmxin__arrow", "→"), el("span", "dmxin__lbl", t("DMXIN_OUT_UNIVERSE")), target, mode,
               el("span", "dmxin__lbl", t("DMXIN_CHANNELS")), first, el("span", "", "–"), last, del);
    return row;
  }

  function triggerRow(tr) {
    const row = el("div", "dmxin__row dmxin__row--trig" + (tr.enabled ? "" : " osc__row--off"));
    const on = switchBox(tr.enabled, (v) => { tr.enabled = v; row.classList.toggle("osc__row--off", !v); saveSoon(); }, t("DMXIN_ENABLED"));
    const name = input("text", tr.name, "osc__addr", { placeholder: t("DMXIN_NAME_PH"), maxLength: 60 });
    name.addEventListener("input", () => { tr.name = name.value; saveSoon(); });
    const proto = select(protocols(), tr.protocol, (v) => { tr.protocol = v; saveSoon(); });
    const uni = input("number", tr.universe, "osc__num", { min: 0, max: 63999, title: t("DMXIN_IN_UNIVERSE") });
    const ch = input("number", tr.channel, "osc__num", { min: 1, max: 512, title: t("DMXIN_CHANNEL") });
    uni.addEventListener("change", () => { tr.universe = Math.max(0, Math.min(63999, parseInt(uni.value, 10) || 0)); saveSoon(); });
    ch.addEventListener("change", () => { tr.channel = Math.max(1, Math.min(512, parseInt(ch.value, 10) || 1)); saveSoon(); });
    const learn = el("button", "modal__button osc__learn", learning === tr.id ? t("DMXIN_LEARNING") : t("DMXIN_LEARN")); learn.type = "button"; learn.title = t("DMXIN_LEARN_HINT");
    learn.addEventListener("click", async () => {
      if (learning === tr.id) { learning = ""; await api("POST", "/api/dmx-in/learn", { on: false }); renderLists(); return; }
      clearTimeout(saveTimer); await api("POST", "/api/dmx-in/config", cfg);                  // der Empfang muss die Universen kennen
      learning = tr.id; learnedSeq = learned ? learned.n : 0; await api("POST", "/api/dmx-in/learn", { on: true }); renderLists();
    });
    const kind = select([["button", t("DMXIN_KIND_BUTTON")], ["level", t("DMXIN_KIND_LEVEL")]], tr.kind, (v) => { tr.kind = v; saveSoon(); renderLists(); });
    const thr = input("number", tr.threshold, "osc__num", { min: 1, max: 255, title: t("DMXIN_THRESHOLD") });
    thr.addEventListener("change", () => { tr.threshold = Math.max(1, Math.min(255, parseInt(thr.value, 10) || 128)); saveSoon(); });
    const cmd = input("text", tr.command, "osc__cmd", { placeholder: tr.kind === "level" ? t("DMXIN_CMD_LEVEL_PH") : t("DMXIN_CMD_ON_PH"), maxLength: 1000, spellcheck: false, autocomplete: "off" });
    cmd.setAttribute("list", "dmxin-commands");
    cmd.addEventListener("input", () => { tr.command = cmd.value; saveSoon(); });
    const del = delButton(t("DMXIN_DELETE"), async () => {
      const empty = !String(tr.command || "").trim() && !String(tr.name || "").trim();
      if (!empty && typeof _askDelete === "function" && !(await _askDelete("other", { title: t("DMXIN_DELETE_TRIG_TITLE"), body: t("DMXIN_DELETE_TRIG_BODY", { name: tr.name || ("U" + tr.universe + "." + tr.channel) }), confirmKey: "FX_DELETE_CONFIRM" }))) return;
      cfg.triggers = cfg.triggers.filter((x) => x.id !== tr.id); saveSoon(); renderLists();
    });
    const top = el("div", "dmxin__line");
    top.append(on, name, proto, el("span", "dmxin__lbl", t("DMXIN_IN_UNIVERSE")), uni, el("span", "dmxin__lbl", t("DMXIN_CHANNEL")), ch, learn, del);
    const bottom = el("div", "dmxin__line");
    bottom.append(kind);
    if (tr.kind === "button") {
      const off = input("text", tr.command_off, "osc__cmd", { placeholder: t("DMXIN_CMD_OFF_PH"), maxLength: 1000, spellcheck: false, autocomplete: "off" });
      off.setAttribute("list", "dmxin-commands");
      off.addEventListener("input", () => { tr.command_off = off.value; saveSoon(); });
      bottom.append(el("span", "dmxin__lbl", t("DMXIN_THRESHOLD")), thr, cmd, off);
    } else {
      const min = input("number", tr.min, "osc__num", { step: "any", title: t("OSC_MIN") }), max = input("number", tr.max, "osc__num", { step: "any", title: t("OSC_MAX") });
      min.addEventListener("change", () => { tr.min = parseFloat(min.value) || 0; saveSoon(); });
      max.addEventListener("change", () => { tr.max = parseFloat(max.value) || 0; saveSoon(); });
      bottom.append(cmd, el("span", "dmxin__lbl", t("DMXIN_RANGE")), min, el("span", "", "–"), max);
    }
    row.append(top, bottom);
    return row;
  }

  function renderLists() {
    const m = $("dmxin-merge"), tr = $("dmxin-triggers");
    if (!m || !tr || !cfg) return;
    m.textContent = ""; tr.textContent = "";
    cfg.merge.forEach((x) => m.appendChild(mergeRow(x)));
    cfg.triggers.forEach((x) => tr.appendChild(triggerRow(x)));
    $("dmxin-merge-empty").hidden = cfg.merge.length > 0;
    $("dmxin-triggers-empty").hidden = cfg.triggers.length > 0;
  }

  // ---------------------------------------------------------------------------------------------- Aufbau
  function build() {
    builtLang = typeof translator !== "undefined" ? translator.language : "";
    const body = $("dmxin-body");
    body.textContent = "";
    body.appendChild(el("p", "osc__intro", t("DMXIN_INTRO")));
    body.appendChild(el("p", "osc__warning", t("DMXIN_WARNING")));
    const grid = el("div", "osc__grid");
    const add = (label, node) => { grid.append(el("label", "", label), node); };
    add(t("DMXIN_ON"), switchBox(cfg.enabled, (v) => { cfg.enabled = v; saveSoon(); paintStatus(); }));
    const protoBox = el("div", "dmxin__protos");
    protoBox.append(switchBox(cfg.artnet, (v) => { cfg.artnet = v; saveSoon(); }), el("span", "", "Art-Net (UDP 6454)"), switchBox(cfg.sacn, (v) => { cfg.sacn = v; saveSoon(); }), el("span", "", "sACN (UDP 5568)"));
    add(t("DMXIN_PROTOCOLS"), protoBox);
    const st = el("div", "osc__status"); st.id = "dmxin-status"; grid.append(el("span"), st);
    add(t("DMXIN_ANNOUNCE"), switchBox(cfg.announce !== false, (v) => { cfg.announce = v; saveSoon(); }));
    grid.append(el("span"), el("p", "osc__hint", t("DMXIN_ANNOUNCE_HINT")));
    const fw = el("div", "dmxin__fw"); fw.id = "dmxin-fw"; fw.hidden = true;
    const fwText = el("span", "", ""); fwText.id = "dmxin-fw-text";
    const fwAdd = el("button", "modal__button", t("DMXIN_FW_ADD")); fwAdd.type = "button"; fwAdd.id = "dmxin-fw-add";
    fwAdd.addEventListener("click", async () => {
      fwAdd.disabled = true;
      await api("POST", "/api/system/firewall", { enabled: true });                    // Windows fragt am Hauptrechner um Erlaubnis
      fwAdd.disabled = false;
      loadFirewall();
    });
    fw.append(fwText, fwAdd);
    grid.append(el("span"), fw);
    const allow = input("text", (cfg.allow || []).join(", "), "", { placeholder: t("DMXIN_ALLOW_PH"), autocomplete: "off", spellcheck: false });
    allow.addEventListener("change", () => { cfg.allow = allow.value.split(/[,;\s]+/).filter(Boolean); saveSoon(); });
    add(t("DMXIN_ALLOW"), allow);
    const bind = input("text", cfg.bind || "", "", { placeholder: t("DMXIN_BIND_PH"), autocomplete: "off", spellcheck: false });
    bind.addEventListener("change", () => { cfg.bind = bind.value.trim(); saveSoon(); });
    add(t("DMXIN_BIND"), bind);
    const timeout = input("number", cfg.timeout, "", { min: 0.5, max: 30, step: 0.5 });
    timeout.addEventListener("change", () => { cfg.timeout = Math.max(0.5, Math.min(30, parseFloat(timeout.value) || 3)); saveSoon(); });
    add(t("DMXIN_TIMEOUT"), timeout);
    grid.append(el("span"), el("p", "osc__hint", t("DMXIN_TIMEOUT_HINT")));
    body.appendChild(grid);

    const src = section(t("DMXIN_SOURCES"), t("DMXIN_SOURCES_HINT"));
    const sbox = el("div", "dmxin__srclist"); sbox.id = "dmxin-sources"; src.appendChild(sbox);
    const viewer = el("div", "dmxin__viewer"); viewer.id = "dmxin-viewer"; viewer.hidden = true; src.appendChild(viewer);
    body.appendChild(src);

    const mg = section(t("DMXIN_MERGE"), t("DMXIN_MERGE_HINT"));
    const mlist = el("div", "dmxin__list"); mlist.id = "dmxin-merge"; mg.appendChild(mlist);
    const mEmpty = el("p", "dmxin__empty", t("DMXIN_MERGE_EMPTY")); mEmpty.id = "dmxin-merge-empty"; mg.appendChild(mEmpty);
    const mAdd = el("button", "modal__button dmxin__edit", "+ " + t("DMXIN_ADD")); mAdd.type = "button";
    mAdd.addEventListener("click", () => { cfg.merge.push({ id: newId(), enabled: true, name: "", protocol: "any", universe: 1, target: 1, mode: "htp", first: 1, last: 512 }); saveSoon(); renderLists(); });
    mg.appendChild(mAdd);
    body.appendChild(mg);

    const tg = section(t("DMXIN_TRIGGERS"), t("DMXIN_TRIGGERS_HINT"));
    const tlist = el("div", "dmxin__list"); tlist.id = "dmxin-triggers"; tg.appendChild(tlist);
    const tEmpty = el("p", "dmxin__empty", t("DMXIN_TRIGGERS_EMPTY")); tEmpty.id = "dmxin-triggers-empty"; tg.appendChild(tEmpty);
    const tAdd = el("button", "modal__button dmxin__edit", "+ " + t("DMXIN_ADD")); tAdd.type = "button";
    tAdd.addEventListener("click", () => { cfg.triggers.push({ id: newId(), enabled: true, name: "", protocol: "any", universe: 1, channel: 1, kind: "button", threshold: 128, command: "", command_off: "", min: 0, max: 100, log: false }); saveSoon(); renderLists(); });
    tg.appendChild(tAdd);
    const dl = document.createElement("datalist"); dl.id = "dmxin-commands"; COMMANDS.forEach((c) => { const o = document.createElement("option"); o.value = c; dl.appendChild(o); }); tg.appendChild(dl);
    body.appendChild(tg);

    const rc = section(t("DMXIN_RECENT"));
    const rbox = el("div", "osc__monitor"); rbox.id = "dmxin-recent"; rc.appendChild(rbox);
    const rEmpty = el("p", "dmxin__empty", t("DMXIN_RECENT_EMPTY")); rEmpty.id = "dmxin-recent-empty"; rc.appendChild(rEmpty);
    body.appendChild(rc);
    renderLists();
    paintStatus();
  }

  async function poll() {
    if (!Modal.isOpen(MODAL)) { clearInterval(pollTimer); pollTimer = null; api("POST", "/api/dmx-in/learn", { on: false }); learning = ""; return; }
    const res = await api("GET", "/api/dmx-in" + (watched ? "?watch=1" : ""));
    if (!res.ok) return;
    status = res.data.status;
    const items = (res.data.recent || []).filter((m) => m.n > recentSeq);
    if (items.length) { recentSeq = Math.max(recentSeq, ...items.map((m) => m.n)); paintRecent(items); }
    const lr = res.data.learned;
    if (lr && lr.n !== (learned && learned.n)) {
      learned = lr;
      const tr = learning && cfg.triggers.find((x) => x.id === learning);
      if (tr) { tr.protocol = lr.protocol; tr.universe = lr.universe; tr.channel = lr.channel; learning = ""; saveSoon(); renderLists(); }
    }
    paintStatus();
  }

  /** Windows-Firewall: gibt es eine Regel fuer OpenCue (sonst blockiert Windows eingehendes Art-Net / sACN)? Nur unter Windows sichtbar. */
  async function loadFirewall() {
    const res = await api("GET", "/api/system");
    const fw = $("dmxin-fw");
    if (!fw) return;
    const info = res.ok && res.data.firewall;
    fw.hidden = !(info && info.available);
    if (fw.hidden) return;
    $("dmxin-fw-text").textContent = t(info.exists ? "DMXIN_FW_OK" : "DMXIN_FW_NONE") + (info.exists ? "" : " " + t("SYS_FIREWALL_AT_CONSOLE"));
    $("dmxin-fw-text").className = info.exists ? "osc__ok" : "osc__err";
    $("dmxin-fw-add").hidden = !!info.exists;
  }

  async function open() {
    const res = await api("GET", "/api/dmx-in");
    if (!res.ok) return;
    cfg = res.data.config; status = res.data.status; learned = res.data.learned; learning = ""; watched = ""; recentSeq = (res.data.recent || []).reduce((a, m) => Math.max(a, m.n), 0);
    build();
    loadFirewall();
    Modal.open(MODAL);
    clearInterval(pollTimer);
    pollTimer = setInterval(poll, 500);
  }

  document.addEventListener("click", (e) => {
    if (e.target.closest('[data-action="open-dmx-in-modal"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); open(); }
  });
  document.addEventListener("i18n-applied", () => { if (cfg && typeof Modal !== "undefined" && Modal.isOpen(MODAL) && typeof translator !== "undefined" && translator.language !== builtLang) build(); });      // nur bei einem Sprachwechsel neu aufbauen (jeder andere Dialog ruft translator.apply() auf)
  window.OCDmxIn = { open };
})();

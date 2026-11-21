// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* OSC-Dialog (Menue "Steuerung" -> "OSC ..."): Empfangen und Senden von OSC-Nachrichten (app/osc.py, GET/POST /api/osc*).
 * Oben: ein-/ausschalten, Port, Zustand; Absender-Liste, "beliebige Befehle", Ziel zum Senden; die Tabelle der Zuordnungen (Adresse -> Befehl, "Einlernen" nimmt die naechste
 * eingehende Adresse); darunter die eingebauten Adressen und der Monitor der letzten Nachrichten (fragt einmal je Sekunde nach, solange der Dialog offen ist).
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
  const MODAL = "osc";
  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);

  let cfg = null;
  let status = null;
  let builtin = [];
  let lastSeq = 0;
  let saveTimer = null;
  let pollTimer = null;
  const FEEDBACK = [["cuelist", "/cuelist", "OSC_FB_I_CUELIST"], ["cue", "/cue", "OSC_FB_I_CUE"], ["cuename", "/cuename", "OSC_FB_I_CUENAME"], ["state", "/state", "OSC_FB_I_STATE"],
    ["fader", "/fader", "OSC_FB_I_FADER"], ["master", "/master", "OSC_FB_I_MASTER"], ["blackout", "/blackout", "OSC_FB_I_BLACKOUT"], ["leds", "/cue/<number>", "OSC_FB_I_LEDS"]];
  let learning = null;                                 // { id, seq }: die naechste Nachricht mit hoeherer Nummer fuellt die Adresse dieser Zuordnung

  async function api(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leer */ }
      return { ok: res.ok && data.ok !== false, data };
    } catch (e) {
      return { ok: false, data: {} };
    }
  }

  function saveSoon() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      const res = await api("POST", "/api/osc/config", cfg);
      if (res.ok) { status = res.data.status; paintStatus(); }
    }, 500);
  }

  function paintStatus() {
    const box = $("osc-status");
    if (!box || !status) return;
    let text, cls = "";
    if (!cfg.enabled) text = t("OSC_STATUS_OFF");
    else if (status.listening) { text = t("OSC_STATUS_ON", { addresses: (status.addresses.length ? status.addresses : ["127.0.0.1"]).map((a) => a + ":" + status.port).join(", ") }); cls = "osc__ok"; }
    else { text = t("OSC_STATUS_ERROR", { error: status.error || "?" }); cls = "osc__err"; }
    box.textContent = text;
    box.className = "osc__status " + cls;
    const fbBox = $("osc-fb-status");
    if (fbBox) {
      const f = status.feedback || {};
      fbBox.hidden = !cfg.feedback || !cfg.feedback.enabled;
      fbBox.textContent = f.active ? (f.targets && f.targets.length ? t("OSC_FB_STATUS", { targets: f.targets.join(", ") }) : t("OSC_FB_NO_TARGET")) : "";
      fbBox.className = "osc__status " + (f.targets && f.targets.length ? "osc__ok" : "");
    }
  }

  const input = (type, value, cls, attrs) => {
    const n = document.createElement("input");
    n.type = type; n.value = value; if (cls) n.className = cls;
    Object.assign(n, attrs || {});
    return n;
  };
  const switchBox = (checked, onChange, title) => {
    const label = el("label", "toggle-switch");
    const box = document.createElement("input");
    box.type = "checkbox"; box.checked = !!checked; if (title) box.title = title;
    box.addEventListener("change", () => onChange(box.checked));
    label.append(box, el("span", "toggle-switch__track"));
    return label;
  };

  function buildRow(b) {
    const row = el("div", "osc__row" + (b.enabled ? "" : " osc__row--off"));
    row.dataset.id = b.id;
    const on = switchBox(b.enabled, (v) => { b.enabled = v; row.classList.toggle("osc__row--off", !v); saveSoon(); }, t("OSC_ENABLED"));
    const address = input("text", b.address, "osc__addr", { placeholder: "/my/button", maxLength: 120, spellcheck: false });
    address.addEventListener("input", () => { b.address = address.value; saveSoon(); });
    const learn = el("button", "modal__button osc__learn", t("OSC_LEARN"));
    learn.type = "button";
    learn.title = t("OSC_LEARN_HINT");
    learn.addEventListener("click", () => {
      if (learning && learning.id === b.id) { learning = null; learn.textContent = t("OSC_LEARN"); return; }
      learning = { id: b.id, seq: lastSeq };
      document.querySelectorAll(".osc__learn").forEach((x) => { x.textContent = t("OSC_LEARN"); });
      learn.textContent = t("OSC_LEARNING");
    });
    const command = input("text", b.command, "osc__cmd", { placeholder: t("OSC_COMMAND_PH"), maxLength: 1000, spellcheck: false, autocomplete: "off" });
    command.addEventListener("input", () => { b.command = command.value; saveSoon(); });
    const mode = document.createElement("select");
    mode.className = "settings__select osc__mode";
    for (const [value, key] of [["press", "OSC_MODE_PRESS"], ["always", "OSC_MODE_ALWAYS"]]) { const o = document.createElement("option"); o.value = value; o.textContent = t(key); mode.appendChild(o); }
    mode.value = b.mode;
    mode.addEventListener("change", () => { b.mode = mode.value; saveSoon(); });
    const scale = el("span", "osc__scale");
    const scaleOn = switchBox(b.scale, (v) => { b.scale = v; min.disabled = max.disabled = !v; saveSoon(); }, t("OSC_SCALE_HINT"));
    const min = input("number", b.min, "osc__num", { step: "any", title: t("OSC_MIN") });
    const max = input("number", b.max, "osc__num", { step: "any", title: t("OSC_MAX") });
    min.disabled = max.disabled = !b.scale;
    min.addEventListener("change", () => { b.min = parseFloat(min.value) || 0; saveSoon(); });
    max.addEventListener("change", () => { b.max = parseFloat(max.value) || 0; saveSoon(); });
    scale.append(el("span", "osc__scale-label", t("OSC_SCALE")), scaleOn, min, el("span", "", "–"), max);
    const log = switchBox(b.log, (v) => { b.log = v; saveSoon(); }, t("OSC_LOG_HINT"));
    const logWrap = el("span", "osc__log");
    logWrap.append(el("span", "osc__scale-label", t("OSC_LOG")), log);
    const del = el("button", "modal__button osc__del");
    del.type = "button";
    del.title = t("OSC_DELETE");
    del.setAttribute("aria-label", t("OSC_DELETE"));
    if (typeof Icons !== "undefined") del.appendChild(Icons.svg("trash"));
    del.addEventListener("click", async () => {
      const empty = !String(b.address || "").trim() && !String(b.command || "").trim();                 // eine frische, leere Zeile ohne Rueckfrage entfernen
      if (!empty && typeof _askDelete === "function" && !(await _askDelete("other", { title: t("OSC_DELETE_TITLE"), body: t("OSC_DELETE_BODY", { address: b.address || "?", command: b.command || "-" }), confirmKey: "OSC_DELETE_OK" }))) return;
      cfg.bindings = cfg.bindings.filter((x) => x.id !== b.id);
      saveSoon();
      render();
    });
    const top = el("div", "osc__line");
    top.append(on, address, learn, command, del);
    const bottom = el("div", "osc__line osc__line--opts");
    bottom.append(mode, scale, logWrap);
    row.append(top, bottom);
    return row;
  }

  function render() {
    if (!cfg) return;
    const local = isLocal();
    $("osc-enabled").checked = !!cfg.enabled;
    $("osc-port").value = cfg.port;
    $("osc-allow").value = (cfg.allow || []).join(", ");
    $("osc-raw").checked = !!cfg.raw;
    $("osc-send-host").value = cfg.send.host || "";
    $("osc-send-port").value = cfg.send.port;
    $("osc-readonly").hidden = true;
    const fb = cfg.feedback || (cfg.feedback = { enabled: false, senders: true, off: [] });
    $("osc-fb-on").checked = !!fb.enabled;
    $("osc-fb-senders").checked = fb.senders !== false;
    ["osc-enabled", "osc-port", "osc-allow", "osc-raw", "osc-send-host", "osc-send-port", "osc-send-test", "osc-add", "osc-fb-on", "osc-fb-senders", "osc-fb-now"].forEach((id) => { const n = $(id); if (n) n.disabled = false; });
    const list = $("osc-list");
    list.textContent = "";
    $("osc-empty").hidden = cfg.bindings.length > 0;
    cfg.bindings.forEach((b) => list.appendChild(buildRow(b)));
    if (!local) list.querySelectorAll("input, select, button").forEach((n) => { n.disabled = true; });
    const builtinBox = $("osc-builtin");
    builtinBox.textContent = "";
    const bi = cfg.builtin || (cfg.builtin = { enabled: true, prefix: "/opencue", off: [] });
    const head = el("div", "osc__b osc__b--head");
    head.append(switchBox(bi.enabled, (v) => { bi.enabled = v; saveSoon(); render(); }, t("OSC_BUILTIN_ON")), el("span", "", t("OSC_BUILTIN_ON")));
    const prefix = input("text", bi.prefix, "osc__prefix", { maxLength: 60, spellcheck: false, placeholder: "/opencue", title: t("OSC_BUILTIN_PREFIX_HINT") });
    prefix.id = "osc-builtin-prefix";
    prefix.addEventListener("change", () => {
      const v = prefix.value.trim().replace(/\/+$/, "");
      if (/^\/[A-Za-z0-9_-]{1,40}(\/[A-Za-z0-9_-]{1,40}){0,3}$/.test(v)) { bi.prefix = v; saveSoon(); setTimeout(() => api("GET", "/api/osc").then((r) => { if (r.ok) { builtin = r.data.builtin || builtin; render(); } }), 700); }
      else { prefix.value = bi.prefix; prefix.classList.add("sch__bad"); setTimeout(() => prefix.classList.remove("sch__bad"), 900); }
    });
    head.append(el("span", "osc__scale-label", t("OSC_BUILTIN_PREFIX")), prefix);
    builtinBox.appendChild(head);
    builtin.forEach((b) => {
      const row = el("div", "osc__b" + (bi.enabled && !(bi.off || []).includes(b.name) ? "" : " osc__row--off"));
      const sw = switchBox(!(bi.off || []).includes(b.name), (v) => { bi.off = (bi.off || []).filter((n) => n !== b.name); if (!v) bi.off.push(b.name); saveSoon(); render(); }, t("OSC_ENABLED"));
      row.append(sw, el("code", "", b.address), el("span", "", b.about));
      builtinBox.appendChild(row);
    });
    if (!local) builtinBox.querySelectorAll("input").forEach((n) => { n.disabled = true; });
    const fbBox = $("osc-fb-items");
    fbBox.textContent = "";
    FEEDBACK.forEach(([name, suffix, key]) => {
      const row = el("div", "osc__b" + (fb.enabled && !(fb.off || []).includes(name) ? "" : " osc__row--off"));
      const sw = switchBox(!(fb.off || []).includes(name), (v) => { fb.off = (fb.off || []).filter((n) => n !== name); if (!v) fb.off.push(name); saveSoon(); render(); }, t("OSC_ENABLED"));
      row.append(sw, el("code", "", ((cfg.builtin && cfg.builtin.prefix) || "/opencue") + suffix), el("span", "", t(key)));
      fbBox.appendChild(row);
    });
    if (!local) fbBox.querySelectorAll("input").forEach((n) => { n.disabled = true; });
    paintStatus();
  }

  function paintMonitor(items) {
    const box = $("osc-monitor");
    if (!box) return;
    for (const m of items) {
      const row = el("div", "osc__msg");
      const time = new Date(m.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      row.append(el("span", "osc__t", time), el("span", "osc__from", m.from), el("code", "osc__a", m.address + (m.args.length ? " " + m.args.join(" ") : "")), el("span", "osc__r", m.result));
      box.prepend(row);
    }
    while (box.children.length > 30) box.lastChild.remove();
    $("osc-monitor-empty").hidden = box.children.length > 0;
  }

  async function poll() {
    if (!Modal.isOpen(MODAL)) { clearInterval(pollTimer); pollTimer = null; return; }
    const res = await api("GET", "/api/osc?since=" + lastSeq);
    if (!res.ok) return;
    status = res.data.status;
    const items = res.data.recent || [];
    if (items.length) {
      lastSeq = Math.max(lastSeq, ...items.map((m) => m.n));
      paintMonitor(items);
      if (learning) {
        const hit = items.find((m) => m.n > learning.seq && !m.result.startsWith("blocked"));
        const b = hit && cfg.bindings.find((x) => x.id === learning.id);
        if (b) { b.address = hit.address; learning = null; saveSoon(); render(); }
      }
    }
    paintStatus();
  }

  async function open() {
    const res = await api("GET", "/api/osc");
    if (!res.ok) return;
    cfg = res.data.config;
    status = res.data.status;
    builtin = res.data.builtin || [];
    lastSeq = status.seq || 0;
    learning = null;
    $("osc-monitor").textContent = "";
    $("osc-monitor-empty").hidden = false;
    Modal.open(MODAL);
    render();
    clearInterval(pollTimer);
    pollTimer = setInterval(poll, 1000);
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="osc"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("osc-enabled").addEventListener("change", (e) => { cfg.enabled = e.target.checked; saveSoon(); paintStatus(); });
    $("osc-port").addEventListener("change", (e) => { cfg.port = parseInt(e.target.value, 10) || 9000; saveSoon(); });
    $("osc-allow").addEventListener("change", (e) => { cfg.allow = e.target.value.split(/[,;\s]+/).filter(Boolean); saveSoon(); });
    $("osc-raw").addEventListener("change", (e) => { cfg.raw = e.target.checked; saveSoon(); });
    $("osc-fb-on").addEventListener("change", (e) => { cfg.feedback.enabled = e.target.checked; saveSoon(); render(); });
    $("osc-fb-senders").addEventListener("change", (e) => { cfg.feedback.senders = e.target.checked; saveSoon(); });
    $("osc-fb-now").addEventListener("click", async () => {
      clearTimeout(saveTimer);
      await api("POST", "/api/osc/config", cfg);
      const res = await api("POST", "/api/osc/feedback/resend");
      if (typeof _showToast === "function") _showToast(res.ok ? t("OSC_FB_NOW_DONE") : t("OSC_SEND_FAILED"), res.ok ? "info" : "warn", 3500);
    });
    $("osc-send-host").addEventListener("change", (e) => { cfg.send.host = e.target.value.trim(); saveSoon(); });
    $("osc-send-port").addEventListener("change", (e) => { cfg.send.port = parseInt(e.target.value, 10) || 9001; saveSoon(); });
    $("osc-add").addEventListener("click", () => {
      cfg.bindings.push({ id: Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-3), enabled: true, address: "", command: "", mode: "press", scale: true, min: 0, max: 100, log: false });
      render();
      const rows = document.querySelectorAll("#osc-list .osc__row");
      const last = rows[rows.length - 1];
      if (last) { last.scrollIntoView({ block: "nearest" }); const a = last.querySelector(".osc__addr"); if (a) a.focus(); }
    });
    $("osc-send-test").addEventListener("click", async () => {
      clearTimeout(saveTimer);
      await api("POST", "/api/osc/config", cfg);
      const res = await api("POST", "/api/osc/send", { address: "/opencue/test", args: ["hello", 1] });
      if (typeof _showToast === "function") _showToast(res.ok ? res.data.message : (res.data.message || t("OSC_SEND_FAILED")), res.ok ? "info" : "warn", 4500);
    });
  }

  document.addEventListener("click", (e) => {
    if (e.target.closest('[data-action="open-osc-modal"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); bind(); open(); }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();

  window.OCOsc = { open };
})();

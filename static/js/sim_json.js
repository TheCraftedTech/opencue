// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* 3D-Buehne als JSON bearbeiten ("JSON"-Knopf im 3D-Panel, Menue Bibliothek): die Arbeitskopie der Buehne (Raum, Koerper, Scheinwerfer-Positionen) als Text, von Hand aenderbar.
 * Damit lassen sich viele Dinge auf einmal setzen, kopieren und genau ausrichten, ohne jedes einzeln zu ziehen. "Pruefen" aendert nichts und zeigt, was uebernommen wuerde;
 * "Uebernehmen" wirkt wie eine Aenderung im Panel (Stern an der Buehne, danach wie gewohnt speichern). Server: app/sim_stages.py (GET/POST /api/sim-stage/json). Einheit Meter / Grad, Z nach oben;
 * die Scheinwerfer stehen unter ihrer Nummer (FID). */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const $ = (id) => document.getElementById(id);
  const MODAL = "sim-json";
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 3500); };

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

  function setStatus(text, kind) {
    const box = $("simjson-status");
    box.textContent = text;
    box.className = "simjson__status" + (kind ? " simjson__status--" + kind : "");
  }

  function jumpTo(line, column) {
    const area = $("simjson-text");
    const lines = area.value.split("\n");
    let offset = 0;
    for (let i = 0; i < Math.min(line - 1, lines.length); i += 1) offset += lines[i].length + 1;
    offset += Math.max(0, (column || 1) - 1);
    area.focus();
    area.setSelectionRange(offset, Math.min(offset + 1, area.value.length));
    const lineHeight = parseFloat(getComputedStyle(area).lineHeight) || 16;
    area.scrollTop = Math.max(0, (line - 4) * lineHeight);
  }

  function reportText(r) {
    const parts = [];
    if (r.objects_in) parts.push(t("SIMJSON_OBJECTS", { kept: r.objects, total: r.objects_in }));
    else parts.push(t("SIMJSON_OBJECTS_N", { n: r.objects }));
    if (r.layout_in) parts.push(t("SIMJSON_LAYOUT", { kept: r.layout, total: r.layout_in }));
    if (r.unknown && r.unknown.length) parts.push(t("SIMJSON_UNKNOWN", { list: r.unknown.join(", ") }));
    return parts.join("  ·  ");
  }

  async function run(apply) {
    const res = await api("POST", "/api/sim-stage/json", { text: $("simjson-text").value, apply });
    if (!res.ok) {
      if (res.data.error === "invalid_json") {
        setStatus(t("SIMJSON_SYNTAX", { line: res.data.line, column: res.data.column, message: res.data.message }), "bad");
        jumpTo(res.data.line, res.data.column);
      } else if (res.data.error === "too_big") setStatus(t("SIMJSON_TOO_BIG"), "bad");
      else setStatus(t("SIMJSON_FAILED"), "bad");
      return false;
    }
    const r = res.data.report;
    const hint = (r.objects_in && r.objects < r.objects_in) || (r.layout_in && r.layout < r.layout_in) || (r.unknown && r.unknown.length);
    setStatus((apply ? t("SIMJSON_APPLIED") + "  " : t("SIMJSON_CHECKED") + "  ") + reportText(r), hint ? "warn" : "ok");
    if (apply) { toast(t("SIMJSON_APPLIED")); await load(false); }
    return true;
  }

  function format() {
    try {
      $("simjson-text").value = JSON.stringify(JSON.parse($("simjson-text").value), null, 2);
      setStatus(t("SIMJSON_FORMATTED"), "ok");
    } catch (e) {
      run(false);                                                      // der Server nennt Zeile und Spalte
    }
  }

  function fillLegend() {
    const box = $("simjson-legend");
    box.textContent = "";
    const fixtures = typeof _fixturesFromGlobal === "function" ? Object.values(_fixturesFromGlobal()) : [];
    fixtures.sort((a, b) => (a.fid || 0) - (b.fid || 0)).forEach((fx) => {
      const line = document.createElement("div");
      line.textContent = (fx.fid || "?") + "  –  " + fx.name;
      box.appendChild(line);
    });
  }

  async function load(announce) {
    const res = await api("GET", "/api/sim-stage/json");
    if (!res.ok) { setStatus(t("SIMJSON_FAILED"), "bad"); return; }
    $("simjson-text").value = res.data.text;
    $("simjson-name").textContent = res.data.name || "";
    if (announce !== false) setStatus("", "");
    fillLegend();
  }

  async function open() {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    Modal.open(MODAL);
    await load(true);
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="sim-json"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("simjson-check").addEventListener("click", () => run(false));
    $("simjson-apply").addEventListener("click", () => run(true));
    $("simjson-format").addEventListener("click", format);
    $("simjson-reload").addEventListener("click", () => load(true));
    $("simjson-text").addEventListener("keydown", (e) => {
      if (e.key === "Tab" && !e.ctrlKey && !e.altKey) {              // Tab rueckt ein, statt das Feld zu verlassen
        e.preventDefault();
        const a = e.target;
        const start = a.selectionStart;
        a.value = a.value.slice(0, start) + "  " + a.value.slice(a.selectionEnd);
        a.selectionStart = a.selectionEnd = start + 2;
      }
    });
  }

  /** JSON-Ansicht fuer die Seitenleiste des 3D-Panels (Baumodus / Scheinwerfer): ersetzt dort die Werkzeuge (Koerper hinzufuegen, Liste, Eigenschaften), der Rest - Buehnenname, Rueckgaengig, Speichern - bleibt.
   *  Live: jede Aenderung im Text wird nach 300 ms geprueft und uebernommen (Syntaxfehler: nichts passiert, die Zeile wird genannt); was im 3D-Fenster geaendert wird, erscheint sofort im Text
   *  (Cursor und Scrollstand bleiben). */
  function createPanel() {
    const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
    const root = el("div", "sim3d__json");
    const bar = el("div", "sim3d__json-bar");
    const live = el("span", "sim3d__json-live", "● " + t("SIMJSON_LIVE_TAG"));
    const status = el("span", "sim3d__json-status");
    const tidy = el("button", "sim3d__btn sim3d__json-btn", t("SIMJSON_FORMAT"));
    tidy.type = "button";
    const area = el("textarea", "sim3d__json-text");
    area.spellcheck = false;
    area.setAttribute("wrap", "off");
    let timer = 0;
    let dirty = false;
    let visible = false;
    let sentText = "";                                                   // der Text, den der Server zuletzt von uns bekam bzw. uns gab
    const setStatus = (text, kind) => { status.textContent = text; status.className = "sim3d__json-status" + (kind ? " sim3d__json-status--" + kind : ""); };

    async function load() {
      const res = await api("GET", "/api/sim-stage/json");
      if (!res.ok || res.data.text === area.value) return;
      const { selectionStart, selectionEnd, scrollTop, scrollLeft } = area;      // Cursor und Scrollstand bleiben, wenn sich der Text von aussen aendert
      area.value = res.data.text;
      try { area.setSelectionRange(Math.min(selectionStart, area.value.length), Math.min(selectionEnd, area.value.length)); } catch (err) { /* nicht fokussiert */ }
      area.scrollTop = scrollTop;
      area.scrollLeft = scrollLeft;
      dirty = false;
    }
    async function push() {
      clearTimeout(timer);
      const text = area.value;
      const res = await api("POST", "/api/sim-stage/json", { text, apply: true });
      if (!res.ok) {
        if (res.data.error === "invalid_json") setStatus(t("SIMJSON_SYNTAX", { line: res.data.line, column: res.data.column, message: res.data.message }), "bad");
        else setStatus(t("SIMJSON_FAILED"), "bad");
        return false;
      }
      if (area.value === text) dirty = false;
      const r = res.data.report;
      setStatus(reportText(r), (r.objects_in && r.objects < r.objects_in) || (r.layout_in && r.layout < r.layout_in) || (r.unknown && r.unknown.length) ? "warn" : "ok");
      return true;
    }
    area.addEventListener("input", () => { dirty = true; clearTimeout(timer); timer = setTimeout(push, 300); });
    area.addEventListener("keydown", (e) => {
      e.stopPropagation();                                              // Tasten gehoeren dem Text, nicht dem 3D-Fenster (Entf, Pfeile, Strg+Z ...)
      if (e.key === "Tab" && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        const start = area.selectionStart;
        area.value = area.value.slice(0, start) + "  " + area.value.slice(area.selectionEnd);
        area.selectionStart = area.selectionEnd = start + 2;
        area.dispatchEvent(new Event("input"));
      }
    });
    area.addEventListener("keyup", (e) => e.stopPropagation());
    const onStage = (e) => {
      const d = e.detail || {};
      if (!visible || d.source === "json-editor" || dirty) return;       // eigene Aenderungen nicht zurueckspielen, nichts ueberschreiben, was gerade getippt wird
      load();
    };
    document.addEventListener("sim-stage", onStage);
    tidy.addEventListener("click", () => { try { area.value = JSON.stringify(JSON.parse(area.value), null, 2); } catch (err) { /* der Server nennt die Zeile */ } dirty = true; push(); });
    bar.append(live, status, tidy);
    root.append(bar, area);
    return {
      el: root,
      async show() { visible = true; setStatus("", ""); await load(); },
      hide() { visible = false; clearTimeout(timer); },
      get dirty() { return dirty; },
      push,
      dispose() { document.removeEventListener("sim-stage", onStage); clearTimeout(timer); },
    };
  }

  document.addEventListener("click", (e) => { if (e.target.closest('[data-action="open-sim-json"]')) { bind(); open(); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  window.OCSimJson = { open, createPanel };
})();

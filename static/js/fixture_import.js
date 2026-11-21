// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Scheinwerfer aus CSV / Excel importieren ("Erweiterte Importfunktionen" im Dialog Scheinwerfer hinzufuegen und im Menue Bibliothek). Server: app/fixture_import.py (/api/fixtures/import/*).
 * Schritt 1: Datei waehlen (.csv, .xlsx; die erste Zeile sind die Spaltenkoepfe) - die Spalten werden erraten. Schritt 2: Zuordnung pruefen, Vorschau mit Fehlern je Zeile. Schritt 3: Importieren.
 * Nichts wird angelegt, bevor man "Importieren" drueckt; Zeilen mit Problemen lassen sich auslassen. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "fx-import";
  const FIELDS = [["name", "FXI_F_NAME"], ["type", "FXI_F_TYPE"], ["mode", "FXI_F_MODE"], ["universe", "FXI_F_UNIVERSE"], ["address", "FXI_F_ADDRESS"], ["fid", "FXI_F_FID"], ["count", "FXI_F_COUNT"]];
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 4500); };

  let table = null;                                                    // {headers, rows, mapping, types, default_universe}
  let previewTimer = null;
  let lastItems = [];

  async function post(url, body, raw, filename) {
    try {
      const res = await fetch(raw ? url + "?filename=" + encodeURIComponent(filename) : url, { method: "POST", headers: raw ? {} : { "Content-Type": "application/json" }, body: raw ? body : JSON.stringify(body) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leer */ }
      return { ok: res.ok && data.ok !== false, data };
    } catch (e) {
      return { ok: false, data: { message: String(e) } };
    }
  }

  function showStep(step) {
    $("fxi-step-file").hidden = step !== "file";
    $("fxi-step-map").hidden = step !== "map";
    $("fxi-import").hidden = step !== "map";
    $("fxi-skip-wrap").hidden = step !== "map";
    $("fxi-again").hidden = step !== "map";
  }

  function open() {
    table = null;
    lastItems = [];
    $("fxi-msg").textContent = "";
    showStep("file");
    Modal.open(MODAL);
  }

  function pickFile() {
    let input = $("fxi-file-input");
    if (!input) {
      input = el("input");
      input.type = "file";
      input.id = "fxi-file-input";
      input.accept = ".csv,.txt,.tsv,.xlsx";
      input.hidden = true;
      document.body.appendChild(input);
    }
    input.value = "";
    input.onchange = async () => {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file) return;
      $("fxi-msg").textContent = t("FXI_READING");
      const res = await post("/api/fixtures/import/parse", await file.arrayBuffer(), true, file.name);
      if (!res.ok) { $("fxi-msg").textContent = res.data.message || t("FXI_READ_FAILED"); return; }
      table = res.data;
      $("fxi-msg").textContent = "";
      renderMapping();
      showStep("map");
      previewSoon(0);
    };
    input.click();
  }

  function mappingNow() {
    const mapping = {};
    FIELDS.forEach(([field]) => { const v = $("fxi-map-" + field).value; if (v !== "") mapping[field] = parseInt(v, 10); });
    return mapping;
  }

  function renderMapping() {
    const box = $("fxi-mapping");
    box.textContent = "";
    FIELDS.forEach(([field, key]) => {
      const wrap = el("label", "fxi__map");
      wrap.append(el("span", "fxi__map-name", t(key)));
      const select = el("select", "settings__select");
      select.id = "fxi-map-" + field;
      const none = el("option", "", t("FXI_NONE"));
      none.value = "";
      select.appendChild(none);
      table.headers.forEach((head, index) => { const o = el("option", "", head); o.value = String(index); select.appendChild(o); });
      select.value = table.mapping[field] === undefined ? "" : String(table.mapping[field]);
      select.addEventListener("change", () => previewSoon(150));
      wrap.appendChild(select);
      box.appendChild(wrap);
    });
    const def = $("fxi-default-type");
    def.textContent = "";
    const none = el("option", "", t("FXI_NONE"));
    none.value = "";
    def.appendChild(none);
    table.types.forEach((ft) => { const o = el("option", "", (ft.manufacturer && !ft.name.toLowerCase().startsWith(ft.manufacturer.toLowerCase()) ? ft.manufacturer + " " : "") + ft.name); o.value = ft.id; def.appendChild(o); });
    $("fxi-default-universe").value = String(table.default_universe || 1);
    $("fxi-count").textContent = t("FXI_ROWS", { n: table.total }) + (table.truncated ? " " + t("FXI_TRUNCATED") : "");
  }

  function previewSoon(delay) {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(preview, delay);
  }

  const request = () => ({ rows: table.rows, mapping: mappingNow(), default_type: $("fxi-default-type").value, default_universe: parseInt($("fxi-default-universe").value, 10) || 1 });

  async function preview() {
    if (!table) return;
    const res = await post("/api/fixtures/import/preview", request());
    if (!res.ok) { $("fxi-msg").textContent = res.data.message || ""; return; }
    lastItems = res.data.items;
    const body = $("fxi-rows");
    body.textContent = "";
    lastItems.slice(0, 300).forEach((item) => {
      const row = el("tr", item.ok ? "" : "fxi__bad");
      const cells = [item.row, item.name, item.type_name, item.mode, item.universe, item.address + (item.channels ? "–" + (item.address + item.channels * item.count - 1) : ""), item.fid || "", item.count];
      cells.forEach((c) => row.appendChild(el("td", "", String(c))));
      row.appendChild(el("td", "fxi__status", item.ok ? "✓" : item.errors.join("; ")));
      body.appendChild(row);
    });
    const summary = t("FXI_SUMMARY", { good: res.data.good, bad: res.data.bad });
    $("fxi-summary").textContent = summary + (lastItems.length > 300 ? " " + t("FXI_SHOWN", { n: 300 }) : "");
    $("fxi-summary").classList.toggle("fxi__summary--bad", res.data.bad > 0);
    refreshButton();
  }

  function refreshButton() {
    const good = lastItems.filter((i) => i.ok).length;
    const bad = lastItems.length - good;
    $("fxi-import").disabled = good === 0 || (bad > 0 && !$("fxi-skip").checked);
  }

  async function doImport() {
    const body = Object.assign(request(), { skip_invalid: $("fxi-skip").checked });
    $("fxi-import").disabled = true;
    const res = await post("/api/fixtures/import/apply", body);
    if (res.ok) {
      toast(t("FXI_DONE", { n: res.data.added }) + (res.data.skipped ? " " + t("FXI_DONE_SKIPPED", { n: res.data.skipped }) : ""), "success");
      Modal.close(MODAL);
    } else {
      $("fxi-msg").textContent = res.data.message || t("FXI_READ_FAILED");
      refreshButton();
    }
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="fx-import"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("fxi-pick").addEventListener("click", pickFile);
    $("fxi-again").addEventListener("click", () => { table = null; showStep("file"); });
    $("fxi-skip").addEventListener("change", refreshButton);
    $("fxi-default-type").addEventListener("change", () => previewSoon(100));
    $("fxi-default-universe").addEventListener("input", () => previewSoon(300));
    $("fxi-import").addEventListener("click", doImport);
    $("fxi-template").addEventListener("click", async () => {
      const address = "/api/fixtures/export.csv";
      let opened = false;
      try { opened = !!(await (await fetch("/api/files/open-download", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: address }) })).json()).opened; } catch (e) { /* offline */ }
      if (!opened) { const a = document.createElement("a"); a.href = address; a.download = "fixtures.csv"; document.body.appendChild(a); a.click(); a.remove(); }
    });
  }

  document.addEventListener("click", (e) => { if (e.target.closest('[data-action="open-fixture-import"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); bind(); open(); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  window.OCFixtureImport = { open };
})();

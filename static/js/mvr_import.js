// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* MVR-Szene importieren (Menue Bibliothek): Buehnenteile + Scheinwerfer aus einer .mvr-Datei (Vectorworks, Capture, Depence ...). Server: app/mvr_import.py (/api/mvr/*).
 * Schritt 1: Datei waehlen oder auf den Dialog ziehen - der Server liest sie nur und liefert eine Zusammenfassung. Schritt 2: Optionen (Buehne ersetzen / ergaenzen / unveraendert,
 * Scheinwerfer patchen). Schritt 3: Ergebnis. Nichts wird veraendert, bevor man "Importieren" drueckt. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "mvr-import";
  const MAX_BYTES = 400 * 1024 * 1024;
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 5000); };

  let session = null;                                                  // Sitzung des Servers (die Datei liegt dort im Speicher)
  let summary = null;
  let working = false;                                                 // gerade wird gelesen / importiert

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
    $("mvr-step-file").hidden = step !== "file";
    $("mvr-step-options").hidden = step !== "options";
    $("mvr-step-busy").hidden = step !== "busy";
    $("mvr-step-done").hidden = step !== "done";
    $("mvr-again").hidden = step !== "options";
    $("mvr-import").hidden = step !== "options";
    $("mvr-cancel").hidden = step === "done" || step === "busy";
    $("mvr-close").hidden = step !== "done";
  }

  /** Ladeanimation: Titel, Hinweis und Balken (percent = null: unbestimmt, der Balken pendelt). */
  function busy(title, sub, percent) {
    showStep("busy");
    $("mvr-busy-title").textContent = title;
    $("mvr-busy-sub").textContent = sub || "";
    const bar = $("mvr-bar");
    bar.parentElement.classList.toggle("mvr__bar--wait", percent === null || percent === undefined);
    bar.style.width = percent === null || percent === undefined ? "" : Math.max(2, Math.min(100, percent)) + "%";
  }

  function open() {
    session = summary = null;
    working = false;
    $("mvr-msg").textContent = "";
    showStep("file");
    Modal.open(MODAL);
  }

  function pickFile() {
    let input = $("mvr-file-input");
    if (!input) {
      input = el("input");
      input.type = "file";
      input.id = "mvr-file-input";
      input.accept = ".mvr";
      input.hidden = true;
      document.body.appendChild(input);
    }
    input.value = "";
    input.onchange = () => { const file = input.files && input.files[0]; input.value = ""; if (file) readFile(file); };
    input.click();
  }

  async function readFile(file) {
    if (working) return;
    if (!/\.mvr$/i.test(file.name)) { $("mvr-msg").textContent = t("MVR_NOT_MVR"); return; }
    if (file.size > MAX_BYTES) { $("mvr-msg").textContent = t("MVR_TOO_BIG"); return; }
    working = true;
    $("mvr-msg").textContent = "";
    busy(t("MVR_BUSY_READ"), file.name, null);
    const res = await post("/api/mvr/preview", await file.arrayBuffer(), true, file.name);
    working = false;
    if (!res.ok) { showStep("file"); $("mvr-msg").textContent = res.data.message || t("MVR_READ_FAILED"); return; }
    session = res.data.session;
    summary = res.data.summary;
    renderOptions();
    showStep("options");
  }

  function noteList(notes) {
    const box = el("div", "mvr__notes");
    box.appendChild(el("div", "mvr__notes-title", t("MVR_NOTES")));
    const list = el("ul", "mvr__notes-list");
    notes.slice(0, 12).forEach((n) => list.appendChild(el("li", "", n)));
    if (notes.length > 12) list.appendChild(el("li", "", t("MVR_MORE_NOTES", { n: notes.length - 12 })));
    box.appendChild(list);
    return box;
  }

  /** "11, 12, 13 ... 62 (22)" - hoechstens zehn Nummern ausgeschrieben. */
  function universeText(list, count) {
    const shown = (list || []).slice(0, 10).join(", ");
    return count > 10 ? shown + " ... " + list[list.length - 1] + " (" + count + ")" : shown;
  }

  function card(name, value, title, sub, checked, disabled) {
    const label = el("label", "hk__card mvr__card");
    const input = el("input");
    input.type = "radio"; input.name = name; input.value = value; input.checked = !!checked; input.disabled = !!disabled;
    const text = el("span", "hk__card-text");
    text.append(el("span", "hk__card-title", title), el("span", "hk__card-sub", sub));
    label.append(input, text);
    return label;
  }

  function renderOptions() {
    const s = summary;
    const body = $("mvr-options");
    body.textContent = "";
    const head = el("div", "mvr__scene");
    head.append(el("div", "mvr__scene-name", s.name), el("div", "mvr__scene-sub", "MVR " + s.version + (s.provider ? " · " + s.provider : "")));
    body.appendChild(head);
    const facts = el("ul", "mvr__facts");
    facts.appendChild(el("li", "", t("MVR_FACT_PARTS", { parts: s.parts, files: s.file_count, layers: s.layer_count })));
    facts.appendChild(el("li", "", t("MVR_FACT_FIXTURES", { fixtures: s.fixtures, types: s.type_count })));
    if (s.universe_count) facts.appendChild(el("li", "", t("MVR_FACT_UNIVERSES", { list: universeText(s.universes, s.universe_count) })));
    if (s.unaddressed) facts.appendChild(el("li", "", t("MVR_FACT_UNADDRESSED", { n: s.unaddressed })));
    body.appendChild(facts);

    const has3d = s.parts > 0 && s.can_read_3d;
    const stageBox = el("section", "mvr__sec");
    stageBox.appendChild(el("div", "mvr__label", t("MVR_STAGE_HEAD")));
    const cards = el("div", "mvr__cards");
    cards.setAttribute("role", "radiogroup");
    const empty = !s.stage_objects;
    cards.append(
      card("mvr-stage", "replace", t("MVR_STAGE_REPLACE"), empty ? t("MVR_STAGE_REPLACE_EMPTY") : t("MVR_STAGE_REPLACE_SUB", { n: s.stage_objects }), has3d, !has3d),
      card("mvr-stage", "add", t("MVR_STAGE_ADD"), t("MVR_STAGE_ADD_SUB"), false, !has3d),
      card("mvr-stage", "none", t("MVR_STAGE_NONE"), t("MVR_STAGE_NONE_SUB"), !has3d, false));
    stageBox.appendChild(cards);
    if (s.parts && !s.can_read_3d) stageBox.appendChild(el("p", "mvr__hint", t("MVR_NO3D")));
    if (!s.parts) stageBox.appendChild(el("p", "mvr__hint", t("MVR_NO_PARTS")));
    body.appendChild(stageBox);

    const fxBox = el("section", "mvr__sec");
    const fxLabel = el("label", "mvr__check");
    const fxInput = el("input", "oc-check");
    fxInput.type = "checkbox"; fxInput.id = "mvr-fixtures"; fxInput.checked = s.fixtures > 0; fxInput.disabled = s.fixtures === 0;
    const fxText = el("span", "mvr__check-text");
    fxText.append(el("span", "mvr__check-title", t("MVR_FIXTURES", { n: s.fixtures })), el("span", "mvr__check-sub", s.fixtures ? t("MVR_FIXTURES_SUB") : t("MVR_NO_FIXTURES")));
    fxLabel.append(fxInput, fxText);
    fxBox.appendChild(fxLabel);
    if (s.fixtures && s.types.length) {
      const types = el("ul", "mvr__types");
      s.types.slice(0, 8).forEach((ty) => types.appendChild(el("li", ty.present ? "" : "mvr__bad", (ty.name || ty.file || "?") + " × " + ty.count + (ty.present ? "" : " – " + t("MVR_TYPE_MISSING")))));
      if (s.types.length > 8) types.appendChild(el("li", "", t("MVR_MORE_NOTES", { n: s.types.length - 8 })));
      fxBox.appendChild(types);
    }
    if (s.fixtures_now) fxBox.appendChild(el("p", "mvr__hint", t("MVR_FIXTURES_NOW", { n: s.fixtures_now })));
    fxBox.appendChild(fixtureOptions(s));
    body.appendChild(fxBox);

    // ---- Ebenen (nur, wenn es mehr als eine mit Inhalt gibt)
    const layers = s.layer_stats || [];
    if (layers.length > 1) {
      const sec = el("details", "mvr__more");
      const sum = el("summary", "", t("MVR_LAYERS_HEAD", { n: layers.length }));
      sec.appendChild(sum);
      const tools = el("div", "mvr__row");
      [["MVR_LAYERS_ALL", true], ["MVR_LAYERS_NONE", false]].forEach(([key, on]) => {
        const b = el("button", "modal__button mvr__small", t(key));
        b.type = "button";
        b.addEventListener("click", () => { sec.querySelectorAll("input.mvr-layer").forEach((c) => { c.checked = on; }); refreshImport(); });
        tools.appendChild(b);
      });
      sec.appendChild(tools);
      const list = el("div", "mvr__layers");
      layers.forEach((layer) => {
        const row = el("label", "mvr__layer");
        const box = el("input", "oc-check mvr-layer");
        box.type = "checkbox"; box.checked = true; box.dataset.layer = layer.name;
        row.append(box, el("span", "mvr__layer-name", layer.name), el("span", "mvr__layer-count", t("MVR_LAYER_ROW", { parts: layer.parts, fixtures: layer.fixtures })));
        list.appendChild(row);
      });
      sec.appendChild(list);
      body.appendChild(sec);
    }

    // ---- Weiteres
    const more = el("details", "mvr__more");
    more.appendChild(el("summary", "", t("MVR_MORE")));
    const colorRow = el("label", "mvr__check");
    const colorBox = el("input", "oc-check");
    colorBox.type = "checkbox"; colorBox.id = "mvr-colors"; colorBox.checked = true;
    const colorText = el("span", "mvr__check-text");
    colorText.append(el("span", "mvr__check-title", t("MVR_COLORS")), el("span", "mvr__check-sub", t("MVR_COLORS_SUB")));
    colorRow.append(colorBox, colorText);
    more.appendChild(colorRow);
    const axisRow = el("label", "mvr__field");
    axisRow.appendChild(el("span", "", t("MVR_UP_AXIS")));
    const axis = el("select", "settings__select");
    axis.id = "mvr-axis";
    [["auto", "MVR_AXIS_AUTO"], ["z", "MVR_AXIS_Z"], ["y", "MVR_AXIS_Y"]].forEach(([value, key]) => { const o = el("option", "", t(key)); o.value = value; axis.appendChild(o); });
    axisRow.appendChild(axis);
    more.append(axisRow, el("p", "mvr__hint", t("MVR_UP_AXIS_SUB")));
    body.appendChild(more);
    if (s.warnings.length) body.appendChild(noteList(s.warnings));
    refreshImport();
  }

  /** Einstellungen zu den Scheinwerfern (erscheinen, solange "patchen" angehakt ist): Adressen aus der Datei (mit Versatz) oder neu, Platzierung in der 3D-Buehne. */
  function fixtureOptions(s) {
    const box = el("div", "mvr__fxopts");
    box.id = "mvr-fx-opts";
    const modes = el("div", "mvr__cards mvr__cards--two");
    modes.setAttribute("role", "radiogroup");
    modes.append(
      card("mvr-addr", "file", t("MVR_ADDR_FILE"), t("MVR_ADDR_FILE_SUB"), true, false),
      card("mvr-addr", "auto", t("MVR_ADDR_AUTO"), t("MVR_ADDR_AUTO_SUB"), false, false));
    box.appendChild(modes);
    const offset = el("label", "mvr__field");
    offset.id = "mvr-offset-row";
    offset.appendChild(el("span", "", t("MVR_UNIVERSE_OFFSET")));
    const offsetInput = el("input", "mvr__num");
    offsetInput.type = "number"; offsetInput.id = "mvr-offset"; offsetInput.value = "0"; offsetInput.min = "-63"; offsetInput.max = "63"; offsetInput.step = "1";
    offset.append(offsetInput, el("span", "mvr__hint", s.universe_count ? t("MVR_UNIVERSE_OFFSET_SUB") : ""));
    const start = el("label", "mvr__field");
    start.id = "mvr-start-row";
    start.hidden = true;
    start.appendChild(el("span", "", t("MVR_START_UNIVERSE")));
    const startInput = el("input", "mvr__num");
    startInput.type = "number"; startInput.id = "mvr-start"; startInput.value = "1"; startInput.min = "1"; startInput.max = "64"; startInput.step = "1";
    start.appendChild(startInput);
    box.append(offset, start);
    const place = el("label", "mvr__check");
    const placeBox = el("input", "oc-check");
    placeBox.type = "checkbox"; placeBox.id = "mvr-place"; placeBox.checked = true;
    const placeText = el("span", "mvr__check-text");
    placeText.append(el("span", "mvr__check-title", t("MVR_PLACE")), el("span", "mvr__check-sub", t("MVR_PLACE_SUB")));
    place.append(placeBox, placeText);
    box.appendChild(place);
    return box;
  }

  /** Alle Einstellungen des Dialogs fuer den Server. */
  function collectOptions() {
    const addressing = (document.querySelector('input[name="mvr-addr"]:checked') || {}).value || "file";
    const layerBoxes = [...document.querySelectorAll("input.mvr-layer")];
    const chosen = layerBoxes.filter((b) => b.checked).map((b) => b.dataset.layer);
    return {
      addressing,
      universe_offset: parseInt(($("mvr-offset") || {}).value, 10) || 0,
      start_universe: parseInt(($("mvr-start") || {}).value, 10) || 1,
      place_fixtures: !!($("mvr-place") && $("mvr-place").checked),
      colors: $("mvr-colors") && !$("mvr-colors").checked ? "neutral" : "keep",
      up_axis: ($("mvr-axis") || {}).value || "auto",
      layers: layerBoxes.length && chosen.length < layerBoxes.length ? chosen : null,
    };
  }

  function refreshImport() {
    const stage = (document.querySelector('input[name="mvr-stage"]:checked') || {}).value || "none";
    const fixtures = !!($("mvr-fixtures") && $("mvr-fixtures").checked);
    const opts = $("mvr-fx-opts");
    if (opts) opts.hidden = !fixtures;
    const addressing = (document.querySelector('input[name="mvr-addr"]:checked') || {}).value || "file";
    if ($("mvr-offset-row")) $("mvr-offset-row").hidden = addressing !== "file";
    if ($("mvr-start-row")) $("mvr-start-row").hidden = addressing !== "auto";
    const layerBoxes = [...document.querySelectorAll("input.mvr-layer")];
    const none = layerBoxes.length > 0 && !layerBoxes.some((b) => b.checked);
    $("mvr-import").disabled = working || none || (stage === "none" && !fixtures);
  }

  async function doImport() {
    const stage = (document.querySelector('input[name="mvr-stage"]:checked') || {}).value || "none";
    const fixtures = !!$("mvr-fixtures").checked;
    if (stage === "replace") {
      const current = window.OCSimStages && window.OCSimStages.current;
      if (current && current.dirty && typeof _askLayoutConfirm === "function" && !(await _askLayoutConfirm({ title: t("SIMSTAGE_REPLACE_TITLE"), body: t("SIMSTAGE_REPLACE_BODY", { name: current.name }), confirmKey: "SIMSTAGE_REPLACE_CONFIRM" }))) return;
    }
    working = true;
    $("mvr-msg").textContent = "";
    busy(t("MVR_BUSY_START"), t("MVR_BUSY_KEEP"), null);
    const started = await post("/api/mvr/apply", Object.assign({ session, stage, fixtures }, collectOptions()));
    if (!started.ok) { working = false; showStep("options"); $("mvr-msg").textContent = started.data.message || t("MVR_READ_FAILED"); refreshImport(); return; }
    // Der Server arbeitet im Hintergrund; hier wird nur nachgefragt und der Fortschritt gezeigt (der Dialog bleibt bedienbar, die Oberflaeche friert nicht ein)
    for (let failures = 0; ; ) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      let res;
      try { res = await (await fetch("/api/mvr/status?job=" + encodeURIComponent(started.data.job), { cache: "no-store" })).json(); failures = 0; }
      catch (e) { if (++failures > 20) { res = { state: "error", message: String(e) }; } else continue; }
      if (res.state === "running") {
        const total = res.total || 0;
        const done = res.done || 0;
        if (res.phase === "types") busy(t("MVR_PHASE_TYPES", { done: Math.min(done + 1, total), total }), t("MVR_PHASE_TYPES_SUB"), total ? (done / total) * 40 : null);
        else if (res.phase === "models") busy(t("MVR_PHASE_MODELS", { done: Math.min(done + 1, total), total }), t("MVR_BUSY_KEEP"), total ? 40 + (done / total) * 50 : null);
        else if (res.phase === "apply") busy(t("MVR_PHASE_APPLY"), t("MVR_BUSY_KEEP"), 95);
        else busy(t("MVR_BUSY_START"), t("MVR_BUSY_KEEP"), null);
        continue;
      }
      working = false;
      if (res.state === "done") {
        renderDone(res.result, stage);
        showStep("done");
        toast(t("MVR_DONE_TOAST"), "success");
      } else {
        showStep("options");
        $("mvr-msg").textContent = t("MVR_FAILED", { message: res.message || "" });
        refreshImport();
      }
      return;
    }
  }

  function renderDone(r, stage) {
    const box = $("mvr-done");
    box.textContent = "";
    box.appendChild(el("div", "mvr__done-title", t("MVR_DONE_TITLE")));
    const list = el("ul", "mvr__facts");
    if (stage !== "none" && r.objects) list.appendChild(el("li", "", t("MVR_DONE_STAGE", { objects: r.objects, models: r.models, name: r.stage_name })));
    if (r.fixtures) list.appendChild(el("li", "", t("MVR_DONE_FIXTURES", { n: r.fixtures })));
    if (r.universes && r.universes.length) list.appendChild(el("li", "", t("MVR_DONE_UNIVERSES", { list: universeText(r.universes, r.universes.length) })));
    if (r.automatic_addresses) list.appendChild(el("li", "", t("MVR_DONE_AUTO", { n: r.automatic_addresses })));
    if (r.mirrored) list.appendChild(el("li", "", t("MVR_DONE_MIRRORED", { n: r.mirrored })));
    if (r.merged === "layers") list.appendChild(el("li", "", t("MVR_DONE_MERGED_LAYERS")));
    if (r.merged === "all") list.appendChild(el("li", "", t("MVR_DONE_MERGED_ALL")));
    if (!list.children.length) list.appendChild(el("li", "", t("MVR_DONE_NOTHING")));
    box.appendChild(list);
    if (stage !== "none" && r.objects) box.appendChild(el("p", "mvr__hint", t("MVR_DONE_SAVE")));
    if (r.warnings && r.warnings.length) box.appendChild(noteList(r.warnings));
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="mvr-import"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("mvr-pick").addEventListener("click", pickFile);
    $("mvr-again").addEventListener("click", () => { session = summary = null; $("mvr-msg").textContent = ""; showStep("file"); });
    $("mvr-import").addEventListener("click", doImport);
    $("mvr-close").addEventListener("click", () => Modal.close(MODAL));
    root.addEventListener("change", (e) => { if (e.target.matches('input[name="mvr-stage"], input[name="mvr-addr"], #mvr-fixtures, input.mvr-layer')) refreshImport(); });
    const zone = root.querySelector(".modal");
    zone.addEventListener("dragover", (e) => { if (e.dataTransfer && [...e.dataTransfer.types].includes("Files")) { e.preventDefault(); zone.classList.add("mvr--drop"); } });
    zone.addEventListener("dragleave", () => zone.classList.remove("mvr--drop"));
    zone.addEventListener("drop", (e) => {
      zone.classList.remove("mvr--drop");
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) { e.preventDefault(); if (!$("mvr-step-file").hidden || !$("mvr-step-options").hidden) readFile(file); }
    });
  }

  window.addEventListener("beforeunload", (e) => { if (working) { e.preventDefault(); e.returnValue = ""; } });
  document.addEventListener("click", (e) => { if (e.target.closest('[data-action="open-mvr-import"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); bind(); open(); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  window.OCMvrImport = { open, readFile };
})();

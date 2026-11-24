// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* MVR-Szene exportieren (Menue Bibliothek): Scheinwerfer + Patch und/oder die 3D-Buehne als .mvr-Datei (Vectorworks, Capture, Depence ...). Server: app/mvr_export.py (/api/mvr/export/*).
 * Ablauf: Dialog zeigt, was exportiert werden kann (Zaehler vom Server) -> zwei Schalter + Dateiname -> "Exportieren" baut die Datei im Hintergrund (Ladeanimation mit Fortschritt)
 * -> erst danach erscheint "Herunterladen"; der Download laeuft wie bei den anderen Export-Paketen ueber den Browser (POST /api/files/open-download, sonst Anker). */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "mvr-export";
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 5000); };

  let info = null;                                                       // Zusammenfassung des Servers
  let choice = { fixtures: true, stage: true, unplaced: false, name: "" };
  let working = false;
  let job = null;                                                        // fertiger Auftrag (fuer den Download)

  async function getJson(url) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leer */ }
      return { ok: res.ok && data.ok !== false, data };
    } catch (e) {
      return { ok: false, data: { message: String(e) } };
    }
  }

  async function postJson(url, body) {
    try {
      const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      let data = {};
      try { data = await res.json(); } catch (e) { /* leer */ }
      return { ok: res.ok && data.ok !== false, data };
    } catch (e) {
      return { ok: false, data: { message: String(e) } };
    }
  }

  function showStep(step) {
    $("mvrx-step-options").hidden = step !== "options";
    $("mvrx-step-busy").hidden = step !== "busy";
    $("mvrx-step-done").hidden = step !== "done";
    $("mvrx-start").hidden = step !== "options";
    $("mvrx-cancel").hidden = step !== "options";
    $("mvrx-download").hidden = step !== "done";
    $("mvrx-again").hidden = step !== "done";
    $("mvrx-close").hidden = step !== "done";
  }

  /** Ladeanimation: Titel, Hinweis und Balken (percent = null: unbestimmt, der Balken pendelt). */
  function busy(title, sub, percent) {
    showStep("busy");
    $("mvrx-busy-title").textContent = title;
    $("mvrx-busy-sub").textContent = sub || "";
    const bar = $("mvrx-bar");
    bar.parentElement.classList.toggle("mvr__bar--wait", percent === null || percent === undefined);
    bar.style.width = percent === null || percent === undefined ? "" : Math.max(2, Math.min(100, percent)) + "%";
  }

  function sizeText(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB";
    return Math.max(1, Math.round(bytes / 1024)) + " KB";
  }

  /** Eine grosse Karte mit Symbol, Titel, Zeile darunter und Schalter rechts. */
  function toggleCard(icon, title, sub, checked, disabled, onChange) {
    const card = el("label", "mvrx__card" + (disabled ? " mvrx__card--off" : ""));
    const symbol = el("span", "mvrx__icon");
    symbol.appendChild(Icons.svg(icon));
    const text = el("span", "mvrx__text");
    text.append(el("span", "mvrx__title", title), el("span", "mvrx__sub", sub));
    const sw = el("span", "toggle-switch");
    const box = el("input");
    box.type = "checkbox"; box.checked = !!checked && !disabled; box.disabled = !!disabled;
    box.addEventListener("change", () => onChange(box.checked));
    sw.append(box, el("span", "toggle-switch__track"));
    card.append(symbol, text, sw);
    return card;
  }

  function renderOptions() {
    const body = $("mvrx-options");
    body.textContent = "";
    if (!info) { body.appendChild(el("p", "mvr__hint", t("MVRX_LOADING"))); refresh(); return; }
    const fx = info.fixtures;
    const st = info.stage;
    const fxCount = choice.unplaced ? fx.exportable : fx.placed;
    const fxUsable = fx.exportable > 0;
    const stUsable = st.objects > 0;

    const cards = el("div", "mvrx__cards");
    cards.appendChild(toggleCard("fixtures", t("MVRX_FX_TITLE"),
      fxUsable ? t("MVRX_FX_SUB", { n: fxCount, types: fx.type_count }) : t("MVRX_FX_NONE"),
      choice.fixtures, !fxUsable, (on) => { choice.fixtures = on; refresh(); }));
    cards.appendChild(toggleCard("stage", t("MVRX_STAGE_TITLE"),
      stUsable ? t("MVRX_STAGE_SUB", { objects: st.objects, name: st.name || "-" }) : t("MVRX_STAGE_NONE"),
      choice.stage, !stUsable, (on) => { choice.stage = on; refresh(); }));
    body.appendChild(cards);

    // Hinweise zu den Scheinwerfern
    const notes = el("div", "mvrx__notes");
    notes.id = "mvrx-notes";
    if (fx.no_gdtf) notes.appendChild(el("p", "mvr__hint", t("MVRX_NOTE_NO_GDTF", { n: fx.no_gdtf })));
    body.appendChild(notes);
    if (fx.unplaced > 0) {
      const row = el("label", "mvr__check mvrx__unplaced");
      row.id = "mvrx-unplaced-row";
      const box = el("input", "oc-check");
      box.type = "checkbox"; box.checked = choice.unplaced;
      box.addEventListener("change", () => { choice.unplaced = box.checked; renderOptions(); });
      const text = el("span", "mvr__check-text");
      text.append(el("span", "mvr__check-title", t("MVRX_UNPLACED", { n: fx.unplaced })), el("span", "mvr__check-sub", t("MVRX_UNPLACED_SUB")));
      row.append(box, text);
      body.appendChild(row);
    }

    const nameRow = el("label", "mvr__field mvrx__name");
    nameRow.appendChild(el("span", "", t("MVRX_NAME")));
    const input = el("input", "modal__input");
    input.type = "text"; input.id = "mvrx-name"; input.maxLength = 60; input.value = choice.name; input.spellcheck = false;
    input.addEventListener("input", () => { choice.name = input.value; });
    nameRow.append(input, el("span", "mvr__hint", t("MVRX_NAME_SUB")));
    body.appendChild(nameRow);
    body.appendChild(el("p", "mvr__hint", t("MVRX_HINT")));
    refresh();
  }

  function refresh() {
    const usable = info && ((choice.fixtures && info.fixtures.exportable > 0) || (choice.stage && info.stage.objects > 0));
    $("mvrx-start").disabled = working || !usable;
    $("mvrx-msg").textContent = info && !usable && (info.fixtures.exportable > 0 || info.stage.objects > 0) ? t("MVRX_NONE_CHOSEN") : ($("mvrx-msg").dataset.error || "");
  }

  function setError(text) {
    $("mvrx-msg").dataset.error = text || "";
    $("mvrx-msg").textContent = text || "";
  }

  async function open() {
    info = null;
    job = null;
    working = false;
    choice = { fixtures: true, stage: true, unplaced: false, name: "" };
    setError("");
    showStep("options");
    renderOptions();
    Modal.open(MODAL);
    const res = await getJson("/api/mvr/export/info");
    if (!res.ok) { setError(t("MVRX_INFO_FAILED")); return; }
    info = res.data;
    choice.fixtures = info.fixtures.exportable > 0;
    choice.stage = info.stage.objects > 0;
    choice.name = info.stage.name && info.stage.objects > 0 ? info.stage.name : "OpenCue scene";
    renderOptions();
  }

  async function start() {
    if (working || !info) return;
    working = true;
    setError("");
    busy(t("MVRX_BUSY_START"), t("MVRX_BUSY_KEEP"), null);
    const started = await postJson("/api/mvr/export/start", { fixtures: choice.fixtures, stage: choice.stage, unplaced: choice.unplaced, name: choice.name });
    if (!started.ok) { working = false; showStep("options"); setError(started.data.message || t("MVRX_FAILED", { message: "" })); refresh(); return; }
    const id = started.data.job;
    // Der Server baut im Hintergrund; hier wird nur nachgefragt und der Fortschritt gezeigt (die Oberflaeche friert nicht ein)
    for (let failures = 0; ; ) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      const res = await getJson("/api/mvr/export/status?job=" + encodeURIComponent(id));
      if (!res.ok && res.data.state !== "error") {
        if (++failures > 20) { working = false; showStep("options"); setError(t("MVRX_FAILED", { message: res.data.message || "" })); refresh(); return; }
        continue;
      }
      failures = 0;
      const st = res.data;
      if (st.state === "running") {
        const total = st.total || 0;
        const done = st.done || 0;
        const at = Math.min(done + 1, total);
        if (st.phase === "types") busy(t("MVRX_PHASE_TYPES", { done: at, total }), t("MVRX_BUSY_KEEP"), total ? (done / total) * 20 : null);
        else if (st.phase === "fixtures") busy(t("MVRX_PHASE_FIXTURES", { done: at, total }), t("MVRX_BUSY_KEEP"), total ? 20 + (done / total) * 20 : null);
        else if (st.phase === "stage") busy(t("MVRX_PHASE_STAGE", { done: at, total }), t("MVRX_BUSY_KEEP"), total ? 40 + (done / total) * 50 : null);
        else if (st.phase === "pack") busy(t("MVRX_PHASE_PACK"), t("MVRX_BUSY_KEEP"), 95);
        else busy(t("MVRX_BUSY_START"), t("MVRX_BUSY_KEEP"), null);
        continue;
      }
      working = false;
      if (st.state === "done") {
        job = { id, result: st.result };
        renderDone(st.result);
        showStep("done");
      } else {
        showStep("options");
        setError(st.error === "empty" ? t("MVRX_EMPTY") : t("MVRX_FAILED", { message: st.message || "" }));
        refresh();
      }
      return;
    }
  }

  function renderDone(r) {
    const box = $("mvrx-done");
    box.textContent = "";
    box.appendChild(el("div", "mvr__done-title", t("MVRX_DONE_TITLE")));
    box.appendChild(el("div", "mvrx__file", r.filename + " · " + sizeText(r.size)));
    const list = el("ul", "mvr__facts");
    if (r.fixtures) list.appendChild(el("li", "", t("MVRX_DONE_FIXTURES", { n: r.fixtures, types: r.types })));
    if (r.objects) list.appendChild(el("li", "", t("MVRX_DONE_STAGE", { objects: r.objects, models: r.models })));
    box.appendChild(list);
    const notes = [];
    if (r.skipped_no_gdtf) notes.push(t("MVRX_NOTE_NO_GDTF", { n: r.skipped_no_gdtf }));
    if (r.skipped_unplaced) notes.push(t("MVRX_NOTE_UNPLACED", { n: r.skipped_unplaced }));
    if (notes.length) {
      const wrap = el("div", "mvr__notes");
      wrap.appendChild(el("div", "mvr__notes-title", t("MVR_NOTES")));
      const ul = el("ul", "mvr__notes-list");
      notes.forEach((n) => ul.appendChild(el("li", "", n)));
      wrap.appendChild(ul);
      box.appendChild(wrap);
    }
    box.appendChild(el("p", "mvr__hint", t("MVRX_DONE_HINT")));
  }

  /** Im Programmfenster oeffnet der Server den Standard-Browser (er laedt die Datei); sonst laedt dieser Browser selbst. */
  async function download() {
    if (!job) return;
    const url = "/api/mvr/export/download?job=" + encodeURIComponent(job.id);
    const res = await postJson("/api/files/open-download", { url });
    if (res.ok && res.data.opened) { toast(t("MVRX_DL_STARTED")); return; }
    const link = el("a");
    link.href = url;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="mvr-export"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("mvrx-start").addEventListener("click", start);
    $("mvrx-download").addEventListener("click", download);
    $("mvrx-again").addEventListener("click", () => { job = null; setError(""); showStep("options"); renderOptions(); });
    $("mvrx-close").addEventListener("click", () => Modal.close(MODAL));
  }

  window.addEventListener("beforeunload", (e) => { if (working) { e.preventDefault(); e.returnValue = ""; } });
  document.addEventListener("click", (e) => { if (e.target.closest('[data-action="open-mvr-export"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); bind(); open(); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  window.OCMvrExport = { open };
})();

// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Datei-Menue -> "Drucken / PDF ...": Dokumentation der geladenen Show als PDF (Patch-Liste, DMX-Belegung, Gruppen, Plan, Cue-Listen). Server: app/reports.py (GET /api/report/*).
 * "Als PDF speichern" laedt die Datei herunter, "Zum Drucken oeffnen" zeigt sie im PDF-Betrachter (dort druckt man mit Strg+P). Im Programmfenster uebernimmt das der Standard-Browser
 * (wie bei den Export-Paketen, POST /api/files/open-download); Fernzugriffs-Geraete laden die Adresse selbst. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const $ = (id) => document.getElementById(id);
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 3500); };
  const MODAL = "report";
  const PARTS = ["patch", "universes", "groups", "plan", "cues"];

  function chosen() { return PARTS.filter((p) => $("report-part-" + p) && $("report-part-" + p).checked); }

  function url(inline) {
    const params = new URLSearchParams({ parts: chosen().join(","), paper: $("report-paper").value, inline: inline ? "1" : "0", lang: (typeof client !== "undefined" && client.state && client.state.language) || "en" });
    return "/api/report/pdf?" + params.toString();
  }

  /** Vorschau: dasselbe PDF in einem Rahmen (der PDF-Betrachter des Browsers). Aenderungen der Auswahl / des Papiers laden es nach kurzer Pause neu; geschlossen: Rahmen leeren. */
  let previewTimer = null;
  function previewNow() {
    const frame = $("report-preview");
    const empty = $("report-preview-empty");
    if (!frame || !empty) return;
    if (!Modal.isOpen(MODAL)) { frame.src = "about:blank"; return; }
    const none = !chosen().length;
    empty.hidden = !none;
    frame.hidden = none;
    frame.src = none ? "about:blank" : url(true) + "&t=" + Date.now() + "#toolbar=0&navpanes=0&view=FitH";
  }
  function previewSoon() { clearTimeout(previewTimer); previewTimer = setTimeout(previewNow, 350); }

  async function go(inline) {
    if (!chosen().length) { toast(t("REPORT_NONE_CHOSEN"), "warn"); return; }
    const address = url(inline);
    let opened = false;
    try {
      const res = await fetch("/api/files/open-download", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: address }) });
      opened = !!(await res.json()).opened;
    } catch (e) { opened = false; }
    if (opened) { toast(t(inline ? "REPORT_OPENED" : "REPORT_SAVING")); return; }
    const a = document.createElement("a");                                      // Fernzugriff: der Browser laedt selbst
    a.href = address;
    a.target = "_blank";
    a.rel = "noopener";
    if (!inline) a.download = "";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function open() {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    let info = { fixtures: 0, groups: 0, cuelists: 0, positions: 0, plan_source: "" };
    try { info = await (await fetch("/api/report/info")).json(); } catch (e) { /* offline */ }
    const counts = { patch: info.fixtures, universes: info.fixtures, groups: info.groups, plan: info.positions, cues: info.cuelists };
    PARTS.forEach((p) => {
      const box = $("report-part-" + p);
      const note = $("report-count-" + p);
      if (box) box.checked = counts[p] > 0 && p !== "cues";                // Cue-Listen sind standardmaessig nicht dabei
      if (note) note.textContent = p === "plan" && !counts[p] ? t("REPORT_NO_POSITIONS") : String(counts[p]);
    });
    Modal.open(MODAL);
    previewNow();
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="report"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("report-save").addEventListener("click", () => go(false));
    $("report-print").addEventListener("click", () => go(true));
    PARTS.forEach((p) => { const box = $("report-part-" + p); if (box) box.addEventListener("change", previewSoon); });
    $("report-paper").addEventListener("change", previewSoon);
    document.addEventListener("i18n-applied", () => { if (Modal.isOpen(MODAL)) previewSoon(); });
    root.querySelectorAll('[data-modal-close="report"], [data-modal-cancel="report"]').forEach((b) => b.addEventListener("click", () => setTimeout(previewNow, 50)));
  }

  document.addEventListener("click", (e) => { if (e.target.closest('[data-action="open-report-modal"]')) { bind(); open(); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  window.OCReport = { open, url };
})();

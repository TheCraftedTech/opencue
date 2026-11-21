// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Meldet JavaScript-Fehler der Oberflaeche an den Server (POST /api/client-error, app/diag.py): sie stehen dann als Zeile "OC-3601" im Protokoll und im Fehlerbericht
 * ("Copy details" / Hilfe -> Problem melden). Wird als ERSTES Skript geladen, damit auch Fehler beim Start erfasst werden. Faengt: Skriptfehler, nicht geladene Skripte und
 * Stile (<script>/<link>/<img>), nicht abgefangene Promise-Fehler (z. B. ein dynamisch nachgeladenes Modul, das nicht kommt). Je Seite hoechstens 30 verschiedene Meldungen;
 * der Server begrenzt zusaetzlich. Nie ein Fehler aus diesem Skript selbst. */
(function () {
  "use strict";
  const MAX = 30;
  const IGNORE = /ResizeObserver loop|^Script error\.?$/i;               // harmlose Browser-Meldungen
  const seen = new Set();
  let sent = 0;

  function send(info) {
    try {
      if (sent >= MAX || !info || IGNORE.test(String(info.message || ""))) return;
      const key = [info.kind, info.message, info.source, info.line].join("|");
      if (seen.has(key)) return;
      seen.add(key);
      sent += 1;
      info.page = location.pathname + (location.hash || "");
      const body = JSON.stringify(info);
      if (navigator.sendBeacon && navigator.sendBeacon("/api/client-error", new Blob([body], { type: "application/json" }))) return;
      fetch("/api/client-error", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
    } catch (e) { /* der Fehlermelder darf nie selbst stoeren */ }
  }

  window.addEventListener("error", (event) => {
    const target = event.target;
    if (target && target !== window && (target.src || target.href)) {      // Ressource nicht geladen (Skript, Stil, Bild)
      send({ kind: "resource", message: "Failed to load <" + String(target.tagName || "").toLowerCase() + ">", source: target.src || target.href });
      return;
    }
    send({ kind: "error", message: event.message, source: event.filename, line: event.lineno, col: event.colno, stack: event.error && event.error.stack });
  }, true);

  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    send({ kind: "promise", message: reason && reason.message ? reason.message : String(reason), stack: reason && reason.stack });
  });

  window.OCErrorReport = { send };                                           // fuer eigene Meldungen aus dem Programm (z. B. "3D konnte nicht geladen werden")
})();

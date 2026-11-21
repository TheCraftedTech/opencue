// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Weitere Optionen -> "Bildschirm wach halten": ein Schalter fuer ALLE Geraete.
 *   - Der Rechner mit OpenCue (Windows): der Server haelt ihn wach (app/keep_awake.py, SetThreadExecutionState) - kein Ruhezustand, kein Abschalten des Bildschirms, keine Leerlauf-Sperre.
 *   - Tablets und andere Fernzugriffs-Geraete (iPad ...): der Browser haelt den Bildschirm an (Screen Wake Lock API, WakeLockKeeper in app.js). Das gibt es NUR auf einer SICHEREN SEITE
 *     (https://, oder http://localhost): ueber http://<IP> fehlt navigator.wakeLock. Darum zeigt diese Seite, ob es auf DIESEM Geraet geht, und fuehrt sonst zur HTTPS-Einstellung (Fernzugriff).
 * Ein Entwurf wie alle festen Einstellungen: der Schalter wirkt erst nach "Speichern" (app.js ruft fillSettings() / saveSettings()). Klassisches Skript. */
(function () {
  "use strict";
  const t = (key) => (typeof i18n === "function" ? i18n(key) : key);
  const $ = (id) => document.getElementById(id);
  let info = null;                                                            // Antwort von /api/system (keep_awake: Zustand am Server)

  const isConsole = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);
  const secure = () => window.isSecureContext === true;
  const wakeLockPossible = () => secure() && "wakeLock" in navigator;

  function statusText() {
    const box = $("settings-keep-awake");
    const on = box ? box.checked : true;
    if (isConsole()) {
      const k = (info && info.keep_awake) || {};
      if (!k.available) return t("KA_ST_NOT_WINDOWS");
      if (!on) return t("KA_ST_OFF");
      return k.active ? t("KA_ST_WINDOWS_ON") : t("KA_ST_PENDING");                // "pending": gespeichert, aber noch nicht uebernommen
    }
    if (!on) return t("KA_ST_OFF");
    if (wakeLockPossible()) return t("KA_ST_DEVICE_OK");
    return secure() ? t("KA_ST_DEVICE_NA") : t("KA_ST_NEEDS_HTTPS");
  }

  function paint() {
    const text = $("settings-keep-awake-status");
    if (text) text.textContent = statusText();
    const open = $("settings-keep-awake-https");
    if (open) open.hidden = isConsole() || secure();                            // nur am Tablet ohne sichere Seite: der Weg dorthin
  }

  async function fillSettings() {
    const box = $("settings-keep-awake");
    if (box) box.checked = !(client.state && client.state.keep_awake === false);
    paint();
    try {
      const res = await fetch("/api/system");
      if (res.ok) { info = await res.json(); paint(); }
    } catch (e) { /* offline */ }
  }

  function saveSettings() {
    const box = $("settings-keep-awake");
    if (!box) return;
    const was = !(client.state && client.state.keep_awake === false);
    if (box.checked !== was) client.send("set_keep_awake", { enabled: box.checked });
  }

  document.addEventListener("change", (e) => { if (e.target && e.target.id === "settings-keep-awake") paint(); });
  document.addEventListener("click", (e) => {
    if (!(e.target && e.target.closest && e.target.closest("#settings-keep-awake-https"))) return;
    const nav = document.querySelector('.modal--settings [data-settings-category="remote"]');          // HTTPS steht unter Fernzugriff
    if (nav && !nav.hidden) nav.click();
  });
  document.addEventListener("i18n-applied", paint);
  window.OCKeepAwake = { fillSettings, saveSettings, wakeLockPossible, secure };
})();

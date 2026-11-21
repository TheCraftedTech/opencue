// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Diktieren (Server: app/dictation.py): Sprache -> Text, zunaechst fuer das Eingabefeld des KI-Chats. Dieses Skript haelt den gemeinsamen Stand (aufnehmen / umschreiben /
 * Modell laden), spricht die Schnittstelle an und verteilt den Pegel fuer die Balkenanimation. Die Aufnahme laeuft am Mikrofon der KONSOLE (nur dort sichtbar).
 *   OCDictation.start()   -> Promise<{ok, error}>      Aufnahme beginnen
 *   OCDictation.stop()    -> Promise<{ok, text, ...}>  beenden und umschreiben
 *   OCDictation.cancel()  OCDictation.subscribe(fn)  (fn bekommt den Stand bei jeder Aenderung; Pegel kommen als { level, seconds })
 * Klassisches Skript, laeuft nach app.js und vor ai_panel.js. */
(function () {
  "use strict";
  const ERRORS = { audio_unavailable: "DICT_ERR_AUDIO", device_missing: "DICT_ERR_DEVICE", open_failed: "DICT_ERR_OPEN", busy: "DICT_ERR_BUSY", local_only: "DICT_ERR_LOCAL",
    download_failed: "DICT_ERR_DOWNLOAD", transcribe_failed: "DICT_ERR_TRANSCRIBE", model_incomplete: "DICT_ERR_DOWNLOAD", not_recording: "DICT_ERR_BUSY" };
  let status = { state: "idle", error: "", level: 0, seconds: 0, percent: 0, limit_s: 120, model: "accurate", models: {} };
  const listeners = new Set();

  const notify = (extra) => listeners.forEach((fn) => { try { fn(status, extra || null); } catch (err) { console.error(err); } });
  function errorText(code) {
    const key = ERRORS[String(code || "").split(":")[0]];
    return key ? i18n(key) : String(code || "");
  }
  async function post(path, body) {
    try {
      const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
      return await res.json();
    } catch (err) { return { ok: false, error: "transcribe_failed" }; }
  }
  async function refresh() {
    try {
      const res = await fetch("/api/dictation", { cache: "no-store" });
      if (res.ok) { status = await res.json(); notify(); }
    } catch (err) { /* Server nicht erreichbar */ }
  }

  async function start() {
    const result = await post("/api/dictation/start");
    if (result && result.state) { status = { ...status, ...result }; notify(); }
    return result;
  }
  async function stop() {
    status = { ...status, state: "transcribing" };
    notify();
    const result = await post("/api/dictation/stop");
    await refresh();
    return result;
  }
  async function cancel() {
    await post("/api/dictation/cancel");
    await refresh();
  }
  /** Das gewaehlte Modell jetzt laden (Einstellungen); der Fortschritt kommt als Stand. */
  async function download(model) { const result = await post("/api/dictation/download", model ? { model } : {}); await refresh(); return result; }

  function onMessage(message) {
    if (message.type === "dictation_state") { status = { ...status, ...(message.payload || {}) }; notify(); }
    else if (message.type === "dictation_level") { status = { ...status, ...(message.payload || {}) }; notify({ level: true }); }
  }
  function boot() {
    if (typeof client !== "undefined" && client.registerModule) client.registerModule("dictation", { onMessage });
    refresh();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();

  window.OCDictation = {
    start, stop, cancel, download, refresh, errorText,
    status: () => status,
    /** Nur an der Konsole selbst (dort haengt das Mikrofon). */
    available: () => !!(typeof client !== "undefined" && client.state && client.state.is_local),
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
  };
})();

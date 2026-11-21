// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Sprachsteuerung (app/voice.py) - der Mikrofon-Knopf in der Menueleiste (nur an der Konsole) ist ein reiner EIN/AUS-SCHALTER: gruen = hoert auf das Weckwort, rot und
 * durchgestrichen = aus, gelb = Fehler. Dazu die Anzeige ueber den Verlauf eines Sprachbefehls: "Ich hoere ..." (Weckwort erkannt) -> "Verstehe ..." -> der Befehl und sein
 * Ergebnis (oder warum es nicht ging). Die Einstellungen stehen in voice_settings.js. Klassisches Skript, laeuft nach app.js. */
(function () {
  "use strict";
  const t = (key, vars) => { let s = i18n(key); if (vars) for (const [k, v] of Object.entries(vars)) s = s.split("{" + k + "}").join(String(v)); return s; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const LISTEN_MS = 4500;
  const ERRORS = { vosk_missing: "VOICE_ERR_VOSK", model_missing: "VOICE_ERR_MODEL", model_failed: "VOICE_ERR_MODEL", wake_word_unknown: "VOICE_ERR_WORD",
    device_missing: "VOICE_ERR_DEVICE", open_failed: "VOICE_ERR_OPEN", audio_unavailable: "VOICE_ERR_AUDIO", apply_failed: "VOICE_ERR_APPLY" };
  let status = null;
  let bubble = null;
  let bubbleTimer = 0;
  const listeners = new Set();

  /** Fehlercode des Servers als Satz (auch fuer die Einstellungen). */
  function errorText(code) {
    const key = ERRORS[String(code || "").split(":")[0]];
    return key ? t(key) : String(code || "");
  }

  async function refresh() {
    try {
      const res = await fetch("/api/voice", { cache: "no-store" });
      if (res.ok) setStatus(await res.json());
    } catch (err) { /* Server nicht erreichbar */ }
  }
  function setStatus(next) {
    status = next;
    paintButton();
    listeners.forEach((fn) => fn(status));
  }

  // ---- Anzeige: "Ich hoere ..." -> "Verstehe ..." -> Befehl + Ergebnis
  /** Die Blase zeigen: kind "" (laeuft), "ok" (Befehl lief), "bad" (ging nicht); hide_ms 0 = bleibt, bis die naechste Meldung kommt. */
  function showBubble(text, meta, kind, hideMs, mono) {
    if (!bubble) {
      bubble = el("div", "voice-bubble");
      bubble.setAttribute("role", "status");
      bubble.setAttribute("aria-live", "polite");
      const icon = Icons.svg("mic");
      icon.classList.add("voice-bubble__icon");
      bubble.append(icon, el("span", "voice-bubble__text"), el("span", "voice-bubble__meta"));
      document.body.appendChild(bubble);
    }
    const label = bubble.querySelector(".voice-bubble__text");
    label.textContent = text;
    label.classList.toggle("voice-bubble__text--mono", !!mono);
    bubble.querySelector(".voice-bubble__meta").textContent = meta || "";
    bubble.classList.toggle("voice-bubble--ok", kind === "ok");
    bubble.classList.toggle("voice-bubble--bad", kind === "bad");
    bubble.classList.toggle("voice-bubble--still", kind === "ok" || kind === "bad");          // das Mikrofon pulsiert nur, solange es arbeitet
    if (!bubble.classList.contains("voice-bubble--in")) { void bubble.offsetWidth; bubble.classList.add("voice-bubble--in"); }
    const button = document.getElementById("toolbar-voice");
    if (button) button.classList.add("menubar__voice--listening");
    clearTimeout(bubbleTimer);
    if (hideMs) bubbleTimer = setTimeout(hideBubble, hideMs);
  }
  function hideBubble() {
    if (bubble) bubble.classList.remove("voice-bubble--in");
    const button = document.getElementById("toolbar-voice");
    if (button) button.classList.remove("menubar__voice--listening");
  }
  function showListening(info) {
    showBubble(t("VOICE_LISTENING"), info && info.source === "voice"
      ? (info.heard_s ? t("VOICE_HEARD_META", { phrase: info.phrase, s: String(info.heard_s).replace(".", ",") }) : t("VOICE_HEARD_META_PLAIN", { phrase: info.phrase })) : t("VOICE_BUTTON_META"), "", LISTEN_MS);
  }
  const PHASE_ERRORS = { nothing_heard: "VOICE_CMD_NOTHING", no_command: "VOICE_CMD_NO_COMMAND", blocked: "VOICE_CMD_BLOCKED", model_missing: "VOICE_CMD_MODEL", transcribe_failed: "VOICE_CMD_FAILED", failed: "VOICE_CMD_FAILED" };
  /** Verlauf eines Sprachbefehls (Server: voice_phase). */
  function showPhase(info) {
    const phase = info && info.phase;
    if (phase === "recording") showBubble(t("VOICE_LISTENING"), t("VOICE_SPEAK_NOW"), "", 14000);
    else if (phase === "thinking") showBubble(t("VOICE_THINKING"), "", "", 30000);
    else if (phase === "done") showBubble(info.command || "", (info.success ? "✓ " : "✗ ") + (info.message || "") + (info.notes && info.notes.length ? "  ·  " + t("VOICE_CORRECTED") + " " + info.notes.slice(0, 3).join(", ") : ""), info.success ? "ok" : "bad", info.success ? 5500 : 8000, true);
    else if (phase === "error") {
      const key = PHASE_ERRORS[info.error] || "VOICE_CMD_FAILED";
      showBubble(t(key, { blocked: info.blocked || "" }), info.heard ? "„" + info.heard + "“" : "", "bad", 6000);
    }
  }

  // ---- Mikrofon-Knopf
  function paintButton() {
    const button = document.getElementById("toolbar-voice");
    if (!button || !status) return;
    const cfg = status.config || {};
    button.hidden = false;                                           // das Mikrofon haengt an der Konsole, der Schalter geht von jedem Geraet (auch iPad im Server-Betrieb)
    button.classList.toggle("menubar__voice--live", !!cfg.enabled && !!status.running && !status.error);
    button.classList.toggle("menubar__voice--error", !!cfg.enabled && !!status.error);
    button.classList.toggle("menubar__voice--off", !cfg.enabled);
    button.setAttribute("aria-pressed", String(!!cfg.enabled));
    const tip = !cfg.enabled ? t("VOICE_TIP_OFF", { word: cfg.wake_word || "OpenCue" })
      : status.error ? t("VOICE_TIP_ERROR", { error: errorText(status.error) }) : t("VOICE_TIP_ON", { word: cfg.wake_word || "OpenCue" });
    button.title = tip;
    button.setAttribute("aria-label", tip);
  }
  let paintTries = 0;
  let toggling = false;
  /** Reiner Ein/Aus-Schalter: ein Klick schaltet die Sprachsteuerung ein oder aus (und speichert das). */
  async function toggle() {
    if (toggling || !status) return;
    toggling = true;
    const button = document.getElementById("toolbar-voice");
    if (button) button.classList.add("menubar__voice--busy");
    try {
      const res = await fetch("/api/voice/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: !(status.config || {}).enabled }) });
      const data = await res.json();
      if (res.ok && data) setStatus({ ...status, ...data, config: data.config || status.config });
    } catch (err) { /* Server nicht erreichbar */ }
    toggling = false;
    if (button) button.classList.remove("menubar__voice--busy");
    refresh();
  }
  function trigger() { return fetch("/api/voice/trigger", { method: "POST" }).catch(() => null); }          // nur fuer Tests / Schnittstelle - der Knopf ist ein Schalter
  document.addEventListener("click", (e) => { if (e.target.closest("#toolbar-voice")) toggle(); });
  document.addEventListener("i18n-applied", paintButton);

  // ---- Nachrichten vom Server
  function onMessage(message) {
    if (message.type === "voice_wake") showListening(message.payload || {});
    else if (message.type === "voice_phase") showPhase(message.payload || {});
    else if (message.type === "voice_state") setStatus(message.payload || status);
  }
  function start() {
    if (typeof client !== "undefined" && client.registerModule) client.registerModule("voice", { onMessage });
    refresh();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();

  window.OCVoice = {
    refresh, trigger, toggle, errorText, showListening, showPhase,
    status: () => status,
    /** Aenderungen des Stands abonnieren (Einstellungen); gibt die Abmeldung zurueck. */
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
  };
})();

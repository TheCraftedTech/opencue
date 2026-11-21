// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Sichermodus: Sperrbildschirm der Konsole und Abmelden an Fernzugriffs-Geraeten. Server: app/remote.py (lock_info, console_unlock), WS `set_lock_config` / `lock_console`, `lock_changed`,
 * POST /api/lock/unlock, POST /auth/logout.
 *
 * - EIN Passwort (Einstellungen -> Sicherheit) fuer Fernzugriff und Sichermodus; es gibt kein Standardpasswort.
 * - Konsole: Sichermodus an -> Schloss in der Kopfleiste, Strg+L, Menue Steuerung -> Sperren. Gesperrt: alles dunkel, nur ein Passwortfenster (Overlay), Tastatur gesperrt, der Server nimmt vom
 *   gesperrten Fenster nichts mehr an. Der Zustand "gesperrt" liegt auf dem Server: ein Neuladen entsperrt nicht (die Seite bekommt die Klasse is-locked schon im HTML).
 *   Die Show laeuft weiter (Cues, MIDI, OSC, Zeitplan, Fernzugriff).
 * - Fernzugriffs-Geraet: der Schloss-Knopf meldet es ab (Sitzung auf dem Server beenden, gemerktes Passwort des Geraets loeschen, Login-Seite) - die Seite bleibt, das Passwortfeld ist leer.
 * - Automatische Sperre nach N Minuten ohne Eingabe (Einstellung, Standard aus): Konsole sperrt, Fernzugriffs-Geraete melden sich ab.
 * Klassisches Skript, laeuft nach app.js. window.OCLock = { sync, lockNow, fillSettings, saveSettings }. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const REMEMBER_KEY = "opencue.rememberedPassword";                 // dasselbe wie die Login-Seite (app/remote.py): "Passwort speichern" liegt nur im Browser dieses Geraets
  const AUTO_CHOICES = [0, 1, 2, 5, 10, 15, 30, 60];
  const isRemote = () => document.documentElement.classList.contains("is-remote");
  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);
  const info = () => (typeof client !== "undefined" && client.state && client.state.lock) || { enabled: false, locked: false, auto_minutes: 0, password_set: false };
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 4000); };

  let overlay = null;
  let waitTimer = null;
  let lastInput = Date.now();
  let idleTimer = null;
  let busy = false;

  // ------------------------------------------------------------------------------------------------ Sperrbildschirm
  function build() {
    if (overlay) return overlay;
    overlay = el("div", "oc-lock");
    overlay.id = "oc-lock";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "oc-lock-title");
    overlay.hidden = true;
    const card = el("form", "oc-lock__card");
    card.autocomplete = "off";
    const icon = el("div", "oc-lock__icon");
    const NS = "http://www.w3.org/2000/svg";                              // Schloss (eigenes SVG: unabhaengig von der Icon-Bibliothek)
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.6");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    const body = document.createElementNS(NS, "rect");
    [["x", "5"], ["y", "11"], ["width", "14"], ["height", "9"], ["rx", "2"]].forEach(([k, v]) => body.setAttribute(k, v));
    const shackle = document.createElementNS(NS, "path");
    shackle.setAttribute("d", "M8 11V8a4 4 0 018 0v3");
    svg.append(body, shackle);
    icon.appendChild(svg);
    const title = el("h2", "oc-lock__title", t("LOCK_TITLE"));
    title.id = "oc-lock-title";
    const hint = el("p", "oc-lock__hint", t("LOCK_PROMPT"));
    const input = document.createElement("input");
    input.type = "password"; input.id = "oc-lock-input"; input.className = "oc-lock__input";
    input.autocomplete = "new-password"; input.maxLength = 64; input.spellcheck = false;
    input.setAttribute("autocapitalize", "off"); input.setAttribute("autocorrect", "off");
    input.setAttribute("aria-label", t("LOCK_PASSWORD"));
    input.placeholder = t("LOCK_PASSWORD");
    const msg = el("div", "oc-lock__msg");
    msg.id = "oc-lock-msg"; msg.setAttribute("role", "alert");
    const ok = el("button", "oc-lock__button", t("LOCK_UNLOCK"));
    ok.type = "submit"; ok.id = "oc-lock-ok";
    card.append(icon, title, hint, input, msg, ok);
    card.addEventListener("submit", (e) => { e.preventDefault(); submit(); });
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    return overlay;
  }

  function relabel() {
    if (!overlay) return;
    overlay.querySelector(".oc-lock__title").textContent = t("LOCK_TITLE");
    overlay.querySelector(".oc-lock__hint").textContent = t("LOCK_PROMPT");
    const input = $("oc-lock-input");
    input.placeholder = t("LOCK_PASSWORD");
    input.setAttribute("aria-label", t("LOCK_PASSWORD"));
    $("oc-lock-ok").textContent = t("LOCK_UNLOCK");
  }

  function show() {
    build();
    document.documentElement.classList.add("is-locked");
    overlay.hidden = false;
    const input = $("oc-lock-input");
    input.value = "";                                                    // nie ein altes Passwort stehen lassen
    $("oc-lock-msg").textContent = "";
    if (document.activeElement && document.activeElement !== input && document.activeElement.blur) document.activeElement.blur();
    setTimeout(() => input.focus(), 30);
  }

  function hide() {
    document.documentElement.classList.remove("is-locked");
    clearInterval(waitTimer);
    waitTimer = null;
    if (overlay) { overlay.hidden = true; $("oc-lock-input").value = ""; $("oc-lock-msg").textContent = ""; }
    lastInput = Date.now();
  }

  /** Waehrend der Pause nach zu vielen Fehlversuchen: Zaehler anzeigen, Eingabe sperren. */
  function startWait(seconds) {
    const input = $("oc-lock-input");
    const ok = $("oc-lock-ok");
    let left = seconds;
    input.disabled = ok.disabled = true;
    clearInterval(waitTimer);
    const tick = () => {
      if (left <= 0) {
        clearInterval(waitTimer); waitTimer = null;
        input.disabled = ok.disabled = false;
        $("oc-lock-msg").textContent = "";
        input.focus();
        return;
      }
      $("oc-lock-msg").textContent = t("LOCK_WAIT", { s: left });
      left -= 1;
    };
    tick();
    waitTimer = setInterval(tick, 1000);
  }

  async function submit() {
    const input = $("oc-lock-input");
    const msg = $("oc-lock-msg");
    if (busy || !input.value) return;
    busy = true;
    const password = input.value;
    input.value = "";                                                    // das Feld wird sofort geleert, egal wie es ausgeht
    let data = {};
    try {
      const res = await fetch("/api/lock/unlock", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
      data = await res.json().catch(() => ({}));
      data.status = res.status;
    } catch (err) { data = { ok: false, error: String(err) }; }
    busy = false;
    if (data.ok) {
      if (client.state && client.state.lock) client.state.lock.locked = false;
      hide();
      return;
    }
    if (data.locked) { startWait(data.locked); return; }
    msg.textContent = data.error && !data.status ? t("LOCK_OFFLINE") : t("LOCK_WRONG");
    overlay.classList.remove("oc-lock--shake");
    void overlay.offsetWidth;                                            // Animation neu starten
    overlay.classList.add("oc-lock--shake");
    input.focus();
  }

  // Gesperrt: keine Tastatur-Eingabe ausserhalb des Passwortfensters (Kuerzel, Befehlszeile, F-Tasten ...)
  const swallow = (e) => {
    if (!document.documentElement.classList.contains("is-locked")) return;
    if (overlay && overlay.contains(e.target)) { e.stopPropagation(); return; }          // im Passwortfeld darf getippt werden, aber kein Kuerzel der Oberflaeche bekommt die Taste
    e.preventDefault();
    e.stopImmediatePropagation();
  };
  ["keydown", "keyup", "keypress"].forEach((type) => window.addEventListener(type, swallow, true));
  document.addEventListener("focusin", (e) => {
    if (!document.documentElement.classList.contains("is-locked") || !overlay || overlay.contains(e.target)) return;
    const input = $("oc-lock-input");
    if (input && !input.disabled) input.focus();
  });
  document.addEventListener("contextmenu", (e) => { if (document.documentElement.classList.contains("is-locked")) e.preventDefault(); });

  // ------------------------------------------------------------------------------------------------ Sperren
  async function logoutRemote() {
    try { localStorage.removeItem(REMEMBER_KEY); } catch (err) { /* privater Modus */ }              // das gemerkte Passwort dieses Geraets muss weg, sonst waere "Sperren" sinnlos
    try { await fetch("/auth/logout", { method: "POST" }); } catch (err) { /* offline: trotzdem neu laden */ }
    location.reload();                                                   // ohne Sitzung zeigt der Server die Login-Seite (leeres Passwortfeld)
  }

  /** Sperren. Am Fernzugriffs-Geraet: abmelden. An der Konsole: nur mit eingeschaltetem Sichermodus; sonst ein Hinweis (und die Einstellung). */
  function lockNow(fromUser) {
    if (isRemote()) { logoutRemote(); return true; }
    const lock = info();
    if (!lock.enabled || !lock.password_set) {
      if (fromUser) {
        toast(t("LOCK_OFF_HINT"), "warn");
        const opener = el("button"); opener.hidden = true; opener.dataset.action = "open-settings-modal"; opener.dataset.settingsCategory = "security";
        document.body.appendChild(opener); opener.click(); opener.remove();
      }
      return false;
    }
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    client.send("lock_console", {});
    return true;
  }

  // ------------------------------------------------------------------------------------------------ Zustand
  function paintButton() {
    const btn = $("toolbar-lock");
    if (!btn) return;
    const lock = info();
    btn.hidden = !(isRemote() || (isLocal() && lock.enabled && lock.password_set));
    btn.title = isRemote() ? t("LOCK_LOGOUT") : t("LOCK_BUTTON");
  }

  /** Nach jedem Zustand / jeder Aenderung des Sichermodus (app.js): Knopf, Sperrbildschirm und automatische Sperre abgleichen. */
  function sync() {
    paintButton();
    const lock = info();
    if (isLocal()) {
      if (lock.locked && lock.enabled) show();
      else if (document.documentElement.classList.contains("is-locked")) hide();
    }
    const active = lock.enabled && lock.auto_minutes > 0 && (isRemote() || isLocal());
    if (active && !idleTimer) idleTimer = setInterval(checkIdle, 5000);
    if (!active && idleTimer) { clearInterval(idleTimer); idleTimer = null; }
    syncSettings();
  }

  function checkIdle() {
    const lock = info();
    if (!lock.enabled || !(lock.auto_minutes > 0) || document.documentElement.classList.contains("is-locked")) return;
    if (Date.now() - lastInput >= lock.auto_minutes * 60000) { lastInput = Date.now(); lockNow(false); }
  }
  ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"].forEach((type) => document.addEventListener(type, () => { lastInput = Date.now(); }, { capture: true, passive: true }));

  // ------------------------------------------------------------------------------------------------ Einstellungen -> Sicherheit
  function fillAutoOptions(select) {
    const current = select.value;
    select.textContent = "";
    AUTO_CHOICES.forEach((n) => { const o = document.createElement("option"); o.value = String(n); o.textContent = n === 0 ? t("SEC_AUTO_OFF") : t("SEC_AUTO_N", { n }); select.appendChild(o); });
    select.value = current || "0";
  }

  function syncSettings() {
    const category = $("settings-security-category");
    if (category) category.hidden = false;                                  // auch am Fernzugriffs-Geraet einstellbar
    const enabled = $("settings-lock-enabled");
    const minutes = $("settings-lock-minutes");
    if (minutes) { minutes.disabled = !(enabled && enabled.checked); const row = minutes.closest(".settings-field"); if (row) row.classList.toggle("settings-field--off", minutes.disabled); }
  }

  function fillSettings() {
    const lock = info();
    const enabled = $("settings-lock-enabled");
    const minutes = $("settings-lock-minutes");
    if (!enabled || !minutes) return;
    fillAutoOptions(minutes);
    enabled.checked = !!lock.enabled;
    minutes.value = String(lock.auto_minutes || 0);
    syncSettings();
  }

  function saveSettings() {
    const enabled = $("settings-lock-enabled");
    const minutes = $("settings-lock-minutes");
    if (!enabled || !minutes) return;
    const lock = info();
    const want = { enabled: enabled.checked, auto_minutes: parseInt(minutes.value, 10) || 0 };
    if (want.enabled === !!lock.enabled && want.auto_minutes === (lock.auto_minutes || 0)) return;
    client.send("set_lock_config", want);
  }

  document.addEventListener("change", async (e) => {
    if (!e.target) return;
    if (e.target.id === "settings-lock-enabled") {
      const password = $("settings-remote-password");
      if (e.target.checked && password && !password.value && typeof _askRemotePassword === "function") {        // Sichermodus braucht ein Passwort: erst eins festlegen
        const chosen = await _askRemotePassword();
        if (chosen === null) { e.target.checked = false; if (window.OCSettings) window.OCSettings.touch(); }          // abgebrochen: Schalter zurueck UND die Aenderungs-Zaehlung nachfuehren
        else {
          password.value = chosen;
          password.dispatchEvent(new Event("input", { bubbles: true }));
          password.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      syncSettings();
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target || !e.target.closest) return;
    if (e.target.closest('[data-action="lock-console"]')) { lockNow(true); return; }
    if (e.target.closest("#toolbar-lock")) { lockNow(true); return; }
    if (e.target.closest("#settings-remote-password-open")) {                                // Fernzugriff -> "Passwort festlegen / aendern": zur Kategorie Sicherheit
      const nav = document.querySelector('.modal--settings [data-settings-category="security"]');
      if (nav && !nav.hidden) { nav.click(); setTimeout(() => { const p = $("settings-remote-password"); if (p) p.focus(); }, 80); }
    }
  });
  document.addEventListener("i18n-applied", () => { relabel(); paintButton(); const minutes = $("settings-lock-minutes"); if (minutes) fillAutoOptions(minutes); });

  window.OCLock = { sync, lockNow, fillSettings, saveSettings };
})();

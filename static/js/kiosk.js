// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Bedienmodus (Kiosk): dieses Geraet darf nur noch BEDIENEN - der Layoutinhalt bleibt, alles andere ist gesperrt: keine Menues / Werkzeugleiste, keine Dialoge (Einstellungen ...),
 * keine Tastenkuerzel, kein Verschieben / Umbauen von Panels, kein Layout- oder Show-Wechsel. Verlassen nur mit dem Passwort (Schloss unten rechts).
 * Server: app/remote.py (KIOSK_ALLOWED_*, verify_password), WS `kiosk_enter` / `kiosk_changed`, POST /api/kiosk/exit; der Server nimmt vom Geraet im Bedienmodus nur Bedien-Nachrichten
 * an (alles andere wird verworfen, schreibende HTTP-Anfragen: 423) - die Sperre gilt also auch an der Oberflaeche vorbei. Der Zustand liegt auf dem Server (Konsole bzw. Fernzugriffs-Geraet):
 * ein Neuladen verlaesst den Bedienmodus nicht (die Seite bekommt die Klasse is-kiosk schon im HTML). Gedacht zusammen mit dem Panel "Einfache Steuerung".
 * Klassisches Skript, laeuft nach app.js. window.OCKiosk = { sync, enter, active }. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const root = () => document.documentElement;
  const active = () => root().classList.contains("is-kiosk");
  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);
  const passwordSet = () => !!(typeof client !== "undefined" && client.state && ((client.state.remote && client.state.remote.password_set) || (client.state.lock && client.state.lock.password_set)));
  const toast = (text, kind) => { if (typeof _showToast === "function") _showToast(text, kind || "info", 4500); };
  const NS = "http://www.w3.org/2000/svg";

  function lockIcon() {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("fill", "none"); svg.setAttribute("stroke", "currentColor"); svg.setAttribute("stroke-width", "1.8");
    svg.setAttribute("stroke-linecap", "round"); svg.setAttribute("stroke-linejoin", "round"); svg.setAttribute("aria-hidden", "true");
    const body = document.createElementNS(NS, "rect");
    [["x", "5"], ["y", "11"], ["width", "14"], ["height", "9"], ["rx", "2"]].forEach(([k, v]) => body.setAttribute(k, v));
    const shackle = document.createElementNS(NS, "path");
    shackle.setAttribute("d", "M8 11V8a4 4 0 018 0v3");
    svg.append(body, shackle);
    return svg;
  }

  // ------------------------------------------------------------------------------------------------ kleine Karte (Bestaetigung / Passwort)
  let card = null;
  let waitTimer = null;
  function closeCard() {
    clearInterval(waitTimer); waitTimer = null;
    if (card) { card.remove(); card = null; }
  }
  /** Karte ueber allem: Titel, Text, optional Passwortfeld, Knoepfe. onOk(passwordOrNull, helpers) darf ein Promise liefern; true = schliessen. */
  function showCard({ title, body, password, okText, onOk }) {
    closeCard();
    card = el("div", "oc-kiosk-card");
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    const box = el("form", "oc-kiosk-card__box");
    box.autocomplete = "off";
    box.append(el("h2", "oc-kiosk-card__title", title), el("p", "oc-kiosk-card__body", body));
    let input = null;
    if (password) {
      input = document.createElement("input");
      input.type = "password"; input.className = "oc-kiosk-card__input"; input.autocomplete = "new-password"; input.maxLength = 64; input.placeholder = t("LOCK_PASSWORD"); input.setAttribute("aria-label", t("LOCK_PASSWORD"));
      box.appendChild(input);
    }
    const msg = el("div", "oc-kiosk-card__msg");
    msg.setAttribute("role", "alert");
    const row = el("div", "oc-kiosk-card__row");
    const cancel = el("button", "oc-kiosk-card__btn", t("CANCEL")); cancel.type = "button";
    const ok = el("button", "oc-kiosk-card__btn oc-kiosk-card__btn--primary", okText); ok.type = "submit";
    row.append(cancel, ok);
    box.append(msg, row);
    card.appendChild(box);
    document.body.appendChild(card);
    const helpers = {
      error(text) { msg.textContent = text; },
      wait(seconds) {
        let left = seconds;
        if (input) input.disabled = true;
        ok.disabled = true;
        clearInterval(waitTimer);
        const tick = () => {
          if (left <= 0) { clearInterval(waitTimer); waitTimer = null; msg.textContent = ""; if (input) { input.disabled = false; input.focus(); } ok.disabled = false; return; }
          msg.textContent = t("LOCK_WAIT", { s: left }); left -= 1;
        };
        tick(); waitTimer = setInterval(tick, 1000);
      },
    };
    cancel.addEventListener("click", closeCard);
    box.addEventListener("submit", async (e) => {
      e.preventDefault();
      const value = input ? input.value : null;
      if (input) input.value = "";                                            // das Feld wird sofort geleert
      if (input && !value) return;
      if (await onOk(value, helpers)) closeCard();
      else if (input && !input.disabled) input.focus();
    });
    setTimeout(() => (input || ok).focus(), 30);
  }

  // ------------------------------------------------------------------------------------------------ Einschalten / Verlassen
  function enter() {
    if (active()) return;
    if (!passwordSet()) {
      toast(t("KIOSK_NEEDS_PASSWORD"), "warn");
      if (isLocal() && typeof _closeAllMenus === "function") {
        _closeAllMenus();
        const opener = el("button"); opener.hidden = true; opener.dataset.action = "open-settings-modal"; opener.dataset.settingsCategory = "security";
        document.body.appendChild(opener); opener.click(); opener.remove();
      }
      return;
    }
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    showCard({ title: t("KIOSK_TITLE"), body: t("KIOSK_ENTER_BODY"), okText: t("KIOSK_START"), onOk: async () => { client.send("kiosk_enter", {}); return true; } });
  }

  function askExit() {
    showCard({
      title: t("KIOSK_EXIT_TITLE"), body: t("KIOSK_EXIT_BODY"), password: true, okText: t("KIOSK_EXIT_OK"),
      async onOk(password, helpers) {
        let data = {};
        try {
          const res = await fetch("/api/kiosk/exit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
          data = await res.json().catch(() => ({}));
          data.status = res.status;
        } catch (err) { data = { ok: false, error: String(err) }; }
        if (data.ok) { if (client.state) client.state.kiosk = false; sync(); return true; }
        if (data.locked) { helpers.wait(data.locked); return false; }
        helpers.error(data.error && !data.status ? t("LOCK_OFFLINE") : t("LOCK_WRONG"));
        return false;
      },
    });
  }

  // ------------------------------------------------------------------------------------------------ Sperren im Bedienmodus
  let installed = false;
  const FKEY = /^F[0-9]{1,2}$/;
  function install() {
    if (installed) return;
    installed = true;
    const swallow = (e) => {
      const k = String(e.key || "").toLowerCase();
      const combo = e.type === "keydown" && (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && k === "l";                 // Strg+L im Bedienmodus: Passwortkarte zum Verlassen (gestartet wird nur ueber Menue / Knopf)
      if (combo && active()) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (!e.repeat && !card) askExit();
        return;
      }
      if (!active()) return;
      const typing = e.target && e.target.closest && e.target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']");
      if (typing && !e.ctrlKey && !e.metaKey && !e.altKey && !FKEY.test(e.key || "")) return;          // Tippen in einem Feld (z. B. Befehlszeile) bleibt moeglich
      e.preventDefault();
      e.stopImmediatePropagation();
    };
    ["keydown", "keyup", "keypress"].forEach((type) => window.addEventListener(type, swallow, true));
    document.addEventListener("contextmenu", (e) => { if (active()) e.preventDefault(); });
    if (typeof Modal !== "undefined" && Modal.open && !Modal.__kiosk) {                                     // keine Dialoge (Einstellungen, Dateimanager ...)
      const original = Modal.open;
      Modal.open = function (...args) { if (active()) return undefined; return original.apply(this, args); };
      Modal.__kiosk = true;
    }
  }

  // ------------------------------------------------------------------------------------------------ Anzeige
  function paint() {
    const button = $("toolbar-kiosk");
    if (button) button.hidden = !(passwordSet() && !active());
    let exit = $("kiosk-exit");
    if (active()) {
      if (!exit) {
        exit = el("button", "oc-kiosk-exit"); exit.id = "kiosk-exit"; exit.type = "button";
        exit.title = t("KIOSK_EXIT_BTN"); exit.setAttribute("aria-label", t("KIOSK_EXIT_BTN"));
        exit.appendChild(lockIcon());
        exit.addEventListener("click", askExit);
        document.body.appendChild(exit);
      }
    } else if (exit) {
      exit.remove();
    }
  }

  /** Nach jedem Zustand / jeder Aenderung (app.js): Klasse, Sperren und Knoepfe abgleichen. */
  function sync() {
    const on = !!(typeof client !== "undefined" && client.state && client.state.kiosk);
    root().classList.toggle("is-kiosk", on);
    if (on) { install(); closeCard(); if (typeof _closeAllMenus === "function") _closeAllMenus(); if (typeof Modal !== "undefined") while (Modal._stack && Modal._stack.length) Modal.closeTop(); }
    paint();
  }

  document.addEventListener("click", (e) => {
    if (!e.target || !e.target.closest) return;
    if (e.target.closest('[data-action="kiosk-enter"]') || e.target.closest("#toolbar-kiosk")) enter();
  });
  document.addEventListener("i18n-applied", paint);
  install();
  window.OCKiosk = { sync, enter, active };
})();

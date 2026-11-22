// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Willkommens-Dialog beim allerersten Start und "Was ist neu?" nach einem Update.
 * Willkommen: vier Seiten zum Durchklicken (Sprache / DMX-Ausgabe / andere Geraete / fertig). Der Dialog laesst sich nicht schliessen (kein X, Escape tut nichts): man klickt sich durch oder
 * drueckt auf der ersten Seite "Ueberspringen". Hier laesst sich z. B. das Netzwerk gleich einschalten - nichts davon passiert ohne ausdrueckliche Eingabe (die Schalter stehen anfangs alle aus),
 * und Windows darf dann fragen. Angewendet wird erst mit "Fertig". Server: state.onboarding_pending (nur frische Installation, main.py), WS `onboarding_done`.
 * Was ist neu: das Fenster aus static/js/whatsnew.js (Texte static/whatsnew/<sprache>.json) oeffnet sich einmal nach einem Update (state.whats_new_pending), WS `whats_new_seen`; auch im Hilfe-Menue. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "welcome";
  const STEPS = 4;

  let step = 0;
  const choice = { artnet: false, usb: false, remote: false, password: "", osc: false };

  const isLocal = () => !!(typeof client !== "undefined" && client.state && client.state.is_local);

  function switchRow(id, label, hint, checked, onChange) {
    const row = el("div", "welcome__row");
    const text = el("div", "welcome__row-text");
    text.append(el("div", "welcome__row-name", label), el("div", "welcome__row-hint", hint));
    const sw = el("label", "toggle-switch");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.id = id;
    box.checked = !!checked;
    box.addEventListener("change", () => onChange(box.checked));
    sw.append(box, el("span", "toggle-switch__track"));
    row.append(text, sw);
    return row;
  }

  function render() {
    const body = $("welcome-body");
    body.textContent = "";
    const dots = $("welcome-dots");
    dots.textContent = "";
    for (let i = 0; i < STEPS; i += 1) dots.appendChild(el("span", "welcome__dot" + (i === step ? " welcome__dot--on" : "")));
    $("welcome-title").textContent = t("WELCOME_T" + (step + 1));
    body.appendChild(el("p", "welcome__intro", t("WELCOME_P" + (step + 1))));
    if (step === 0) {
      const langs = el("div", "welcome__langs");
      (window.OC_LANGUAGES || [{ code: "en", name: "English" }, { code: "de", name: "Deutsch" }]).forEach(({ code, name: label }) => {
        const b = el("button", "modal__button welcome__lang" + (typeof translator !== "undefined" && translator.language === code ? " modal__button--primary" : ""), label);
        b.type = "button";
        b.addEventListener("click", () => { client.send("set_language", { language: code }); setTimeout(render, 250); });
        langs.appendChild(b);
      });
      body.appendChild(langs);
    } else if (step === 1) {
      body.appendChild(switchRow("welcome-artnet", t("WELCOME_ARTNET"), t("WELCOME_ARTNET_HINT"), choice.artnet, (v) => { choice.artnet = v; }));
      body.appendChild(switchRow("welcome-usb", t("WELCOME_USB"), t("WELCOME_USB_HINT"), choice.usb, (v) => { choice.usb = v; }));
      body.appendChild(el("p", "welcome__note", t("WELCOME_FIREWALL")));
    } else if (step === 2) {
      body.appendChild(switchRow("welcome-remote", t("WELCOME_REMOTE"), t("WELCOME_REMOTE_HINT"), choice.remote, (v) => { choice.remote = v; render(); }));
      if (choice.remote) {
        const wrap = el("div", "welcome__pw");
        wrap.appendChild(el("label", "welcome__pw-label", t("WELCOME_PASSWORD")));
        const input = document.createElement("input");
        input.type = "text";
        input.id = "welcome-password";
        input.maxLength = 64;
        input.autocomplete = "off";
        input.spellcheck = false;
        input.placeholder = t("WELCOME_PASSWORD_PH");
        input.value = choice.password;
        input.addEventListener("input", () => { choice.password = input.value; validate(); });
        wrap.appendChild(input);
        wrap.appendChild(el("div", "welcome__pw-hint", t("WELCOME_PASSWORD_HINT")));
        body.appendChild(wrap);
      }
      body.appendChild(switchRow("welcome-osc", t("WELCOME_OSC"), t("WELCOME_OSC_HINT"), choice.osc, (v) => { choice.osc = v; }));
      body.appendChild(el("p", "welcome__note", t("WELCOME_FIREWALL")));
    } else {
      const list = el("ul", "welcome__summary");
      const on = [];
      if (choice.artnet) on.push(t("WELCOME_SUM_ARTNET"));
      if (choice.usb) on.push(t("WELCOME_SUM_USB"));
      if (choice.remote) on.push(t("WELCOME_SUM_REMOTE"));
      if (choice.osc) on.push(t("WELCOME_SUM_OSC"));
      (on.length ? on : [t("WELCOME_SUM_NONE")]).forEach((s) => list.appendChild(el("li", "", s)));
      body.appendChild(list);
      body.appendChild(el("p", "welcome__note", t("WELCOME_LATER")));
    }
    $("welcome-skip").hidden = step !== 0;
    $("welcome-back").hidden = step === 0;
    $("welcome-next").textContent = t(step === STEPS - 1 ? "WELCOME_FINISH" : "WELCOME_NEXT");
    validate();
  }

  function validate() {
    let ok = true;
    if (step === 2 && choice.remote) {
      const pw = choice.password;
      ok = pw.length >= 4;
      const hint = document.querySelector(".welcome__pw-hint");
      if (hint) hint.classList.toggle("welcome__pw-hint--bad", !ok && pw.length > 0);
    }
    $("welcome-next").disabled = !ok;
  }

  async function finish() {
    $("welcome-next").disabled = true;
    if (choice.artnet) client.send("set_artnet_enabled", { enabled: true });
    if (choice.usb) client.send("set_enttec_enabled", { enabled: true });
    if (choice.remote) {
      client.send("set_remote_password", { password: choice.password });
      client.send("set_remote_enabled", { enabled: true });
    }
    if (choice.osc) {
      try {
        const cfg = (await (await fetch("/api/osc")).json()).config;
        await fetch("/api/osc/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...cfg, enabled: true }) });
      } catch (e) { /* offline */ }
    }
    done();
  }

  function done() {
    client.send("onboarding_done", {});
    if (client.state) client.state.onboarding_pending = false;
    Modal.close(MODAL);
  }

  function open() {
    step = 0;
    Object.assign(choice, { artnet: false, usb: false, remote: false, password: "", osc: false });
    Modal._escape = Modal._escape || {};
    Modal._escape[MODAL] = () => {};                                   // Escape schliesst den Willkommens-Dialog nicht
    Modal.open(MODAL);
    render();
  }

  function bind() {
    const root = document.querySelector('[data-modal-backdrop="welcome"]');
    if (!root || root.dataset.bound) return;
    root.dataset.bound = "1";
    $("welcome-next").addEventListener("click", () => { if (step < STEPS - 1) { step += 1; render(); } else finish(); });
    $("welcome-back").addEventListener("click", () => { if (step > 0) { step -= 1; render(); } });
    $("welcome-skip").addEventListener("click", done);
    document.addEventListener("i18n-applied", () => { if (Modal.isOpen(MODAL)) render(); });
  }

  // ------------------------------------------------------------------------------------------------ Was ist neu?
  function openWhatsNew() {
    if (typeof _closeAllMenus === "function") _closeAllMenus();
    if (window.OCWhatsNew) window.OCWhatsNew.open();
    if (typeof client !== "undefined" && client.state && client.state.whats_new_pending) { client.state.whats_new_pending = false; client.send("whats_new_seen", {}); }
  }

  /** Nach dem ersten Zustand (app.js): Willkommen bei einer frischen Installation, sonst "Was ist neu?" einmal nach einem Update - nur an der Konsole selbst. */
  function onReady() {
    bind();
    if (!isLocal()) return;
    if (client.state.onboarding_pending) open();
    else if (client.state.whats_new_pending) openWhatsNew();
  }

  document.addEventListener("click", (e) => { if (e.target.closest('[data-action="open-whats-new"]')) openWhatsNew(); });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
  window.OCWelcome = { onReady, open, openWhatsNew };
})();

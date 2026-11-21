// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Einstellungen -> Kategorie "Ein- & Ausgaenge" (nur an der Konsole selbst; Server: app/io_overview.py). Reine Anzeige: ALLE Ein- und Ausgaenge, die OpenCue gerade benutzt, und
 * wofuer - DMX-Ausgabe (Art-Net, sACN, Enttec, Universen), Netzwerk (Fernzugriff, Netzwerk-Name, REST-API, verbundene Geraete), Audio-Eingaenge (Triggerwort, Diktieren, Audio-Analyse),
 * Tastaturen und KI-Server / Stream-Quellen. Darunter alle Audio-Geraete, die der Computer hat. Der Stand wird aktualisiert, solange die Seite offen ist.
 * Hier wird nichts eingestellt (kein Entwurf, kein Speichern). Klassisches Skript, laeuft nach settings_tracker.js. */
(function () {
  "use strict";
  const t = (key, vars) => { let s = i18n(key); if (vars) for (const [k, v] of Object.entries(vars)) s = s.split("{" + k + "}").join(String(v)); return s; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const root = () => document.getElementById("settings-io-root");
  const visible = () => { const r = root(); return !!(r && r.offsetParent); };
  /** Kurze Ursache zu einem Fehler-Code des Servers (app/net_diag.py). */
  function netError(code) {
    if (/^http_\d+$/.test(code || "")) return t("NET_ERR_HTTP", { n: code.slice(5) });
    const key = "NET_ERR_" + String(code || "network").toUpperCase();
    const text = i18n(key);
    return text === key ? t("NET_ERR_NETWORK") : text;
  }
  const NET_STAGES = { dns: "NET_STAGE_DNS", tcp: "NET_STAGE_TCP", tls: "NET_STAGE_TLS" };

  /** "Verbindung testen" (Allgemein): Update-Server und GDTF Share, mit der Stufe, an der es scheitert. */
  async function netTest() {
    const list = document.getElementById("settings-net-result");
    const button = document.getElementById("settings-net-test");
    if (!list || !button) return;
    button.disabled = true;
    list.textContent = "";
    list.appendChild(el("li", "net-result__row", t("NET_TESTING")));
    let data = null;
    try { data = await (await fetch("/api/net-check", { method: "POST", cache: "no-store" })).json(); } catch (err) { data = null; }
    list.textContent = "";
    button.disabled = false;
    if (!data || !data.results) { list.appendChild(el("li", "net-result__row net-result__row--bad", t("NET_ERR_NETWORK"))); return; }
    data.results.forEach((r) => {
      const row = el("li", "net-result__row net-result__row--" + (r.ok ? "ok" : "bad"));
      row.appendChild(el("span", "net-result__name", t(r.service === "gdtf" ? "NET_SERVICE_GDTF" : "NET_SERVICE_UPDATE") + " (" + r.host + ")"));
      const what = r.ok ? t("NET_OK", { ms: r.ms }) : [netError(r.code), r.stage ? t("NET_AT", { stage: t(NET_STAGES[r.stage] || "NET_STAGE_TCP") }) : ""].filter(Boolean).join(" · ");
      row.appendChild(el("span", "net-result__what", what));
      if (!r.ok && (r.direct_detail || r.detail)) row.appendChild(el("span", "net-result__detail", r.direct_detail || r.detail));
      list.appendChild(row);
    });
    if (data.proxy) list.appendChild(el("li", "net-result__row", t("NET_PROXY", { p: data.proxy })));
  }
  document.addEventListener("click", (e) => { if (e.target && e.target.id === "settings-net-test") netTest(); });

  let overview = null;
  let devices = null;
  let timer = 0;

  /** Beide Mikrofon-Zeilen (Triggerwort, Diktieren) heissen gleich: "Standard-Mikrofon von Windows -> <aktuelles Geraet>" oder der gewaehlte Name. */
  function micName(r) {
    if (!r.extra.default) return r.name || t("IOV_N_DEFAULT_MIC");
    return r.name ? t("IOV_N_DEFAULT_MIC") + " \u2192 " + r.name : t("IOV_N_DEFAULT_MIC");
  }

  // Rolle -> [Schluessel der Beschreibung ("wofuer"), Funktion fuer den Zusatztext, Funktion fuer den Namen (sonst row.name)]
  const none = () => "";
  const ROLES = {
    artnet: ["IOV_ROLE_ARTNET", (r) => (r.extra.bind ? t("IOV_D_BIND", { ip: r.extra.bind }) : ""), (r) => (r.name === "-" ? t("IOV_N_UNSET") : r.name)],
    sacn: ["IOV_ROLE_SACN", none, () => t("IOV_N_MULTICAST")],
    dmx_in: ["IOV_ROLE_DMXIN", (r) => r.extra.error || ""],
    enttec: ["IOV_ROLE_ENTTEC", (r) => [t("IOV_D_UNIVERSE", { n: r.extra.universe }), r.extra.error].filter(Boolean).join(" · "), (r) => (r.name === "-" ? t("IOV_N_UNSET") : r.name)],
    universe: ["IOV_ROLE_UNIVERSE", (r) => t("IOV_D_FIXTURES", { n: r.extra.fixtures }), (r) => t("IOV_N_UNIVERSE", { n: r.name })],
    local_server: ["IOV_ROLE_LOCAL", none],
    remote_http: ["IOV_ROLE_HTTP", (r) => r.extra.error || "", (r) => (r.name.startsWith(":") && r.state === "off" ? t("IOV_N_PORT", { p: r.name.slice(1) }) : r.name)],
    remote_https: ["IOV_ROLE_HTTPS", (r) => r.extra.error || "", (r) => (r.name.startsWith(":") && r.state === "off" ? t("IOV_N_PORT", { p: r.name.slice(1) }) : r.name)],
    mdns: ["IOV_ROLE_MDNS", (r) => r.extra.error || ""],
    rest_api: ["IOV_ROLE_API", (r) => (r.extra.needs_remote ? t("IOV_D_NEEDS_REMOTE") : "")],
    clients: ["IOV_ROLE_CLIENTS", none, (r) => t("IOV_N_CLIENTS", { n: r.extra.count })],
    wake_mic: ["IOV_ROLE_WAKE", (r) => [r.state === "off" ? t("IOV_D_WAKE_OFF") : "", r.extra.error ? t("IOV_D_ERROR", { e: window.OCVoice ? window.OCVoice.errorText(r.extra.error) : r.extra.error }) : ""].filter(Boolean).join(" · "),
      micName, (r) => ({ word: r.extra.word || "OpenCue" })],
    dictation_mic: ["IOV_ROLE_DICT", none, micName],
    audio_analysis: ["IOV_ROLE_ANALYSIS", none, (r) => r.name || r.extra.configured || t("IOV_N_NONE")],
    clock: ["IOV_ROLE_CLOCK", none, (r) => t("IOV_N_CLOCK_" + String(r.name).toUpperCase())],
    ltc_in: ["IOV_ROLE_LTC_IN", (r) => (r.extra.error ? t("IOV_D_ERROR", { e: r.extra.error }) : (r.extra.locked ? t("IOV_D_LTC_LOCKED", { tc: r.extra.timecode }) : "")), (r) => (r.name === "-" ? t("IOV_N_UNSET") : r.name)],
    ltc_out: ["IOV_ROLE_LTC_OUT", (r) => (r.extra.error ? t("IOV_D_ERROR", { e: r.extra.error }) : t("IOV_D_LTC_FPS", { fps: String(r.extra.fps).replace(".", ",") })), (r) => (r.name === "-" ? t("IOV_N_UNSET") : r.name)],
    mtc_in: ["IOV_ROLE_MTC_IN", none, () => t("IOV_N_MIDI_ALL")],
    mtc_out: ["IOV_ROLE_MTC_OUT", none, () => t("IOV_N_MIDI_OUTPUT")],
    keyboard_all: ["IOV_ROLE_KB_ALL", (r) => t("IOV_D_HOTKEYS", { n: r.extra.count }), () => t("IOV_N_ALL_KB")],
    keyboard_device: ["IOV_ROLE_KB_DEVICE", (r) => [t("IOV_D_HOTKEYS", { n: r.extra.count }), r.extra.connected ? "" : t("IOV_D_NOT_CONNECTED")].filter(Boolean).join(" · ")],
    keyboard_idle: ["IOV_ROLE_KB_IDLE", none],
    midi_map: ["IOV_ROLE_MIDI_MAP", (r) => (r.extra.error ? t("IOV_D_MIDI_LIB", { e: r.extra.error }) : (r.extra.enabled === false ? t("IOV_D_MIDI_OFF") : t("IOV_D_MIDI_BINDINGS", { n: r.extra.count }))), () => t("IOV_N_MIDI_MAP")],
    midi_in: ["IOV_ROLE_MIDI_IN", (r) => (r.extra.error ? t("IOV_D_MIDI_BUSY") : (r.extra.open ? t("IOV_D_MIDI_OPEN") : t("IOV_D_MIDI_IDLE")))],
    midi_in_none: ["IOV_ROLE_MIDI_NONE", none, () => t("IOV_N_MIDI_NO_DEVICE")],
    midi_out: ["IOV_ROLE_MIDI_OUT", (r) => t("IOV_D_MIDI_OUTS", { n: r.extra.count })],
    ai_server: ["IOV_ROLE_AI", (r) => (r.extra.model ? t("IOV_D_MODEL", { m: r.extra.model }) : "")],
    stream: ["IOV_ROLE_STREAM", (r) => r.extra.type || ""],
    update: ["IOV_ROLE_UPDATE", (r) => (r.extra.error_code ? t("IOV_D_NET_ERR", { e: netError(r.extra.error_code) }) : "")],
    gdtf: ["IOV_ROLE_GDTF", (r) => [r.extra.logged_in ? t("IOV_D_GDTF_IN") : t("IOV_D_ON_CLICK"), r.extra.error_code ? t("IOV_D_NET_ERR", { e: netError(r.extra.error_code) }) : ""].filter(Boolean).join(" · ")],
  };

  /** "Einstellen": springt zu der Kategorie, in der man es aendert. */
  function goto(row) {
    const holder = el("span", "io-row__goto");
    if (!row.link) return holder;
    const button = el("button", "modal__button--link", t("IOV_GOTO"));
    button.type = "button";
    button.addEventListener("click", () => {
      if (row.link === "midi-dialog") { if (window.OCMidi) window.OCMidi.open(); return; }          // kein Einstellungsbereich: der Dialog "MIDI-Belegung"
      const b = document.querySelector('.modal--settings [data-settings-category="' + row.link + '"]');
      if (b && !b.hidden) b.click();
    });
    holder.appendChild(button);
    return holder;
  }

  function line(row) {
    const spec = ROLES[row.role];
    const li = el("li", "io-row io-row--" + row.state);
    const dot = el("span", "io-row__dot");
    dot.title = t("IOV_STATE_" + row.state.toUpperCase());
    const name = el("span", "io-row__name", spec && spec[2] ? spec[2](row) : row.name);
    const what = spec ? t(spec[0], spec[3] ? spec[3](row) : null) : row.role;
    const meta = [what, spec && spec[1] ? spec[1](row) : ""].filter(Boolean).join(" · ");
    const reach = el("span", "io-reach io-reach--" + row.reach, row.reach === "none" ? "" : t("IOV_REACH_" + row.reach.toUpperCase()));
    li.append(dot, name, el("span", "io-row__what", meta), reach, goto(row));
    return li;
  }

  function render() {
    const host = root();
    if (!host) return;
    host.textContent = "";
    const used = el("div", "settings-section");
    used.appendChild(el("div", "settings-section__title", t("IOV_USED")));
    used.appendChild(el("p", "ai-row__hint", t("IOV_USED_HINT")));
    if (!overview) used.appendChild(el("p", "ai-row__hint", "..."));
    (overview ? overview.groups : []).forEach((group) => {
      used.appendChild(el("div", "io-group__title", t("IOV_G_" + group.id.toUpperCase())));
      const list = el("ul", "io-rows");
      group.rows.forEach((row) => list.appendChild(line(row)));
      used.appendChild(list);
    });
    host.appendChild(used);

    const all = el("div", "settings-section");
    all.appendChild(el("div", "settings-section__title", t("IO_SECTION")));
    all.appendChild(el("p", "ai-row__hint", t("IO_SECTION_HINT")));
    [["inputs", "IO_INPUTS"], ["outputs", "IO_OUTPUTS"], ["loopbacks", "IO_LOOPBACKS"]].forEach(([key, labelKey]) => {
      all.appendChild(el("div", "io-group__title", t(labelKey)));
      const list = el("ul", "io-list");
      const items = (devices && devices[key]) || [];
      if (!items.length) list.appendChild(el("li", "", devices ? t("IO_NONE") : "..."));
      items.forEach((d) => {
        const li = el("li");
        li.appendChild(el("span", "io-list__name", d.name));
        li.appendChild(el("span", "io-list__meta", (d.channels ? d.channels + " ch · " : "") + (d.rate ? d.rate + " Hz" : "")));
        if (d.default) li.appendChild(el("span", "io-list__default", t("IO_DEFAULT")));
        list.appendChild(li);
      });
      all.appendChild(list);
    });
    const refresh = el("button", "modal__button", t("IO_REFRESH"));
    refresh.type = "button";
    refresh.id = "settings-io-refresh";
    refresh.addEventListener("click", () => load(true));
    all.appendChild(refresh);
    host.appendChild(all);
  }

  async function load(withDevices) {
    try { overview = await (await fetch("/api/io-overview", { cache: "no-store" })).json(); } catch (err) { return; }
    if (withDevices || !devices) {
      try { devices = await (await fetch("/api/audio/io", { cache: "no-store" })).json(); } catch (err) { /* bleibt wie es war */ }
    }
    if (visible()) render();
  }
  function schedule() {
    clearInterval(timer);
    timer = setInterval(() => { if (!visible()) { clearInterval(timer); return; } load(false); }, 3000);       // solange die Seite offen ist, bleibt der Stand aktuell
  }

  document.addEventListener("settings-category-shown", (e) => { if (e.detail && e.detail.category === "io") { overview = null; render(); load(true); schedule(); } });
  document.addEventListener("i18n-applied", () => { if (visible()) render(); });
  window.OCIoOverview = { load, render };
})();

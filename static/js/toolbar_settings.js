// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * Toolbar-Einstellungen: was oben rechts in der Menueleiste angezeigt wird.
 *
 * - Pro Geraet (localStorage "opencue.toolbar" = Liste der ABGESCHALTETEN Eintraege; leer = alles wie bisher sichtbar).
 * - Ausgeblendet wird rein ueber CSS: html.tb-off-<name> (static/css/modern.css). Die Elemente selbst arbeiten weiter
 *   (Timecode, Blackout, Sprachsteuerung usw. laufen unabhaengig davon, ob ihr Symbol zu sehen ist).
 * - Das Zahnrad (Einstellungen) gehoert nicht dazu und ist immer sichtbar.
 * - Die Schalter im Einstellungsdialog sind feste Zeilen (Allgemein): Aenderungszaehler / Zuruecksetzen kommen aus settings_tracker.js,
 *   die Werte werden mit "Speichern" uebernommen (app.js ruft fillSettings() / saveSettings()).
 */
(() => {
  "use strict";

  const KEY = "opencue.toolbar";
  const ITEMS = ["layout", "stage", "show", "blackout", "timecode", "clock", "dmx", "remote", "kiosk", "lock", "voice", "midi", "undogo"];

  function readOff() {
    try {
      const list = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(list) ? list.filter((k) => ITEMS.includes(k)) : [];
    } catch (error) { return []; }
  }

  function writeOff(list) {
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (error) { /* privates Fenster: gilt dann nur bis zum Neuladen nicht */ }
  }

  function apply(off) {
    const list = off || readOff();
    ITEMS.forEach((key) => document.documentElement.classList.toggle("tb-off-" + key, list.includes(key)));
  }

  const boxes = () => [...document.querySelectorAll("#settings-toolbar-section input[data-tb]")];

  // ---- Schnellschalter: wirken sofort (nicht erst mit "Speichern") und gehen auch, wenn der Knopf in der Toolbar ausgeblendet ist
  const quick = () => [...document.querySelectorAll("#settings-quick-section input[data-qs]")];
  const READ = {
    voice: () => !!(window.OCVoice && window.OCVoice.status() && (window.OCVoice.status().config || {}).enabled),
    midi: () => !(window.__midi && window.__midi.enabled === false),
    blackout: () => !!window.__blackout,
    undogo: () => !!(typeof client !== "undefined" && client.state && client.state.undo_playback),
  };
  const WRITE = {
    voice: (on) => { if (window.OCVoice && READ.voice() !== on) window.OCVoice.toggle(); },
    midi: (on) => client.send("set_midi", { midi: { ...(window.__midi || {}), enabled: on } }),
    blackout: (on) => client.send("set_blackout", { enabled: on }),
    undogo: (on) => client.send("set_undo_playback", { enabled: on }),
  };

  function fillQuick() {
    quick().forEach((box) => {
      const key = box.dataset.qs;
      box.checked = READ[key]();
      box.disabled = key === "voice" && !(window.OCVoice && window.OCVoice.status());       // Sprachsteuerung: erst nach dem ersten Statusabruf bedienbar
    });
  }

  document.addEventListener("change", (e) => {
    const box = e.target.closest && e.target.closest("#settings-quick-section input[data-qs]");
    if (box) WRITE[box.dataset.qs](box.checked);
  });
  ["oc-quick-sync", "blackout-changed", "oc-midi-event"].forEach((name) => document.addEventListener(name, () => setTimeout(fillQuick, 50)));
  document.addEventListener("DOMContentLoaded", () => { if (window.OCVoice) window.OCVoice.subscribe(fillQuick); });

  function fillSettings() {
    const off = readOff();
    boxes().forEach((box) => { box.checked = !off.includes(box.dataset.tb); });
    fillQuick();
  }

  function saveSettings() {
    const list = boxes();
    if (!list.length) return;
    const off = list.filter((box) => !box.checked).map((box) => box.dataset.tb);
    if (JSON.stringify(off) === JSON.stringify(readOff())) return;
    writeOff(off);
    apply(off);
  }

  apply();         // sofort beim Laden (kein Aufblitzen der Eintraege, die aus sein sollen)
  window.OCToolbar = { fillSettings, saveSettings, apply, ITEMS, fillQuick };
})();

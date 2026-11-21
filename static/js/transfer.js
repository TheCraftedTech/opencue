// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Dateien speichern und einlesen, die der Browser selbst zusammenstellt (Einstellungen, eigene Tastenbelegung, MIDI-Belegung): window.OCTransfer.
 *   save(name, data)  - bietet `data` als JSON-Datei zum Speichern an. Im Programmfenster gibt es keinen Browser-Download: der Server legt den Inhalt kurz ab (app/transfer.py)
 *                       und oeffnet den Standard-Browser mit der Download-Adresse; auf anderen Geraeten laedt dieser Browser selbst.
 *   pickJson()        - oeffnet die Dateiauswahl und liefert den Inhalt einer JSON-Datei (null bei Abbruch / unlesbarer Datei, mit Hinweis).
 * Klassisches Skript, laeuft nach app.js. */
(function () {
  "use strict";
  const t = (key) => (typeof i18n === "function" ? i18n(key) : key);
  const toast = (text, type) => { if (typeof _showToast === "function") _showToast(text, type || "info", 3500, true); };

  async function save(name, data) {
    let url = "";
    try {
      const res = await fetch("/api/transfer/stash", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, data }) });
      const body = await res.json();
      if (!res.ok || !body.ok) throw new Error(body.error || res.status);
      url = body.url;
    } catch (err) {
      toast(t("TRANSFER_FAILED"), "error");
      return false;
    }
    try {                                                                         // Programmfenster: der Server oeffnet den Standard-Browser
      const res = await fetch("/api/files/open-download", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
      const body = await res.json();
      if (res.ok && body.opened) { toast(t("TRANSFER_STARTED")); return true; }
    } catch (err) { /* dann laedt dieser Browser selbst */ }
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    return true;
  }

  function pickJson() {
    return new Promise((resolve) => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".json,application/json";
      input.hidden = true;
      let done = false;
      const finish = (value) => { if (done) return; done = true; input.remove(); resolve(value); };
      input.addEventListener("change", () => {
        const file = input.files && input.files[0];
        if (!file) { finish(null); return; }
        const reader = new FileReader();
        reader.onload = () => {
          try { finish(JSON.parse(String(reader.result || ""))); } catch (err) { toast(t("TRANSFER_BAD_FILE"), "error"); finish(null); }
        };
        reader.onerror = () => { toast(t("TRANSFER_BAD_FILE"), "error"); finish(null); };
        reader.readAsText(file);
      });
      input.addEventListener("cancel", () => finish(null));
      document.body.appendChild(input);
      input.click();
    });
  }

  window.OCTransfer = { save, pickJson };
})();

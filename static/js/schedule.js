// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Zeitplan der Show (Menue "Steuerung" -> "Zeitplan ..."): Befehle der Befehlszeile zu einer Uhrzeit, an Wochentagen oder an einem Datum.
 * Server: app/schedule.py (Eintraege bereinigen), app/timeofday.py (Uhrzeiten), `_schedule_pump` in app/server.py (alle 0,25 s). WS: `set_schedule` -> `schedule_changed`,
 * `schedule_run` ("Jetzt ausfuehren"), `schedule_fired` (ein Eintrag ist gelaufen). Der Zeitplan gehoert zur Show (steht in der Show-Datei).
 * Eintrag: {id, enabled, label, time "HH:MM[:SS]", days [0-6, Montag = 0; leer = jeden Tag], date "" | "JJJJ-MM-TT", command}
 * Auch hier: window.OCSchedule = { open, fmtDays, parseDays, nextRun } (fmtDays / parseDays benutzt der Cue-Dialog fuer den Uhrzeit-Ausloeser). */
(function () {
  "use strict";

  const t = (key, vars) => {
    let text = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const name of Object.keys(vars)) text = text.split("{" + name + "}").join(String(vars[name]));
    return text;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const $ = (id) => document.getElementById(id);
  const MODAL = "schedule";
  const dayName = (d) => t("SCH_DAY_" + d);

  // ------------------------------------------------------------------------------------------------ Tage / Uhrzeit (wie app/timeofday.py)
  const ALIASES = { mon: 0, monday: 0, mo: 0, montag: 0, tue: 1, tuesday: 1, tu: 1, di: 1, dienstag: 1, wed: 2, wednesday: 2, mi: 2, mittwoch: 2, thu: 3, thursday: 3, th: 3, do: 3, donnerstag: 3,
    fri: 4, friday: 4, fr: 4, freitag: 4, sat: 5, saturday: 5, sa: 5, samstag: 5, sun: 6, sunday: 6, su: 6, so: 6, sonntag: 6 };
  const GROUPS = { daily: [], everyday: [], all: [], taeglich: [], "täglich": [], weekdays: [0, 1, 2, 3, 4], workdays: [0, 1, 2, 3, 4], werktags: [0, 1, 2, 3, 4], weekend: [5, 6], weekends: [5, 6], wochenende: [5, 6] };

  /** Wochentage aus Text oder Liste -> sortierte Liste (leer = jeden Tag); null bei Unverstandenem. */
  function parseDays(value) {
    if (Array.isArray(value)) { const set = new Set(value.filter((d) => Number.isInteger(d) && d >= 0 && d <= 6)); return set.size === 7 ? [] : [...set].sort(); }
    const text = String(value || "").trim().toLowerCase();
    if (!text) return [];
    if (text in GROUPS) return GROUPS[text].slice();
    const days = new Set();
    for (const part of text.split(/[,;\s]+/)) {
      if (!part) continue;
      if (part in GROUPS) GROUPS[part].forEach((d) => days.add(d));
      else if (part.includes("-")) {
        const [low, high] = part.split("-");
        if (!(low in ALIASES) || !(high in ALIASES)) return null;
        const a = ALIASES[low], b = ALIASES[high];
        if (a <= b) for (let d = a; d <= b; d += 1) days.add(d); else { for (let d = a; d <= 6; d += 1) days.add(d); for (let d = 0; d <= b; d += 1) days.add(d); }
      } else if (part in ALIASES) days.add(ALIASES[part]);
      else return null;
    }
    return days.size === 7 ? [] : [...days].sort();
  }

  /** "daily", "Mon-Fri", "Sat, Sun", "Mon, Wed, Fri" in der Sprache der Oberflaeche. */
  function fmtDays(days) {
    if (!days || !days.length) return t("SCH_DAILY");
    if (days.join() === "0,1,2,3,4") return dayName(0) + "–" + dayName(4);
    const runs = [];
    let start = days[0];
    days.forEach((d, i) => { if (i + 1 === days.length || days[i + 1] !== d + 1) { runs.push([start, d]); if (i + 1 < days.length) start = days[i + 1]; } });
    return runs.map(([a, b]) => (a === b ? dayName(a) : b === a + 1 ? dayName(a) + ", " + dayName(b) : dayName(a) + "–" + dayName(b))).join(", ");
  }

  const validTime = (text) => /^([01]?\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/.test(String(text || "").trim());
  const normTime = (text) => { const p = String(text).trim().split(":"); return p[0].padStart(2, "0") + ":" + p[1] + (p[2] && p[2] !== "00" ? ":" + p[2] : ""); };

  /** Naechste Ausfuehrung nach `now` (Date) oder null. */
  function nextRun(entry, now) {
    const [h, m, s] = String(entry.time).split(":").map((x) => parseInt(x, 10) || 0);
    if (entry.date) { const at = new Date(entry.date + "T00:00:00"); at.setHours(h, m, s || 0, 0); return at > now ? at : null; }
    for (let offset = 0; offset < 9; offset += 1) {
      const at = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset, h, m, s || 0, 0);
      const weekday = (at.getDay() + 6) % 7;                              // Montag = 0
      if (entry.days && entry.days.length && !entry.days.includes(weekday)) continue;
      if (at > now) return at;
    }
    return null;
  }

  // ------------------------------------------------------------------------------------------------ Dialog
  let list = [];
  let sendTimer = null;
  let clockTimer = null;

  const isLocalOrAny = () => typeof client !== "undefined" && client && client.send;

  function persistSoon() {
    clearTimeout(sendTimer);
    sendTimer = setTimeout(() => { if (isLocalOrAny()) client.send("set_schedule", { schedule: list }); }, 350);
  }

  function nextText(entry) {
    if (!entry.enabled) return t("SCH_OFF");
    if (!entry.command) return t("SCH_NO_COMMAND");
    const at = nextRun(entry, new Date());
    if (!at) return t("SCH_NEVER");
    const sameDay = at.toDateString() === new Date().toDateString();
    const time = at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: entry.time.length > 5 ? "2-digit" : undefined });
    return sameDay ? t("SCH_NEXT_TODAY", { time }) : t("SCH_NEXT", { day: at.toLocaleDateString([], { weekday: "short", day: "2-digit", month: "2-digit" }), time });
  }

  function buildRow(entry) {
    const row = el("div", "sch__row" + (entry.enabled ? "" : " sch__row--off"));
    row.dataset.id = entry.id;
    const on = el("label", "toggle-switch");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = !!entry.enabled;
    check.title = t("SCH_ENABLED");
    check.addEventListener("change", () => { entry.enabled = check.checked; row.classList.toggle("sch__row--off", !entry.enabled); persistSoon(); paintNext(); });
    on.append(check, el("span", "toggle-switch__track"));

    const time = document.createElement("input");
    time.type = "text";
    time.className = "sch__time";
    time.value = entry.time;
    time.placeholder = "HH:MM";
    time.maxLength = 8;
    time.setAttribute("aria-label", t("SCH_TIME"));
    time.addEventListener("change", () => {
      if (!validTime(time.value)) { time.value = entry.time; time.classList.add("sch__bad"); setTimeout(() => time.classList.remove("sch__bad"), 900); return; }
      entry.time = normTime(time.value); time.value = entry.time; persistSoon(); paintNext();
    });

    const modeOf = () => (entry.date ? "date" : (entry.days && entry.days.length ? "days" : "daily"));
    const mode = document.createElement("select");
    mode.className = "settings__select sch__mode";
    mode.setAttribute("aria-label", t("SCH_REPEAT"));
    for (const [value, key] of [["daily", "SCH_MODE_DAILY"], ["days", "SCH_MODE_DAYS"], ["date", "SCH_MODE_DATE"]]) { const o = document.createElement("option"); o.value = value; o.textContent = t(key); mode.appendChild(o); }
    mode.value = modeOf();

    const days = el("div", "sch__days");
    for (let d = 0; d < 7; d += 1) {
      const b = el("button", "sch__day" + (entry.days && entry.days.includes(d) ? " sch__day--on" : ""), dayName(d));
      b.type = "button";
      b.addEventListener("click", () => {
        const set = new Set(entry.days || []);
        if (set.has(d)) set.delete(d); else set.add(d);
        entry.days = set.size === 7 ? [] : [...set].sort();
        days.querySelectorAll(".sch__day").forEach((x, i) => x.classList.toggle("sch__day--on", entry.days.includes(i)));
        if (!entry.days.length) { mode.value = "daily"; paintMode(); }                      // keine Tage gewaehlt = jeden Tag
        persistSoon(); paintNext();
      });
      days.appendChild(b);
    }

    const date = document.createElement("input");
    date.type = "date";
    date.className = "sch__date";
    date.value = entry.date || "";
    date.title = t("SCH_DATE_HINT");
    date.addEventListener("change", () => {
      entry.date = date.value || "";
      if (!entry.date) { mode.value = entry.days && entry.days.length ? "days" : "daily"; paintMode(); }
      persistSoon(); paintNext();
    });

    const paintMode = () => {
      days.hidden = mode.value !== "days";
      date.hidden = mode.value !== "date";
    };
    mode.addEventListener("change", () => {
      if (mode.value === "daily") { entry.days = []; entry.date = ""; }
      else if (mode.value === "days") { entry.date = ""; if (!entry.days || !entry.days.length) entry.days = [0, 1, 2, 3, 4]; days.querySelectorAll(".sch__day").forEach((x, i) => x.classList.toggle("sch__day--on", entry.days.includes(i))); }
      else { entry.days = []; if (!entry.date) { const n = new Date(); entry.date = n.getFullYear() + "-" + String(n.getMonth() + 1).padStart(2, "0") + "-" + String(n.getDate()).padStart(2, "0"); } date.value = entry.date; }
      paintMode(); persistSoon(); paintNext();
    });
    paintMode();

    const label = document.createElement("input");
    label.type = "text";
    label.className = "sch__label";
    label.value = entry.label || "";
    label.placeholder = t("SCH_LABEL");
    label.maxLength = 60;
    label.addEventListener("input", () => { entry.label = label.value; persistSoon(); });

    const command = document.createElement("input");
    command.type = "text";
    command.className = "sch__command";
    command.value = entry.command || "";
    command.placeholder = t("SCH_COMMAND_PH");
    command.maxLength = 1000;
    command.autocomplete = "off";
    command.spellcheck = false;
    command.addEventListener("input", () => { entry.command = command.value; persistSoon(); paintNext(); });

    const next = el("div", "sch__next");
    const run = el("button", "modal__button sch__run", t("SCH_RUN"));
    run.type = "button";
    run.title = t("SCH_RUN_HINT");
    run.addEventListener("click", () => { clearTimeout(sendTimer); client.send("set_schedule", { schedule: list }); client.send("schedule_run", { id: entry.id }); });
    const del = el("button", "modal__button sch__del");
    del.type = "button";
    del.title = t("SCH_DELETE");
    del.setAttribute("aria-label", t("SCH_DELETE"));
    if (typeof Icons !== "undefined") del.appendChild(Icons.svg("trash"));
    del.addEventListener("click", async () => {
      const empty = !String(entry.command || "").trim() && !String(entry.label || "").trim();                 // frische, leere Zeile ohne Rueckfrage entfernen
      if (!empty && typeof _askDelete === "function" && !(await _askDelete("other", { title: t("SCH_DELETE_TITLE"), body: t("SCH_DELETE_BODY", { name: entry.label || entry.command || entry.time }), confirmKey: "SCH_DELETE_OK" }))) return;
      list = list.filter((e) => e.id !== entry.id); persistSoon(); render();
    });

    const when = el("div", "sch__when");
    when.append(time, mode, days, date);
    const what = el("div", "sch__what");
    what.append(label, command);
    const acts = el("div", "sch__acts");
    acts.append(run, del);
    row.append(on, when, what, next, acts);
    return row;
  }

  function paintNext() {
    const root = $("schedule-list");
    if (!root) return;
    root.querySelectorAll(".sch__row").forEach((row) => {
      const entry = list.find((e) => e.id === row.dataset.id);
      const cell = row.querySelector(".sch__next");
      if (entry && cell) cell.textContent = nextText(entry);
    });
  }

  function render() {
    const root = $("schedule-list");
    if (!root) return;
    root.textContent = "";
    $("schedule-empty").hidden = list.length > 0;
    list.forEach((entry) => root.appendChild(buildRow(entry)));
    paintNext();
  }

  function tickClock() {
    const clock = $("schedule-clock");
    if (clock) clock.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    if (!Modal.isOpen(MODAL)) { clearInterval(clockTimer); clockTimer = null; }
    else paintNext();
  }

  function open() {
    list = JSON.parse(JSON.stringify(window.__schedule || []));
    Modal.open(MODAL);
    render();
    tickClock();
    clearInterval(clockTimer);
    clockTimer = setInterval(tickClock, 1000);
  }

  function addEntry() {
    const now = new Date();
    const hour = (now.getHours() + 1) % 24;
    list.push({ id: Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-3), enabled: true, label: "", time: String(hour).padStart(2, "0") + ":00", days: [], date: "", command: "" });
    persistSoon();
    render();
    const rows = document.querySelectorAll("#schedule-list .sch__row");
    const last = rows[rows.length - 1];
    if (last) { last.scrollIntoView({ block: "nearest" }); const input = last.querySelector(".sch__command"); if (input) input.focus(); }
  }

  document.addEventListener("click", (e) => {
    if (e.target.closest('[data-action="open-schedule-modal"]')) { if (typeof _closeAllMenus === "function") _closeAllMenus(); open(); return; }
    if (e.target.closest("#schedule-add")) addEntry();
  });

  // Aenderung vom Server (anderes Geraet, ein einmaliger Eintrag hat sich ausgeschaltet, Start): uebernehmen, wenn nicht gerade getippt wird
  document.addEventListener("schedule-changed", () => {
    const typing = document.activeElement && document.activeElement.closest && document.activeElement.closest("#schedule-list");
    if (!Modal.isOpen(MODAL)) return;
    if (typing && sendTimer) return;
    list = JSON.parse(JSON.stringify(window.__schedule || []));
    if (!typing) render(); else paintNext();
  });

  document.addEventListener("schedule-fired", (e) => {
    const p = e.detail || {};
    const name = p.label || p.command || "";
    if (typeof _showToast === "function") _showToast(t(p.success ? "SCH_FIRED" : "SCH_FAILED", { name, message: p.message || "" }), p.success ? "info" : "warn", 4500);
  });

  window.OCSchedule = { open, fmtDays, parseDays, nextRun };
})();

// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Startskript des Panels "3D-Simulation": registriert den Panel-Typ sofort (klassisches Skript) und laedt das eigentliche Panel (ES-Modul sim3d.js mit three.js)
 * im Hintergrund. Ohne diesen Umweg koennte der erste Snapshot die Panels aufbauen, bevor das Modul fertig geladen ist - das Panel bliebe dann leer. */
(function () {
  "use strict";
  /** Registratur "Anleuchten": jede 3D-Simulation meldet sich mit {root, aim, placedCount, canAim} an. Die Scheinwerfersteuerung (app.js) zeigt ihre Knoepfe ("Punkt in 3D-Simulation setzen",
   *  Auto-Fokus/-Zoom) nur, wenn eine angemeldete Simulation im Layout steht und Scheinwerfer auf der Buehne platziert sind; jede Aenderung kommt als Ereignis "sim-aim-changed". */
  const instances = new Set();
  const registry = {
    register(inst) { instances.add(inst); registry.notify(); return () => { instances.delete(inst); registry.notify(); }; },
    notify() { document.dispatchEvent(new CustomEvent("sim-aim-changed")); },
    active() { return [...instances].find((i) => i.root.isConnected && i.placedCount() > 0) || null; },
    available() { return !!registry.active(); },
    get armed() { const a = registry.active(); return !!a && a.aim.armed; },
    arm(on) { instances.forEach((i) => { if (i.aim.armed) i.aim.arm(false); }); const a = registry.active(); if (a && on) a.aim.arm(true); },
    /** Wie viele der Scheinwerfer `ids` zielen koennen (Moving Head mit 3D-Modell auf der Buehne). */
    aimable(ids) { const a = registry.active(); return a ? ids.filter((id) => a.canAim(id)).length : 0; },
    /** Auto-Fokus / Auto-Zoom (Radius in m) fuer `ids`; Rueckgabe {done, skipped, miss} oder null ohne Simulation. */
    auto(kind, ids, radius) { const a = registry.active(); return a ? a.aim.auto(kind, ids, radius) : null; },
    /** Moegliche Radien des Lichtkreises fuer `ids` (siehe sim3d_aim.js zoomInfo). */
    zoomInfo(ids) { const a = registry.active(); return a ? a.aim.zoomInfo(ids) : null; },
    get radius() { const a = registry.active(); return a ? a.aim.prefs.radius : 0.5; },
    set radius(value) { const a = registry.active(); if (a) a.aim.setRadius(value); },
  };
  window.OCSimAim = registry;

  /** Kamera-Gruppen: die Kamera der 3D-Simulation zwischen Geraeten teilen (Praesentationsmodus / Synchronisation).
   *  Jedes Geraet gehoert zu einer Gruppe: "global" (alle, Vorgabe), ein frei gewaehlter Name oder "off" (eigene Kamera). Wer die Kamera bewegt, bewegt
   *  sie bei allen anderen Mitgliedern der Gruppe (Server: sim_cam / sim_cam_state / sim_cam_groups); Geraete gleiten in etwa einer halben Sekunde zum
   *  neuen Stand, bei fortlaufender Bewegung folgen sie weich. Wer zuletzt bewegt, gewinnt: waehrend und kurz nach einer eigenen Bewegung ignoriert
   *  ein Geraet fremde Staende. Diese Verwaltung laeuft immer (auch ohne offenes 3D-Panel): der Gruppenstand wird gemerkt und beim Oeffnen uebernommen.
   *  Gruppe und "nur ansehen" werden je Geraet gespeichert (wie die GUI-Skalierung). */
  const CAM_STORE = "opencue.simCam.v1";
  const CAM_TAU = 0.11;                     // Zeitkonstante der Annaeherung (s)
  const CAM_HOLD_MS = 350;                  // Vorrang der eigenen Kamera nach der letzten eigenen Bewegung
  const CAM_SEND_MS = 66;                   // hoechstens etwa 15 Meldungen pro Sekunde
  const camPrefs = { group: "global", lock: false };
  try {
    const saved = JSON.parse(localStorage.getItem(CAM_STORE) || "{}");
    if (saved && typeof saved.group === "string" && saved.group.trim()) camPrefs.group = saved.group.trim().slice(0, 48);
    camPrefs.lock = !!(saved && saved.lock === true);
  } catch (err) { /* ohne Speicher: Vorgabe */ }
  const camSims = new Set();                // angemeldete 3D-Panels (Eintraege mit sim, Zielstand, Zeiten)
  const camLatest = {};                     // Gruppe -> zuletzt bekannter Stand { p: [x, y, z], t: [x, y, z] }
  let camCounts = {};                       // Gruppe -> Anzahl Geraete (vom Server)
  const camListeners = new Set();
  const camSend = (type, payload) => { if (window.__panelAPI && window.__panelAPI.sendToServer) window.__panelAPI.sendToServer(type, payload); };
  const camGroup = () => (camPrefs.group === "off" ? "" : camPrefs.group);
  const camNotify = () => camListeners.forEach((fn) => { try { fn(); } catch (err) { console.error(err); } });
  const camSave = () => { try { localStorage.setItem(CAM_STORE, JSON.stringify(camPrefs)); } catch (err) { /* nur eine Bequemlichkeit */ } };
  const r3 = (v) => Math.round(v * 1000) / 1000;
  const camSnapshot = (sim) => {
    const p = sim.camera.position, t = sim.controls.target;
    return { p: [r3(p.x), r3(p.y), r3(p.z)], t: [r3(t.x), r3(t.y), r3(t.z)] };
  };
  const camValid = (s) => !!s && Array.isArray(s.p) && Array.isArray(s.t) && s.p.length === 3 && s.t.length === 3 && s.p.concat(s.t).every(Number.isFinite);

  function camPublish(item) {
    const group = camGroup();
    if (!group || camPrefs.lock || !camSims.has(item)) return;
    item.lastSend = performance.now();
    item.sendTimer = 0;
    const state = camSnapshot(item.sim);
    const key = JSON.stringify(state);
    if (key === item.lastKey) return;
    item.lastKey = key;
    camLatest[group] = state;
    camSend("sim_cam", { group, state });
  }
  function camSchedule(item) {
    if (!camGroup() || camPrefs.lock) return;
    const wait = CAM_SEND_MS - (performance.now() - (item.lastSend || 0));
    if (wait <= 0) camPublish(item);
    else if (!item.sendTimer) item.sendTimer = setTimeout(() => camPublish(item), wait);        // der letzte Stand geht immer noch hinaus
  }
  function camStep(item, now) {
    item.raf = 0;
    const goal = item.desired;
    if (!goal) return;
    if (item.sim.vrActive) { item.desired = null; return; }                      // mit VR-Brille bestimmt der Kopf die Kamera
    if (performance.now() - item.lastLocal < CAM_HOLD_MS) { item.desired = null; return; }       // die eigene Bewegung hat Vorrang (zuletzt bewegt gewinnt)
    const dt = Math.min(0.1, Math.max(0.001, (now - item.last) / 1000));
    item.last = now;
    const k = 1 - Math.exp(-dt / CAM_TAU);
    const cam = item.sim.camera, target = item.sim.controls.target;
    item.applying = true;
    cam.position.set(cam.position.x + (goal.p[0] - cam.position.x) * k, cam.position.y + (goal.p[1] - cam.position.y) * k, cam.position.z + (goal.p[2] - cam.position.z) * k);
    target.set(target.x + (goal.t[0] - target.x) * k, target.y + (goal.t[1] - target.y) * k, target.z + (goal.t[2] - target.z) * k);
    item.sim.controls.update();
    item.applying = false;
    item.sim.invalidateView();
    const close = Math.hypot(cam.position.x - goal.p[0], cam.position.y - goal.p[1], cam.position.z - goal.p[2]) < 0.004
      && Math.hypot(target.x - goal.t[0], target.y - goal.t[1], target.z - goal.t[2]) < 0.004;
    if (close || now > item.deadline) { item.desired = null; return; }               // angekommen (oder durch Grenzen der Kamera nicht erreichbar)
    item.raf = requestAnimationFrame((t) => camStep(item, t));
  }
  function camApply(item, state) {
    if (!camValid(state)) return;
    const sinceLocal = performance.now() - item.lastLocal;
    if (sinceLocal < CAM_HOLD_MS) {
      // Waehrend der eigenen Bewegung hat sie Vorrang. Ein Stand, der NACH meiner letzten Meldung eintrifft, ist aber neuer als alles, was ich geschrieben habe:
      // er wird nach der Pause uebernommen (zuletzt bewegt gewinnt).
      item.pending = state;
      item.pendingAt = performance.now();
      clearTimeout(item.pendingTimer);
      item.pendingTimer = setTimeout(() => {
        const next = item.pending;
        item.pending = null;
        if (next && camSims.has(item) && item.pendingAt > item.lastSend) camApply(item, next);
      }, CAM_HOLD_MS - sinceLocal + 30);
      return;
    }
    item.desired = state;
    item.last = performance.now();
    item.deadline = item.last + 1800;
    if (!item.raf) item.raf = requestAnimationFrame((t) => camStep(item, t));
  }
  const camApplyAll = (state) => camSims.forEach((item) => camApply(item, state));
  function camApplyLock() { camSims.forEach((item) => { item.sim.controls.enabled = !(camPrefs.lock && camGroup()); }); }
  function camJoin() {
    const group = camGroup();
    delete camLatest[group];
    camSend("sim_cam_join", { group });
    if (!group) return;
    // Gab der Server keinen Stand der Gruppe (neue oder leere Gruppe), gilt die Kamera dieses Geraets als Stand der Gruppe
    setTimeout(() => {
      if (camGroup() !== group || camLatest[group] || camPrefs.lock) return;
      const first = camSims.values().next().value;
      if (first) camPublish(first);
    }, 250);
  }

  window.OCSimCam = {
    get group() { return camPrefs.group; },
    get lock() { return camPrefs.lock; },
    get counts() { return camCounts; },
    /** Alle bekannten Gruppen (global, off, eigene): [{ key, count }] */
    groups() {
      const keys = new Set(["global", ...Object.keys(camCounts), camPrefs.group]);
      keys.delete("off");
      return [...keys].map((key) => ({ key, count: camCounts[key] || 0 }));
    },
    setGroup(key) {
      key = String(key || "").trim().slice(0, 48) || "global";
      if (key === camPrefs.group) return;
      camPrefs.group = key;
      camSave();
      camApplyLock();
      camJoin();
      camNotify();
    },
    setLock(on) { camPrefs.lock = !!on; camSave(); camApplyLock(); camNotify(); },
    subscribe(fn) { camListeners.add(fn); return () => camListeners.delete(fn); },
    onConnected() { camJoin(); camNotify(); },
    onMessage(type, payload) {
      if (type === "sim_cam_groups") { camCounts = payload.groups || {}; camNotify(); return; }
      if ((type === "sim_cam" || type === "sim_cam_state") && payload.group === camGroup() && camValid(payload.state)) {
        camLatest[payload.group] = payload.state;
        camApplyAll(payload.state);
      }
    },
    /** Ein 3D-Panel meldet sich an ({ camera, controls, invalidateView }); gibt die Abmeldung zurueck. */
    attach(sim) {
      const item = { sim, lastLocal: -1e9, lastSend: 0, sendTimer: 0, pending: null, pendingAt: 0, pendingTimer: 0, lastKey: "", desired: null, raf: 0, last: 0, deadline: 0, applying: false };
      const controls = sim.controls;
      const local = () => { item.lastLocal = performance.now(); item.desired = null; };
      const onStart = () => local();
      const onEnd = () => local();
      const onChange = () => { if (item.applying) return; local(); camSchedule(item); };
      controls.addEventListener("start", onStart);
      controls.addEventListener("end", onEnd);
      controls.addEventListener("change", onChange);
      camSims.add(item);
      camApplyLock();
      const known = camLatest[camGroup()];
      if (known) camApply(item, known);                          // das Panel wurde geoeffnet: Stand der Gruppe uebernehmen (mit Gleiten)
      else if (camGroup() && !camPrefs.lock) setTimeout(() => { if (camSims.has(item) && !camLatest[camGroup()]) camPublish(item); }, 250);
      return () => {
        camSims.delete(item);
        cancelAnimationFrame(item.raf);
        clearTimeout(item.sendTimer);
        clearTimeout(item.pendingTimer);
        controls.removeEventListener("start", onStart);
        controls.removeEventListener("end", onEnd);
        controls.removeEventListener("change", onChange);
      };
    },
  };
  let real = null;
  const loading = import("/static/js/sim3d.js").then((module) => { real = module.plugin; return real; }).catch((error) => {
    console.error("3D-Simulation konnte nicht geladen werden:", error);
    return null;
  });
  window.__panelPlugins.register({
    type: "sim3d",
    buildContent(panel) {
      const host = document.createElement("div");
      host.style.cssText = "display:contents";
      loading.then((plugin) => { if (plugin) host.appendChild(plugin.buildContent(panel)); });
      return host;
    },
    onMessage(panelEl, messageType, payload) { if (real && real.onMessage) real.onMessage(panelEl, messageType, payload); },
  });
})();

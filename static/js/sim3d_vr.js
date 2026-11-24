// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* 3D-Simulation: VR-Modus (WebXR). Der Knopf mit der VR-Brille erscheint oben rechts (neben Raum & Licht / Praesentation) nur, wenn er etwas nuetzt: der Browser bietet eine Brille an
 * (navigator.xr, z. B. Meta Quest Browser) UND es ist nicht die Konsole selbst (am Laptop bleibt er weg). WebXR braucht einen SICHEREN Kontext: https:// (Remote ueber die https-Adresse aus den
 * Einstellungen) oder localhost - unter http://<IP> gibt es navigator.xr nicht; auf einer Quest erscheint der Knopf dann trotzdem und erklaert das.
 *
 * Im VR-Modus steht man auf dem Boden der Buehne (Welt: Z nach oben, die Brille arbeitet mit Y nach oben - die Kamera haengt deshalb in einer um 90 Grad gekippten
 * "Rig"-Gruppe, die auch zum Fliegen bewegt wird). Steuerung (die Tafel in der Brille zeigt sie, mit den aktuellen Einstellungen):
 *   Bewegungs-Hand (Standard links): Stick = gehen / seitlich gehen            Trigger (beide) = schneller
 *   Dreh-Hand (Standard rechts):     Stick seitlich = drehen (Schritte von 30 Grad oder fliessend), Stick hoch/runter = steigen / sinken
 *   Tasten A / X: steigen und sinken (Standard: A (Dreh-Hand) steigt, X (Bewegungs-Hand) sinkt)      Taste B oder Y: VR beenden
 *   linker Stick druecken: Tafel ein/aus (steht dann im Raum vor einem)         rechter Stick druecken: Qualitaet wechseln (Einfach / Standard / Hoch)
 * Die Tafel hat Knoepfe zum Anzeigen mit dem Laserstrahl der Controller (Trigger = klicken): Drehen (Schritte / fliessend), Haende (Rechts-/Linkshaender: Bewegung und Drehen tauschen
 * die Hand), Hoch/Runter vertauschen, Qualitaet, VR beenden, Schliessen. Die Einstellungen werden auf dem Geraet gemerkt.
 * Qualitaet: "Einfach" = Lichtkegel, "Standard" und "Hoch" = Nebel-Volumen mit Schatten je Auge (siehe sim3d_live.js, Tiefenbild je Auge); die Medien laufen weiter. */
import * as THREE from "three";

const SPEED = 2.5;                  // m/s
const FAST = 3;                     // Faktor mit gedrueckter Taste
const CLIMB = 2;                    // m/s
const SNAP = Math.PI / 6;
const SMOOTH_TURN = Math.PI / 2;    // rad/s bei vollem Ausschlag (fliessendes Drehen)
const DEAD = 0.18;
const MAX_HEIGHT = 40;
const SCALE_FACTOR = 0.8;           // Aufloesung der Brille (1 = voll)
const QUALITIES = [["simple", 0, "SIM3D_VR_Q_SIMPLE"], ["standard", 2, "SIM3D_VR_Q_STANDARD"], ["high", 3, "SIM3D_VR_Q_HIGH"]];      // Name, Qualitaetsstufe der Simulation, Text
const QUALITY_STORE = "opencue.simVrQuality";
const CONFIG_STORE = "opencue.simVr.v1";
const HELP_W = 2048;
const HELP_H = 1152;
const CTRL_X = 860;                  // Mitte der Controller-Skizzen auf der Tafel (links / rechts gespiegelt)

export const VR_DEFAULTS = { turn: "snap", swapHands: false, swapUpDown: false };

/** Die Rollen der Controller aus den Einstellungen: welche Hand geht, welche dreht, welche Taste steigt. */
export function vrRoles(cfg) {
  const moveHand = cfg.swapHands ? "right" : "left";
  const turnHand = cfg.swapHands ? "left" : "right";
  return { moveHand, turnHand, upHand: cfg.swapUpDown ? moveHand : turnHand, downHand: cfg.swapUpDown ? turnHand : moveHand };
}

/** Anker der Tasten eines Controllers (Ansicht von oben auf die Kopfplatte; Quest 3 Touch Plus ohne Tracking-Ring): side = -1 links, +1 rechts. */
function anchors(cx, cy, side) {
  return {
    trigger: { x: cx - side * 18, y: cy - 168 },
    stick: { x: cx + side * 58, y: cy - 48, r: 44 },                 // aussen
    upper: { x: cx - side * 58, y: cy - 92, r: 27 },                 // B / Y (innen oben)
    lower: { x: cx - side * 34, y: cy - 20, r: 27 },                 // A / X (innen unten)
  };
}

/** Hilfe-Tafel: beide Controller als Skizze (mit Licht und Schatten), von jeder Taste eine Linie zur Beschriftung, unten die Knoepfe. t(key) liefert die Texte.
 *  Gibt die Knoepfe als [{id, x, y, w, h}] (Pixel der Tafel) zurueck - zum Zielen mit dem Laserstrahl. hover = id des Knopfes unter dem Strahl. */
export function drawVrHelp(canvas, t, cfg = VR_DEFAULTS, quality = "standard", hover = null) {
  canvas.width = HELP_W;
  canvas.height = HELP_H;
  const g = canvas.getContext("2d");
  const roles = vrRoles(cfg);
  const ACCENT = "#ffb000";
  g.clearRect(0, 0, HELP_W, HELP_H);
  const bg = g.createLinearGradient(0, 0, 0, HELP_H);
  bg.addColorStop(0, "rgba(26,26,30,0.96)"); bg.addColorStop(1, "rgba(12,12,14,0.97)");
  g.fillStyle = bg;
  g.beginPath(); g.roundRect(0, 0, HELP_W, HELP_H, 56); g.fill();
  g.strokeStyle = ACCENT; g.lineWidth = 7;
  g.beginPath(); g.roundRect(6, 6, HELP_W - 12, HELP_H - 12, 52); g.stroke();

  const buttons = [];
  /** Knopf (wie in der Oberflaeche): Beschriftung + aktueller Wert, mit Hervorhebung unter dem Strahl. */
  function button(id, x, y, w, h, title, value, danger) {
    buttons.push({ id, x, y, w, h });
    const on = hover === id;
    const grad = g.createLinearGradient(0, y, 0, y + h);
    grad.addColorStop(0, on ? "#4a4a54" : "#34343c"); grad.addColorStop(1, on ? "#35353d" : "#25252b");
    g.fillStyle = grad;
    g.beginPath(); g.roundRect(x, y, w, h, 22); g.fill();
    g.strokeStyle = on ? ACCENT : danger ? "#c4504a" : "#6b6b76"; g.lineWidth = on ? 6 : 3;
    g.beginPath(); g.roundRect(x, y, w, h, 22); g.stroke();
    g.textAlign = "center"; g.textBaseline = "middle";
    if (value) {
      g.fillStyle = "#b9b9c4"; g.font = "30px sans-serif"; g.fillText(title, x + w / 2, y + h * 0.31);
      g.fillStyle = on ? ACCENT : "#ffffff"; g.font = "bold 40px sans-serif"; g.fillText(value, x + w / 2, y + h * 0.68);
    } else {
      g.fillStyle = danger ? "#ff8a80" : "#ffffff"; g.font = "bold 38px sans-serif"; g.fillText(title, x + w / 2, y + h / 2 + 2);
    }
    g.textBaseline = "alphabetic";
  }

  g.fillStyle = "#ffffff"; g.font = "bold 66px sans-serif"; g.textAlign = "center";
  g.fillText(t("SIM3D_VR_HELP_TITLE"), HELP_W / 2, 105);
  button("exit", 46, 40, 360, 84, t("SIM3D_VR_BTN_EXIT"), "", true);
  button("close", HELP_W - 406, 40, 360, 84, t("SIM3D_VR_BTN_CLOSE"), "", false);

  // ---- Beschriftungen: je Hand von oben nach unten in der Reihenfolge der Tasten (die Linien kreuzen sich nicht)
  const turnText = cfg.turn === "smooth" ? t("SIM3D_VR_H_TURN_SMOOTH") : t("SIM3D_VR_H_TURN_SNAP");
  const handRows = (hand) => {
    const side = hand === "left" ? -1 : 1;
    const a = anchors(hand === "left" ? CTRL_X : HELP_W - CTRL_X, 500, side);
    const rows = [{ from: a.trigger, text: t("SIM3D_VR_P_TRIGGER") + ": " + t("SIM3D_VR_H_FAST") }];
    rows.push({ from: a.upper, text: (side < 0 ? "Y" : "B") + ": " + t("SIM3D_VR_H_EXIT"), hot: true });
    if (hand === roles.moveHand) rows.push({ from: a.stick, text: t("SIM3D_VR_P_STICK") + ": " + t("SIM3D_VR_H_WALK") });
    else {
      rows.push({ from: { x: a.stick.x, y: a.stick.y - 24, r: 0 }, text: t("SIM3D_VR_P_STICK_UPDOWN") + ": " + t("SIM3D_VR_H_CLIMB") });
      rows.push({ from: a.stick, text: t("SIM3D_VR_P_STICK_SIDE") + ": " + turnText });
    }
    const upDown = hand === roles.upHand ? t("SIM3D_VR_H_UP") : hand === roles.downHand ? t("SIM3D_VR_H_DOWN") : "";
    rows.push({ from: a.lower, text: (side < 0 ? "X" : "A") + ": " + upDown });
    rows.push({ from: { x: a.stick.x, y: a.stick.y + 26, r: 0 }, text: t("SIM3D_VR_P_STICK_PRESS") + ": " + (hand === "left" ? t("SIM3D_VR_H_HELP_PRESS") : t("SIM3D_VR_H_QUALITY_PRESS")) });
    return { side, cx: hand === "left" ? CTRL_X : HELP_W - CTRL_X, rows, align: hand === "left" ? "left" : "right" };
  };
  const hands = [handRows("left"), handRows("right")];
  g.font = "38px sans-serif";
  const labelPos = [];
  hands.forEach((h) => h.rows.forEach((row, i) => {
    const tx = h.align === "left" ? 64 : HELP_W - 64;
    const ty = 250 + i * 86;
    const w = g.measureText(row.text).width;
    row.end = { x: h.align === "left" ? tx + w + 22 : tx - w - 22, y: ty - 14 };
    row.tx = tx; row.ty = ty;
    const dx = row.end.x - row.from.x, dy = row.end.y - row.from.y, len = Math.hypot(dx, dy) || 1;
    const r = row.from.r || 0;
    row.anchor = { x: row.from.x + (dx / len) * r, y: row.from.y + (dy / len) * r };
    labelPos.push(row);
  }));
  // Linien zuerst (liegen unter den Controllern, nur der Punkt an der Taste bleibt sichtbar)
  labelPos.forEach((row) => {
    g.strokeStyle = row.hot ? ACCENT : "#9a9aa6"; g.lineWidth = 4;
    g.beginPath(); g.moveTo(row.end.x, row.end.y); g.lineTo(row.anchor.x, row.anchor.y); g.stroke();
  });

  // ---- Controller mit Licht (von oben links) und Schatten
  const edge = "#8f8f9b";
  function shaded(x0, y0, x1, y1, stops) { const gr = g.createLinearGradient(x0, y0, x1, y1); stops.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; }
  function cap(x, y, r, base, glow) {                                                     // Druckknopf / Stickkappe mit Glanzlicht
    const gr = g.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
    gr.addColorStop(0, glow); gr.addColorStop(1, base);
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fillStyle = gr; g.fill();
    g.strokeStyle = "#0c0c0e"; g.lineWidth = 3; g.stroke();
  }
  function controller(cx, cy, side) {
    const a = anchors(cx, cy, side);
    g.save();
    g.shadowColor = "rgba(0,0,0,0.65)"; g.shadowBlur = 38; g.shadowOffsetX = 10; g.shadowOffsetY = 20;
    // Griff
    g.beginPath();
    g.moveTo(cx - 118, cy - 5);
    g.bezierCurveTo(cx - 140, cy + 110, cx - 100, cy + 250, cx - 66, cy + 326);
    g.quadraticCurveTo(cx, cy + 368, cx + 66, cy + 326);
    g.bezierCurveTo(cx + 100, cy + 250, cx + 140, cy + 110, cx + 118, cy - 5);
    g.closePath();
    g.fillStyle = shaded(cx - 140, 0, cx + 140, 0, [[0, "#1c1c22"], [0.3, "#4a4a55"], [0.55, "#33333b"], [1, "#141418"]]);
    g.fill();
    g.restore();
    g.strokeStyle = edge; g.lineWidth = 3; g.stroke();
    // Gummiband-Struktur am Griff
    g.strokeStyle = "rgba(255,255,255,0.07)"; g.lineWidth = 2;
    for (let i = 0; i < 6; i++) { g.beginPath(); g.moveTo(cx - 90 + i * 6, cy + 120 + i * 18); g.quadraticCurveTo(cx, cy + 150 + i * 18, cx + 90 - i * 6, cy + 120 + i * 18); g.stroke(); }
    // Grip-Taste an der Aussenseite
    const gx = cx + side * 124;
    g.fillStyle = shaded(gx - 22, 0, gx + 22, 0, [[0, "#2a2a31"], [0.5, "#5a5a66"], [1, "#25252b"]]);
    g.beginPath(); g.roundRect(gx - 22, cy + 40, 44, 200, 22); g.fill(); g.strokeStyle = edge; g.lineWidth = 3; g.stroke();
    // Kopf (Oberseite) mit weichem Licht
    const head = g.createRadialGradient(cx - 55, cy - 105, 20, cx, cy - 30, 175);
    head.addColorStop(0, "#6b6b78"); head.addColorStop(0.55, "#3b3b44"); head.addColorStop(1, "#1d1d23");
    g.beginPath(); g.ellipse(cx, cy - 30, 152, 108, 0, 0, Math.PI * 2); g.fillStyle = head; g.fill();
    g.strokeStyle = edge; g.lineWidth = 3; g.stroke();
    g.strokeStyle = "rgba(255,255,255,0.20)"; g.lineWidth = 5;
    g.beginPath(); g.ellipse(cx, cy - 30, 140, 96, 0, Math.PI * 1.08, Math.PI * 1.62); g.stroke();       // Glanzkante oben links
    // Trigger (vorn, ueber der Kopfplatte)
    g.fillStyle = shaded(0, cy - 190, 0, cy - 130, [[0, "#6a6a76"], [1, "#2a2a31"]]);
    g.beginPath(); g.roundRect(cx - side * 18 - 52, cy - 192, 104, 50, 24); g.fill(); g.strokeStyle = edge; g.lineWidth = 3; g.stroke();
    // Stick: Mulde + Kappe
    g.beginPath(); g.arc(a.stick.x, a.stick.y, 54, 0, Math.PI * 2); g.fillStyle = "#101014"; g.fill();
    cap(a.stick.x, a.stick.y, 40, "#26262c", "#5e5e6b");
    g.strokeStyle = "rgba(255,255,255,0.12)"; g.lineWidth = 2;
    for (let r = 14; r <= 30; r += 8) { g.beginPath(); g.arc(a.stick.x, a.stick.y, r, 0, Math.PI * 2); g.stroke(); }
    // Tasten
    cap(a.upper.x, a.upper.y, 27, "#2c2c33", "#70707e");
    cap(a.lower.x, a.lower.y, 27, "#2c2c33", "#70707e");
    g.fillStyle = "#f2f2f6"; g.font = "bold 30px sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(side < 0 ? "Y" : "B", a.upper.x, a.upper.y + 2);
    g.fillText(side < 0 ? "X" : "A", a.lower.x, a.lower.y + 2);
    g.textBaseline = "alphabetic";
    // Meta-/Menue-Taste (ohne Funktion hier) und Sensor-Punkte
    cap(cx - side * 6, cy + 42, 15, "#2c2c33", "#6a6a76");
    g.fillStyle = "rgba(0,0,0,0.55)";
    for (let i = 0; i < 5; i++) { g.beginPath(); g.arc(cx - 100 + i * 50, cy - 3 + (i % 2) * 5, 5, 0, Math.PI * 2); g.fill(); }
  }
  controller(CTRL_X, 500, -1);
  controller(HELP_W - CTRL_X, 500, +1);

  // ---- Beschriftungen und Punkte (ueber den Controllern)
  labelPos.forEach((row) => {
    g.fillStyle = row.hot ? ACCENT : "#d9d9e2";
    g.beginPath(); g.arc(row.anchor.x, row.anchor.y, 9, 0, Math.PI * 2); g.fill();
    g.fillStyle = row.hot ? ACCENT : "#ffffff"; g.font = "38px sans-serif"; g.textAlign = row.tx < HELP_W / 2 ? "left" : "right"; g.textBaseline = "alphabetic";
    g.fillText(row.text, row.tx, row.ty);
  });

  // ---- Einstellungen zum Anzeigen mit dem Laserstrahl
  const q = QUALITIES.find((item) => item[0] === quality) || QUALITIES[1];
  const bw = 440, gap = 36, x0 = (HELP_W - (4 * bw + 3 * gap)) / 2, by = 905, bh = 112;
  button("turn", x0, by, bw, bh, t("SIM3D_VR_S_TURN"), cfg.turn === "smooth" ? t("SIM3D_VR_V_SMOOTH") : t("SIM3D_VR_V_SNAP"));
  button("hands", x0 + (bw + gap), by, bw, bh, t("SIM3D_VR_S_HANDS"), cfg.swapHands ? t("SIM3D_VR_V_LEFTY") : t("SIM3D_VR_V_RIGHTY"));
  button("updown", x0 + 2 * (bw + gap), by, bw, bh, t("SIM3D_VR_S_UPDOWN"), cfg.swapUpDown ? t("SIM3D_VR_V_SWAPPED") : t("SIM3D_VR_V_NORMAL"));
  button("quality", x0 + 3 * (bw + gap), by, bw, bh, t("SIM3D_VR_QUALITY"), t(q[2]));
  g.fillStyle = "#b9b9c4"; g.font = "34px sans-serif"; g.textAlign = "center";
  g.fillText(t("SIM3D_VR_H_FOOT"), HELP_W / 2, HELP_H - 50);
  return buttons;
}

export function createVR(sim, host, tools) {
  const i18nKey = (key) => (typeof i18n === "function" ? i18n(key) : key);
  const toast = (key) => { if (typeof window._showToast === "function") window._showToast(i18nKey(key), "info", 6000); };
  const quest = /OculusBrowser|Quest/i.test(navigator.userAgent || "");
  const secure = window.isSecureContext !== false;
  const isConsole = () => { try { return !!(client && client.state && client.state.is_local); } catch (err) { return false; } };

  const button = document.createElement("button");
  button.type = "button";
  button.className = "sim3d__btn";
  button.dataset.act = "vr";
  button.hidden = true;
  button.title = i18nKey("SIM3D_VR_TIP");
  button.setAttribute("aria-label", i18nKey("SIM3D_VR"));
  button.appendChild(Icons.svg("vr"));
  button.addEventListener("dblclick", (e) => e.stopPropagation());
  tools.insertBefore(button, tools.firstChild);                                         // ganz links in der Knopfleiste

  // Sichtbar nur, wenn VR hier etwas nuetzt: eine Brille ist da (oder eine Quest ohne https - dann erklaert der Knopf es) und es ist nicht die Konsole (Laptop)
  let supported = false;
  // Einstellung "VR-Knopf" (je Geraet): Automatisch = nur auf VR-Geraeten (Quest, Pico, Vision Pro ...), nicht am PC / Laptop - dort meldet der Browser oft "VR moeglich", auch ohne Brille; Immer = wenn der Browser VR
  // anbietet (PC-VR mit SteamVR o. ae.); Nie = nie.
  const vrBrowser = /OculusBrowser|Quest|Pico|Wolvic|VisionOS|Vision Pro|HoloLens/i.test(navigator.userAgent || "");
  const refreshVisible = () => {
    const mode = sim.limits.values.vrButton;
    if (mode === 2) { button.hidden = true; return; }
    if (mode === 1) { button.hidden = !(supported || (quest && !secure && !navigator.xr)); return; }
    button.hidden = isConsole() || !vrBrowser || !(supported || (quest && !secure && !navigator.xr));
  };
  sim.limits.listeners.push(refreshVisible);
  if (navigator.xr && typeof navigator.xr.isSessionSupported === "function") {
    navigator.xr.isSessionSupported("immersive-vr").then((ok) => { supported = !!ok; refreshVisible(); }).catch(() => {});
  } else if (quest && !secure) {
    button.classList.add("sim3d__btn--idle");
    refreshVisible();
  }
  const recheck = setTimeout(refreshVisible, 1500);                                       // der Zustand "Konsole oder Fernzugriff" kann erst nach dem ersten Snapshot feststehen

  let cfg = { ...VR_DEFAULTS };
  try { Object.assign(cfg, JSON.parse(localStorage.getItem(CONFIG_STORE) || "{}")); } catch (err) { /* ohne Speicher: Standard */ }
  cfg.turn = cfg.turn === "smooth" ? "smooth" : "snap";
  cfg.swapHands = cfg.swapHands === true;
  cfg.swapUpDown = cfg.swapUpDown === true;
  const saveCfg = () => { try { localStorage.setItem(CONFIG_STORE, JSON.stringify(cfg)); } catch (err) { /* nur eine Bequemlichkeit */ } };
  let quality = "standard";
  try { const saved = localStorage.getItem(QUALITY_STORE); if (QUALITIES.some((q) => q[0] === saved)) quality = saved; } catch (err) { /* ohne Speicher: Standard */ }
  const levelOf = (name) => (QUALITIES.find((q) => q[0] === name) || QUALITIES[1])[1];

  let session = null;
  let state = null;

  async function enter() {
    if (session) { session.end(); return; }
    if (!navigator.xr) { toast("SIM3D_VR_NEEDS_HTTPS"); return; }
    let next;
    try {
      sim.vrActive = true;
      sim.quality.force(levelOf(quality));                                               // vor dem Start (danach laesst sich die Groesse nicht mehr aendern)
      next = await navigator.xr.requestSession("immersive-vr", { optionalFeatures: ["local-floor", "bounded-floor"] });
    } catch (err) {
      sim.vrActive = false;
      sim.quality.force(null);
      console.warn("VR konnte nicht gestartet werden:", err);
      toast("SIM3D_VR_FAILED");
      return;
    }
    session = next;
    const renderer = sim.renderer;
    const camera = sim.camera;
    const builder = host._builder;
    if (builder && builder.setMode) builder.setMode("view");                              // VR zeigt nur die Ansicht (Bauen/Scheinwerfer gibt es dort nicht)
    renderer.xr.enabled = true;
    renderer.xr.setReferenceSpaceType("local-floor");
    renderer.xr.setFramebufferScaleFactor(SCALE_FACTOR);
    try { renderer.xr.setFoveation(1); } catch (err) { /* nicht ueberall vorhanden */ }
    try {
      await renderer.xr.setSession(session);
    } catch (err) {                                                                        // die Brille hat die Sitzung nicht angenommen: alles zurueck
      console.warn("VR-Sitzung konnte nicht eingerichtet werden:", err);
      try { session.end(); } catch (e) { /* schon beendet */ }
      renderer.xr.enabled = false;
      sim.vrActive = false;
      sim.quality.force(null);
      session = null;
      toast("SIM3D_VR_FAILED");
      return;
    }

    // Kamera in eine gekippte Rig-Gruppe: rig = Standort + Blickrichtung (Z-Achse), tilt = Y-oben der Brille auf Z-oben der Buehne
    const rig = new THREE.Group();
    const tilt = new THREE.Group();
    tilt.rotation.x = Math.PI / 2;
    rig.add(tilt);
    const saved = { pos: camera.position.clone(), quat: camera.quaternion.clone(), target: sim.controls.target.clone() };
    const toTarget = new THREE.Vector3(saved.target.x - saved.pos.x, saved.target.y - saved.pos.y, 0);
    const dist = Math.hypot(toTarget.x, toTarget.y);
    if (dist < 0.5) toTarget.set(0, 1, 0); else toTarget.divideScalar(dist);
    const start = Math.min(dist, 9);                                                       // so weit von der Mitte, wie die Ansicht war (hoechstens 9 m)
    rig.position.set(saved.target.x - toTarget.x * start, saved.target.y - toTarget.y * start, 0);
    rig.rotation.z = Math.atan2(-toTarget.x, toTarget.y);                                  // Blick zur Mitte
    sim.scene.add(rig);
    tilt.add(camera);

    // Controller: schlanker Koerper mit Kopf, Laserstrahl (zielt auf die Tafel) und Zielpunkt
    const rayMaterial = new THREE.LineBasicMaterial({ color: 0xffb000, transparent: true, opacity: 0.85, depthTest: false });
    const bodyMaterial = new THREE.MeshBasicMaterial({ color: 0x3d3d46 });
    const headMaterial = new THREE.MeshBasicMaterial({ color: 0x6a6a76 });
    const dotMaterial = new THREE.MeshBasicMaterial({ color: 0xffd466, depthTest: false });
    const controllers = [0, 1].map((i) => {
      const c = renderer.xr.getController(i);
      const grip = new THREE.Mesh(new THREE.CapsuleGeometry(0.018, 0.09, 4, 10), bodyMaterial);
      grip.rotation.x = Math.PI / 2 - 0.5; grip.position.set(0, -0.02, 0.03);
      const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.03, 14, 10), headMaterial);
      headMesh.scale.set(1, 0.45, 1); headMesh.position.set(0, 0.015, -0.02);
      const ray = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1)]), rayMaterial);
      ray.scale.z = 0.4; ray.renderOrder = 90;
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.012, 10, 8), dotMaterial);
      dot.visible = false; dot.renderOrder = 102;
      c.add(grip, headMesh, ray, dot);
      c.userData = { ray, dot, aim: null };
      tilt.add(c);
      return c;
    });

    // Tafel: steht im Raum (in der Rig-Gruppe) dort, wo man beim Oeffnen hinschaut; linker Stick druecken = ein/aus. Kurze Meldungen schweben als kleines Schild vor dem Gesicht.
    const helpCanvas = document.createElement("canvas");
    let boardButtons = drawVrHelp(helpCanvas, i18nKey, cfg, quality, null);
    const helpTexture = new THREE.CanvasTexture(helpCanvas);
    helpTexture.colorSpace = THREE.SRGBColorSpace;
    helpTexture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    const help = new THREE.Mesh(new THREE.PlaneGeometry(2.6, (2.6 * HELP_H) / HELP_W), new THREE.MeshBasicMaterial({ map: helpTexture, transparent: true, depthTest: false, toneMapped: false }));
    help.renderOrder = 100;
    tilt.add(help);
    const placeHelp = () => {                                                              // vor den Kopf, mit Blick zum Kopf (nur die Blickrichtung nach rechts/links zaehlt)
      const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
      forward.y = 0;
      if (forward.lengthSq() < 1e-4) forward.set(0, 0, -1);
      forward.normalize();
      help.position.set(camera.position.x + forward.x * 2.0, Math.max(camera.position.y - 0.05, 0.9), camera.position.z + forward.z * 2.0);
      help.rotation.set(0, Math.atan2(-forward.x, -forward.z), 0);
    };
    let hover = null;
    const redraw = () => { boardButtons = drawVrHelp(helpCanvas, i18nKey, cfg, quality, hover); helpTexture.needsUpdate = true; };
    const flashCanvas = document.createElement("canvas");
    flashCanvas.width = 1024; flashCanvas.height = 160;
    const flashTexture = new THREE.CanvasTexture(flashCanvas);
    flashTexture.colorSpace = THREE.SRGBColorSpace;
    const flash = new THREE.Mesh(new THREE.PlaneGeometry(0.7, (0.7 * 160) / 1024), new THREE.MeshBasicMaterial({ map: flashTexture, transparent: true, depthTest: false, toneMapped: false }));
    flash.position.set(0, -0.2, -1.0);
    flash.renderOrder = 101;
    flash.visible = false;
    camera.add(flash);
    let flashUntil = 0;
    const say = (text) => {
      const g = flashCanvas.getContext("2d");
      g.clearRect(0, 0, 1024, 160);
      g.fillStyle = "rgba(14,14,16,0.92)"; g.beginPath(); g.roundRect(0, 0, 1024, 160, 40); g.fill();
      g.strokeStyle = "#ffb000"; g.lineWidth = 6; g.beginPath(); g.roundRect(4, 4, 1016, 152, 36); g.stroke();
      g.fillStyle = "#ffffff"; g.font = "bold 58px sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText(text, 512, 84);
      flashTexture.needsUpdate = true;
      flashUntil = performance.now() + 2200;
    };
    const cycleQuality = () => {
      const index = (QUALITIES.findIndex((q) => q[0] === quality) + 1) % QUALITIES.length;
      quality = QUALITIES[index][0];
      try { localStorage.setItem(QUALITY_STORE, quality); } catch (err) { /* nur eine Bequemlichkeit */ }
      sim.quality.force(QUALITIES[index][1]);
      say(i18nKey("SIM3D_VR_QUALITY") + ": " + i18nKey(QUALITIES[index][2]));
      redraw();
    };
    /** Ein Knopf der Tafel wurde mit dem Laserstrahl angeklickt. */
    const activate = (id) => {
      if (id === "exit") { session.end(); return; }
      if (id === "close") { state.helpOpen = false; return; }
      if (id === "turn") cfg.turn = cfg.turn === "smooth" ? "snap" : "smooth";
      else if (id === "hands") cfg.swapHands = !cfg.swapHands;
      else if (id === "updown") cfg.swapUpDown = !cfg.swapUpDown;
      else if (id === "quality") { cycleQuality(); return; }
      saveCfg();
      redraw();
    };
    controllers.forEach((c, i) => c.addEventListener("selectstart", () => {
      const aim = c.userData.aim;
      if (state && state.helpOpen && aim && aim.id) activate(aim.id);
    }));

    state = { rig, tilt, saved, controllers, camera, last: performance.now(), turned: false, exitHeld: true, helpHeld: true, qualityHeld: true, helpOpen: true };
    let placed = false;

    const raycaster = new THREE.Raycaster();
    const origin = new THREE.Vector3();
    const direction = new THREE.Vector3();
    /** Zielt jeder Controller auf die Tafel? Setzt Laserlaenge, Zielpunkt und den Knopf unter dem Strahl. */
    const aimAtBoard = () => {
      let hovered = null;
      if (state.helpOpen) help.updateWorldMatrix(true, false);                              // Lage dieses Bildes (die Tafel kann gerade erst verschoben worden sein)
      controllers.forEach((c) => {
        const { ray, dot } = c.userData;
        c.userData.aim = null;
        ray.scale.z = 0.4; dot.visible = false;
        if (!state.helpOpen) return;
        c.updateWorldMatrix(true, false);
        origin.setFromMatrixPosition(c.matrixWorld);
        direction.set(0, 0, -1).transformDirection(c.matrixWorld);
        raycaster.set(origin, direction);
        const hit = raycaster.intersectObject(help, false)[0];
        if (!hit || !hit.uv) return;
        const px = hit.uv.x * HELP_W, py = (1 - hit.uv.y) * HELP_H;
        const b = boardButtons.find((k) => px >= k.x && px <= k.x + k.w && py >= k.y && py <= k.y + k.h);
        c.userData.aim = { id: b ? b.id : null };
        ray.scale.z = hit.distance; dot.position.set(0, 0, -hit.distance); dot.visible = true;
        if (b) hovered = b.id;
      });
      if (hovered !== hover) { hover = hovered; redraw(); }
    };

    const head = new THREE.Vector3();
    const forward = new THREE.Vector3();
    const loop = () => {
      const now = performance.now();
      const dt = Math.min(0.1, (now - state.last) / 1000);
      state.last = now;
      renderer.xr.updateCamera(camera);                                                    // Kopfhaltung dieses Bildes, bevor irgendetwas rechnet (Eingabe, Bildhaken fuer Licht und Dunst)
      if (!placed) { placeHelp(); placed = true; }
      pollInput(dt, head, forward);
      if (!session) return;
      help.visible = state.helpOpen;
      flash.visible = now < flashUntil;
      aimAtBoard();
      sim.frameHooks.forEach((fn) => fn());
      renderer.render(sim.scene, camera);
    };
    const pollInput = (dt, headPos, fwd) => {
      const roles = vrRoles(cfg);
      let moveX = 0, moveY = 0, turnX = 0, climb = 0, fast = false, exit = false, helpKey = false, qualityKey = false;
      for (const source of session.inputSources) {
        const gp = source.gamepad;
        if (!gp) continue;
        const hand = source.handedness;
        const ax = gp.axes.length >= 4 ? [gp.axes[2], gp.axes[3]] : [gp.axes[0] || 0, gp.axes[1] || 0];
        const dz = (v) => (Math.abs(v) < DEAD ? 0 : v);
        const pressed = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);
        if (pressed(0)) fast = true;                                                       // Trigger (beide Haende)
        if (hand === roles.moveHand) { moveX = dz(ax[0]); moveY = -dz(ax[1]); }
        else if (hand === roles.turnHand) { turnX = ax[0]; climb += -dz(ax[1]); }
        if (hand === "left" && pressed(3)) helpKey = true;                                  // linker Stick druecken: Tafel
        if (hand === "right" && pressed(3)) qualityKey = true;                              // rechter Stick druecken: Qualitaet
        if (pressed(4)) { if (hand === roles.upHand) climb += 1; else if (hand === roles.downHand) climb -= 1; }          // A / X
        if (pressed(5)) exit = true;                                                       // B (rechts) / Y (links)
      }
      if (exit && !state.exitHeld) { session.end(); return; }
      state.exitHeld = exit;
      if (helpKey && !state.helpHeld) {
        state.helpOpen = !state.helpOpen;
        if (state.helpOpen) placeHelp();
      }
      state.helpHeld = helpKey;
      if (qualityKey && !state.qualityHeld) cycleQuality();
      state.qualityHeld = qualityKey;
      camera.getWorldPosition(headPos);
      camera.getWorldDirection(fwd);
      fwd.z = 0;
      if (fwd.lengthSq() < 1e-4) fwd.set(Math.sin(rig.rotation.z) * -1, Math.cos(rig.rotation.z), 0);
      fwd.normalize();
      if (moveX || moveY) {
        const v = SPEED * (fast ? FAST : 1) * dt;
        rig.position.x += (fwd.x * moveY + fwd.y * moveX) * v;
        rig.position.y += (fwd.y * moveY - fwd.x * moveX) * v;
      }
      if (climb) rig.position.z = Math.min(MAX_HEIGHT, Math.max(0, rig.position.z + Math.max(-1, Math.min(1, climb)) * CLIMB * (fast ? 2 : 1) * dt));
      let turn = 0;                                                                        // Drehung um den Kopf (nicht um den Fuss der Rig)
      if (cfg.turn === "smooth") {
        const v = Math.abs(turnX) < DEAD ? 0 : turnX;
        turn = -v * SMOOTH_TURN * dt;
      } else if (Math.abs(turnX) > 0.7) {
        if (!state.turned) { state.turned = true; turn = -Math.sign(turnX) * SNAP; }
      } else state.turned = false;
      if (turn) {
        const cx = headPos.x, cy = headPos.y;
        const dx = rig.position.x - cx, dy = rig.position.y - cy;
        rig.position.x = cx + dx * Math.cos(turn) - dy * Math.sin(turn);
        rig.position.y = cy + dx * Math.sin(turn) + dy * Math.cos(turn);
        rig.rotation.z += turn;
      }
    };

    renderer.setAnimationLoop(loop);
    button.classList.add("sim3d__btn--on");
    session.addEventListener("end", () => {
      renderer.setAnimationLoop(null);
      renderer.xr.enabled = false;
      camera.remove(flash);
      [flash, help].forEach((m) => { m.geometry.dispose(); m.material.dispose(); });
      flashTexture.dispose(); helpTexture.dispose();
      controllers.forEach((c) => { tilt.remove(c); c.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); });
      [rayMaterial, bodyMaterial, headMaterial, dotMaterial].forEach((m) => m.dispose());
      tilt.remove(camera);
      sim.scene.remove(rig);
      camera.position.copy(saved.pos);
      camera.quaternion.copy(saved.quat);
      camera.up.set(0, 0, 1);
      camera.updateProjectionMatrix();
      sim.controls.target.copy(saved.target);
      sim.vrActive = false;
      sim.quality.force(null);
      sim.controls.update();
      button.classList.remove("sim3d__btn--on");
      session = null;
      state = null;
      sim.invalidate();
    });
  }

  button.addEventListener("click", () => {
    if (!navigator.xr && quest && !secure) { toast("SIM3D_VR_NEEDS_HTTPS"); return; }
    enter();
  });

  return {
    get supported() { return supported; },
    get active() { return !!session; },
    button,
    refreshVisible,
    dispose() { clearTimeout(recheck); if (session) { try { session.end(); } catch (err) { /* schon beendet */ } } button.remove(); },
  };
}

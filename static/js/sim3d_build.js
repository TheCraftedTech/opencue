// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* 3D-Simulation, Baumodus. Oben links schaltet ein Umschalter zwischen "Ansicht" (nur anschauen) und "Bauen". Im Baumodus gleitet rechts eine breite Seitenleiste ein
 * (die Mitte der Buehne rueckt dabei in die Mitte des freien Bereichs): Grundkoerper hinzufuegen (Quader, Zylinder, Kugel, Keil) oder eigene 3D-Modelle (STL/OBJ aus der
 * Modell-Bibliothek, app/sim_models.py - ein Modell wird in seinen Rahmen = Groesse gestreckt, die Datei-Einheit mm/cm/m/Zoll setzt die Originalgroesse), Objekte in der Liste oder im Bild waehlen,
 * Eigenschaften aendern (Name, Farbe, Position, Drehung, Groesse), duplizieren, loeschen (mit Rueckfrage). Alle Masse in Metern (eine Rasterkachel = 1 m), Winkel in Grad, Z nach oben.
 *
 * Direkt im Bild (wie in Tinkercad): ein gewaehltes Objekt hat einen gelben Rahmen und Griffe -
 *   - Ziehen auf dem Objekt verschiebt es auf dem Boden (auch ein ungewaehltes: es wird dabei gewaehlt),
 *   - weisse Punkte an den vier unteren Ecken aendern die Groesse (X/Y) einseitig: die gegenueberliegende Ecke bleibt stehen (Umschalt = gleichmaessig, Alt = von der Mitte aus).
 *     Die Griffe sitzen auf der Welt-Box des Objekts am unteren Rand und drehen sich NIE mit; ein gedrehtes Objekt wird so skaliert, dass seine Welt-Box die gezogene Groesse erhaelt,
 *   - der weisse Punkt oben aendert die Hoehe, das gruene Dreieck darueber hebt das Objekt (Z),
 *   - mehrere gewaehlte Koerper/Scheinwerfer haben dieselben Griffe und Pfeile als Gruppe (Skalieren/Verzerren, Drehen um die Mitte, Heben; Scheinwerfer drehen sich dabei an Ort und Stelle, Alt = starr um die Mitte),
 *   - Maus wie in Tinkercad: links waehlen/verschieben/Rahmen aufziehen, rechts die Ansicht drehen, Mitte verschieben, Rad zoomt (Touch: ein Finger dreht die Ansicht wie bisher),
 *   - drei kleine Dreh-Pfeile (X rot, Y gruen, Z blau) drehen um die jeweilige Achse (5-Grad-Schritte); Strichstaerke und Greifflaeche haben eine feste
 *     Bildschirmgroesse (wachsen nicht mit dem Objekt), damit sie das Objekt nicht verdecken und das Verschieben nicht abfangen.
 * POSITION = Fusspunkt (Mitte der Unterseite): steht das Objekt auf dem Boden, ist Z = 0. Gedreht wird um diesen Fusspunkt ("Auf Boden setzen" schiebt ein gedrehtes Objekt
 * so, dass sein tiefster Punkt auf dem Boden liegt). Raster-Einrasten waehlbar (Standard 0,5 m).
 * Rueckgaengig/Wiederholen (Strg+Z / Strg+Y): jede abgeschlossene Aenderung ist ein Schritt. Die Objekte gehoeren zur aktiven BUEHNE auf dem Server (app/sim_stages.py,
 * Verwaltung und Toolbar-Chip in sim3d_stages.js): jede Aenderung geht (leicht gebuendelt) dorthin und zu allen Geraeten; Speichern schreibt die Buehnen-Datei.
 * Wechsel Bauen -> Ansicht mit ungespeicherten Aenderungen fragt: Weiter bearbeiten / Verwerfen / Speichern. */
import * as THREE from "three";
import { createTestSpot } from "/static/js/sim3d_spot.js";
import { createLive } from "/static/js/sim3d_live.js";
import { createAim, canAim } from "/static/js/sim3d_aim.js";
import { attachScreen } from "/static/js/sim3d_screen.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const MAX_OBJECTS = 200;
const MIN_SIZE = 0.05;
const SHAPES = {
  box: { key: "SIM3D_BOX", icon: "cube", size: [2, 2, 1] },
  screen: { key: "SIM3D_SCREEN", icon: "screen", size: [3.2, 0.02, 1.8] },          // Bildschirm: duenne Tafel mit Bild/Video (sim3d_screen.js); Dicke in Metern (2 cm, bis 1 mm einstellbar)
  cylinder: { key: "SIM3D_CYLINDER", icon: "cylinder", size: [1, 1, 2] },
  sphere: { key: "SIM3D_SPHERE", icon: "sphere", size: [1, 1, 1] },
  wedge: { key: "SIM3D_WEDGE", icon: "wedge", size: [2, 2, 1] },
  model: { key: "SIM3D_MODEL", icon: "model", size: [1, 1, 1], library: true },          // eigenes 3D-Modell: wird ueber die Modell-Liste hinzugefuegt
};
const MODEL_UNITS = { mm: 0.001, cm: 0.01, m: 1, in: 0.0254 };
const MODEL_UNIT_KEYS = { mm: "SIM3D_UNIT_MM", cm: "SIM3D_UNIT_CM", m: "SIM3D_UNIT_M", in: "SIM3D_UNIT_IN" };
/** Einheit einer Datei schaetzen: CAD-Dateien sind meist in Millimetern (eine 2-m-Traverse = 2000); was hoechstens 50 gross ist, gilt als Meter. */
const guessUnit = (size) => (Math.max(...size) > 50 ? "mm" : "m");
// Dreh-Pfeile: Masse in "Bildschirm-Einheiten" u (~1 % der Bildhoehe), unabhaengig von der Objektgroesse
const ARC_SPAN = Math.PI / 3;
const ARC_TUBE = 0.16;                 // Strich (schlank)
const ARC_HIT = 1.1;                   // Greifflaeche (Halbmesser) - vorher wuchs sie mit dem Objekt und fing das Verschieben ab
const ARC_TIP_R = 0.6;
const ARC_TIP_L = 1.7;
// Griffe: feste Bildschirmgroesse in Pixeln (unabhaengig von Zoom und Objektgroesse); getroffen wird per Abstand zum Griffmittelpunkt in Pixeln, mit der Maus eng, mit dem Finger weit
const HANDLE_PX = 10;
const LIFT_PX = 17;
const UNIT_PX = 11;                    // "u" der Dreh-Pfeile
const PICK_PX_MOUSE = 12;
const PICK_PX_TOUCH = 26;

// ---- 3D-Modelle (STL): einmal je Datei geladen und auf einen Einheitswuerfel gebracht (Unterseite z = 0, Mitte x/y = 0), alle Panels teilen die Geometrie
const stlCache = new Map();            // Dateiname -> Promise<{geometry, native: [x, y, z]} | null>
function parseStl(buffer) {
  if (!buffer || buffer.byteLength < 84) return null;
  const view = new DataView(buffer);
  const count = view.getUint32(80, true);
  if (!count || buffer.byteLength < 84 + count * 50) return null;
  const positions = new Float32Array(count * 9);
  let colors = null;                                                    // Farbe je Dreieck (MVR-Import): Attribut-Bytes, Bit 15 = gueltig, je 5 Bit R / G / B (app/sim_models.py pack_colors)
  for (let i = 0; i < count; i++) {
    const base = 84 + i * 50 + 12;                                      // 12 Bytes Normale ueberspringen (die rechnet three selbst)
    for (let k = 0; k < 9; k++) positions[i * 9 + k] = view.getFloat32(base + k * 4, true);
    const attr = view.getUint16(base + 36, true);
    if (attr & 0x8000) {
      if (!colors) { colors = new Float32Array(count * 9).fill(0.62); }
      const r = ((attr >> 10) & 31) / 31, g = ((attr >> 5) & 31) / 31, b = (attr & 31) / 31;
      for (let v = 0; v < 3; v++) { colors[i * 9 + v * 3] = r; colors[i * 9 + v * 3 + 1] = g; colors[i * 9 + v * 3 + 2] = b; }
    }
  }
  positions.colors = colors;
  return positions;
}
function loadStl(filename) {
  if (!stlCache.has(filename)) {
    stlCache.set(filename, fetch("/api/sim-models/file/" + encodeURIComponent(filename))
      .then((r) => (r.ok ? r.arrayBuffer() : null))
      .then((buffer) => {
        const positions = parseStl(buffer);
        if (!positions) return null;
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        if (positions.colors) g.setAttribute("color", new THREE.BufferAttribute(positions.colors, 3));
        g.computeBoundingBox();
        const b = g.boundingBox;
        const size = b.getSize(new THREE.Vector3());
        g.translate(-(b.min.x + b.max.x) / 2, -(b.min.y + b.max.y) / 2, -b.min.z);
        g.scale(1 / (size.x || 1), 1 / (size.y || 1), 1 / (size.z || 1));
        g.computeVertexNormals();
        g.computeBoundingBox();
        g.computeBoundingSphere();
        return { geometry: g, native: [size.x, size.y, size.z], colored: !!positions.colors };
      })
      .catch(() => null));
  }
  return stlCache.get(filename);
}
let modelPlaceholder = null;           // Quader, solange ein Modell laedt oder seine Datei fehlt
const SNAPS = [0.1, 0.25, 0.5, 1, 0];
/** Oberflaechen (PBR: roughness = Rauheit, metalness = Metall, env = Staerke der Umgebungs-Spiegelung). Die Farbe bleibt frei waehlbar.
 *  Spiegelungen zeigen eine feste Studio-Umgebung (RoomEnvironment); sobald es Scheinwerfer gibt, wird ihre Staerke an das vorhandene Licht gekoppelt. */
const MATERIALS = {
  matt: { key: "SIM3D_MAT_MATT", roughness: 0.92, metalness: 0, env: 0 },
  satin: { key: "SIM3D_MAT_SATIN", roughness: 0.55, metalness: 0, env: 0.25 },
  glossy: { key: "SIM3D_MAT_GLOSSY", roughness: 0.18, metalness: 0, env: 0.7 },
  metal: { key: "SIM3D_MAT_METAL", roughness: 0.32, metalness: 0.9, env: 1 },
  mirror: { key: "SIM3D_MAT_MIRROR", roughness: 0.05, metalness: 1, env: 1.2 },
};
const DEFAULT_COLOR = "#9c9ca0";                 // neutrales Grau (wie der globale Stil)
let clipboard = null;                              // kopierte Objekte {items: [...], cut} (gilt fuer alle 3D-Panels)
let pasteCount = 0;
const AXES = [[[0, 1, 0], [0, 0, 1], 45], [[0, 0, 1], [1, 0, 0], 45], [[1, 0, 0], [0, 1, 0], 205]];     // je Drehachse (X, Y, Z): zwei Richtungen u, w (u x w = Achse) und Startwinkel des Pfeils
const AXIS_COLORS = [0xff5a5a, 0x4fd66b, 0x4aa3ff];
const round = (v, d = 3) => Math.round(v * 10 ** d) / 10 ** d;
const deg = THREE.MathUtils.degToRad;
const fmt = (v) => String(round(v, 2)).replace(".", ",");

/** Einheitsgeometrien mit der Unterseite auf z = 0 (Fusspunkt im Ursprung), Hoehe 1. */
function buildGeometry(type) {
  let g;
  if (type === "cylinder") {
    g = new THREE.CylinderGeometry(0.5, 0.5, 1, 48, 1);
    g.rotateX(Math.PI / 2);
  } else if (type === "sphere") {
    g = new THREE.SphereGeometry(0.5, 40, 24);
    g.rotateX(Math.PI / 2);
  } else if (type === "wedge") {          // Dreiecksprisma: rechtwinkliges Dreieck in der XZ-Ebene (hoch bei -X), Tiefe entlang Y
    const A = [-0.5, -0.5, 0], B = [0.5, -0.5, 0], C = [-0.5, -0.5, 1];
    const D = [-0.5, 0.5, 0], E = [0.5, 0.5, 0], F = [-0.5, 0.5, 1];
    const tris = [A, B, C, D, F, E, A, D, E, A, E, B, A, C, F, A, F, D, B, E, F, B, F, C];
    g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(tris.flat()), 3));
    g.computeVertexNormals();
    return g;
  } else {
    g = new THREE.BoxGeometry(1, 1, 1);
  }
  g.translate(0, 0, 0.5);
  return g;
}

export function attachBuilder(root, sim) {
  const t = (key) => i18n(key);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const geometries = {};
  const entries = new Map();            // id -> {data, group, mesh, material, frame, kind: "object"}
  const counts = { box: 0, cylinder: 0, sphere: 0, wedge: 0, model: 0, screen: 0 };
  let modelList = null;                  // Modell-Bibliothek (GET /api/sim-models), geladen bei Bedarf
  let modelsOpen = false;                // Liste "Modell hinzufuegen" in der Seitenleiste aufgeklappt
  let counter = 0;
  let selected = null;                   // Hauptauswahl: Objekt-Id, "spot" oder null
  const extra = new Set();               // weitere gewaehlte Objekte (Umschalt-Klick): zusammen mit `selected` die Mehrfachauswahl
  const fixtureEntries = new Map();      // Scheinwerfer-Id -> {id, kind: "fixture", data: {position, rotation, size}, group, mesh (Trefferkoerper), frame}
  const entryOf = (id) => entries.get(id) || fixtureEntries.get(id);
  const editing = () => mode !== "view";                       // Bauen und Scheinwerfer: Seitenleiste, Auswahl, Hilfen
  /** Im Modus "Scheinwerfer" lassen sich nur Scheinwerfer waehlen, im Modus "Bauen" nur Koerper. */
  const inMode = (entry) => !!entry && (mode === "fixtures" ? entry.kind === "fixture" && !entry.data.hidden : entry.kind !== "fixture");
  const selectedIds = () => (selected && selected !== "spot" && inMode(entryOf(selected)) ? [selected] : []).concat([...extra].filter((id) => inMode(entryOf(id))));
  const isSelected = (id) => id === selected || extra.has(id);
  let layout = {};                       // Positionen der Scheinwerfer (gehoeren zur Show): Id -> {position, rotation}
  let fxHistory = [];
  let fxIndex = 0;
  let fxPushTimer = 0;
  let fxRows = null;                     // Rueckgaengig/Wiederholen in der Seitenleiste des Modus "Scheinwerfer"
  let fxFilter = "";                     // Suchtext der Scheinwerfer-Liste
  let fxMulti = false;                   // Mehrfachwahl: jedes Antippen in der Liste fuegt hinzu / nimmt heraus (fuer Touch)
  let fxScroll = 0;
  let fxAnchor = null;                   // zuletzt angeklickter Eintrag (Anfang des Umschalt-Bereichs)
  let dupChain = null;                   // Strg+D: {ids, prev} - die letzte Kopie und die Lage ihrer Vorlage (fuer "dasselbe nochmal")
  let nudgeTimer = 0;
  let mode = "view";
  let snap = 0.5;
  let drag = null;
  let fieldRefs = null;                  // Eingabefelder der Eigenschaften (werden beim Ziehen nachgefuehrt)
  const uid = "p" + Math.random().toString(36).slice(2, 10);       // Kennung dieses Panels (sein Echo vom Server wird ignoriert)
  const stages = () => window.OCSimStages || null;
  let history = [];                      // Schritte fuer Rueckgaengig/Wiederholen (JSON der Objektliste)
  let hIndex = 0;
  let pushTimer = 0;
  let appliedRevision = -1;
  let stageRow = null;                   // Elemente der Buehnen-Zeile der Seitenleiste

  let envTexture = null;                 // Studio-Umgebung fuer Spiegelungen (erst bei der ersten glaenzenden Oberflaeche erzeugt)
  const environment = () => {
    if (!envTexture) {
      const generator = new THREE.PMREMGenerator(sim.renderer);
      envTexture = generator.fromScene(new RoomEnvironment(), 0.04).texture;
      generator.dispose();
    }
    return envTexture;
  };
  const makeMaterial = (kind, color) => {
    const def = MATERIALS[kind] || MATERIALS.matt;
    const material = new THREE.MeshStandardMaterial({ color, roughness: def.roughness, metalness: def.metalness });
    if (def.env > 0) { material.envMap = environment(); material.envMapIntensity = def.env * room.envScale; material.userData.envBase = def.env; }
    material.userData.kind = kind;
    sim.patchBleed(material);
    return material;
  };

  // Beleuchtung des Raums (Arbeitslicht, Raumlicht durch Lichtquellen) steckt in sim3d_room.js; die Spiegelungen glaenzender Koerper folgen ihrer Helligkeit
  const room = sim.room;
  const setWorkLevel = (pct) => room.setWork(pct, false);
  const applyEnv = () => entries.forEach((en) => { const base = en.material.userData.envBase; if (base) en.material.envMapIntensity = base * room.envScale; });
  room.onEnv(applyEnv);
  /** Fuer das Raumlicht: Ausdehnung, Oberflaeche und Farbe (Reflexion) aller Koerper. */
  const boxA = new THREE.Box3();
  const boxB = new THREE.Box3();
  sim.roomInfo = () => {
    let area = 0;
    const albedo = [0, 0, 0];
    boxA.makeEmpty();
    entries.forEach((en) => {
      const [x, y, z] = en.data.size;
      const base = 2 * (x * y + y * z + x * z);
      const a = en.data.type === "sphere" ? Math.PI * ((x + y + z) / 3) ** 2 : en.data.type === "cylinder" ? Math.PI * ((x + y) / 2) * z + Math.PI * x * y / 2 : en.data.type === "wedge" ? base * 0.8 : base;
      const m = en.material;
      const k = 1 - (m.metalness || 0);
      area += a;
      albedo[0] += a * m.color.r * k; albedo[1] += a * m.color.g * k; albedo[2] += a * m.color.b * k;
      en.mesh.updateWorldMatrix(true, false);
      boxA.union(boxB.setFromObject(en.mesh));
    });
    if (boxA.isEmpty()) return { min: [0, 0, 0], max: [0, 0, 0], area: 0, albedo };
    return { min: [boxA.min.x, boxA.min.y, boxA.min.z], max: [boxA.max.x, boxA.max.y, boxA.max.z], area, albedo };
  };

  // ------------------------------------------------------------------------------------------ Umschalter und Seitenleiste
  const modes = el("div", "sim3d__modes");
  modes.setAttribute("role", "tablist");
  const modeButtons = {};
  [["view", "SIM3D_MODE_VIEW", "eye"], ["build", "SIM3D_MODE_BUILD", "cube"], ["fixtures", "SIM3D_MODE_FIXTURES", "fixture"]].forEach(([id, key, icon]) => {
    const b = el("button", "sim3d__mode");
    b.type = "button";
    b.setAttribute("role", "tab");
    const label = el("span", "sim3d__mode-label", t(key));
    label.dataset.i18n = key;
    b.append(Icons.svg(icon), label);
    b.addEventListener("click", () => requestMode(id));
    modes.appendChild(b);
    modeButtons[id] = b;
  });
  const side = el("aside", "sim3d__side");
  side.hidden = true;
  const readout = el("div", "sim3d__readout");
  readout.hidden = true;
  root.append(modes, side, readout);
  root.tabIndex = -1;

  // ------------------------------------------------------------------------------------------ Breite der Seitenleiste (Ziehgriff)
  const SIDE_KEY = "opencue.sim3d.sidefrac";                          // Anteil an der Panelbreite (0.2 .. 0.75), gemerkt je Geraet (localStorage; die Konsole spiegelt opencue.*-Schluessel in die Einstellungen)
  const SIDE_MIN = 240;                                              // Pixel: nie schmaler
  const FRAC_MAX = 0.75;                                             // nie mehr als drei Viertel: die 3D-Ansicht bleibt immer sichtbar
  const clampFrac = (f) => Math.max(0.1, Math.min(FRAC_MAX, f));
  /** Die Breite ist immer ein PROZENTWERT (mit Pixel-Untergrenze): aendert sich die Panelgroesse (Vollbild an / aus, Fenster, Layout), bleibt der Anteil gleich. */
  const setSideFrac = (f) => root.style.setProperty("--side", "clamp(" + SIDE_MIN + "px, " + (clampFrac(f) * 100).toFixed(2) + "%, " + FRAC_MAX * 100 + "%)");
  try {
    localStorage.removeItem("opencue.sim3d.side");                   // fruehere Fassung speicherte Pixel
    const saved = parseFloat(localStorage.getItem(SIDE_KEY));
    if (saved > 0 && saved <= 1) setSideFrac(saved);
  } catch (err) { /* ohne Speicher */ }
  const sideObserver = new ResizeObserver(() => { if (editing()) { sim.setShift(side.offsetWidth / 2); sim.invalidate(); } });      // Panelgroesse geaendert (Vollbild ...): die Mitte der Buehne folgt
  sideObserver.observe(root);
  const grip = el("div", "sim3d__resize");
  grip.title = t("SIM3D_RESIZE");
  grip.setAttribute("role", "separator");
  grip.setAttribute("aria-orientation", "vertical");
  root.appendChild(grip);
  let gripDrag = null;
  const currentSide = () => side.offsetWidth;
  grip.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    grip.setPointerCapture(e.pointerId);
    grip.classList.add("sim3d__resize--drag");
    gripDrag = { right: root.getBoundingClientRect().right };
  });
  grip.addEventListener("pointermove", (e) => {
    if (!gripDrag) return;
    const total = root.clientWidth || 1;
    setSideFrac((gripDrag.right - e.clientX) / total);
    sim.setShift(side.offsetWidth / 2);                              // die Mitte der Buehne bleibt in der Mitte des freien Bereichs
    sim.invalidate();
  });
  const gripEnd = (e) => {
    if (!gripDrag) return;
    gripDrag = null;
    grip.classList.remove("sim3d__resize--drag");
    try { grip.releasePointerCapture(e.pointerId); } catch (err) { /* schon frei */ }
    try { localStorage.setItem(SIDE_KEY, String(clampFrac(currentSide() / (root.clientWidth || 1)).toFixed(4))); } catch (err) { /* ohne Speicher */ }
    sim.invalidate();
  };
  grip.addEventListener("pointerup", gripEnd);
  grip.addEventListener("pointercancel", gripEnd);
  grip.addEventListener("dblclick", () => {                          // Doppelklick: wieder die Standardbreite
    root.style.removeProperty("--side");
    try { localStorage.removeItem(SIDE_KEY); } catch (err) { /* ohne Speicher */ }
    if (editing()) sim.setShift(currentSide() / 2);
    sim.invalidate();
  });

  /** Wechsel des Modus. Bauen -> Ansicht mit ungespeicherten Aenderungen: Dialog "Weiter bearbeiten / Verwerfen / Speichern" (wie beim Verlassen des Panel-Bearbeitungsmodus). */
  async function requestMode(next) {
    if (next === mode) return;
    if (mode === "fixtures") await flushFx();                        // Positionen der Scheinwerfer gehen als Teil der Show sofort an den Server
    if (mode === "build" && next === "view") {
      await flushPush();
      const cur = stages() && stages().current;
      if (cur && cur.dirty && typeof _askExitEdit === "function") {
        const choice = await _askExitEdit(cur.name, { body: t("SIMSTAGE_EXIT_BODY").split("{name}").join(cur.name) });
        if (choice === "cancel") return;
        if (choice === "save") { if (!(await stages().save(false))) return; }
        else await stages().discard();
      }
    }
    setMode(next);
  }

  let hideTimer = 0;
  let persistMode = false;                                           // erst nach dem Start: der Anfangsmodus "view" darf den gemerkten nicht ueberschreiben
  function setMode(next) {
    const changed = next !== mode;
    if (persistMode && window.OCViewState) OCViewState.set(OCViewState.scopeOf(root), "sim3d:mode", next);
    if (changed && (selected || extra.size)) { extra.clear(); selected = null; clearSelectionVisuals(); }
    mode = next;
    sim.controls.mouseButtons.LEFT = editing() ? null : THREE.MOUSE.ROTATE;                    // Baumodus: links waehlen/verschieben/Rahmen, die Ansicht dreht die rechte Taste (Touch dreht wie bisher mit einem Finger)
    if (mode === "fixtures") syncFixtureEntries();
    root.classList.toggle("sim3d--build", editing());
    if (typeof spot !== "undefined") spot.setVisibleHelpers(mode === "build");
    room.setMode(mode);
    Object.entries(modeButtons).forEach(([id, b]) => { b.classList.toggle("sim3d__mode--on", id === mode); b.setAttribute("aria-selected", String(id === mode)); });
    clearTimeout(hideTimer);
    if (!editing() && jsonMode) { jsonMode = false; if (jsonPanel) jsonPanel.hide(); }        // Ansicht: zurueck zu den normalen Werkzeugen
    if (editing()) {
      renderSide();
      side.hidden = false;
      void side.offsetWidth;                                         // Startzustand uebernehmen, damit das Einblenden animiert
      side.classList.add("sim3d__side--in");
      sim.setShift(side.offsetWidth / 2);                            // die Mitte der Buehne rueckt in die Mitte des freien Bereichs
    } else {
      select(null);
      side.classList.remove("sim3d__side--in");
      sim.setShift(0);
      hideTimer = setTimeout(() => { if (editing()) return; side.hidden = true; }, 300);
    }
    sim.invalidate();
  }

  // ------------------------------------------------------------------------------------------ Objekte
  function apply(entry) {
    if (entry.kind === "fixture") { applyFixture(entry); return; }
    const d = entry.data;
    entry.group.position.set(...d.position);
    entry.group.rotation.set(deg(d.rotation[0]), deg(d.rotation[1]), deg(d.rotation[2]), "XYZ");
    entry.mesh.scale.set(...d.size);
    if ((entry.material.userData.kind || "matt") !== (d.material || "matt")) {      // Oberflaeche gewechselt: neues Material
      const old = entry.material;
      entry.material = makeMaterial(d.material, d.color);
      entry.mesh.material = entry.material;
      old.dispose();
    }
    entry.material.color.set(d.color);
    if (entry.screen) entry.screen.update();
    if (isSelected(entry.id)) layoutSelection(entry);
    sim.invalidate();
  }

  function addObject(type, source, offset = 0.5, keepName = false, silent = false) {
    if (entries.size >= MAX_OBJECTS) return null;
    geometries[type] = geometries[type] || buildGeometry(type);
    counts[type] += 1;
    counter += 1;
    const step = snap || 0.5;
    const near = (v) => Math.round(v / step) * step;
    const data = source ? { ...JSON.parse(JSON.stringify(source)), id: uniqueId(), name: keepName ? source.name : source.name + t("SIM3D_COPY_SUFFIX") }
      : { id: uniqueId(), type, name: t(SHAPES[type].key) + " " + counts[type], color: type === "screen" ? "#18181c" : DEFAULT_COLOR, position: [near(sim.controls.target.x), near(sim.controls.target.y), type === "screen" ? 1 : 0], rotation: [0, 0, 0], size: SHAPES[type].size.slice(), material: "matt",
        ...(type === "screen" ? screenDefaults() : {}) };
    if (source) data.position = [round(source.position[0] + offset), round(source.position[1] + offset), source.position[2]];
    const entry = createEntry(data);
    if (entry && !silent) commit();
    return entry;
  }

  /** Felder eines neuen Bildschirms (gleich wie app/sim_stages.py normalize_screen). */
  const screenDefaults = () => ({ media: "", fit: "stretch", look: { brightness: 100, contrast: 100, saturation: 100, hue: 0, tint: "#ffffff", flip: false }, sync: "timecode", tc_start_ms: 0, loop: true, muted: true, emissive: true });
  let reuseScreens = null;                                                                  // beim Neuaufbau der Buehne (Rueckgaengig, anderes Geraet) laufen Videos weiter, statt neu zu starten
  const uniqueId = () => { let id; do { counter += 1; id = "o" + counter; } while (entries.has(id)); return id; };

  /** Koerper (Netz in der Szene) zu den Daten anlegen, ohne Verlauf/Server zu beruehren. */
  function createEntry(data) {
    let geometry;
    if (data.type === "model") geometry = modelPlaceholder || (modelPlaceholder = new THREE.BoxGeometry(1, 1, 1).translate(0, 0, 0.5));
    else geometry = geometries[data.type] = geometries[data.type] || buildGeometry(data.type);
    data.material = MATERIALS[data.material] ? data.material : "matt";
    const material = makeMaterial(data.material, data.color);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData.id = data.id;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const group = new THREE.Group();
    group.add(mesh);
    sim.scene.add(group);
    const entry = { id: data.id, kind: "object", data, group, mesh, material, frame: null };
    entries.set(data.id, entry);
    if (data.type === "screen") {
      const kept = reuseScreens && reuseScreens.get(data.id);
      if (kept) { reuseScreens.delete(data.id); entry.screen = kept; kept.attach(entry); }
      else entry.screen = attachScreen(sim, entry);
    }
    apply(entry);
    if (data.type === "model") attachModel(entry);
    return entry;
  }

  /** Netz eines Modells nachladen; fehlt die Datei, bleibt ein Gitter-Quader als Platzhalter (die Seitenleiste sagt, welche Datei fehlt). */
  function attachModel(entry) {
    entry.loading = true;
    loadStl(entry.data.model).then((loaded) => {
      if (entries.get(entry.id) !== entry) return;                     // inzwischen entfernt/ersetzt
      entry.loading = false;
      if (!loaded) {
        entry.missing = true;
        entry.material.wireframe = true;
      } else {
        entry.missing = false;
        entry.native = loaded.native;
        entry.mesh.geometry = loaded.geometry;
        if (loaded.colored && !entry.material.vertexColors) { entry.material.vertexColors = true; entry.material.side = THREE.DoubleSide; entry.material.needsUpdate = true; }          // Farben der Datei (z. B. aus einer MVR-Szene); die Farbe des Objekts faerbt sie ein. Beidseitig: Planungsprogramme liefern Vorhaenge / Waende oft mit unterschiedlicher Dreiecksrichtung (von einer Seite waeren sie unsichtbar)
      }
      if (isSelected(entry.id) && editing()) renderSide();
      sim.invalidate();
    });
  }

  /** Ein Modell der Bibliothek auf die Buehne stellen: Originalgroesse in der geschaetzten Einheit der Datei, auf dem Boden in der Bildmitte. */
  function addModel(info) {
    if (!info || entries.size >= MAX_OBJECTS) return null;
    const unit = guessUnit(info.size);
    const step = snap || 0.5;
    const near = (v) => Math.round(v / step) * step;
    counts.model += 1;
    const data = { id: uniqueId(), type: "model", model: info.id, unit, name: info.name, color: DEFAULT_COLOR, position: [near(sim.controls.target.x), near(sim.controls.target.y), 0],
      rotation: [0, 0, 0], size: info.size.map((v) => round(Math.max(MIN_SIZE, v * MODEL_UNITS[unit]))), material: "matt" };
    const entry = createEntry(data);
    commit();
    select(entry.id);
    return entry;
  }

  /** Mehrere Modelle auf einmal auf die Buehne stellen: in Reihen nebeneinander (Luecke 0,5 m, Reihen bis etwa 12 m breit), die Gruppe um die Bildmitte; alle neuen Objekte sind danach
   *  ausgewaehlt (gemeinsam verschiebbar) und ein einziger Schritt im Verlauf. */
  function addModels(infos) {
    const list = (infos || []).filter(Boolean).slice(0, Math.max(0, MAX_OBJECTS - entries.size));
    if (list.length <= 1) return list.length ? [addModel(list[0])] : [];
    const gap = 0.5;
    const maxRow = 12;
    const items = list.map((info) => {
      const unit = guessUnit(info.size);
      return { info, unit, size: info.size.map((v) => round(Math.max(MIN_SIZE, v * MODEL_UNITS[unit]))) };
    });
    const rows = [];
    let row = { items: [], w: 0, h: 0 };
    items.forEach((it) => {
      if (row.items.length && row.w + gap + it.size[0] > maxRow) { rows.push(row); row = { items: [], w: 0, h: 0 }; }
      it.rx = row.items.length ? row.w + gap : 0;
      row.w = it.rx + it.size[0];
      row.h = Math.max(row.h, it.size[1]);
      row.items.push(it);
    });
    rows.push(row);
    const totalH = rows.reduce((sum, r) => sum + r.h, 0) + gap * (rows.length - 1);
    const cx = sim.controls.target.x;
    const cy = sim.controls.target.y;
    let top = cy - totalH / 2;
    const ids = [];
    rows.forEach((r) => {
      r.items.forEach((it) => {
        counts.model += 1;
        const data = { id: uniqueId(), type: "model", model: it.info.id, unit: it.unit, name: it.info.name, color: DEFAULT_COLOR,
          position: [round(cx - r.w / 2 + it.rx + it.size[0] / 2), round(top + r.h / 2), 0], rotation: [0, 0, 0], size: it.size, material: "matt" };
        ids.push(createEntry(data).id);
      });
      top += r.h + gap;
    });
    commit();
    selectMany(ids);
    return ids.map((id) => entries.get(id));
  }

  /** Modell-Bibliothek holen (fuer die Liste "Modell hinzufuegen" und die Eigenschaften). */
  async function loadModelList(force) {
    if (modelList && !force) return modelList;
    try { modelList = (await (await fetch("/api/sim-models")).json()).models || []; } catch (err) { modelList = []; }
    return modelList;
  }

  /** STL/OBJ-Dateien einlesen (dieselbe Pruefung wie im Dateimanager), eine nach der anderen, und alle gemeinsam auf die Buehne stellen. Fehler einzelner Dateien stoppen die anderen nicht. */
  async function importModelFiles(files) {
    const say = (text, type) => { if (typeof _showToast === "function") _showToast(text, type || "info", 4000); };
    const picked = [...files].filter((f) => /\.(stl|obj)$/i.test(f.name));
    if (!picked.length) { if (files.length) say(t("SIM3D_MODEL_IMPORT_NONE"), "warn"); return; }
    const ids = [];
    for (const file of picked) {
      let data = {};
      let ok = false;
      try {
        const res = await fetch("/api/files/models/upload?filename=" + encodeURIComponent(file.name), { method: "POST", body: file });
        data = await res.json().catch(() => ({}));
        ok = res.ok && data.ok;
      } catch (err) { data = { message: String(err) }; }
      if (ok) ids.push(data.id);
      else say((picked.length > 1 ? file.name + ": " : "") + t("SIM3D_MODEL_IMPORT_FAILED").split("{msg}").join(data.message || data.error || "?"), "error");
    }
    if (!ids.length) return;
    await loadModelList(true);
    const added = addModels(ids.map((id) => modelList.find((m) => m.id === id)));
    if (ids.length > 1) say(t("SIM3D_MODEL_IMPORT_MANY").split("{n}").join(String(added.length)), "info");
    if (window.OCFileManager) window.OCFileManager.changed("models");
  }
  const importModelFile = (file) => importModelFiles([file]);
  function pickModelFile() {
    const input = el("input");
    input.type = "file";
    input.accept = ".stl,.obj";
    input.multiple = true;
    input.hidden = true;
    input.addEventListener("change", () => { const files = [...(input.files || [])]; input.remove(); if (files.length) importModelFiles(files); });
    document.body.appendChild(input);
    input.click();
  }

  const serialize = () => [...entries.values()].map((en) => JSON.parse(JSON.stringify(en.data)));

  /** Objektliste ersetzen (Laden, Rueckgaengig, Aenderung von einem anderen Geraet/Panel); die Auswahl bleibt, wenn es das Objekt noch gibt. */
  function loadObjects(list) {
    const keep = selected;
    const keepExtra = [...extra];
    clearSelectionVisuals();
    selected = null;
    extra.clear();
    reuseScreens = new Map();
    [...entries.keys()].forEach((id) => { const en = entries.get(id); sim.scene.remove(en.group); en.material.dispose(); if (en.screen) reuseScreens.set(id, en.screen); entries.delete(id); });
    for (const d of list) {
      const n = parseInt(String(d.id).replace(/\D/g, ""), 10);
      if (Number.isFinite(n) && n > counter) counter = n;
      counts[d.type] = Math.max(counts[d.type] || 0, 0);
      createEntry(JSON.parse(JSON.stringify(d)));
    }
    reuseScreens.forEach((screen) => screen.dispose());                       // Bildschirme, die es nicht mehr gibt
    reuseScreens = null;
    if (keep && entries.has(keep)) { selected = keep; keepExtra.filter((id) => entries.has(id)).forEach((id) => extra.add(id)); }
    if (editing()) refreshVisuals();
    sim.invalidate();
  }

  // ---- Verlauf (Rueckgaengig / Wiederholen)
  const snapshot = () => JSON.stringify(serialize());
  function resetHistory() { history = [snapshot()]; hIndex = 0; updateUndoButtons(); }
  /** Eine abgeschlossene Aenderung: Schritt im Verlauf merken und (gebuendelt) an den Server senden. */
  function commit() {
    const snap = snapshot();
    if (history[hIndex] === snap) return;
    history = history.slice(0, hIndex + 1);
    history.push(snap);
    if (history.length > 100) history.shift();
    hIndex = history.length - 1;
    schedulePush();
    updateUndoButtons();
  }
  /** Aktuellen Stand als weiteren Schritt merken, OHNE ihn an den Server zu senden (er kam von dort: Laden, Verwerfen, anderes Geraet). */
  function recordStep() {
    const snap = snapshot();
    if (history[hIndex] === snap) return;
    history = history.slice(0, hIndex + 1);
    history.push(snap);
    if (history.length > 100) history.shift();
    hIndex = history.length - 1;
    updateUndoButtons();
  }
  const commitCurrent = () => { if (mode === "fixtures") commitFx(); else commit(); };
  function undo() { if (hIndex > 0) { hIndex -= 1; loadObjects(JSON.parse(history[hIndex])); schedulePush(); updateUndoButtons(); } }
  function redo() { if (hIndex < history.length - 1) { hIndex += 1; loadObjects(JSON.parse(history[hIndex])); schedulePush(); updateUndoButtons(); } }
  function updateUndoButtons() {
    if (!stageRow) return;
    stageRow.undo.disabled = hIndex <= 0;
    stageRow.redo.disabled = hIndex >= history.length - 1;
  }

  // ---- Abgleich mit der aktiven Buehne auf dem Server
  function schedulePush() {
    clearTimeout(pushTimer);
    pushTimer = setTimeout(flushPush, 200);
  }
  async function flushPush() {
    if (!pushTimer) return;
    clearTimeout(pushTimer);
    pushTimer = 0;
    if (stages()) await stages().push(serialize(), uid);
  }
  function paintStage() {
    const cur = stages() && stages().current;
    if (!stageRow || !cur) return;
    stageRow.name.textContent = cur.name + (cur.dirty ? " *" : "");
    stageRow.save.classList.toggle("sim3d__btn--attention", !!cur.dirty);          // Speichern leuchtet gelb mit rotem Punkt, solange es etwas zu speichern gibt
  }
  /** Ereignis der Buehnen-Verwaltung: neue Objektliste von anderswo (Laden, Verwerfen, anderes Geraet/Panel) oder Stand der Buehne. */
  function onStage(e) {
    const { kind, stage, source } = e.detail || {};
    paintStage();
    if (stage && stage.fixture_layout && source !== uid && !drag && !fxPushTimer) applyRemoteLayout(stage.fixture_layout);       // Positionen von einem anderen Geraet/Panel oder aus einer geladenen Show
    if (!stage || !Array.isArray(stage.objects)) return;
    if (source === uid || (kind === "changed" && stage.revision === appliedRevision) || drag) return;
    if (pushTimer && kind === "changed") return;                       // eigene, noch nicht gesendete Aenderung geht vor
    appliedRevision = stage.revision;
    if (JSON.stringify(stage.objects) === snapshot()) return;           // z. B. nach dem Speichern: Objekte unveraendert -> Verlauf und Auswahl bleiben
    loadObjects(stage.objects);
    recordStep();
  }
  document.addEventListener("sim-stage", onStage);

  function removeObject(id) {
    const entry = entries.get(id);
    if (!entry) return;
    const wasSelected = isSelected(id);
    if (wasSelected) clearSelectionVisuals();
    sim.scene.remove(entry.group);
    entry.material.dispose();
    if (entry.screen) entry.screen.dispose();
    entries.delete(id);
    extra.delete(id);
    if (selected === id) { selected = extra.size ? [...extra].pop() : null; if (selected) extra.delete(selected); }
    if (wasSelected && editing()) refreshVisuals();
    sim.invalidate();
  }

  /** Loescht ein Objekt oder mehrere (Liste von Ids) nach Rueckfrage. */
  async function confirmDelete(idOrIds) {
    const ids = (Array.isArray(idOrIds) ? idOrIds : [idOrIds]).filter((id) => entries.has(id));
    if (!ids.length) return;
    const body = ids.length > 1 ? t("SIM3D_DELETE_MANY_BODY").split("{n}").join(String(ids.length)) : t("SIM3D_DELETE_BODY").split("{name}").join(entries.get(ids[0]).data.name);
    const ok = typeof _askLayoutConfirm === "function"
      ? await _askDelete("other", { title: t("SIM3D_DELETE_TITLE"), body, confirmKey: "SIM3D_DELETE_CONFIRM" })
      : window.confirm(body);
    if (!ok) return;
    ids.forEach((id) => removeObject(id));
    commit();
    if (editing()) renderSide();
  }

  // ------------------------------------------------------------------------------------------ Auswahl: gelber Rahmen, Griffe, Dreh-Pfeile
  const frameMaterial = new THREE.LineBasicMaterial({ color: 0xffd400, depthTest: false, transparent: true });
  const frameGeometry = new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1).translate(0, 0, 0.5));
  let handles = [];                      // {object, kind, cx, cy} - Kinder von handleRig (Weltachsen, drehen nie mit dem Objekt)
  let handleRig = null;                  // Gruppe in der Szene: Eck-, Hoehen- und Heben-Griffe und die Umrandung der Welt-Box
  let baseOutline = null;                // Linie um den Fuss der Welt-Box (verbindet die vier Eck-Griffe)
  let arcRig = null;                     // Dreh-Pfeile: Gruppe am Fusspunkt, achsparallel (dreht nicht mit)
  let arcs = [];

  const handleMaterial = (color) => new THREE.MeshBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.95 });
  function makeHandle(kind, geometry, color, cx = 0, cy = 0) {
    const object = new THREE.Mesh(geometry, handleMaterial(color));
    object.renderOrder = 30;
    return { object, kind, cx, cy };
  }

  /** Bogen, Spitze und Greifflaeche fuer das Verhaeltnis k = Bildschirm-Einheit / Radius (der Bogen selbst wird auf den Radius skaliert). */
  function arcGeometries(k) {
    return {
      tube: new THREE.TorusGeometry(1, ARC_TUBE * k, 8, 40, ARC_SPAN),
      tip: new THREE.ConeGeometry(ARC_TIP_R * k, ARC_TIP_L * k, 14),
      hit: new THREE.TorusGeometry(1, ARC_HIT * k, 6, 28, ARC_SPAN + 0.15),
    };
  }
  function shapeArc(arc, k) {
    const g = arcGeometries(k);
    arc.object.geometry.dispose(); arc.object.geometry = g.tube;
    const tip = arc.object.children[0];
    tip.geometry.dispose(); tip.geometry = g.tip;
    tip.position.set(Math.cos(ARC_SPAN) - Math.sin(ARC_SPAN) * ARC_TIP_L * k * 0.5, Math.sin(ARC_SPAN) + Math.cos(ARC_SPAN) * ARC_TIP_L * k * 0.5, 0);     // Spitze schliesst am Bogenende an
    arc.hit.geometry.dispose(); arc.hit.geometry = g.hit;
    arc.k = k;
  }
  function makeArc(axis) {
    const [u, w, theta] = AXES[axis];
    const k = 0.1;
    const g = arcGeometries(k);
    const mesh = new THREE.Mesh(g.tube, handleMaterial(AXIS_COLORS[axis]));
    mesh.renderOrder = 30;
    const tip = new THREE.Mesh(g.tip, mesh.material);       // Pfeilspitze am Ende des Bogens
    tip.rotation.z = ARC_SPAN;
    tip.renderOrder = 30;
    mesh.add(tip);
    const hit = new THREE.Mesh(g.hit, new THREE.MeshBasicMaterial({ visible: false }));
    mesh.add(hit);
    const U = new THREE.Vector3(...u), W = new THREE.Vector3(...w);
    const basis = new THREE.Matrix4().makeBasis(U, W, new THREE.Vector3().crossVectors(U, W));
    basis.multiply(new THREE.Matrix4().makeRotationZ(deg(theta)));
    mesh.quaternion.setFromRotationMatrix(basis);
    const arc = { object: mesh, hit, kind: "arc", axis, u: U, w: W, k };
    shapeArc(arc, k);
    return arc;
  }

  let handlesOwner = null;               // Objekt, an dem die Griffe haengen (nur bei Einzelauswahl)
  function clearSelectionVisuals() {
    entries.forEach((en) => { if (en.frame) { en.group.remove(en.frame); en.frame = null; } });
    fixtureEntries.forEach((en) => { if (en.frame) { en.group.remove(en.frame); en.frame = null; } });
    if (handleRig) {
      sim.scene.remove(handleRig);
      handles.forEach((h) => { h.object.geometry.dispose(); h.object.material.dispose(); });
      if (baseOutline) { baseOutline.geometry.dispose(); baseOutline.material.dispose(); }
    }
    handleRig = null;
    baseOutline = null;
    handlesOwner = null;
    handles = [];
    if (arcRig) {
      sim.scene.remove(arcRig);
      arcs.forEach((a) => { a.object.geometry.dispose(); a.object.material.dispose(); a.hit.geometry.dispose(); a.hit.material.dispose(); a.object.children[0].geometry.dispose(); });
    }
    arcRig = null;
    arcs = [];
  }

  function addFrame(entry) {
    if (entry.frame) return;
    entry.frame = new THREE.LineSegments(frameGeometry, frameMaterial);
    entry.frame.renderOrder = 29;
    entry.group.add(entry.frame);
    layoutSelection(entry);
  }

  /** Rahmen (und bei Einzelauswahl Griffe und Dreh-Pfeile) passend zur Auswahl neu aufbauen und die Seitenleiste nachziehen. */
  function refreshVisuals() {
    clearSelectionVisuals();
    if (editing()) {
      const ids = selectedIds();
      if (ids.length === 1) buildSelectionVisuals(entryOf(ids[0]));
      else if (ids.length > 1) buildSelectionVisuals({ kind: "group", id: "__group", ids: ids.slice() });                  // Gruppe: dieselben Griffe um alle gewaehlten Teile
      renderSide();
    }
    sim.invalidate();
  }

  function buildSelectionVisuals(entry) {
    handlesOwner = entry;
    const isGroup = entry.kind === "group";
    if (isGroup) entry.ids.forEach((id) => addFrame(entryOf(id)));
    else addFrame(entry);
    handleRig = new THREE.Group();
    if (entry.kind !== "fixture") {                                      // Groesse aendern: bei Koerpern; bei einer Gruppe auch fuer Scheinwerfer (die Anordnung wird gedehnt); ein einzelner Scheinwerfer hat feste Groesse
      const cornerGeo = new THREE.BoxGeometry(1, 1, 1);
      for (const cx of [-1, 1]) for (const cy of [-1, 1]) handles.push(makeHandle("corner", cornerGeo, 0xffffff, cx, cy));
      handles.push(makeHandle("height", cornerGeo, 0xffffff));
      for (const s of [-1, 1]) { handles.push(makeHandle("edge", cornerGeo, 0xffffff, s, 0)); handles.push(makeHandle("edge", cornerGeo, 0xffffff, 0, s)); }          // Kantenmitten: nur diese eine Kante laenger/kuerzer
      baseOutline = new THREE.LineLoop(new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(new Float32Array(12), 3)),
        new THREE.LineBasicMaterial({ color: 0xffd400, depthTest: false, transparent: true, opacity: 0.55 }));
      baseOutline.renderOrder = 28;
      baseOutline.frustumCulled = false;
      handleRig.add(baseOutline);
    }
    handles.push(makeHandle("lift", new THREE.ConeGeometry(0.8, 1.5, 3), 0x35d07f));         // Dreieck ueber dem Objekt
    handles.forEach((h) => handleRig.add(h.object));
    sim.scene.add(handleRig);
    arcRig = new THREE.Group();
    for (const axis of [0, 1, 2]) { const a = makeArc(axis); arcs.push(a); arcRig.add(a.object); }
    sim.scene.add(arcRig);
    if (isGroup) scaleSelection();
    else layoutSelection(entry);
  }

  /** Rahmen und Griffe an Groesse/Lage des Objekts anpassen; Griffe behalten ihre Bildschirmgroesse (siehe frame-Hook). */
  function layoutSelection(entry) {
    const [sx, sy, sz] = entry.data.size;
    if (entry.frame) { entry.frame.scale.set(sx, sy, sz); entry.frame.position.set(...(entry.offset || [0, 0, 0])); }       // Scheinwerfer: der Rahmen sitzt um das Modell (haengt meist vom Aufhaengepunkt nach unten)
    if (arcRig && entry === handlesOwner) arcRig.position.set(...entry.data.position);
    scaleSelection();
  }

  const tmp = new THREE.Vector3();
  /** Weltmass eines Pixels in der Entfernung des Punktes (Perspektive): damit bleiben Griffe und Pfeile bei jedem Zoom gleich gross. */
  function worldPerPixel(point) {
    const height = sim.canvas.clientHeight || 600;
    return (2 * sim.camera.position.distanceTo(point) * Math.tan(THREE.MathUtils.degToRad(sim.camera.fov) / 2)) / height;
  }
  const touchLike = () => window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
  const unitAt = (point) => Math.max(worldPerPixel(point) * UNIT_PX * (touchLike() ? 1.25 : 1), 0.002);

  // Welt-Box eines gedrehten Quaders (Rahmen des Objekts: x/y um den Fusspunkt, z von 0 bis Hoehe): exakt aus den acht Ecken
  const _boxMatrix = new THREE.Matrix4();
  const _boxEuler = new THREE.Euler();
  const _boxVec = new THREE.Vector3();
  function boxFor(position, rotation, size) {
    _boxEuler.set(deg(rotation[0]), deg(rotation[1]), deg(rotation[2]), "XYZ");
    _boxMatrix.makeRotationFromEuler(_boxEuler);
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (const x of [-size[0] / 2, size[0] / 2]) for (const y of [-size[1] / 2, size[1] / 2]) for (const z of [0, size[2]]) {
      _boxVec.set(x, y, z).applyMatrix4(_boxMatrix);
      for (let i = 0; i < 3; i++) { const v = _boxVec.getComponent(i) + position[i]; if (v < min[i]) min[i] = v; if (v > max[i]) max[i] = v; }
    }
    const m = [0, 1, 2].map((i) => [0, 1, 2].map((j) => Math.abs(_boxMatrix.elements[j * 4 + i])));       // |R|: wie stark jede lokale Ausdehnung in jede Weltachse faellt
    return { min, max, m };
  }
  const boxOf = (entry) => boxFor(entry.data.position, entry.data.rotation, entry.data.size);

  /** Loest A * x = b (3x3) per Gauss. */
  function solve3(A, b) {
    const M = A.map((row, i) => row.concat([b[i]]));
    for (let c = 0; c < 3; c++) {
      let p = c;
      for (let r = c + 1; r < 3; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      [M[c], M[p]] = [M[p], M[c]];
      const d = M[c][c] || 1e-9;
      for (let r = 0; r < 3; r++) {
        if (r === c) continue;
        const f = M[r][c] / d;
        for (let k = c; k < 4; k++) M[r][k] -= f * M[c][k];
      }
    }
    return [0, 1, 2].map((i) => M[i][3] / (M[i][i] || 1e-9));
  }
  /** Lokale Groesse so aendern, dass die Welt-Box die Ausdehnungen `want` bekommt (kleinste Aenderung, wo die Achsen sich vermischen, z. B. bei 45 Grad). */
  const minSizeOf = (type) => (type === "screen" ? [MIN_SIZE, 0.001, MIN_SIZE] : [MIN_SIZE, MIN_SIZE, MIN_SIZE]);          // die Dicke eines Bildschirms darf 1 mm sein
  function sizeForExtents(box, size0, want, mins = [MIN_SIZE, MIN_SIZE, MIN_SIZE]) {
    const ext0 = [0, 1, 2].map((i) => box.max[i] - box.min[i]);
    const dE = [0, 1, 2].map((i) => want[i] - ext0[i]);
    const m = box.m;
    const lambda = 1e-3;
    const mmT = [0, 1, 2].map((i) => [0, 1, 2].map((j) => m[i][0] * m[j][0] + m[i][1] * m[j][1] + m[i][2] * m[j][2] + (i === j ? lambda : 0)));
    const y = solve3(mmT, dE);
    return [0, 1, 2].map((j) => Math.max(mins[j], size0[j] + m[0][j] * y[0] + m[1][j] * y[1] + m[2][j] * y[2]));
  }

  /** Welt-Box eines Teils: Koerper exakt aus den Ecken, Scheinwerfer aus dem Trefferkoerper des Modells. */
  function memberBox(en) {
    if (en.kind !== "fixture") return boxOf(en);
    en.group.updateWorldMatrix(true, false);
    en.mesh.updateWorldMatrix(true, false);
    const b = new THREE.Box3().setFromObject(en.mesh);
    return { min: [b.min.x, b.min.y, b.min.z], max: [b.max.x, b.max.y, b.max.z], m: null };
  }
  function unionBox(boxes) {
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    boxes.forEach((b) => { for (let i = 0; i < 3; i++) { min[i] = Math.min(min[i], b.min[i]); max[i] = Math.max(max[i], b.max[i]); } });
    return { min, max, m: null };
  }
  const groupBox = (ids) => unionBox(ids.map((id) => entryOf(id)).filter(Boolean).map(memberBox));

  function scaleSelection() {
    const owner = handlesOwner;
    if (!owner || !handles.length) return;
    const isGroup = owner.kind === "group";
    if (isGroup && !owner.ids.some((id) => entryOf(id))) return;
    const box = isGroup ? groupBox(owner.ids) : memberBox(owner);
    const cx = (box.min[0] + box.max[0]) / 2;
    const cy = (box.min[1] + box.max[1]) / 2;
    const zb = box.min[2];
    const k = touchLike() ? 1.25 : 1;
    if (owner.kind === "fixture") {
      const lift = handles.find((h) => h.kind === "lift");
      const [px, py, pz] = owner.data.position;
      const base = new THREE.Vector3(px, py, pz + (owner.top || 0));
      const u = worldPerPixel(base) * LIFT_PX * k;
      lift.object.position.set(px, py, pz + (owner.top || 0) + u * 2.6);
      lift.object.rotation.set(Math.PI / 2, 0, 0);
      lift.object.scale.setScalar(u / 1.5);
    } else {
      handles.forEach((h) => {
        if (h.kind === "corner") h.object.position.set(h.cx > 0 ? box.max[0] : box.min[0], h.cy > 0 ? box.max[1] : box.min[1], zb);
        else if (h.kind === "edge") h.object.position.set(h.cx !== 0 ? (h.cx > 0 ? box.max[0] : box.min[0]) : cx, h.cy !== 0 ? (h.cy > 0 ? box.max[1] : box.min[1]) : cy, zb);
        else if (h.kind === "height") h.object.position.set(cx, cy, box.max[2]);
        else if (h.kind === "lift") { h.object.position.set(cx, cy, box.max[2] + worldPerPixel(tmp.set(cx, cy, box.max[2])) * 30 * k); h.object.rotation.set(Math.PI / 2, 0, 0); }
        const px = worldPerPixel(h.object.position);
        if (h.kind === "edge") h.object.scale.set(px * (h.cy !== 0 ? 18 : 7) * k, px * (h.cx !== 0 ? 18 : 7) * k, px * 7 * k);          // flacher Balken entlang der Kante
        else h.object.scale.setScalar(h.kind === "lift" ? (px * LIFT_PX * k) / 1.5 : px * HANDLE_PX * k);
      });
      if (baseOutline) {
        const a = baseOutline.geometry.attributes.position;
        [[box.min[0], box.min[1]], [box.max[0], box.min[1]], [box.max[0], box.max[1]], [box.min[0], box.max[1]]].forEach(([x, y], i) => a.setXYZ(i, x, y, zb));
        a.needsUpdate = true;
      }
    }
    if (arcRig) {
      arcRig.position.set(...(isGroup ? [cx, cy, zb] : owner.data.position));                       // Drehpunkt: Fusspunkt, bei einer Gruppe die Mitte ihrer Box am Boden
      const span = Math.hypot(box.max[0] - box.min[0], box.max[1] - box.min[1], box.max[2] - box.min[2]);
      const u = unitAt(arcRig.position);
      const radius = Math.min(Math.max(span * 0.5 + u * 1.5, u * 4), u * 18);                        // waechst mit dem Objekt: kleine Scheinwerfer bekommen kleine Pfeile, grosse nie ueber den halben Bildschirm
      const kk = u / radius;
      arcs.forEach((a) => {
        if (!a.k || Math.abs(a.k - kk) / a.k > 0.12) shapeArc(a, kk);      // Strich und Greifflaeche bleiben auf dem Bildschirm gleich gross
        a.object.scale.setScalar(radius);
      });
      arcRig.userData.radius = radius;
    }
  }
  sim.frameHooks.push(scaleSelection);

  /** Auswahl setzen. opts.add (Umschalt/Strg): das Objekt zur Auswahl hinzufuegen bzw. wieder herausnehmen (Mehrfachauswahl). */
  function select(id, opts = {}) {
    if (opts.add && id && id !== "spot" && inMode(entryOf(id)) && selected !== "spot") {
      if (isSelected(id)) {
        extra.delete(id);
        if (selected === id) { selected = extra.size ? [...extra].pop() : null; if (selected) extra.delete(selected); }
      } else {
        if (selected) extra.add(selected);
        selected = id;
      }
      refreshVisuals();
      return;
    }
    const next = id === "spot" ? (spot.exists ? "spot" : null) : id && inMode(entryOf(id)) ? id : null;
    if (next === selected && !extra.size) { if (editing()) renderSide(); return; }
    extra.clear();
    selected = next;
    refreshVisuals();
  }
  function selectMany(ids) {
    const list = ids.filter((id) => inMode(entryOf(id)));
    extra.clear();
    selected = list.length ? list[list.length - 1] : null;
    list.slice(0, -1).forEach((id) => extra.add(id));
    refreshVisuals();
  }

  // ------------------------------------------------------------------------------------------ Seitenleiste
  const section = (title) => { const g = el("div", "sim3d__group"); if (title) g.appendChild(el("h4", "sim3d__title", title)); return g; };
  const iconButton = (icon, label, cls, onClick) => {
    const b = el("button", "sim3d__btn sim3d__btn--wide" + (cls ? " " + cls : ""));
    b.type = "button";
    b.append(Icons.svg(icon), el("span", "", label));
    b.addEventListener("click", onClick);
    return b;
  };

  function numberRow(label, values, onChange, opts) {
    const cfg = { step: 0.1, unit: "m", min: null, tip: "", ...(opts || {}) };
    const row = el("div", "sim3d__grid");
    const l = el("label", "", label);
    if (cfg.tip) l.title = cfg.tip;
    row.appendChild(l);
    const inputs = [0, 1, 2].map((i) => {
      const wrap = el("span", "sim3d__field");
      wrap.append(el("span", "sim3d__axis", "XYZ"[i]));
      const input = el("input", "sim3d__num");
      input.type = "number";
      input.step = String(cfg.step);
      if (cfg.min !== null) input.min = String(cfg.min);
      input.value = String(round(values[i]));
      input.inputMode = "decimal";
      input.addEventListener("change", () => {
        const next = inputs.map((n) => Number(n.value));
        if (!next.every(Number.isFinite)) return;
        onChange(next.map((v) => (cfg.min !== null ? Math.max(cfg.min, v) : v)));
      });
      wrap.append(input, el("span", "sim3d__unit", cfg.unit));
      row.appendChild(wrap);
      return input;
    });
    row._inputs = inputs;
    return row;
  }

  function syncFields() {
    const entry = entryOf(selected);
    if (!entry || !fieldRefs) return;
    const set = (row, values) => row._inputs.forEach((input, i) => { if (document.activeElement !== input) input.value = String(round(values[i])); });
    set(fieldRefs.position, entry.data.position);
    set(fieldRefs.rotation, entry.data.rotation);
    if (fieldRefs.size) set(fieldRefs.size, entry.data.size);
  }

  /** Eigenschaften eines Bildschirms: Medium (Bild/Video aus der Medienbibliothek), Darstellung, Wiedergabe (Timecode/frei, Startzeit, Wiederholen, Ton) und Farbanpassung. */
  function buildScreenControls(entry) {
    const d = entry.data;
    d.look = { brightness: 100, contrast: 100, saturation: 100, hue: 0, tint: "#ffffff", flip: false, ...(d.look || {}) };
    const box = el("div", "sim3d__group sim3d__screen");
    const row = (labelKey, control, tipKey) => {
      const r = el("div", "sim3d__row");
      const label = el("label", "sim3d__snap-label", t(labelKey));
      if (tipKey) label.title = t(tipKey);
      r.append(label, control);
      return r;
    };
    const items = () => Object.values(window.OCMedia ? OCMedia.items : {}).filter((m) => m.kind === "image" || m.kind === "video");
    // Medium: ein Knopf oeffnet den Dateimanager als Auswahl (vorhandenes Bild/Video nehmen oder direkt hochladen)
    const meta = d.media && window.OCMedia ? OCMedia.get(d.media) : null;
    const chooser = iconButton(meta ? (meta.kind === "image" ? "image" : "film") : "plus", meta ? meta.name : (d.media ? t("SIM3D_SCREEN_LOST") : t("SIM3D_SCREEN_CHOOSE")), "", async () => {
      if (!window.OCMedia) return;
      const picked = await OCMedia.choose(["image", "video"]);
      if (!picked) return;
      if (picked.kind !== "image" && picked.kind !== "video") { _showToast(t("SIM3D_SCREEN_NOT_VISUAL"), "warn", 5000); return; }
      d.media = picked.id;
      apply(entry);
      commit();
      renderSide();
    });
    chooser.dataset.act = "screen-media";
    chooser.title = t("SIM3D_SCREEN_CHOOSE_TIP");
    const mediaRow = el("div", "sim3d__row");
    const mediaLabel = el("label", "sim3d__snap-label", t("SIM3D_SCREEN_MEDIA"));
    mediaRow.append(mediaLabel, chooser);
    if (d.media) {
      const clear = el("button", "sim3d__btn");
      clear.type = "button";
      clear.dataset.act = "screen-clear";
      clear.title = t("SIM3D_SCREEN_CLEAR");
      clear.appendChild(Icons.svg("close"));
      clear.addEventListener("click", () => { d.media = ""; apply(entry); commit(); renderSide(); });
      mediaRow.appendChild(clear);
    }
    box.appendChild(mediaRow);
    if (d.media && (!meta || meta.missing)) box.appendChild(el("p", "sim3d__hint sim3d__hint--warn", t("SIM3D_SCREEN_MISSING")));
    // Darstellung und Seitenverhaeltnis
    const fit = el("select", "sim3d__select");
    fit.dataset.field = "fit";
    [["stretch", "SIM3D_FIT_STRETCH"], ["contain", "SIM3D_FIT_CONTAIN"], ["cover", "SIM3D_FIT_COVER"]].forEach(([id, key]) => { const o = el("option", "", t(key)); o.value = id; fit.appendChild(o); });
    fit.value = d.fit || "stretch";
    fit.addEventListener("change", () => { d.fit = fit.value; apply(entry); commit(); });
    box.appendChild(row("SIM3D_SCREEN_FIT", fit, "SIM3D_SCREEN_FIT_TIP"));
    const aspect = iconButton("scale", t("SIM3D_SCREEN_ASPECT"), "", () => {
      const a = entry.screen && entry.screen.mediaAspect;
      if (!a) return;
      d.size = [d.size[0], d.size[1], round(Math.max(0.05, d.size[0] / a))];
      apply(entry);
      syncFields();
      commit();
    });
    aspect.dataset.act = "screen-aspect";
    aspect.title = t("SIM3D_SCREEN_ASPECT_TIP");
    aspect.style.flex = "0 0 auto";
    box.appendChild(aspect);
    // Beleuchtung: leuchtet selbst (LED-Wand) oder wie eine Wand (nur Scheinwerfer und Raumlicht beleuchten sie)
    const emissiveLabel = el("label", "sim3d__check");
    emissiveLabel.title = t("SIM3D_SCREEN_EMISSIVE_TIP");
    const emissive = el("input");
    emissive.type = "checkbox";
    emissive.dataset.field = "emissive";
    emissive.checked = d.emissive !== false;
    emissive.addEventListener("change", () => { d.emissive = emissive.checked; apply(entry); commit(); });
    emissiveLabel.append(emissive, el("span", "", t("SIM3D_SCREEN_EMISSIVE")));
    box.appendChild(emissiveLabel);
    // Wiedergabe (nur Video)
    if (meta && meta.kind === "video") {
      const sync = el("select", "sim3d__select");
      sync.dataset.field = "sync";
      [["timecode", "SIM3D_SYNC_TC"], ["free", "SIM3D_SYNC_FREE"]].forEach(([id, key]) => { const o = el("option", "", t(key)); o.value = id; sync.appendChild(o); });
      sync.value = d.sync === "free" ? "free" : "timecode";
      sync.addEventListener("change", () => { d.sync = sync.value; apply(entry); commit(); renderSide(); });
      box.appendChild(row("SIM3D_SCREEN_SYNC", sync, "SIM3D_SCREEN_SYNC_TIP"));
      if (d.sync !== "free") {
        const start = el("input", "sim3d__text");
        start.type = "text";
        start.dataset.field = "tc_start";
        start.value = window.OCTimecode ? OCTimecode.fmt(d.tc_start_ms || 0, true) : String(d.tc_start_ms || 0);
        start.addEventListener("change", () => {
          const ms = window.OCTimecode ? OCTimecode.parse(start.value) : null;
          if (ms === null || ms === undefined || !Number.isFinite(ms)) { start.value = window.OCTimecode ? OCTimecode.fmt(d.tc_start_ms || 0, true) : ""; return; }
          d.tc_start_ms = Math.max(0, Math.round(ms));
          start.value = OCTimecode.fmt(d.tc_start_ms, true);
          apply(entry);
          commit();
        });
        box.appendChild(row("SIM3D_SCREEN_START", start, "SIM3D_SCREEN_START_TIP"));
      }
      const checks = el("div", "sim3d__row");
      const check = (labelKey, key, invert) => {
        const label = el("label", "sim3d__check");
        const input = el("input");
        input.type = "checkbox";
        input.dataset.field = key;
        input.checked = invert ? !d[key] : !!d[key];
        input.addEventListener("change", () => { d[key] = invert ? !input.checked : input.checked; apply(entry); commit(); });
        label.append(input, el("span", "", t(labelKey)));
        return label;
      };
      checks.append(check("SIM3D_SCREEN_LOOP", "loop", false), check("SIM3D_SCREEN_SOUND", "muted", true));
      box.appendChild(checks);
    }
    // Farbe und Bild
    box.appendChild(el("h4", "sim3d__title", t("SIM3D_LOOK_TITLE")));
    const look = d.look;
    const range = (labelKey, key, min, max, step, unit) => {
      const r = el("div", "sim3d__row sim3d__range");
      const label = el("label", "sim3d__snap-label", t(labelKey));
      const input = el("input");
      input.type = "range";
      input.min = String(min); input.max = String(max); input.step = String(step);
      input.value = String(look[key]);
      input.dataset.field = key;
      const out = el("output", "", look[key] + unit);
      input.addEventListener("input", () => { look[key] = Number(input.value); out.textContent = look[key] + unit; apply(entry); });
      input.addEventListener("change", () => commit());
      input.addEventListener("dblclick", () => { look[key] = key === "hue" ? 0 : 100; input.value = String(look[key]); out.textContent = look[key] + unit; apply(entry); commit(); });
      r.append(label, input, out);
      return r;
    };
    box.append(range("SIM3D_LOOK_BRIGHT", "brightness", 0, 300, 1, " %"), range("SIM3D_LOOK_CONTRAST", "contrast", 0, 300, 1, " %"), range("SIM3D_LOOK_SAT", "saturation", 0, 300, 1, " %"), range("SIM3D_LOOK_HUE", "hue", -180, 180, 1, "°"));
    const tint = el("input", "sim3d__color");
    tint.type = "color";
    tint.value = look.tint || "#ffffff";
    tint.dataset.field = "tint";
    tint.addEventListener("input", () => { look.tint = tint.value; apply(entry); });
    tint.addEventListener("change", () => commit());
    const flipLabel = el("label", "sim3d__check");
    const flip = el("input");
    flip.type = "checkbox";
    flip.dataset.field = "flip";
    flip.checked = !!look.flip;
    flip.addEventListener("change", () => { look.flip = flip.checked; apply(entry); commit(); });
    flipLabel.append(flip, el("span", "", t("SIM3D_LOOK_FLIP")));
    const tintRow = row("SIM3D_LOOK_TINT", tint);
    tintRow.appendChild(flipLabel);
    box.appendChild(tintRow);
    const reset = iconButton("refresh", t("SIM3D_LOOK_RESET"), "", () => { d.look = { brightness: 100, contrast: 100, saturation: 100, hue: 0, tint: "#ffffff", flip: false }; apply(entry); commit(); renderSide(); });
    reset.dataset.act = "look-reset";
    reset.style.flex = "0 0 auto";
    box.appendChild(reset);
    return box;
  }

  /** Kleiner Knopf "MVR-Szene importieren ..." (Buehne + Scheinwerfer aus einer .mvr-Datei, static/js/mvr_import.js). */
  function mvrButton() {
    const b = iconButton("stage", t("SIM3D_MVR_BTN"), "", () => { if (window.OCMvrImport) window.OCMvrImport.open(); });
    b.dataset.act = "mvr-import";
    b.title = t("SIM3D_MVR_TIP");
    return b;
  }
  let jsonPanel = null;
  let jsonMode = false;
  /** Die Seitenleiste zeigt entweder die Werkzeuge (Koerper hinzufuegen, Liste, Eigenschaften) oder den Text der Buehne (JSON, live); Buehnenname, Rueckgaengig und Speichern bleiben in beiden gleich. */
  async function setJsonMode(on) {
    if (!window.OCSimJson || on === jsonMode) return;
    if (on) {
      await flushPush();
      if (mode === "fixtures") await flushFx();
      if (!jsonPanel) jsonPanel = window.OCSimJson.createPanel();
      jsonMode = true;
      await jsonPanel.show();
    } else {
      jsonMode = false;
      if (jsonPanel) jsonPanel.hide();
    }
    renderSide();
    sim.invalidate();
  }

  /** Umschalter oben in der Seitenleiste (unter dem Speichern-Knopf): Werkzeuge <-> JSON. */
  function viewToggle() {
    const bar = el("div", "sim3d__viewtoggle");
    [[false, "SIM3D_VIEW_TOOLS"], [true, "SIM3D_VIEW_JSON"]].forEach(([json, key]) => {
      const b = el("button", "sim3d__viewbtn" + (json === jsonMode ? " sim3d__viewbtn--on" : ""), t(key));
      b.type = "button";
      b.dataset.view = json ? "json" : "tools";
      b.setAttribute("aria-pressed", String(json === jsonMode));
      b.addEventListener("click", () => setJsonMode(json));
      bar.appendChild(b);
    });
    return bar;
  }

  function renderSide() {
    renderSideBody();
  }

  function renderSideBody() {
    side.textContent = "";
    fieldRefs = null;
    fxRows = null;
    if (mode === "fixtures") {
      stageRow = null;
      side.appendChild(viewToggle());
      if (jsonMode && jsonPanel) side.appendChild(jsonPanel.el); else renderFixturesSide();
      return;
    }
    const stageGroup = section(t("SIMSTAGE_LABEL"));
    const stageTop = el("div", "sim3d__stage");
    const stageName = el("span", "sim3d__stage-name", "—");
    const undoBtn = el("button", "sim3d__btn");
    undoBtn.type = "button";
    undoBtn.dataset.act = "undo";
    undoBtn.title = t("SIM3D_UNDO");
    undoBtn.append(Icons.svg("undo"));
    undoBtn.addEventListener("click", undo);
    const redoBtn = el("button", "sim3d__btn");
    redoBtn.type = "button";
    redoBtn.dataset.act = "redo";
    redoBtn.title = t("SIM3D_REDO");
    redoBtn.append(Icons.svg("redo"));
    redoBtn.addEventListener("click", redo);
    stageTop.append(stageName, undoBtn, redoBtn);
    const saveRow = el("div", "sim3d__row");
    const saveBtn = iconButton("save", t("SIMSTAGE_SAVE"), "", async () => { await flushPush(); if (stages()) await stages().save(false); });
    saveBtn.dataset.act = "save";
    saveBtn.title = t("SIMSTAGE_SAVE_TIP");
    const manageBtn = iconButton("folder", t("SIMSTAGE_MANAGE_SHORT"), "", () => { if (stages()) stages().open(); });
    manageBtn.dataset.act = "manage";
    saveRow.append(saveBtn, manageBtn);
    stageGroup.append(stageTop, saveRow);
    side.appendChild(stageGroup);
    saveBtn.append(el("span", "sim3d__badge"));
    stageRow = { name: stageName, undo: undoBtn, redo: redoBtn, save: saveBtn };
    paintStage();
    updateUndoButtons();
    side.appendChild(viewToggle());
    if (jsonMode && jsonPanel) { side.appendChild(jsonPanel.el); return; }                      // JSON statt der Werkzeuge
    const add = section(t("SIM3D_ADD"));
    const addRow = el("div", "sim3d__add");
    Object.entries(SHAPES).filter(([, info]) => !info.library).forEach(([type, info]) => {
      const b = iconButton(info.icon, t(info.key), "", () => { const entry = addObject(type); if (entry) select(entry.id); });
      b.dataset.add = type;
      addRow.appendChild(b);
    });
    add.appendChild(addRow);
    const modelToggle = iconButton("model", t("SIM3D_MODEL_ADD"), "sim3d__btn--toggle" + (modelsOpen ? " sim3d__btn--on" : ""), () => {
      modelsOpen = !modelsOpen;
      if (modelsOpen && !modelList) loadModelList().then(() => { if (editing()) renderSide(); });
      renderSide();
    });
    modelToggle.dataset.act = "models";
    modelToggle.setAttribute("aria-expanded", String(modelsOpen));
    modelToggle.title = t("SIM3D_MODEL_ADD_TIP");
    add.appendChild(modelToggle);
    add.appendChild(mvrButton());
    if (modelsOpen) {
      const box = el("div", "sim3d__models");
      if (!modelList) box.appendChild(el("p", "sim3d__hint", t("SIM3D_MODEL_LOADING")));
      else if (!modelList.length) box.appendChild(el("p", "sim3d__hint", t("SIM3D_MODEL_EMPTY")));
      else {
        const ul = el("ul", "sim3d__model-list");
        modelList.forEach((info) => {
          const li = el("li");
          const b = el("button", "sim3d__model");
          b.type = "button";
          b.dataset.model = info.id;
          b.disabled = info.ok === false;
          b.append(Icons.svg("model"), el("span", "sim3d__model-name", info.name), el("span", "sim3d__model-meta", info.ok === false ? t("FM_MODEL_BROKEN") : t("FM_TRIANGLES").split("{n}").join(Number(info.triangles).toLocaleString())));
          b.title = info.size.map((v) => fmt(v)).join(" × ") + " (" + t("SIM3D_MODEL_FILE_UNITS") + ")";
          b.addEventListener("click", () => addModel(info));
          li.appendChild(b);
          ul.appendChild(li);
        });
        box.appendChild(ul);
      }
      const row = el("div", "sim3d__row");
      const imp = iconButton("upload", t("SIM3D_MODEL_IMPORT"), "", pickModelFile);
      imp.dataset.act = "model-import";
      imp.title = t("SIM3D_MODEL_IMPORT_TIP");
      const fm = iconButton("folder", t("SIM3D_MODEL_MANAGE"), "", () => { if (window.OCFileManager) window.OCFileManager.open("models"); });
      fm.dataset.act = "model-manage";
      row.append(imp, fm);
      box.appendChild(row);
      add.appendChild(box);
    }
    const snapRow = el("div", "sim3d__row");
    const snapLabel = el("label", "sim3d__snap-label", t("SIM3D_SNAP"));
    const snapSelect = el("select", "sim3d__select");
    SNAPS.forEach((v) => { const o = el("option", "", v ? fmt(v) + " m" : t("SIM3D_SNAP_OFF")); o.value = String(v); snapSelect.appendChild(o); });
    snapSelect.value = String(snap);
    snapSelect.addEventListener("change", () => { snap = Number(snapSelect.value); });
    snapLabel.title = t("SIM3D_SNAP_TIP");
    snapRow.append(snapLabel, snapSelect);
    add.appendChild(snapRow);
    side.appendChild(add);
    if (spot.enabled !== false) side.appendChild(spot.renderSection(selected === "spot"));

    const list = section(t("SIM3D_OBJECTS") + " (" + entries.size + ")");
    list.classList.add("sim3d__group--fill");
    const ul = el("ul", "sim3d__list");
    if (!entries.size) ul.appendChild(el("li", "sim3d__empty", t("SIM3D_EMPTY")));
    entries.forEach((entry, id) => {
      const li = el("li", "sim3d__item" + (isSelected(id) ? " sim3d__item--sel" : ""));
      li.dataset.id = id;
      const swatch = el("span", "sim3d__swatch");
      swatch.style.background = entry.data.color;
      li.append(swatch, el("span", "sim3d__item-name", entry.data.name), el("span", "sim3d__item-tag", t(SHAPES[entry.data.type].key)));
      li.addEventListener("click", (ev) => select(id, { add: ev.shiftKey || ev.ctrlKey || ev.metaKey }));
      ul.appendChild(li);
    });
    list.appendChild(ul);

    if (extra.size) {                                                  // Mehrfachauswahl: nur Sammelaktionen
      const ids = selectedIds();
      const multi = section(t("SIM3D_PROPS"));
      multi.appendChild(el("p", "sim3d__hint", t("SIM3D_MULTI").split("{n}").join(String(ids.length))));
      const row = el("div", "sim3d__row");
      const dupAll = iconButton("copy", t("SIM3D_DUPLICATE"), "", () => duplicateSelection());
      dupAll.dataset.act = "duplicate";
      const delAll = iconButton("trash", t("SIM3D_DELETE"), "sim3d__btn--danger", () => confirmDelete(selectedIds()));
      delAll.dataset.act = "delete";
      row.append(dupAll, delAll);
      multi.appendChild(row);
      multi.appendChild(poseRows(true));
      side.appendChild(multi);
      side.appendChild(list);
      return;
    }
    const entry = selected && entries.get(selected);
    if (!entry) {
      if (entries.size && selected !== "spot") side.appendChild(el("p", "sim3d__hint", t("SIM3D_SELECT_HINT")));
      side.appendChild(list);
      return;
    }
    const d = entry.data;
    const props = section(t("SIM3D_PROPS"));
    const nameRow = el("div", "sim3d__row");
    const name = el("input", "sim3d__text");
    name.type = "text";
    name.maxLength = 60;
    name.value = d.name;
    name.setAttribute("aria-label", t("SIM3D_NAME"));
    name.addEventListener("change", () => {
      d.name = name.value.trim() || d.name;
      name.value = d.name;
      commit();
      const item = ul.querySelector('[data-id="' + d.id + '"] .sim3d__item-name');
      if (item) item.textContent = d.name;
    });
    const color = el("input", "sim3d__color");
    color.type = "color";
    color.value = d.color;
    color.title = t("SIM3D_COLOR");
    color.addEventListener("input", () => {
      d.color = color.value;
      apply(entry);
      const sw = ul.querySelector('[data-id="' + d.id + '"] .sim3d__swatch');
      if (sw) sw.style.background = d.color;
    });
    color.addEventListener("change", commit);
    nameRow.append(name, color);
    props.appendChild(nameRow);
    const matRow = el("div", "sim3d__row");
    const matLabel = el("label", "sim3d__snap-label", t("SIM3D_MATERIAL"));
    matLabel.title = t("SIM3D_MATERIAL_TIP");
    const matSelect = el("select", "sim3d__select");
    matSelect.dataset.field = "material";
    Object.entries(MATERIALS).forEach(([id, def]) => { const o = el("option", "", t(def.key)); o.value = id; matSelect.appendChild(o); });
    matSelect.value = d.material || "matt";
    matSelect.addEventListener("change", () => { d.material = matSelect.value; apply(entry); commit(); });
    matRow.append(matLabel, matSelect);
    props.appendChild(matRow);
    if (d.type === "screen") props.appendChild(buildScreenControls(entry));
    if (d.type === "model") {
      const info = (modelList || []).find((m) => m.id === d.model);
      if (!modelList) loadModelList().then(() => { if (editing() && entries.get(selected) === entry) renderSide(); });
      if (entry.missing) props.appendChild(el("p", "sim3d__hint sim3d__hint--warn", t("SIM3D_MODEL_MISSING").split("{name}").join(d.model)));
      else props.appendChild(el("p", "sim3d__hint", d.model.replace(/\.stl$/i, "") + (info ? " · " + t("FM_TRIANGLES").split("{n}").join(Number(info.triangles).toLocaleString()) : "")));
      const unitRow = el("div", "sim3d__row");
      const unitLabel = el("label", "sim3d__snap-label", t("SIM3D_MODEL_UNIT"));
      unitLabel.title = t("SIM3D_MODEL_UNIT_TIP");
      const unitSelect = el("select", "sim3d__select");
      unitSelect.dataset.field = "unit";
      Object.keys(MODEL_UNITS).forEach((u) => { const o = el("option", "", t(MODEL_UNIT_KEYS[u])); o.value = u; unitSelect.appendChild(o); });
      unitSelect.value = MODEL_UNITS[d.unit] ? d.unit : "m";
      const original = () => {
        const native = entry.native || (info && info.size);
        if (!native) return;
        d.size = native.map((v) => round(Math.max(MIN_SIZE, v * MODEL_UNITS[d.unit])));
        apply(entry);
        syncFields();
        commit();
      };
      unitSelect.addEventListener("change", () => { d.unit = unitSelect.value; original(); });
      const reset = el("button", "sim3d__btn");
      reset.type = "button";
      reset.dataset.act = "model-original";
      reset.title = t("SIM3D_MODEL_ORIGINAL_TIP");
      reset.append(Icons.svg("undo"));
      reset.disabled = !!entry.missing;
      reset.addEventListener("click", original);
      unitRow.append(unitLabel, unitSelect, reset);
      props.appendChild(unitRow);
    }
    fieldRefs = {
      position: numberRow(t("SIM3D_POSITION"), d.position, (v) => { d.position = v; apply(entry); commit(); }, { step: 0.1, tip: t("SIM3D_POSITION_TIP") }),
      rotation: numberRow(t("SIM3D_ROTATION"), d.rotation, (v) => { d.rotation = v; apply(entry); commit(); }, { step: 5, unit: "°" }),
      size: numberRow(t("SIM3D_SIZE"), d.size, (v) => { d.size = v; apply(entry); commit(); }, { step: 0.1, min: d.type === "screen" ? 0.001 : MIN_SIZE }),
    };
    props.append(fieldRefs.position, fieldRefs.rotation, fieldRefs.size, poseRows(false));
    const drop = iconButton("move", t("SIM3D_DROP"), "", () => {
      entry.group.updateMatrixWorld(true);
      const low = new THREE.Box3().setFromObject(entry.mesh, true).min.z;
      d.position = [d.position[0], d.position[1], round(d.position[2] - low, 4)];
      apply(entry);
      syncFields();
      commit();
    });
    drop.dataset.act = "drop";
    drop.style.flex = "0 0 auto";                                  // in der Spalte nicht auf Hoehe 0 schrumpfen
    drop.title = t("SIM3D_DROP_TIP");
    const actions = el("div", "sim3d__row");
    const dup = iconButton("copy", t("SIM3D_DUPLICATE"), "", () => duplicateSelection());
    dup.dataset.act = "duplicate";
    const del = iconButton("trash", t("SIM3D_DELETE"), "sim3d__btn--danger", () => confirmDelete(d.id));
    del.dataset.act = "delete";
    actions.append(dup, del);
    props.append(drop, actions);
    side.appendChild(props);
    side.appendChild(list);                                          // Eigenschaften zuerst, die Liste darunter
  }

  // ------------------------------------------------------------------------------------------ Scheinwerfer der Show auf der Buehne (Modus "Scheinwerfer")
  // Die Positionen gehoeren zur Show (Showfile, Block "sim_stage" -> fixture_layout), nicht zur Buehnendatei. Gleiche Bedienung wie bei den Koerpern (Antippen waehlt, Umschalt-Klick
  // mehrere, Ziehen verschiebt das gewaehlte, Pfeiltasten, Griffe fuer Hoehe und Drehung), aber ohne Kopieren: jeden Scheinwerfer der Show gibt es nur einmal.
  const FIXTURE_SIZE = [0.5, 0.5, 0.6];
  let fxParts = null;
  const fixtureParts = () => fxParts || (fxParts = {
    pick: new THREE.BoxGeometry(1, 1, 1).translate(0, 0, 0.5),
    clamp: new THREE.BoxGeometry(0.3, 0.22, 0.06).translate(0, 0, -0.03),
    arm: new THREE.BoxGeometry(0.04, 0.08, 0.34).translate(0, 0, -0.23),
    head: new THREE.CylinderGeometry(0.13, 0.15, 0.3, 24).rotateX(Math.PI / 2).translate(0, 0, -0.4),
    lens: new THREE.CylinderGeometry(0.115, 0.115, 0.02, 24).rotateX(Math.PI / 2).translate(0, 0, -0.56),
    body: new THREE.MeshStandardMaterial({ color: 0x2b2b2f, roughness: 0.55, metalness: 0.4 }),
    glass: new THREE.MeshStandardMaterial({ color: 0x77777c, roughness: 0.3, metalness: 0.2 }),
    hidden: new THREE.MeshBasicMaterial({ visible: false }),
  });
  const showFixtures = () => {
    try {
      const all = (typeof client !== "undefined" && client.state && client.state.fixtures) || {};
      return Object.values(all).sort((a, b) => (a.fid || 0) - (b.fid || 0) || String(a.name).localeCompare(String(b.name)));
    } catch (err) {
      return [];
    }
  };
  const fixtureById = (id) => showFixtures().find((f) => f.id === id) || null;

  /** Koerper eines Scheinwerfers: Aufhaengung, Buegel, Kopf mit Linse - haengt mit der Linse nach unten (Drehung 0 = haengend); der unsichtbare Trefferkoerper deckt das Ganze ab. */
  function createFixtureEntry(id, item) {
    const parts = fixtureParts();
    const group = new THREE.Group();
    const pick = new THREE.Mesh(parts.pick, parts.hidden);
    pick.userData.id = id;
    group.add(pick);
    const model = new THREE.Group();
    const add = (geometry, material, x = 0) => { const m = new THREE.Mesh(geometry, material); m.position.x = x; m.castShadow = true; m.receiveShadow = true; model.add(m); return m; };
    add(parts.clamp, parts.body);
    add(parts.arm, parts.body, 0.19);
    add(parts.arm, parts.body, -0.19);
    add(parts.head, parts.body);
    add(parts.lens, parts.glass);
    const lensNode = new THREE.Object3D();                              // hier sitzt der Lichtkegel des Standardmodells (Strahl nach -Z)
    lensNode.position.set(0, 0, -0.58);
    model.add(lensNode);
    group.add(model);
    sim.scene.add(group);
    const entry = { id, kind: "fixture", data: { position: item.position.slice(), rotation: item.rotation.slice(), size: FIXTURE_SIZE.slice(), hidden: !!item.hidden, scale: item.scale || 1 }, group, mesh: pick, model, frame: null,
      bounds: GENERIC_BOUNDS.slice(), real: false, modelType: null, offset: [0, 0, 0], top: 0, built: null, axes: null, zoomRange: null, beams: [{ object: lensNode, angle: 25, radius: 0.1 }] };
    fixtureEntries.set(id, entry);
    applyFixture(entry);
    attachRealModel(entry);
    if (window.OCSimAim) window.OCSimAim.notify();
    return entry;
  }

  // ---- 3D-Modell aus der Scheinwerfer-Datei (dieselbe Bibliothek wie die Details der Scheinwerfer-Bibliothek: /api/library/installed/<Typ>/model, OCModelViewer.buildFixture)
  const GENERIC_BOUNDS = [-0.25, -0.25, -0.6, 0.25, 0.25, 0];       // Standardmodell (Meter, haengend: von der Aufhaengung nach unten)
  const MIN_PICK = 0.25;                                              // kleinste Trefferflaeche (Meter), damit auch kleine Geraete antippbar sind
  const modelCache = new Map();                                       // Typ -> Promise<{built, bounds} | null>
  function loadFixtureModel(typeId) {
    if (!typeId || !window.OCModelViewer) return Promise.resolve(null);
    if (modelCache.has(typeId)) return modelCache.get(typeId);
    const promise = (async () => {
      try {
        const res = await fetch("/api/library/installed/" + encodeURIComponent(typeId) + "/model?scope=show");
        if (!res.ok) return null;
        const data = await res.json();
        if (!data || data.available === false || !data.root || !Array.isArray(data.bounds)) return null;
        return { data, bounds: data.bounds.slice(0, 6) };               // jede Instanz baut sich daraus selbst (eigene Achsen und Linse); die Netze werden geteilt
      } catch (err) {
        console.error("3D-Modell des Scheinwerfers nicht geladen:", err);
        return null;
      }
    })();
    modelCache.set(typeId, promise);
    return promise;
  }
  /** Ersetzt das Standardmodell durch das echte Modell des Scheinwerfertyps (sobald es geladen ist); ohne 3D-Daten bleibt das Standardmodell. */
  async function attachRealModel(entry) {
    const info = fixtureById(entry.id);
    const typeId = info && info.fixture_type;
    if (!typeId || entry.modelType === typeId) return;
    entry.modelType = typeId;
    const loaded = await loadFixtureModel(typeId);
    if (!loaded || !fixtureEntries.has(entry.id) || entry.modelType !== typeId) return;
    const built = window.OCModelViewer.buildFixture(loaded.data, { castShadow: true, beam: false, beamMesh: false, shareGeometry: true });
    built.group.traverse((o) => { if (o.isMesh) o.userData.canCast = o.castShadow; });
    built.lensMaterial.emissiveIntensity = 0;                           // Linse dunkel (das Leuchten kommt mit den DMX-Werten)
    entry.group.remove(entry.model);
    if (entry.built) entry.built.dispose();
    entry.model = built.group;
    entry.group.add(entry.model);
    entry.built = built;
    entry.castApplied = undefined;
    applyFixtureCasting();
    entry.axes = loaded.data.axes || {};
    if (window.OCSimAim) window.OCSimAim.notify();                      // jetzt kann dieser Scheinwerfer zielen
    const zoom = entry.axes.zoom;
    entry.zoomRange = zoom && zoom.from > 0 && zoom.to > 0 ? { from: zoom.from, to: zoom.to, segments: Array.isArray(zoom.segments) ? zoom.segments : [] } : null;       // Geraete ohne Zoom: der Winkel des Modells bleibt
    entry.focusRange = entry.axes.focus || null;
    entry.beams = built.beamNodes.length ? built.beamNodes : entry.beams;
    entry.bounds = loaded.bounds.slice();
    entry.real = true;
    applyFixture(entry);
    if (mode === "fixtures" && isSelected(entry.id)) renderSide();                       // Modell-Info der Eigenschaften nachziehen
  }
  function applyFixture(entry) {
    const d = entry.data;
    const k = d.scale || 1;
    entry.group.position.set(...d.position);
    entry.group.rotation.set(deg(d.rotation[0]), deg(d.rotation[1]), deg(d.rotation[2]), "XYZ");
    entry.model.scale.setScalar(k);
    const [x0, y0, z0, x1, y1, z1] = entry.bounds;                    // Ausdehnung des Modells bei Skalierung 1
    const size = [Math.max((x1 - x0) * k, MIN_PICK), Math.max((y1 - y0) * k, MIN_PICK), Math.max((z1 - z0) * k, MIN_PICK)];
    d.size = size;
    entry.top = z1 * k;
    entry.offset = [((x0 + x1) / 2) * k, ((y0 + y1) / 2) * k, z1 * k - size[2]];       // Unterkante des Trefferkoerpers (die Oberkante bleibt am Modell)
    entry.mesh.scale.set(...size);
    entry.mesh.position.set(entry.offset[0], entry.offset[1], entry.offset[2]);
    entry.group.visible = !d.hidden;                                  // ausgeblendet: unsichtbar und nicht waehlbar
    if (isSelected(entry.id)) layoutSelection(entry);
    sim.invalidate();
  }
  function removeFixtureEntry(id) {
    const entry = fixtureEntries.get(id);
    if (!entry) return;
    const wasSelected = isSelected(id);
    if (wasSelected) clearSelectionVisuals();
    sim.scene.remove(entry.group);
    if (entry.built) entry.built.dispose();
    fixtureEntries.delete(id);
    if (window.OCSimAim) window.OCSimAim.notify();
    extra.delete(id);
    if (selected === id) { selected = extra.size ? [...extra].pop() : null; if (selected) extra.delete(selected); }
    if (wasSelected && editing()) refreshVisuals();
    sim.invalidate();
  }
  const serializeFx = () => Object.fromEntries([...fixtureEntries].map(([id, en]) => [id, { position: en.data.position.slice(), rotation: en.data.rotation.slice(), ...(en.data.hidden ? { hidden: true } : {}), ...(en.data.scale && en.data.scale !== 1 ? { scale: en.data.scale } : {}) }]));
  const snapshotFx = () => JSON.stringify(serializeFx());
  function resetFxHistory() { fxHistory = [snapshotFx()]; fxIndex = 0; updateFxUndo(); }

  /** Koerper der platzierten Scheinwerfer mit der Show abgleichen: Scheinwerfer, die es nicht mehr gibt, verschwinden; neue Positionen werden uebernommen. */
  /** Die Gehaeuse der Scheinwerfer werfen Schatten in die Lichtkegel. Ausschalten (Raum & Licht, nur dieses Geraet) spart bei grossen Buehnen viel Leistung: jede Schattenkarte zeichnet sonst alle Gehaeuse neu. */
  function applyFixtureCasting() {
    const cast = sim.limits.values.fixtureShadows !== 0;                // Einstellung "Scheinwerfer werfen Schatten" (je Geraet; Vorgabe: ein, wie frueher)
    fixtureEntries.forEach((entry) => {
      if (!entry.built || entry.castApplied === cast) return;
      entry.castApplied = cast;
      entry.built.group.traverse((o) => { if (o.isMesh && o.userData.canCast !== undefined) o.castShadow = o.userData.canCast && cast; });
    });
    sim.renderer.shadowMap.needsUpdate = true;
  }
  sim.limits.listeners.push(() => { fixtureEntries.forEach((entry) => { entry.castApplied = undefined; }); applyFixtureCasting(); });
  function syncFixtureEntries() {
    const known = new Set(showFixtures().map((f) => f.id));
    for (const id of [...fixtureEntries.keys()]) if (!known.has(id) || !layout[id]) removeFixtureEntry(id);
    for (const [id, item] of Object.entries(layout)) {
      if (!known.has(id)) continue;
      const entry = fixtureEntries.get(id);
      if (entry) { entry.data.position = item.position.slice(); entry.data.rotation = item.rotation.slice(); entry.data.hidden = !!item.hidden; entry.data.scale = item.scale || 1; applyFixture(entry); attachRealModel(entry); }
      else createFixtureEntry(id, item);
    }
    applyFixtureCasting();
    sim.invalidate();
  }
  function applyRemoteLayout(incoming) {
    layout = JSON.parse(JSON.stringify(incoming));
    syncFixtureEntries();
    recordFxStep();
    if (mode === "fixtures") refreshVisuals();
  }

  // ---- Verlauf und Abgleich mit dem Server (Positionen gehen als Teil der Show an alle Geraete)
  function updateFxUndo() {
    if (!fxRows) return;
    fxRows.undo.disabled = fxIndex <= 0;
    fxRows.redo.disabled = fxIndex >= fxHistory.length - 1;
  }
  function commitFx() {
    const snap = snapshotFx();
    layout = JSON.parse(snap);
    if (fxHistory[fxIndex] === snap) return;
    fxHistory = fxHistory.slice(0, fxIndex + 1);
    fxHistory.push(snap);
    if (fxHistory.length > 100) fxHistory.shift();
    fxIndex = fxHistory.length - 1;
    schedulePushFx();
    updateFxUndo();
  }
  function recordFxStep() {
    const snap = snapshotFx();
    layout = JSON.parse(snap);
    if (fxHistory[fxIndex] === snap) return;
    fxHistory = fxHistory.slice(0, fxIndex + 1);
    fxHistory.push(snap);
    if (fxHistory.length > 100) fxHistory.shift();
    fxIndex = fxHistory.length - 1;
    updateFxUndo();
  }
  function stepFx(delta) {
    const next = fxIndex + delta;
    if (next < 0 || next >= fxHistory.length) return;
    fxIndex = next;
    layout = JSON.parse(fxHistory[fxIndex]);
    syncFixtureEntries();
    schedulePushFx();
    updateFxUndo();
    if (mode === "fixtures") refreshVisuals();
  }
  const undoFx = () => stepFx(-1);
  const redoFx = () => stepFx(1);
  function schedulePushFx() {
    clearTimeout(fxPushTimer);
    fxPushTimer = setTimeout(flushFx, 200);
  }
  async function flushFx() {
    if (!fxPushTimer) return;
    clearTimeout(fxPushTimer);
    fxPushTimer = 0;
    try {
      await fetch("/api/sim-fixtures", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ layout: serializeFx(), source: uid }) });
    } catch (err) { /* offline: bleibt lokal */ }
  }

  // ---- Aktionen
  /** Einen Scheinwerfer der Show auf die Buehne setzen (bei der Mitte der Ansicht, auf Standardhoehe; nicht auf einen schon belegten Platz). */
  function placeFixture(id, silent) {
    if (!fixtureById(id) || fixtureEntries.has(id)) return null;
    const step = snap || 0.5;
    const near = (v) => Math.round(v / step) * step;
    let x = near(sim.controls.target.x);
    const y = near(sim.controls.target.y);
    while ([...fixtureEntries.values()].some((en) => Math.abs(en.data.position[0] - x) < 0.3 && Math.abs(en.data.position[1] - y) < 0.3)) x += 0.6;
    const entry = createFixtureEntry(id, { position: [round(x), round(y), 3], rotation: [0, 0, 0] });
    if (!silent) commitFx();
    return entry;
  }
  function placeAllFixtures() {
    const missing = showFixtures().filter((f) => !fixtureEntries.has(f.id));
    if (!missing.length) return;
    const cx = Math.round(sim.controls.target.x);
    const cy = Math.round(sim.controls.target.y);
    const taken = (x) => [...fixtureEntries.values()].some((en) => Math.abs(en.data.position[0] - x) < 0.3 && Math.abs(en.data.position[1] - cy) < 0.3);
    let x = cx - Math.floor((missing.length - 1) / 2);                       // eine Reihe um die Mitte der Ansicht, schon belegte Plaetze werden uebersprungen
    const ids = missing.map((f) => {
      while (taken(x)) x += 1;
      const entry = createFixtureEntry(f.id, { position: [x, cy, 3], rotation: [0, 0, 0] });
      x += 1;
      return entry.id;
    });
    commitFx();
    selectMany(ids);
  }
  /** Scheinwerfer ein-/ausblenden (Haken in der Liste); ein ausgeblendeter ist nicht mehr gewaehlt. */
  function setFixtureHidden(id, hidden) {
    const entry = fixtureEntries.get(id);
    if (!entry || !!entry.data.hidden === hidden) return;
    entry.data.hidden = hidden;
    if (hidden && isSelected(id)) {
      extra.delete(id);
      if (selected === id) { selected = extra.size ? [...extra].pop() : null; if (selected) extra.delete(selected); }
    }
    applyFixture(entry);
    commitFx();
    if (editing()) refreshVisuals();
  }
  function unplaceSelected() {
    const ids = selectedIds();
    if (!ids.length) return;
    ids.forEach((id) => removeFixtureEntry(id));
    commitFx();
    if (editing()) renderSide();
  }

  /** Seitenleiste des Modus "Scheinwerfer": Liste aller Scheinwerfer der Show (Antippen setzt/waehlt), Eigenschaften des gewaehlten. */
  function renderFixturesSide() {
    const fixtures = showFixtures();
    const placed = fixtures.filter((f) => fixtureEntries.has(f.id)).length;
    const head = section(t("SIM3D_FIXTURES"));
    const top = el("div", "sim3d__stage");
    top.appendChild(el("span", "sim3d__stage-name", t("SIM3D_FIXTURES_COUNT").split("{n}").join(String(placed)).split("{m}").join(String(fixtures.length))));
    const undoBtn = el("button", "sim3d__btn");
    undoBtn.type = "button";
    undoBtn.dataset.act = "undo";
    undoBtn.title = t("SIM3D_UNDO");
    undoBtn.append(Icons.svg("undo"));
    undoBtn.addEventListener("click", undoFx);
    const redoBtn = el("button", "sim3d__btn");
    redoBtn.type = "button";
    redoBtn.dataset.act = "redo";
    redoBtn.title = t("SIM3D_REDO");
    redoBtn.append(Icons.svg("redo"));
    redoBtn.addEventListener("click", redoFx);
    top.append(undoBtn, redoBtn);
    fxRows = { undo: undoBtn, redo: redoBtn };
    updateFxUndo();
    head.appendChild(top);
    const all = iconButton("fixture", t("SIM3D_FIXTURE_PLACE_ALL"), "", placeAllFixtures);
    all.dataset.act = "place-all";
    all.disabled = placed >= fixtures.length;
    all.style.flex = "0 0 auto";
    head.appendChild(all);
    head.appendChild(mvrButton());
    side.appendChild(head);

    const list = section("");
    list.classList.add("sim3d__group--fill");                          // die Liste nutzt die ganze restliche Hoehe der Seitenleiste (im Vollbild entsprechend viel)
    const bar = el("div", "sim3d__filter");                            // Suchen, Mehrfachwahl (fuer Touch ohne Umschalt-Taste), ins Bild holen
    const filterInput = el("input", "sim3d__text");
    filterInput.type = "search";
    filterInput.placeholder = t("SIM3D_FIXTURES_FILTER");
    filterInput.value = fxFilter;
    filterInput.dataset.field = "filter";
    filterInput.addEventListener("input", () => { fxFilter = filterInput.value; paintFxList(); });
    const multiBtn = el("button", "sim3d__btn" + (fxMulti ? " sim3d__btn--on" : ""));
    multiBtn.type = "button";
    multiBtn.dataset.act = "multi";
    multiBtn.title = t("SIM3D_FIXTURES_MULTI_TIP");
    multiBtn.setAttribute("aria-pressed", String(fxMulti));
    multiBtn.append(Icons.svg("check"));
    multiBtn.addEventListener("click", () => { fxMulti = !fxMulti; multiBtn.classList.toggle("sim3d__btn--on", fxMulti); multiBtn.setAttribute("aria-pressed", String(fxMulti)); });
    const allBtn = el("button", "sim3d__btn");
    allBtn.type = "button";
    allBtn.dataset.act = "select-all";
    allBtn.title = t("SIM3D_SELECT_ALL_TIP");
    allBtn.append(Icons.svg("list"));
    allBtn.addEventListener("click", selectAll);
    const frameBtn = el("button", "sim3d__btn");
    frameBtn.type = "button";
    frameBtn.dataset.act = "frame";
    frameBtn.title = t("SIM3D_FRAME_TIP");
    frameBtn.append(Icons.svg("target"));
    frameBtn.addEventListener("click", frameSelection);
    bar.append(filterInput, multiBtn, allBtn, frameBtn);
    list.appendChild(bar);
    const ul = el("ul", "sim3d__list");
    if (!fixtures.length) ul.appendChild(el("li", "sim3d__empty", t("SIM3D_FIXTURES_EMPTY")));
    const shownFixtures = () => {
      const q = fxFilter.trim().toLowerCase();
      return q ? fixtures.filter((f) => ((f.fid ? f.fid + " " : "") + f.name).toLowerCase().includes(q)) : fixtures;
    };
    function paintFxList() {
      ul.querySelectorAll(".sim3d__item, .sim3d__empty").forEach((n) => n.remove());
      const rows = shownFixtures();
      if (!rows.length) ul.appendChild(el("li", "sim3d__empty", t(fixtures.length ? "SIM3D_FIXTURES_NONE_FOUND" : "SIM3D_FIXTURES_EMPTY")));
      rows.forEach((f) => ul.appendChild(fixtureRow(f, rows)));
    }
    function fixtureRow(f, rows) {
      const isPlaced = fixtureEntries.has(f.id);
      const li = el("li", "sim3d__item" + (isSelected(f.id) ? " sim3d__item--sel" : ""));
      li.dataset.id = f.id;
      li.title = isPlaced ? "" : t("SIM3D_FIXTURE_PLACE");
      const mark = el("span", "sim3d__swatch");
      mark.style.background = isPlaced ? "var(--accent-color)" : "transparent";
      const hiddenNow = isPlaced && !!fixtureEntries.get(f.id).data.hidden;
      if (hiddenNow) li.classList.add("sim3d__item--off");
      li.append(mark, el("span", "sim3d__item-name", (f.fid ? f.fid + "  " : "") + f.name), el("span", "sim3d__item-tag", isPlaced ? "" : t("SIM3D_FIXTURE_NOT_PLACED")));
      if (isPlaced) {                                                // Auge: Scheinwerfer im Bild ein-/ausblenden
        const eye = el("button", "sim3d__eye");
        eye.type = "button";
        eye.dataset.act = "toggle-visible";
        eye.title = hiddenNow ? t("SIM3D_FIXTURE_SHOW") : t("SIM3D_FIXTURE_HIDE");
        eye.setAttribute("aria-label", eye.title);
        eye.setAttribute("aria-pressed", String(!hiddenNow));
        eye.appendChild(Icons.svg(hiddenNow ? "eye-off" : "eye"));
        eye.addEventListener("click", (ev) => { ev.stopPropagation(); setFixtureHidden(f.id, !hiddenNow); });
        li.appendChild(eye);
      }
      li.addEventListener("click", (ev) => {
        const toggle = ev.ctrlKey || ev.metaKey || fxMulti;
        if (ev.shiftKey && fxAnchor && rows.some((r) => r.id === fxAnchor)) {                // Umschalt: Bereich vom zuletzt angeklickten bis hierher (noch nicht platzierte werden gesetzt)
          const a = rows.findIndex((r) => r.id === fxAnchor);
          const b = rows.findIndex((r) => r.id === f.id);
          const range = rows.slice(Math.min(a, b), Math.max(a, b) + 1);
          let placedNow = false;
          range.forEach((r) => { if (!fixtureEntries.has(r.id) && placeFixture(r.id, true)) placedNow = true; });
          if (placedNow) commitFx();
          selectMany(range.map((r) => r.id).filter((id) => fixtureEntries.has(id) && !fixtureEntries.get(id).data.hidden));
          return;
        }
        fxAnchor = f.id;
        if (!fixtureEntries.has(f.id)) { placeFixture(f.id); select(f.id, { add: toggle }); return; }       // noch nicht auf der Buehne: Antippen setzt ihn
        if (fixtureEntries.get(f.id).data.hidden) return;                                  // ausgeblendet: erst einblenden
        select(f.id, { add: toggle });
      });
      li.addEventListener("dblclick", () => { if (fixtureEntries.has(f.id) && !fixtureEntries.get(f.id).data.hidden) { select(f.id); frameSelection(); } });          // Doppelklick: ins Bild holen
      return li;
    }
    paintFxList();
    ul.addEventListener("scroll", () => { fxScroll = ul.scrollTop; });         // bleibt beim Neuaufbau der Seitenleiste (jede Auswahl) erhalten
    list.appendChild(ul);

    const ids = selectedIds();
    if (!ids.length) {
      if (fixtures.length) side.appendChild(el("p", "sim3d__hint", t("SIM3D_FIXTURES_HINT")));
      side.appendChild(list);
      ul.scrollTop = fxScroll;
      return;
    }
    const props = section(t("SIM3D_PROPS"));
    const scaleRow = () => {                                          // Skalierung des 3D-Modells (gilt fuer alle gewaehlten Scheinwerfer)
      const list = ids.map((id) => fixtureEntries.get(id));
      const row = el("div", "sim3d__row");
      const label = el("label", "sim3d__snap-label", t("SIM3D_FIXTURE_SCALE"));
      label.title = t("SIM3D_FIXTURE_SCALE_TIP");
      const input = el("input", "sim3d__text");
      input.type = "number";
      input.step = "0.05";
      input.min = "0.05";
      input.max = "20";
      input.dataset.field = "scale";
      input.inputMode = "decimal";
      input.value = String(list[0].data.scale || 1);
      input.addEventListener("change", () => {
        const v = Math.min(20, Math.max(0.05, Number(input.value)));
        if (!Number.isFinite(v)) return;
        input.value = String(v);
        list.forEach((en) => { en.data.scale = Math.round(v * 1000) / 1000; applyFixture(en); });
        commitFx();
      });
      const reset = el("button", "sim3d__btn");
      reset.type = "button";
      reset.title = t("SIM3D_FIXTURE_SCALE_RESET");
      reset.append(Icons.svg("refresh"));
      reset.addEventListener("click", () => { list.forEach((en) => { en.data.scale = 1; applyFixture(en); }); input.value = "1"; commitFx(); });
      row.append(label, input, reset);
      return row;
    };
    if (ids.length > 1) {
      props.appendChild(el("p", "sim3d__hint", t("SIM3D_FIXTURES_MULTI").split("{n}").join(String(ids.length))));
      props.appendChild(scaleRow());
      props.appendChild(poseRows(true));
    } else {
      const entry = fixtureEntries.get(ids[0]);
      const d = entry.data;
      const info = fixtureById(entry.id);
      props.appendChild(el("p", "sim3d__item-name", info ? info.name : entry.id));
      fieldRefs = {
        position: numberRow(t("SIM3D_POSITION"), d.position, (v) => { d.position = v; applyFixture(entry); commitFx(); }, { step: 0.1, tip: t("SIM3D_FIXTURE_POSITION_TIP") }),
        rotation: numberRow(t("SIM3D_ROTATION"), d.rotation, (v) => { d.rotation = v; applyFixture(entry); commitFx(); }, { step: 5, unit: "°", tip: t("SIM3D_FIXTURE_ROTATION_TIP") }),
      };
      props.append(fieldRefs.position, fieldRefs.rotation, scaleRow(), poseRows(false));
      const sizeText = [0, 1, 2].map((i) => String(Math.round((entry.bounds[i + 3] - entry.bounds[i]) * 100) / 100).replace(".", ",")).join(" × ");
      props.appendChild(el("p", "sim3d__hint", entry.real ? t("SIM3D_FIXTURE_MODEL_REAL").split("{size}").join(sizeText) : t("SIM3D_FIXTURE_MODEL_GENERIC")));
    }
    const remove = iconButton("trash", t("SIM3D_FIXTURE_REMOVE"), "sim3d__btn--danger", unplaceSelected);
    remove.dataset.act = "unplace";
    remove.style.flex = "0 0 auto";
    props.appendChild(remove);
    side.appendChild(props);
    side.appendChild(list);                                          // Eigenschaften zuerst, die Liste darunter
    ul.scrollTop = fxScroll;
  }

  // ------------------------------------------------------------------------------------------ Zeigerbedienung im Bild
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const pointers = new Set();
  let tap = null;

  function rayFrom(e) {
    const rect = sim.canvas.getBoundingClientRect();
    ndc.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(ndc, sim.camera);
    return raycaster.ray.clone();
  }
  function castAt(ray, objects) {
    raycaster.ray.copy(ray);
    raycaster.near = 0.01;
    raycaster.far = 1000;
    return raycaster.intersectObjects(objects, false);
  }
  const planeZ = (ray, z) => {
    if (Math.abs(ray.direction.z) < 1e-4) return null;
    const s = (z - ray.origin.z) / ray.direction.z;
    return s > 0 ? ray.origin.clone().addScaledVector(ray.direction, s) : null;
  };
  /** Parameter s des Punktes P + s*d (d normiert) auf der Geraden, die dem Sehstrahl am naechsten liegt. */
  function closestOnLine(ray, point, dir) {
    const w0 = point.clone().sub(ray.origin);
    const b = dir.dot(ray.direction);
    const denom = 1 - b * b;
    if (Math.abs(denom) < 1e-4) return null;
    return (b * ray.direction.dot(w0) - dir.dot(w0)) / denom;
  }
  const snapTo = (v, step = snap) => (step ? Math.round(v / step) * step : v);
  function say(text, e) {
    readout.hidden = !text;
    if (!text) return;
    const rect = root.getBoundingClientRect();
    readout.textContent = text;
    readout.style.left = Math.min(Math.max(e.clientX - rect.left + 14, 4), rect.width - 120) + "px";
    readout.style.top = Math.max(e.clientY - rect.top - 30, 4) + "px";
  }

  /** Der Griff (Eck-, Hoehen-, Heben-Griff) unter dem Zeiger: Abstand in Pixeln zum Griffmittelpunkt, der naechste gewinnt. */
  function pickHandle(e) {
    const rect = sim.canvas.getBoundingClientRect();
    const limit = e.pointerType === "mouse" ? PICK_PX_MOUSE : PICK_PX_TOUCH;
    let best = null;
    handles.forEach((h) => {
      tmp.copy(h.object.position).project(sim.camera);
      if (tmp.z < -1 || tmp.z > 1) return;
      const dist = Math.hypot(rect.left + ((tmp.x + 1) / 2) * rect.width - e.clientX, rect.top + ((1 - tmp.y) / 2) * rect.height - e.clientY);
      if (dist <= limit && (!best || dist < best.dist)) best = { h, dist };
    });
    return best ? best.h : null;
  }

  function startDrag(d, e) {
    drag = d;
    sim.controls.enabled = false;                       // die Kamera wartet, solange gezogen wird
    try { sim.canvas.setPointerCapture(e.pointerId); } catch (err) { /* kein Capture */ }
    e.preventDefault();
    e.stopPropagation();
  }

  function onDown(e) {
    pointers.add(e.pointerId);
    root.focus({ preventScroll: true });
    if (aim.armed) {                                                  // Zielmodus (aus der Scheinwerfersteuerung, auch in der Ansicht): ein Antippen setzt den Punkt, Ziehen bewegt die Kamera
      tap = pointers.size > 1 || (e.pointerType === "mouse" && e.button !== 0) ? null : { x: e.clientX, y: e.clientY, time: performance.now(), id: e.pointerId, aim: true };
      return;
    }
    if (mode === "view" || (e.pointerType === "mouse" && e.button !== 0) || pointers.size > 1) { tap = null; if (pointers.size > 1) endDrag(e, true); return; }
    const ray = rayFrom(e);
    const add = e.shiftKey || e.ctrlKey || e.metaKey;
    const spotHit = spot.hitTest(ray);                // der Test-Scheinwerfer (Koerper oder Zielkugel) geht vor
    if (spotHit) {
      if (selected === "spot") { spot.begin(spotHit, ray, e); return; }              // schon gewaehlt: ziehen verschiebt/zielt
      tap = { x: e.clientX, y: e.clientY, time: performance.now(), id: e.pointerId, pick: "spot" };       // noch nicht gewaehlt: Antippen waehlt, Ziehen dreht die Ansicht
      return;
    }
    const owner = handlesOwner && handles.length ? handlesOwner : null;                    // das gewaehlte Objekt oder die Gruppe
    // 1. Griffe und Dreh-Pfeile
    if (owner) {
      const handle = pickHandle(e);                                                         // die kleinen Griffe gehen den Dreh-Pfeilen vor
      if (handle) { beginHandle(owner, handle, ray, e); return; }
      const arcHit = castAt(ray, arcs.map((a) => a.hit))[0];
      if (arcHit) { beginHandle(owner, arcs.find((a) => a.hit === arcHit.object), ray, e); return; }
    }
    // 2. ein Objekt: ein schon gewaehltes laesst sich auf dem Boden verschieben; ein noch nicht gewaehltes wird nur durch Antippen (kurz, ohne Ziehen) gewaehlt -
    //    wer darauf drueckt und zieht, dreht die Ansicht (so verschiebt man nicht versehentlich eine Wand)
    const body = castAt(ray, [...(mode === "fixtures" ? fixtureEntries : entries).values()].filter((en) => !en.data.hidden).map((en) => en.mesh))[0];
    if (body) {
      const hitEntry = entryOf(body.object.userData.id);
      if (add || (!isSelected(hitEntry.id) && e.pointerType !== "mouse")) {          // Umschalt/Strg: zur Auswahl hinzufuegen bzw. herausnehmen (beim Loslassen, ohne Ziehen); Touch: Antippen waehlt, Ziehen dreht die Ansicht
        tap = { x: e.clientX, y: e.clientY, time: performance.now(), id: e.pointerId, pick: hitEntry.id, add };
        return;
      }
      if (!isSelected(hitEntry.id)) select(hitEntry.id);                  // Maus (wie Tinkercad): ein Objekt anklicken und gleich ziehen verschiebt es
      const z0 = hitEntry.data.position[2];
      const q = planeZ(ray, z0) || body.point;
      const group = selectedIds().map((id) => ({ entry: entryOf(id), start: entryOf(id).data.position.slice() }));
      startDrag({ type: "move", entry: hitEntry, z0, offset: [hitEntry.data.position[0] - q.x, hitEntry.data.position[1] - q.y], moved: false, group, start: hitEntry.data.position.slice() }, e);
      return;
    }
    // 3. leer: ein kurzes Antippen hebt die Auswahl auf; mit der Maus zieht Ziehen einen Auswahlrahmen auf (Touch: Ziehen/Gesten bewegen die Kamera)
    tap = { x: e.clientX, y: e.clientY, time: performance.now(), id: e.pointerId, keep: add, empty: e.pointerType === "mouse" };
  }

  /** Griff einer Gruppe: alle Teile werden zusammen skaliert (Anordnung und Groesse), gehoben oder gedreht; Ausgangslage aller Teile wird gemerkt. */
  function beginGroupHandle(group, handle, ray, e) {
    const members = group.ids.map((id) => entryOf(id)).filter(Boolean).map((en) => ({
      en, pos0: en.data.position.slice(), rot0: en.data.rotation.slice(), size0: en.data.size.slice(), box0: memberBox(en),
      q0: new THREE.Quaternion().setFromEuler(new THREE.Euler(deg(en.data.rotation[0]), deg(en.data.rotation[1]), deg(en.data.rotation[2]), "XYZ")),
    }));
    if (!members.length) return;
    const box = unionBox(members.map((m) => m.box0));
    const cx = (box.min[0] + box.max[0]) / 2;
    const cy = (box.min[1] + box.max[1]) / 2;
    const base = { isGroup: true, entry: members[0].en, handle, members, box, moved: false };
    if (handle.kind === "corner" || handle.kind === "edge") {
      const p = planeZ(ray, box.min[2]);
      if (!p) return;
      const grab = [handle.cx > 0 ? p.x - box.max[0] : handle.cx < 0 ? p.x - box.min[0] : 0, handle.cy > 0 ? p.y - box.max[1] : handle.cy < 0 ? p.y - box.min[1] : 0];
      startDrag({ ...base, type: "g-scale", grab }, e);
    } else if (handle.kind === "height") {
      const axisPoint = new THREE.Vector3(cx, cy, 0);
      const s0 = closestOnLine(ray, axisPoint, new THREE.Vector3(0, 0, 1));
      if (s0 === null) return;
      startDrag({ ...base, type: "g-height", axisPoint, grab: s0 - box.max[2] }, e);
    } else if (handle.kind === "lift") {
      const axisPoint = new THREE.Vector3(cx, cy, 0);
      const s0 = closestOnLine(ray, axisPoint, new THREE.Vector3(0, 0, 1));
      if (s0 === null) return;
      startDrag({ ...base, type: "g-lift", axisPoint, s0, low0: Math.min(...members.map((m) => m.pos0[2])) }, e);
    } else {
      const center = new THREE.Vector3(cx, cy, box.min[2]);
      const normal = new THREE.Vector3().crossVectors(handle.u, handle.w);
      const q = rayPlane(ray, center, normal);
      if (!q) return;
      const rel = q.clone().sub(center);
      startDrag({ ...base, type: "g-arc", center, normal, a0: Math.atan2(rel.dot(handle.w), rel.dot(handle.u)) }, e);
    }
  }

  function beginHandle(entry, handle, ray, e) {
    if (entry.kind === "group") { beginGroupHandle(entry, handle, ray, e); return; }
    const d = entry.data;
    entry.group.updateWorldMatrix(true, false);
    const inverse = entry.group.matrixWorld.clone().invert();
    const quat = entry.group.getWorldQuaternion(new THREE.Quaternion());
    const base = { entry, handle, inverse, quat, size0: d.size.slice(), pos0: d.position.slice(), moved: false };
    const local = { origin: ray.origin.clone().applyMatrix4(inverse), direction: ray.direction.clone().transformDirection(inverse) };
    if (handle.kind === "corner" || handle.kind === "edge") {
      const box = boxOf(entry);
      const p = planeZ(ray, box.min[2]);
      if (!p) return;
      const grab = [handle.cx > 0 ? p.x - box.max[0] : handle.cx < 0 ? p.x - box.min[0] : 0, handle.cy > 0 ? p.y - box.max[1] : handle.cy < 0 ? p.y - box.min[1] : 0];
      startDrag({ ...base, type: "corner", box, grab }, e);
    } else if (handle.kind === "height") {
      const box = boxOf(entry);
      const axisPoint = new THREE.Vector3((box.min[0] + box.max[0]) / 2, (box.min[1] + box.max[1]) / 2, 0);
      const s0 = closestOnLine(ray, axisPoint, new THREE.Vector3(0, 0, 1));
      if (s0 === null) return;
      startDrag({ ...base, type: "height", box, axisPoint, grab: s0 - box.max[2] }, e);
    } else if (handle.kind === "lift") {
      const origin = new THREE.Vector3(d.position[0], d.position[1], 0);                  // gleiche Bezugslinie wie beim Ziehen (onMove), sonst springt die Hoehe um z0
      const s0 = closestOnLine(ray, origin, new THREE.Vector3(0, 0, 1));
      if (s0 === null) return;
      startDrag({ ...base, type: "lift", s0, z0: d.position[2] }, e);
    } else {
      const center = new THREE.Vector3(...d.position);
      const normal = new THREE.Vector3().crossVectors(handle.u, handle.w);
      const q = rayPlane(ray, center, normal);
      if (!q) return;
      const rel = q.clone().sub(center);
      startDrag({ ...base, type: "arc", center, normal, a0: Math.atan2(rel.dot(handle.w), rel.dot(handle.u)), quat0: entry.group.quaternion.clone() }, e);
    }
  }

  function rayPlane(ray, point, normal) {
    const denom = normal.dot(ray.direction);
    if (Math.abs(denom) < 1e-4) return null;
    const s = point.clone().sub(ray.origin).dot(normal) / denom;
    return s > 0 ? ray.origin.clone().addScaledVector(ray.direction, s) : null;
  }

  // Auswahlrahmen (Maus, linke Taste auf leerer Flaeche): alle Koerper, deren Umriss im Bild den Rahmen beruehrt; Umschalt/Strg fuegt zur Auswahl hinzu
  const marqueeEl = el("div", "sim3d__marquee");
  marqueeEl.hidden = true;
  root.appendChild(marqueeEl);
  let marquee = null;
  const _mBox = new THREE.Box3();
  function updateMarquee(e) {
    if (!tap || !tap.empty || tap.id !== e.pointerId || (e.buttons & 1) === 0 || mode === "view") return;
    if (!marquee) {
      if (Math.hypot(e.clientX - tap.x, e.clientY - tap.y) <= 6) return;
      marquee = { x0: tap.x, y0: tap.y, add: tap.keep };
      try { sim.canvas.setPointerCapture(e.pointerId); } catch (err) { /* kein Capture */ }
    }
    const rect = root.getBoundingClientRect();
    const left = Math.min(marquee.x0, e.clientX), top = Math.min(marquee.y0, e.clientY);
    marqueeEl.hidden = false;
    marqueeEl.style.left = left - rect.left + "px";
    marqueeEl.style.top = top - rect.top + "px";
    marqueeEl.style.width = Math.abs(e.clientX - marquee.x0) + "px";
    marqueeEl.style.height = Math.abs(e.clientY - marquee.y0) + "px";
    marquee.rect = [left, top, Math.max(marquee.x0, e.clientX), Math.max(marquee.y0, e.clientY)];
  }
  function finishMarquee(e) {
    const m = marquee;
    marquee = null;
    marqueeEl.hidden = true;
    try { sim.canvas.releasePointerCapture(e.pointerId); } catch (err) { /* nichts zu loesen */ }
    if (!m || !m.rect) return;
    const canvas = sim.canvas.getBoundingClientRect();
    const hits = [];
    (mode === "fixtures" ? fixtureEntries : entries).forEach((en) => {
      if (en.data.hidden || !inMode(en)) return;
      en.mesh.updateWorldMatrix(true, false);
      _mBox.setFromObject(en.mesh);
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const x of [_mBox.min.x, _mBox.max.x]) for (const y of [_mBox.min.y, _mBox.max.y]) for (const z of [_mBox.min.z, _mBox.max.z]) {
        tmp.set(x, y, z).project(sim.camera);
        const sx = canvas.left + ((tmp.x + 1) / 2) * canvas.width;
        const sy = canvas.top + ((1 - tmp.y) / 2) * canvas.height;
        x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
      }
      if (x1 >= m.rect[0] && x0 <= m.rect[2] && y1 >= m.rect[1] && y0 <= m.rect[3]) hits.push(en.id);
    });
    selectMany(m.add ? [...new Set([...selectedIds(), ...hits])] : hits);
  }

  /** Gewuenschte Ausdehnungen der Welt-Box beim Ziehen eines Eck-/Kanten-/Hoehen-Griffs (Einzelobjekt und Gruppe): Raster, Umschalt = gleichmaessig, Alt = von der Mitte. */
  function wantExtents(drag, e, ray) {
    const b0 = drag.box;
    const ext0 = [0, 1, 2].map((i) => b0.max[i] - b0.min[i]);
    const want = ext0.slice();
    const heightDrag = drag.type === "height" || drag.type === "g-height";
    const centered = e.altKey && !heightDrag;                                        // Alt: von der Mitte aus
    const c = heightDrag ? [0, 0] : [drag.handle.cx, drag.handle.cy];
    if (!heightDrag) {
      const p = planeZ(ray, b0.min[2]);
      if (!p) return null;
      for (const a of [0, 1]) {
        if (c[a] === 0) continue;                                                    // Kanten-Griff: die andere Richtung bleibt wie sie ist
        const fixed = centered ? (b0.min[a] + b0.max[a]) / 2 : c[a] > 0 ? b0.min[a] : b0.max[a];          // die gegenueberliegende Seite bleibt stehen
        let next = Math.max(MIN_SIZE, c[a] * (p.getComponent(a) - drag.grab[a] - fixed) * (centered ? 2 : 1));
        if (snap) next = Math.max(snap, snapTo(next));
        want[a] = next;
      }
    } else {
      const s = closestOnLine(ray, drag.axisPoint, new THREE.Vector3(0, 0, 1));
      if (s === null) return null;
      let next = Math.max(MIN_SIZE, s - drag.grab - b0.min[2]);
      if (snap) next = Math.max(snap, snapTo(next));
      want[2] = next;
    }
    if (e.shiftKey) {                                                                // Umschalt: gleichmaessig in allen Richtungen
      const factors = want.map((v, i) => v / ext0[i]);
      let f = 1;
      factors.forEach((v) => { if (Math.abs(v - 1) > Math.abs(f - 1)) f = v; });
      for (let i = 0; i < 3; i++) want[i] = Math.max(MIN_SIZE, ext0[i] * f);
    }
    return { b0, ext0, want, centered, c };
  }

  /** Ziehen an einem Griff der Gruppe: skalieren (verzerren), Hoehe, heben, drehen - jeweils fuer alle Teile zugleich. */
  function dragGroup(e, ray) {
    drag.moved = true;
    const members = drag.members;
    const finish = (text) => { members.forEach((m) => apply(m.en)); syncFields(); say(text, e); };
    if (drag.type === "g-scale" || drag.type === "g-height") {
      const w = wantExtents(drag, e, ray);
      if (!w) return;
      const { b0, ext0, want, centered, c } = w;
      const f = want.map((v, i) => v / Math.max(ext0[i], 1e-6));
      const anchor = [0, 1].map((a) => (centered || drag.type === "g-height" || c[a] === 0 ? (b0.min[a] + b0.max[a]) / 2 : c[a] > 0 ? b0.min[a] : b0.max[a]));
      members.forEach((m) => {
        const mb = m.box0;
        const ext = [0, 1, 2].map((i) => mb.max[i] - mb.min[i]);
        const c0 = [(mb.min[0] + mb.max[0]) / 2, (mb.min[1] + mb.max[1]) / 2];
        const c1 = [anchor[0] + (c0[0] - anchor[0]) * f[0], anchor[1] + (c0[1] - anchor[1]) * f[1]];
        const minZ1 = b0.min[2] + (mb.min[2] - b0.min[2]) * f[2];
        let shift;
        if (m.en.kind === "fixture") {                                                // Scheinwerfer behalten ihre Groesse, nur die Anordnung wird gedehnt
          shift = [c1[0] - c0[0], c1[1] - c0[1], minZ1 - mb.min[2]];
        } else {
          const size = sizeForExtents(mb, m.size0, [ext[0] * f[0], ext[1] * f[1], ext[2] * f[2]], minSizeOf(m.en.data.type));
          if (m.en.data.type === "screen") size[1] = m.size0[1];
          const b1 = boxFor(m.pos0, m.rot0, size);
          shift = [c1[0] - (b1.min[0] + b1.max[0]) / 2, c1[1] - (b1.min[1] + b1.max[1]) / 2, minZ1 - b1.min[2]];
          m.en.data.size = size.map((v) => round(v));
        }
        m.en.data.position = [round(m.pos0[0] + shift[0]), round(m.pos0[1] + shift[1]), round(m.pos0[2] + shift[2])];
      });
      finish(drag.type === "g-height" ? `Z ${fmt(want[2])} m` : `X ${fmt(want[0])}   Y ${fmt(want[1])} m`);
    } else if (drag.type === "g-lift") {
      const s = closestOnLine(ray, drag.axisPoint, new THREE.Vector3(0, 0, 1));
      if (s === null) return;
      const low = Math.max(0, snapTo(drag.low0 + (s - drag.s0)));
      const dz = low - drag.low0;
      members.forEach((m) => { m.en.data.position = [m.pos0[0], m.pos0[1], round(m.pos0[2] + dz)]; });
      finish(`Z ${fmt(low)} m`);
    } else if (drag.type === "g-arc") {
      const q = rayPlane(ray, drag.center, drag.normal);
      if (!q) return;
      const rel = q.clone().sub(drag.center);
      let delta = Math.atan2(rel.dot(drag.handle.w), rel.dot(drag.handle.u)) - drag.a0;
      delta = Math.atan2(Math.sin(delta), Math.cos(delta));
      if (snap) delta = Math.round(delta / deg(5)) * deg(5);
      const axis = new THREE.Vector3().crossVectors(drag.handle.u, drag.handle.w);
      const qd = new THREE.Quaternion().setFromAxisAngle(axis, delta);
      members.forEach((m) => {
        const euler = new THREE.Euler().setFromQuaternion(qd.clone().multiply(m.q0), "XYZ");
        m.en.data.rotation = [euler.x, euler.y, euler.z].map((v) => round((v * 180) / Math.PI, 2));
        const inPlace = (m.en.kind === "fixture") !== e.altKey;                       // Scheinwerfer drehen sich an Ort und Stelle (Alt: starr um die Mitte), Koerper starr um die Mitte (Alt: an Ort und Stelle)
        if (!inPlace) {
          const p = new THREE.Vector3(...m.pos0).sub(drag.center).applyQuaternion(qd).add(drag.center);
          m.en.data.position = [round(p.x), round(p.y), round(p.z)];
        } else m.en.data.position = m.pos0.slice();
      });
      finish(`${"XYZ"[drag.handle.axis]} ${Math.round((delta * 180) / Math.PI)}°`);
    }
  }

  function onMove(e) {
    if (!drag) { updateMarquee(e); return; }
    const ray = rayFrom(e);
    if (drag.type === "spot") { spot.move(drag, ray, e); return; }
    if (drag.isGroup) { dragGroup(e, ray); return; }
    const d = drag.entry.data;
    drag.moved = true;
    if (drag.type === "move") {
      const q = planeZ(ray, drag.z0);
      if (!q) return;
      d.position = [round(snapTo(q.x + drag.offset[0])), round(snapTo(q.y + drag.offset[1])), d.position[2]];
      if (drag.group && drag.group.length > 1) {                                   // Mehrfachauswahl: alle um dieselbe Strecke
        const dx = d.position[0] - drag.start[0];
        const dy = d.position[1] - drag.start[1];
        drag.group.forEach((g) => { if (g.entry === drag.entry) return; g.entry.data.position = [round(g.start[0] + dx), round(g.start[1] + dy), g.start[2]]; apply(g.entry); });
      }
      say(`X ${fmt(d.position[0])}   Y ${fmt(d.position[1])} m`, e);
    } else if (drag.type === "lift") {
      const s = closestOnLine(ray, new THREE.Vector3(d.position[0], d.position[1], 0), new THREE.Vector3(0, 0, 1));
      if (s === null) return;
      const z = Math.max(0, snapTo(drag.z0 + (s - drag.s0)));
      d.position = [d.position[0], d.position[1], round(z)];
      say(`Z ${fmt(z)} m`, e);
    } else if (drag.type === "corner" || drag.type === "height") {
      const w = wantExtents(drag, e, ray);
      if (!w) return;
      const { b0, want, centered, c } = w;
      const size = sizeForExtents(b0, drag.size0, want, minSizeOf(d.type));
      if (d.type === "screen") size[1] = drag.size0[1];                              // die Dicke eines Bildschirms aendern nur die Eigenschaften, nicht die Griffe
      const b1 = boxFor(drag.pos0, d.rotation, size);
      const shift = [0, 0, b0.min[2] - b1.min[2]];                                    // der Boden der Box bleibt stehen
      for (const a of [0, 1]) {
        shift[a] = drag.type === "height" || centered || c[a] === 0
          ? (b0.min[a] + b0.max[a]) / 2 - (b1.min[a] + b1.max[a]) / 2
          : c[a] > 0 ? b0.min[a] - b1.min[a] : b0.max[a] - b1.max[a];
      }
      d.position = [round(drag.pos0[0] + shift[0]), round(drag.pos0[1] + shift[1]), round(drag.pos0[2] + shift[2])];
      d.size = size.map((v) => round(v));
      say(drag.type === "height" ? `Z ${fmt(want[2])} m` : `X ${fmt(want[0])}   Y ${fmt(want[1])} m`, e);
    } else if (drag.type === "arc") {
      const q = rayPlane(ray, drag.center, drag.normal);
      if (!q) return;
      const rel = q.clone().sub(drag.center);
      let delta = Math.atan2(rel.dot(drag.handle.w), rel.dot(drag.handle.u)) - drag.a0;
      delta = Math.atan2(Math.sin(delta), Math.cos(delta));
      if (snap) delta = Math.round(delta / deg(5)) * deg(5);
      const axis = new THREE.Vector3().crossVectors(drag.handle.u, drag.handle.w);
      const rotated = new THREE.Quaternion().setFromAxisAngle(axis, delta).multiply(drag.quat0);
      const euler = new THREE.Euler().setFromQuaternion(rotated, "XYZ");
      d.rotation = [euler.x, euler.y, euler.z].map((v) => round((v * 180) / Math.PI, 2));
      say(`${"XYZ"[drag.handle.axis]} ${Math.round((delta * 180) / Math.PI)}°`, e);
    }
    apply(drag.entry);
    syncFields();
  }

  function endDrag(e, cancel) {
    if (!drag) return;
    const finished = drag;
    drag = null;
    sim.controls.enabled = true;
    say("", e);
    try { sim.canvas.releasePointerCapture(e.pointerId); } catch (err) { /* nichts zu loesen */ }
    if (finished && finished.type === "move" && !finished.moved && finished.group && finished.group.length > 1) { select(finished.entry.id); return; }      // Klick auf ein Mitglied der Mehrfachauswahl: nur dieses behalten
    if (editing()) renderSide();
    if (finished && finished.moved && finished.type !== "spot") commitCurrent();
    void cancel;
  }

  function onUp(e) {
    pointers.delete(e.pointerId);
    if (drag) { endDrag(e); return; }
    if (marquee) { tap = null; finishMarquee(e); return; }
    const was = tap;
    tap = null;
    if (was && was.aim) { if (was.id === e.pointerId && e.type !== "pointercancel" && Math.hypot(e.clientX - was.x, e.clientY - was.y) <= 6 && aim.armed) aim.pick(rayFrom(e)); return; }
    if (!was || was.id !== e.pointerId || mode === "view" || e.type === "pointercancel") return;
    if (Math.hypot(e.clientX - was.x, e.clientY - was.y) > 6) return;                  // gezogen: die Kamera hat sich bewegt
    if (was.pick) { select(was.pick, { add: was.add }); return; }                   // Antippen eines Objekts (auch langes Halten ohne Bewegen); mit Umschalt/Strg: zur Auswahl hinzufuegen
    if (was.keep || performance.now() - was.time > 500) return;
    select(null);
  }
  // Dateien aus dem Explorer auf die Buehne ziehen (nur beim Bauen): STL/OBJ werden eingelesen und nebeneinander platziert
  const hasFiles = (e) => !!(e.dataTransfer && [...(e.dataTransfer.types || [])].includes("Files"));
  sim.canvas.addEventListener("dragover", (e) => { if (mode === "build" && hasFiles(e)) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; } });
  sim.canvas.addEventListener("drop", (e) => {
    if (mode !== "build" || !hasFiles(e)) return;
    e.preventDefault();
    const files = [...e.dataTransfer.files];
    if (files.length) importModelFiles(files);
  });
  sim.canvas.addEventListener("pointerdown", onDown, true);       // vor der Kamerasteuerung: Griffe und Objekte gehen vor
  sim.canvas.addEventListener("pointermove", onMove);
  sim.canvas.addEventListener("pointerup", onUp);
  sim.canvas.addEventListener("pointercancel", onUp);

  // Tastatur (Baumodus): Strg+C / X / V kopieren, ausschneiden, einfuegen (alle gewaehlten Objekte), Strg+D dupliziert (nochmal Strg+D wiederholt die Verschiebung), Pfeiltasten
  // verschieben die Auswahl (in Blickrichtung der Kamera, ohne Hoehe), Entf loescht (mit Rueckfrage), Esc hebt die Auswahl auf
  const copySelected = () => {
    const ids = selectedIds();
    if (!ids.length) return false;
    clipboard = { items: ids.map((id) => JSON.parse(JSON.stringify(entries.get(id).data))), cut: false };
    pasteCount = 0;
    return true;
  };
  const pasteClipboard = (keepName) => {
    if (!clipboard || !clipboard.items.length) return;
    pasteCount += 1;
    const created = clipboard.items.map((src) => addObject(src.type, src, 0.5 * pasteCount, keepName, true)).filter(Boolean);
    if (!created.length) return;
    commit();
    selectMany(created.map((en) => en.id));                                      // das Eingefuegte ist gleich gewaehlt
  };
  /** Strg+D: die Auswahl duplizieren; die Kopien sind gewaehlt. Wird sie danach verschoben/gedreht und Strg+D nochmal gedrueckt (ohne die Auswahl zu wechseln), wiederholt sich dieselbe
   *  Verschiebung/Drehung ausgehend von der letzten Kopie - so reiht man schnell viele Gegenstaende auf. */
  function duplicateSelection() {
    const ids = selectedIds();
    if (!ids.length) return;
    const chaining = !!dupChain && dupChain.ids.length === ids.length && dupChain.ids.every((id) => ids.includes(id));
    const step = snap || 0.5;
    const created = [];
    const prev = new Map();
    for (const id of ids) {
      const src = entries.get(id).data;
      let dpos = [step, step, 0];
      let drot = [0, 0, 0];
      const was = chaining ? dupChain.prev.get(id) : null;
      if (was) {
        const moved = src.position.map((v, i) => v - was.position[i]);
        if (moved.some((v) => Math.abs(v) > 1e-6)) dpos = moved;
        drot = src.rotation.map((v, i) => v - was.rotation[i]);
      }
      const entry = addObject(src.type, src, 0, chaining, true);
      if (!entry) continue;
      entry.data.position = src.position.map((v, i) => round(v + dpos[i]));
      entry.data.rotation = src.rotation.map((v, i) => round(v + drot[i], 2));
      apply(entry);
      prev.set(entry.id, { position: src.position.slice(), rotation: src.rotation.slice() });
      created.push(entry.id);
    }
    if (!created.length) return;
    commit();
    selectMany(created);
    dupChain = { ids: created, prev };
  }
  /** Pfeiltasten: Auswahl um einen Schritt (Raster, ohne Raster 0,1 m; mit Umschalt 5-fach) auf der Bodenebene verschieben - "rechts" ist rechts im Bild, "hoch" ist von der Kamera weg, ausgerichtet an der naechsten Achse. */
  function nudge(right, forward, big) {
    const dir = sim.camera.getWorldDirection(new THREE.Vector3());
    let fx = dir.x;
    let fy = dir.y;
    if (Math.hypot(fx, fy) < 0.2) { const up = new THREE.Vector3().setFromMatrixColumn(sim.camera.matrixWorld, 1); fx = up.x; fy = up.y; }   // von oben gesehen: "hoch" im Bild
    const len = Math.hypot(fx, fy) || 1;
    fx /= len;
    fy /= len;
    let vx = fy * right + fx * forward;
    let vy = -fx * right + fy * forward;
    if (Math.abs(vx) >= Math.abs(vy)) { vx = Math.sign(vx); vy = 0; } else { vy = Math.sign(vy); vx = 0; }
    const step = (snap || 0.1) * (big ? 5 : 1);
    if (selected === "spot") { spot.nudge(vx * step, vy * step); return; }
    for (const id of selectedIds()) {
      const entry = entryOf(id);
      entry.data.position = [round(entry.data.position[0] + vx * step), round(entry.data.position[1] + vy * step), entry.data.position[2]];
      apply(entry);
    }
    syncFields();
    clearTimeout(nudgeTimer);
    nudgeTimer = setTimeout(commitCurrent, 400);                               // gehaltene Taste = ein Schritt im Verlauf
  }
  // ---- Lage (Position + Drehung) kopieren/einfuegen, ausrichten, verteilen: damit stellt man z. B. Scheinwerfer schnell in eine Reihe
  let poseClip = null;
  function poseCopy() {
    const en = entryOf(selected);
    if (!en || !inMode(en)) return false;
    poseClip = { position: en.data.position.slice(), rotation: en.data.rotation.slice() };
    if (editing()) renderSide();
    return true;
  }
  /** what: "all" (bei einem gewaehlten Teil Position + Drehung, bei mehreren nur die Drehung), "rotation". */
  function posePaste(what) {
    if (!poseClip) return;
    const ids = selectedIds();
    if (!ids.length) return;
    ids.forEach((id) => {
      const en = entryOf(id);
      if (what === "all" && ids.length === 1) en.data.position = poseClip.position.slice();
      en.data.rotation = poseClip.rotation.slice();
      apply(en);
    });
    syncFields();
    commitCurrent();
    if (editing()) renderSide();
  }
  function alignSelected(axis) {
    const ids = selectedIds();
    const ref = entryOf(selected).data.position[axis];
    ids.forEach((id) => { const en = entryOf(id); const p = en.data.position.slice(); p[axis] = ref; en.data.position = p; apply(en); });
    syncFields();
    commitCurrent();
  }
  function distributeSelected(axis) {
    const list = selectedIds().map((id) => entryOf(id)).sort((a, b) => a.data.position[axis] - b.data.position[axis]);
    if (list.length < 3) return;
    const first = list[0].data.position[axis];
    const last = list[list.length - 1].data.position[axis];
    list.forEach((en, i) => { const p = en.data.position.slice(); p[axis] = round(first + ((last - first) * i) / (list.length - 1)); en.data.position = p; apply(en); });
    syncFields();
    commitCurrent();
  }
  /** Knopfzeilen fuer die Seitenleiste: Lage kopieren / einfuegen und (bei mehreren) Ausrichten / Verteilen. */
  function poseRows(multi) {
    const wrap = el("div", "sim3d__group");
    const small = (text, tip, act, onClick, disabled) => {
      const b = el("button", "sim3d__btn sim3d__btn--wide", text);
      b.type = "button";
      b.title = tip;
      b.dataset.act = act;
      b.style.flex = "1 1 0";
      b.style.justifyContent = "center";
      b.disabled = !!disabled;
      b.addEventListener("click", onClick);
      return b;
    };
    const pose = el("div", "sim3d__row");
    pose.append(
      small(t("SIM3D_POSE_COPY"), t("SIM3D_POSE_COPY_TIP"), "pose-copy", () => poseCopy(), multi && false),
      small(t("SIM3D_POSE_PASTE"), t("SIM3D_POSE_PASTE_TIP"), "pose-paste", () => posePaste("all"), !poseClip),
      small(t("SIM3D_POSE_PASTE_ROT"), t("SIM3D_POSE_PASTE_ROT_TIP"), "pose-paste-rot", () => posePaste("rotation"), !poseClip),
    );
    wrap.appendChild(pose);
    if (multi) {
      [["SIM3D_ALIGN", "SIM3D_ALIGN_TIP", "align", alignSelected], ["SIM3D_DISTRIBUTE", "SIM3D_DISTRIBUTE_TIP", "distribute", distributeSelected]].forEach(([labelKey, tipKey, act, fn]) => {
        const row = el("div", "sim3d__row");
        const label = el("span", "sim3d__snap-label", t(labelKey));
        label.title = t(tipKey);
        label.style.flex = "0 0 5.5rem";
        row.appendChild(label);
        [0, 1, 2].forEach((axis) => row.appendChild(small("XYZ"[axis], t(tipKey), act + "-" + "xyz"[axis], () => fn(axis), act === "distribute" && selectedIds().length < 3)));
        wrap.appendChild(row);
      });
    }
    return wrap;
  }

  /** Strg+A: alle sichtbaren Koerper (Bauen) bzw. alle platzierten Scheinwerfer (Scheinwerfer) waehlen. */
  function selectAll() {
    selectMany([...(mode === "fixtures" ? fixtureEntries : entries).values()].filter((en) => inMode(en) && !en.data.hidden).map((en) => en.id));
  }
  /** D: gewaehlte Koerper auf den Boden setzen (der tiefste Punkt liegt auf z = 0), wie der Knopf "Auf Boden setzen". */
  function dropSelection() {
    const ids = selectedIds().filter((id) => entries.has(id));
    ids.forEach((id) => {
      const entry = entries.get(id);
      const low = boxOf(entry).min[2];
      entry.data.position = [entry.data.position[0], entry.data.position[1], round(entry.data.position[2] - low, 4)];
      apply(entry);
    });
    if (ids.length) { syncFields(); commit(); }
  }
  /** F: die Kamera gleitet so, dass die Auswahl im Bild ist (Blickrichtung bleibt). */
  let frameFlight = 0;
  function frameSelection() {
    const box = new THREE.Box3();
    selectedIds().forEach((id) => { const en = entryOf(id); en.mesh.updateWorldMatrix(true, false); box.union(new THREE.Box3().setFromObject(en.mesh)); });
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    const radius = Math.max(box.getSize(new THREE.Vector3()).length() / 2, 0.5);
    const dir = sim.camera.position.clone().sub(sim.controls.target).normalize();
    const dist = Math.min(Math.max(radius / Math.tan(THREE.MathUtils.degToRad(sim.camera.fov) / 2) * 1.6, 3), 60);
    const fromTarget = sim.controls.target.clone();
    const fromPos = sim.camera.position.clone();
    const toPos = center.clone().addScaledVector(dir, dist);
    const start = performance.now();
    cancelAnimationFrame(frameFlight);
    const step = (now) => {
      const k = Math.min(1, (now - start) / 350);
      const s = k * k * (3 - 2 * k);
      sim.controls.target.lerpVectors(fromTarget, center, s);
      sim.camera.position.lerpVectors(fromPos, toPos, s);
      sim.controls.update();
      sim.invalidateView();
      if (k < 1) frameFlight = requestAnimationFrame(step);
    };
    frameFlight = requestAnimationFrame(step);
  }
  const ARROWS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
  root.addEventListener("keydown", (e) => {
    if (mode === "view") return;
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    const ctrl = (e.ctrlKey || e.metaKey) && !e.altKey;
    const key = e.key.toLowerCase();
    const handled = () => { e.preventDefault(); e.stopPropagation(); };
    const hasObjects = selectedIds().length > 0;
    const fx = mode === "fixtures";
    if (ctrl && key === "z" && !e.shiftKey) { handled(); if (fx) undoFx(); else undo(); }
    else if (ctrl && (key === "y" || (key === "z" && e.shiftKey))) { handled(); if (fx) redoFx(); else redo(); }
    else if (fx && ctrl && key === "c" && selected) { handled(); poseCopy(); }                         // Scheinwerfer gibt es nur einmal: Strg+C/V kopiert/uebertraegt ihre Lage (Position + Drehung)
    else if (fx && ctrl && key === "v") { handled(); posePaste("all"); }
    else if (fx && ctrl && "xd".includes(key) && key.length === 1) handled();                // Scheinwerfer gibt es nur einmal: kein Kopieren/Duplizieren
    else if (fx && hasObjects && (e.key === "Delete" || e.key === "Backspace")) { handled(); unplaceSelected(); }
    else if (ctrl && key === "c" && copySelected()) handled();
    else if (ctrl && key === "x" && copySelected()) { handled(); const ids = selectedIds(); ids.forEach((id) => removeObject(id)); commit(); renderSide(); clipboard.cut = true; }
    else if (ctrl && key === "v" && clipboard) { handled(); pasteClipboard(!!clipboard.cut); }
    else if (ctrl && key === "d" && hasObjects) { handled(); duplicateSelection(); }
    else if (ctrl && key === "a") { handled(); selectAll(); }
    else if (!ctrl && !e.altKey && ARROWS[e.key] && (hasObjects || selected === "spot")) { handled(); nudge(ARROWS[e.key][0], ARROWS[e.key][1], e.shiftKey); }       // mit Auswahl gehoeren die Pfeiltasten dem Objekt (kein Layoutwechsel)
    else if (selected === "spot" && (e.key === "Delete" || e.key === "Backspace")) { handled(); spot._api.remove(); select(null); }
    else if (hasObjects && (e.key === "Delete" || e.key === "Backspace")) { handled(); confirmDelete(selectedIds()); }
    else if (!ctrl && !e.altKey && !fx && key === "d" && hasObjects) { handled(); dropSelection(); }
    else if (!ctrl && !e.altKey && key === "f" && hasObjects) { handled(); frameSelection(); }
    else if (selected && e.key === "Escape") { handled(); select(null); }
  });

  // Sprachwechsel: Beschriftungen neu setzen (Panels bauen sich nicht neu auf)
  const onTranslated = () => {
    if (!root.isConnected && !root.classList.contains("oc-fs")) { document.removeEventListener("i18n-applied", onTranslated); return; }
    root.querySelectorAll(".sim3d__modes [data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    if (editing()) renderSide();
  };
  document.addEventListener("i18n-applied", onTranslated);

  // Der Test-Scheinwerfer ist aus der Oberflaeche ausgebaut (Scheinwerfer gibt es jetzt im Modus "Scheinwerfer"). Sein Licht-Code (sim3d_spot.js: Kegel, Schatten, Raumlicht-Quelle)
  // bleibt erhalten - er wird die Grundlage fuer das Licht der Scheinwerfer der Show (DMX-Werte live).
  const TEST_SPOT = false;
  const spotStub = { enabled: false, exists: false, data: {}, hitTest: () => null, begin() {}, move() {}, renderSection: () => document.createElement("div"), syncFields() {}, setVisibleHelpers() {}, nudge() {}, dispose() {}, _api: { add() {}, remove() {}, update() {} } };
  const spot = TEST_SPOT ? createTestSpot(sim, {
    meshes: () => [...entries.values()].map((en) => en.mesh), floor: sim.floor,
    startDrag, say, select, selectedIsSpot: () => selected === "spot", snap: () => snap, refreshSide: () => { if (editing()) renderSide(); }, setWorkLevel,
    tools: { el, t, numberRow, section, iconButton },
  }) : spotStub;
  const live = createLive(sim, {
    entries: () => fixtureEntries,
    targets: () => [...entries.values()].map((en) => en.mesh).concat([sim.floor]),
    haze: () => sim.room.state.haze / 100,
  });
  // Anleuchten: ausgeloest in der Scheinwerfersteuerung (window.OCSimAim), gezielt wird auf deren Auswahl - die Simulation bleibt in der Ansicht
  const aim = createAim(sim, {
    t, el, root, live,
    icon: (name) => Icons.svg(name),
    entry: (id) => fixtureEntries.get(id),
    selectedIds: () => (window.ProgrammerState ? [...window.ProgrammerState.selectedIds].filter((id) => fixtureEntries.has(id)) : []),
    targets: () => [...entries.values()].filter((en) => en.group.visible !== false).map((en) => en.mesh).concat([sim.floor]),
    send: (type, payload) => { if (window.__panelAPI && window.__panelAPI.sendToServer) window.__panelAPI.sendToServer(type, payload); },
  });
  const unregisterAim = window.OCSimAim ? window.OCSimAim.register({ root, aim, placedCount: () => fixtureEntries.size, canAim: (id) => canAim(fixtureEntries.get(id)) }) : () => {};
  setMode("view");
  setTimeout(() => {                                                 // zuletzt benutzten Modus dieses Geraets wiederherstellen (Ansicht / Bauen / Scheinwerfer)
    try {
      const saved = window.OCViewState ? OCViewState.get(OCViewState.scopeOf(root), "sim3d:mode", "view") : "view";
      if (saved !== "view" && modeButtons[saved]) requestMode(saved);
    } catch (err) { /* Standardansicht */ }
    persistMode = true;
  }, 900);
  resetHistory();
  if (stages() && stages().current && stages().current.fixture_layout) layout = JSON.parse(JSON.stringify(stages().current.fixture_layout));
  syncFixtureEntries();
  resetFxHistory();
  if (stages()) {
    if (stages().current && Array.isArray(stages().current.objects)) { appliedRevision = stages().current.revision; loadObjects(stages().current.objects); resetHistory(); }
    else stages().refresh();                                           // Antwort kommt als Ereignis "sim-stage"
  }
  return {
    setMode, requestMode,
    /** Die Scheinwerfer der Show haben sich geaendert (neu, entfernt, umbenannt): Koerper und Liste abgleichen. */
    fixturesChanged() { syncFixtureEntries(); recordFxStep(); if (mode === "fixtures") renderSide(); live.touch(); },
    /** Grand Master o. Ae. hat sich geaendert: Live-Licht neu berechnen. */
    liveChanged() { live.touch(); },
    /** Die Modell-Bibliothek hat sich geaendert (Dateimanager, anderes Geraet): Liste neu holen. */
    modelsChanged() { modelList = null; if (editing() && (modelsOpen || (entries.get(selected) && entries.get(selected).data.type === "model"))) loadModelList().then(() => { if (editing()) renderSide(); }); },
    // fuer Tests / spaeteren Ausbau
    _api: {
      live, aim, spot, fixtureEntries, placeFixture, placeAllFixtures, unplaceSelected, get layout() { return layout; }, addObject, addModel, addModels, loadModelList, importModelFile, importModelFiles, removeObject, select, selectMany, entries, confirmDelete, copySelected, pasteClipboard, duplicateSelection, nudge, undo, redo, commit, flushPush, serialize, loadObjects,
      get historyIndex() { return hIndex; }, get historyLength() { return history.length; },
      get selected() { return selected; }, get selection() { return selectedIds(); }, get mode() { return mode; }, get handles() { return handles; }, get arcs() { return arcs; },
      hitAt(x, y, pointerType = "mouse") { const h = pickHandle({ clientX: x, clientY: y, pointerType }); if (h) return h.kind; const a = castAt(rayFrom({ clientX: x, clientY: y }), arcs.map((q) => q.hit))[0]; const f = a && arcs.find((q) => q.hit === a.object); return f ? f.kind + f.axis : null; },
      boxOf, worldPerPixel, selectAll, poseCopy, posePaste, alignSelected, distributeSelected, get arcRadius() { return arcRig ? arcRig.userData.radius : null; }, get owner() { return handlesOwner; }, handlePositions() { return handles.map((h) => ({ kind: h.kind, cx: h.cx, cy: h.cy, p: h.object.position.toArray(), scale: h.object.scale.x })); }, frameSelection, dropSelection,
      screen(world) { const v = new THREE.Vector3(...world).project(sim.camera); const r = sim.canvas.getBoundingClientRect(); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; },
    },
    dispose() {
      spot.dispose();
      unregisterAim();
      aim.dispose();
      clearSelectionVisuals();
      clearTimeout(fxPushTimer);
      fixtureEntries.forEach((en) => sim.scene.remove(en.group));
      modelCache.forEach((promise) => promise.then((loaded) => { if (loaded && window.OCModelViewer) window.OCModelViewer.disposeShared(loaded.data); }));
      live.dispose();
      if (fxParts) { ["pick", "clamp", "arm", "head", "lens"].forEach((k) => fxParts[k].dispose()); ["body", "glass", "hidden"].forEach((k) => fxParts[k].dispose()); }
      entries.forEach((en) => { en.material.dispose(); if (en.screen) en.screen.dispose(); });
      Object.values(geometries).forEach((g) => g.dispose());
      frameGeometry.dispose();
      frameMaterial.dispose();
      document.removeEventListener("i18n-applied", onTranslated);
      document.removeEventListener("sim-stage", onStage);
      if (jsonPanel) jsonPanel.dispose();
      sideObserver.disconnect();
      if (envTexture) envTexture.dispose();
      clearTimeout(pushTimer);
      [modes, side, readout, grip, marqueeEl].forEach((node) => { if (node) node.remove(); });          // Oberflaeche des Panels abbauen (die Simulation kann ausgeschaltet und neu gestartet werden)
    },
  };
}

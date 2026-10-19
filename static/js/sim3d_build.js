/* 3D-Simulation, Baumodus. Oben links schaltet ein Umschalter zwischen "Ansicht" (nur anschauen) und "Bauen". Im Baumodus gleitet rechts eine breite Seitenleiste ein
 * (die Mitte der Buehne rueckt dabei in die Mitte des freien Bereichs): Grundkoerper hinzufuegen (Quader, Zylinder, Kugel, Keil), Objekte in der Liste oder im Bild waehlen,
 * Eigenschaften aendern (Name, Farbe, Position, Drehung, Groesse), duplizieren, loeschen (mit Rueckfrage). Alle Masse in Metern (eine Rasterkachel = 1 m), Winkel in Grad, Z nach oben.
 *
 * Direkt im Bild (wie in Tinkercad): ein gewaehltes Objekt hat einen gelben Rahmen und Griffe -
 *   - Ziehen auf dem Objekt verschiebt es auf dem Boden (auch ein ungewaehltes: es wird dabei gewaehlt),
 *   - weisse Punkte an den vier unteren Ecken aendern die Groesse (X/Y) einseitig: die gegenueberliegende Ecke bleibt stehen,
 *   - der weisse Punkt oben aendert die Hoehe, das gruene Dreieck darueber hebt das Objekt (Z),
 *   - drei kleine Dreh-Pfeile (X rot, Y gruen, Z blau) drehen um die jeweilige Achse (5-Grad-Schritte).
 * POSITION = Fusspunkt (Mitte der Unterseite): steht das Objekt auf dem Boden, ist Z = 0. Gedreht wird um diesen Fusspunkt ("Auf Boden setzen" schiebt ein gedrehtes Objekt
 * so, dass sein tiefster Punkt auf dem Boden liegt). Raster-Einrasten waehlbar (Standard 0,5 m).
 * Rueckgaengig/Wiederholen (Strg+Z / Strg+Y): jede abgeschlossene Aenderung ist ein Schritt. Die Objekte gehoeren zur aktiven BUEHNE auf dem Server (app/sim_stages.py,
 * Verwaltung und Toolbar-Chip in sim3d_stages.js): jede Aenderung geht (leicht gebuendelt) dorthin und zu allen Geraeten; Speichern schreibt die Buehnen-Datei.
 * Wechsel Bauen -> Ansicht mit ungespeicherten Aenderungen fragt: Weiter bearbeiten / Verwerfen / Speichern. */
import * as THREE from "three";
import { createTestSpot } from "/static/js/sim3d_spot.js";
import { createLive } from "/static/js/sim3d_live.js";
import { createAim, canAim } from "/static/js/sim3d_aim.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const MAX_OBJECTS = 200;
const MIN_SIZE = 0.05;
const SHAPES = {
  box: { key: "SIM3D_BOX", icon: "cube", size: [2, 2, 1] },
  cylinder: { key: "SIM3D_CYLINDER", icon: "cylinder", size: [1, 1, 2] },
  sphere: { key: "SIM3D_SPHERE", icon: "sphere", size: [1, 1, 1] },
  wedge: { key: "SIM3D_WEDGE", icon: "wedge", size: [2, 2, 1] },
};
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
  const counts = { box: 0, cylinder: 0, sphere: 0, wedge: 0 };
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
  function setMode(next) {
    const changed = next !== mode;
    if (changed && (selected || extra.size)) { extra.clear(); selected = null; clearSelectionVisuals(); }
    mode = next;
    if (mode === "fixtures") syncFixtureEntries();
    root.classList.toggle("sim3d--build", editing());
    if (typeof spot !== "undefined") spot.setVisibleHelpers(mode === "build");
    room.setMode(mode);
    Object.entries(modeButtons).forEach(([id, b]) => { b.classList.toggle("sim3d__mode--on", id === mode); b.setAttribute("aria-selected", String(id === mode)); });
    clearTimeout(hideTimer);
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
      : { id: uniqueId(), type, name: t(SHAPES[type].key) + " " + counts[type], color: DEFAULT_COLOR, position: [near(sim.controls.target.x), near(sim.controls.target.y), 0], rotation: [0, 0, 0], size: SHAPES[type].size.slice(), material: "matt" };
    if (source) data.position = [round(source.position[0] + offset), round(source.position[1] + offset), source.position[2]];
    const entry = createEntry(data);
    if (entry && !silent) commit();
    return entry;
  }

  const uniqueId = () => { let id; do { counter += 1; id = "o" + counter; } while (entries.has(id)); return id; };

  /** Koerper (Netz in der Szene) zu den Daten anlegen, ohne Verlauf/Server zu beruehren. */
  function createEntry(data) {
    geometries[data.type] = geometries[data.type] || buildGeometry(data.type);
    data.material = MATERIALS[data.material] ? data.material : "matt";
    const material = makeMaterial(data.material, data.color);
    const mesh = new THREE.Mesh(geometries[data.type], material);
    mesh.userData.id = data.id;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const group = new THREE.Group();
    group.add(mesh);
    sim.scene.add(group);
    const entry = { id: data.id, kind: "object", data, group, mesh, material, frame: null };
    entries.set(data.id, entry);
    apply(entry);
    return entry;
  }

  const serialize = () => [...entries.values()].map((en) => JSON.parse(JSON.stringify(en.data)));

  /** Objektliste ersetzen (Laden, Rueckgaengig, Aenderung von einem anderen Geraet/Panel); die Auswahl bleibt, wenn es das Objekt noch gibt. */
  function loadObjects(list) {
    const keep = selected;
    const keepExtra = [...extra];
    clearSelectionVisuals();
    selected = null;
    extra.clear();
    [...entries.keys()].forEach((id) => { const en = entries.get(id); sim.scene.remove(en.group); en.material.dispose(); entries.delete(id); });
    for (const d of list) {
      const n = parseInt(String(d.id).replace(/\D/g, ""), 10);
      if (Number.isFinite(n) && n > counter) counter = n;
      counts[d.type] = Math.max(counts[d.type] || 0, 0);
      createEntry(JSON.parse(JSON.stringify(d)));
    }
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
      ? await _askLayoutConfirm({ title: t("SIM3D_DELETE_TITLE"), body, confirmKey: "SIM3D_DELETE_CONFIRM" })
      : window.confirm(body);
    if (!ok) return;
    ids.forEach((id) => removeObject(id));
    commit();
    if (editing()) renderSide();
  }

  // ------------------------------------------------------------------------------------------ Auswahl: gelber Rahmen, Griffe, Dreh-Pfeile
  const frameMaterial = new THREE.LineBasicMaterial({ color: 0xffd400, depthTest: false, transparent: true });
  const frameGeometry = new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1).translate(0, 0, 0.5));
  let handles = [];                      // {object, hit, kind, cx, cy} - Kinder der Gruppe des gewaehlten Objekts
  let arcRig = null;                     // Dreh-Pfeile: Gruppe am Fusspunkt, achsparallel (dreht nicht mit)
  let arcs = [];

  const handleMaterial = (color) => new THREE.MeshBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.95 });
  function makeHandle(kind, geometry, color, cx = 0, cy = 0) {
    const object = new THREE.Mesh(geometry, handleMaterial(color));
    object.renderOrder = 30;
    const hit = new THREE.Mesh(new THREE.SphereGeometry(1.9, 8, 6), new THREE.MeshBasicMaterial({ visible: false }));      // grosse, unsichtbare Trefferflaeche (Finger)
    object.add(hit);
    return { object, hit, kind, cx, cy };
  }

  function makeArc(axis) {
    const [u, w, theta] = AXES[axis];
    const span = Math.PI / 3;
    const mesh = new THREE.Mesh(new THREE.TorusGeometry(1, 0.014, 8, 24, span), handleMaterial(AXIS_COLORS[axis]));
    mesh.renderOrder = 30;
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.11, 14), mesh.material);       // Pfeilspitze am Ende des Bogens
    tip.position.set(Math.cos(span), Math.sin(span), 0);
    tip.rotation.z = span;
    tip.renderOrder = 30;
    mesh.add(tip);
    const hit = new THREE.Mesh(new THREE.TorusGeometry(1, 0.1, 6, 16, span + 0.25), new THREE.MeshBasicMaterial({ visible: false }));
    mesh.add(hit);
    const U = new THREE.Vector3(...u), W = new THREE.Vector3(...w);
    const basis = new THREE.Matrix4().makeBasis(U, W, new THREE.Vector3().crossVectors(U, W));
    basis.multiply(new THREE.Matrix4().makeRotationZ(deg(theta)));
    mesh.quaternion.setFromRotationMatrix(basis);
    return { object: mesh, hit, kind: "arc", axis, u: U, w: W };
  }

  let handlesOwner = null;               // Objekt, an dem die Griffe haengen (nur bei Einzelauswahl)
  function clearSelectionVisuals() {
    entries.forEach((en) => { if (en.frame) { en.group.remove(en.frame); en.frame = null; } });
    fixtureEntries.forEach((en) => { if (en.frame) { en.group.remove(en.frame); en.frame = null; } });
    if (handlesOwner) handles.forEach((h) => { handlesOwner.group.remove(h.object); h.object.geometry.dispose(); h.object.material.dispose(); h.hit.geometry.dispose(); h.hit.material.dispose(); });
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
      else ids.forEach((id) => addFrame(entryOf(id)));
      renderSide();
    }
    sim.invalidate();
  }

  function buildSelectionVisuals(entry) {
    handlesOwner = entry;
    addFrame(entry);
    if (entry.kind !== "fixture") {                                      // Groesse aendern: nur bei Koerpern, Scheinwerfer haben feste Groesse
      const cornerGeo = new THREE.BoxGeometry(1, 1, 1);
      for (const cx of [-1, 1]) for (const cy of [-1, 1]) handles.push(makeHandle("corner", cornerGeo, 0xffffff, cx, cy));
      handles.push(makeHandle("height", cornerGeo, 0xffffff));
    }
    handles.push(makeHandle("lift", new THREE.ConeGeometry(0.8, 1.5, 3), 0x35d07f));         // Dreieck ueber dem Objekt
    handles.forEach((h) => entry.group.add(h.object));
    arcRig = new THREE.Group();
    for (const axis of [0, 1, 2]) { const a = makeArc(axis); arcs.push(a); arcRig.add(a.object); }
    sim.scene.add(arcRig);
    layoutSelection(entry);
  }

  /** Rahmen und Griffe an Groesse/Lage des Objekts anpassen; Griffe behalten ihre Bildschirmgroesse (siehe frame-Hook). */
  function layoutSelection(entry) {
    const [sx, sy, sz] = entry.data.size;
    if (entry.frame) { entry.frame.scale.set(sx, sy, sz); entry.frame.position.set(...(entry.offset || [0, 0, 0])); }       // Scheinwerfer: der Rahmen sitzt um das Modell (haengt meist vom Aufhaengepunkt nach unten)
    handles.forEach((h) => {
      if (h.kind === "corner") h.object.position.set((h.cx * sx) / 2, (h.cy * sy) / 2, 0);
      else if (h.kind === "height") h.object.position.set(0, 0, sz);
    });
    if (arcRig && entry === handlesOwner) arcRig.position.set(...entry.data.position);
    scaleSelection();
  }

  const tmp = new THREE.Vector3();
  function scaleSelection() {
    const entry = entryOf(selected);
    if (!entry || !handles.length) return;
    const unitAt = (point) => Math.max(sim.camera.position.distanceTo(point) * 0.011, 0.015);
    entry.group.updateWorldMatrix(true, false);
    handles.forEach((h) => {
      h.object.getWorldPosition(tmp);
      const u = unitAt(tmp);
      if (h.kind === "lift") {
        h.object.position.set(0, 0, (entry.kind === "fixture" ? entry.top || 0 : entry.data.size[2]) + u * 4.5);
        h.object.rotation.set(Math.PI / 2, 0, 0);
        h.object.scale.setScalar(u * 1.4);
      } else {
        h.object.scale.setScalar(u * 1.5);
      }
    });
    if (arcRig) {
      const [sx, sy, sz] = entry.data.size;
      const u = unitAt(arcRig.position);
      const radius = Math.max(Math.hypot(sx, sy, sz) * 0.5 + u * 3, u * 9);
      arcs.forEach((a) => a.object.scale.setScalar(radius));
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

  function renderSide() {
    side.textContent = "";
    fieldRefs = null;
    fxRows = null;
    if (mode === "fixtures") { stageRow = null; renderFixturesSide(); return; }
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
    const add = section(t("SIM3D_ADD"));
    const addRow = el("div", "sim3d__add");
    Object.entries(SHAPES).forEach(([type, info]) => {
      const b = iconButton(info.icon, t(info.key), "", () => { const entry = addObject(type); if (entry) select(entry.id); });
      b.dataset.add = type;
      addRow.appendChild(b);
    });
    add.appendChild(addRow);
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
    fieldRefs = {
      position: numberRow(t("SIM3D_POSITION"), d.position, (v) => { d.position = v; apply(entry); commit(); }, { step: 0.1, tip: t("SIM3D_POSITION_TIP") }),
      rotation: numberRow(t("SIM3D_ROTATION"), d.rotation, (v) => { d.rotation = v; apply(entry); commit(); }, { step: 5, unit: "°" }),
      size: numberRow(t("SIM3D_SIZE"), d.size, (v) => { d.size = v; apply(entry); commit(); }, { step: 0.1, min: MIN_SIZE }),
    };
    props.append(fieldRefs.position, fieldRefs.rotation, fieldRefs.size);
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
    built.lensMaterial.emissiveIntensity = 0;                           // Linse dunkel (das Leuchten kommt mit den DMX-Werten)
    entry.group.remove(entry.model);
    if (entry.built) entry.built.dispose();
    entry.model = built.group;
    entry.group.add(entry.model);
    entry.built = built;
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
  function syncFixtureEntries() {
    const known = new Set(showFixtures().map((f) => f.id));
    for (const id of [...fixtureEntries.keys()]) if (!known.has(id) || !layout[id]) removeFixtureEntry(id);
    for (const [id, item] of Object.entries(layout)) {
      if (!known.has(id)) continue;
      const entry = fixtureEntries.get(id);
      if (entry) { entry.data.position = item.position.slice(); entry.data.rotation = item.rotation.slice(); entry.data.hidden = !!item.hidden; entry.data.scale = item.scale || 1; applyFixture(entry); attachRealModel(entry); }
      else createFixtureEntry(id, item);
    }
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
    side.appendChild(head);

    const list = section("");
    const ul = el("ul", "sim3d__list");
    ul.style.maxHeight = "18rem";
    if (!fixtures.length) ul.appendChild(el("li", "sim3d__empty", t("SIM3D_FIXTURES_EMPTY")));
    fixtures.forEach((f) => {
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
        if (!fixtureEntries.has(f.id)) { placeFixture(f.id); select(f.id); return; }       // noch nicht auf der Buehne: Antippen setzt ihn
        if (fixtureEntries.get(f.id).data.hidden) return;                                  // ausgeblendet: erst einblenden
        select(f.id, { add: ev.shiftKey || ev.ctrlKey || ev.metaKey });
      });
      ul.appendChild(li);
    });
    list.appendChild(ul);

    const ids = selectedIds();
    if (!ids.length) {
      if (fixtures.length) side.appendChild(el("p", "sim3d__hint", t("SIM3D_FIXTURES_HINT")));
      side.appendChild(list);
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
    } else {
      const entry = fixtureEntries.get(ids[0]);
      const d = entry.data;
      const info = fixtureById(entry.id);
      props.appendChild(el("p", "sim3d__item-name", info ? info.name : entry.id));
      fieldRefs = {
        position: numberRow(t("SIM3D_POSITION"), d.position, (v) => { d.position = v; applyFixture(entry); commitFx(); }, { step: 0.1, tip: t("SIM3D_FIXTURE_POSITION_TIP") }),
        rotation: numberRow(t("SIM3D_ROTATION"), d.rotation, (v) => { d.rotation = v; applyFixture(entry); commitFx(); }, { step: 5, unit: "°", tip: t("SIM3D_FIXTURE_ROTATION_TIP") }),
      };
      props.append(fieldRefs.position, fieldRefs.rotation, scaleRow());
      const sizeText = [0, 1, 2].map((i) => String(Math.round((entry.bounds[i + 3] - entry.bounds[i]) * 100) / 100).replace(".", ",")).join(" × ");
      props.appendChild(el("p", "sim3d__hint", entry.real ? t("SIM3D_FIXTURE_MODEL_REAL").split("{size}").join(sizeText) : t("SIM3D_FIXTURE_MODEL_GENERIC")));
    }
    const remove = iconButton("trash", t("SIM3D_FIXTURE_REMOVE"), "sim3d__btn--danger", unplaceSelected);
    remove.dataset.act = "unplace";
    remove.style.flex = "0 0 auto";
    props.appendChild(remove);
    side.appendChild(props);
    side.appendChild(list);                                          // Eigenschaften zuerst, die Liste darunter
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
    const entry = inMode(entryOf(selected)) ? entryOf(selected) : null;
    // 1. Griffe und Dreh-Pfeile des gewaehlten Objekts
    if (entry) {
      const targets = [...handles.map((h) => h.hit), ...arcs.map((a) => a.hit)];
      const hits = castAt(ray, targets);
      const hit = hits.find((h) => handles.some((q) => q.hit === h.object)) || hits[0];       // die kleinen Griffe gehen den (grossen) Dreh-Pfeilen vor
      if (hit) {
        const handle = handles.find((h) => h.hit === hit.object) || arcs.find((a) => a.hit === hit.object);
        beginHandle(entry, handle, ray, e);
        return;
      }
    }
    // 2. ein Objekt: ein schon gewaehltes laesst sich auf dem Boden verschieben; ein noch nicht gewaehltes wird nur durch Antippen (kurz, ohne Ziehen) gewaehlt -
    //    wer darauf drueckt und zieht, dreht die Ansicht (so verschiebt man nicht versehentlich eine Wand)
    const body = castAt(ray, [...(mode === "fixtures" ? fixtureEntries : entries).values()].filter((en) => !en.data.hidden).map((en) => en.mesh))[0];
    if (body) {
      const hitEntry = entryOf(body.object.userData.id);
      if (add || !isSelected(hitEntry.id)) {                          // Umschalt/Strg: zur Auswahl hinzufuegen bzw. herausnehmen (beim Loslassen, ohne Ziehen)
        tap = { x: e.clientX, y: e.clientY, time: performance.now(), id: e.pointerId, pick: hitEntry.id, add };
        return;
      }
      const z0 = hitEntry.data.position[2];
      const q = planeZ(ray, z0) || body.point;
      const group = selectedIds().map((id) => ({ entry: entryOf(id), start: entryOf(id).data.position.slice() }));
      startDrag({ type: "move", entry: hitEntry, z0, offset: [hitEntry.data.position[0] - q.x, hitEntry.data.position[1] - q.y], moved: false, group, start: hitEntry.data.position.slice() }, e);
      return;
    }
    // 3. leer: ein kurzes Antippen hebt die Auswahl auf (Ziehen/Gesten bewegen die Kamera)
    tap = { x: e.clientX, y: e.clientY, time: performance.now(), id: e.pointerId, keep: add };
  }

  function beginHandle(entry, handle, ray, e) {
    const d = entry.data;
    entry.group.updateWorldMatrix(true, false);
    const inverse = entry.group.matrixWorld.clone().invert();
    const quat = entry.group.getWorldQuaternion(new THREE.Quaternion());
    const base = { entry, handle, inverse, quat, size0: d.size.slice(), pos0: d.position.slice(), moved: false };
    const local = { origin: ray.origin.clone().applyMatrix4(inverse), direction: ray.direction.clone().transformDirection(inverse) };
    if (handle.kind === "corner") {
      const p = planeZ(local, 0);
      if (!p) return;
      startDrag({ ...base, type: "corner", grab: [p.x - (handle.cx * d.size[0]) / 2, p.y - (handle.cy * d.size[1]) / 2] }, e);
    } else if (handle.kind === "height") {
      const s0 = closestOnLine(local, new THREE.Vector3(), new THREE.Vector3(0, 0, 1));
      if (s0 === null) return;
      startDrag({ ...base, type: "height", grab: s0 - d.size[2] }, e);
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

  function onMove(e) {
    if (!drag) return;
    const ray = rayFrom(e);
    if (drag.type === "spot") { spot.move(drag, ray, e); return; }
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
      const local = { origin: ray.origin.clone().applyMatrix4(drag.inverse), direction: ray.direction.clone().transformDirection(drag.inverse) };
      const size = drag.size0.slice();
      const shift = new THREE.Vector3();
      if (drag.type === "corner") {
        const p = planeZ(local, 0);
        if (!p) return;
        const c = [drag.handle.cx, drag.handle.cy];
        for (const a of [0, 1]) {
          const fixed = (-c[a] * drag.size0[a]) / 2;                                     // die gegenueberliegende Seite bleibt stehen
          let next = Math.max(MIN_SIZE, c[a] * (p.getComponent(a) - drag.grab[a] - fixed));
          if (snap) next = Math.max(snap, snapTo(next));
          size[a] = next;
          shift.setComponent(a, (c[a] * (next - drag.size0[a])) / 2);
        }
        shift.applyQuaternion(drag.quat);
        d.position = [round(drag.pos0[0] + shift.x), round(drag.pos0[1] + shift.y), round(drag.pos0[2] + shift.z)];
        say(`X ${fmt(size[0])}   Y ${fmt(size[1])} m`, e);
      } else {
        const s = closestOnLine(local, new THREE.Vector3(), new THREE.Vector3(0, 0, 1));
        if (s === null) return;
        let next = Math.max(MIN_SIZE, s - drag.grab);
        if (snap) next = Math.max(snap, snapTo(next));
        size[2] = next;
        say(`Z ${fmt(next)} m`, e);
      }
      d.size = size.map((v) => round(v));
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
    const was = tap;
    tap = null;
    if (was && was.aim) { if (was.id === e.pointerId && e.type !== "pointercancel" && Math.hypot(e.clientX - was.x, e.clientY - was.y) <= 6 && aim.armed) aim.pick(rayFrom(e)); return; }
    if (!was || was.id !== e.pointerId || mode === "view" || e.type === "pointercancel") return;
    if (Math.hypot(e.clientX - was.x, e.clientY - was.y) > 6) return;                  // gezogen: die Kamera hat sich bewegt
    if (was.pick) { select(was.pick, { add: was.add }); return; }                   // Antippen eines Objekts (auch langes Halten ohne Bewegen); mit Umschalt/Strg: zur Auswahl hinzufuegen
    if (was.keep || performance.now() - was.time > 500) return;
    select(null);
  }
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
    else if (fx && ctrl && "cxvd".includes(key) && key.length === 1) handled();                // Scheinwerfer gibt es nur einmal: kein Kopieren/Duplizieren
    else if (fx && hasObjects && (e.key === "Delete" || e.key === "Backspace")) { handled(); unplaceSelected(); }
    else if (ctrl && key === "c" && copySelected()) handled();
    else if (ctrl && key === "x" && copySelected()) { handled(); const ids = selectedIds(); ids.forEach((id) => removeObject(id)); commit(); renderSide(); clipboard.cut = true; }
    else if (ctrl && key === "v" && clipboard) { handled(); pasteClipboard(!!clipboard.cut); }
    else if (ctrl && key === "d" && hasObjects) { handled(); duplicateSelection(); }
    else if (!ctrl && !e.altKey && ARROWS[e.key] && (hasObjects || selected === "spot")) { handled(); nudge(ARROWS[e.key][0], ARROWS[e.key][1], e.shiftKey); }       // mit Auswahl gehoeren die Pfeiltasten dem Objekt (kein Layoutwechsel)
    else if (selected === "spot" && (e.key === "Delete" || e.key === "Backspace")) { handled(); spot._api.remove(); select(null); }
    else if (hasObjects && (e.key === "Delete" || e.key === "Backspace")) { handled(); confirmDelete(selectedIds()); }
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
    // fuer Tests / spaeteren Ausbau
    _api: {
      live, aim, spot, fixtureEntries, placeFixture, placeAllFixtures, unplaceSelected, get layout() { return layout; }, addObject, removeObject, select, selectMany, entries, confirmDelete, copySelected, pasteClipboard, duplicateSelection, nudge, undo, redo, commit, flushPush, serialize, loadObjects,
      get historyIndex() { return hIndex; }, get historyLength() { return history.length; },
      get selected() { return selected; }, get selection() { return selectedIds(); }, get mode() { return mode; }, get handles() { return handles; }, get arcs() { return arcs; },
      hitAt(x, y) { const hs = castAt(rayFrom({ clientX: x, clientY: y }), [...handles.map((q) => q.hit), ...arcs.map((q) => q.hit)]); const h = hs.find((k) => handles.some((q) => q.hit === k.object)) || hs[0]; const f = h && (handles.find((q) => q.hit === h.object) || arcs.find((q) => q.hit === h.object)); return f ? f.kind + (f.axis !== undefined ? f.axis : "") : null; },
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
      entries.forEach((en) => en.material.dispose());
      Object.values(geometries).forEach((g) => g.dispose());
      frameGeometry.dispose();
      frameMaterial.dispose();
      document.removeEventListener("i18n-applied", onTranslated);
      document.removeEventListener("sim-stage", onStage);
      if (envTexture) envTexture.dispose();
      clearTimeout(pushTimer);
    },
  };
}

/* 3D-Simulation: ANLEUCHTEN. Die im Programmer (Scheinwerfersteuerung) gewaehlten Moving Heads richten sich auf einen Punkt der Buehne aus. Ausgeloest wird es in der Scheinwerfer-
 * steuerung (Position: "Punkt in 3D-Simulation setzen", Registratur window.OCSimAim aus sim3d_boot.js); die Simulation bleibt in der Ansicht: ein Banner zeigt den Zielmodus,
 * ein Antippen einer Flaeche (Koerper oder Boden) setzt den Punkt. Fuer jeden Kopf wird Pan/Tilt aus dem echten 3D-Modell gerechnet (die Achsen des Modells werden durchprobiert: grobes Raster, dann
 * Feinabgleich; von zwei gleichwertigen Loesungen - Pan +180 Grad mit gespiegeltem Tilt - gilt die naehere zur aktuellen Stellung); ein dunkler Kopf bekommt Dimmer 100.
 * Auto-Fokus / Auto-Zoom (Scheinwerfersteuerung, Reiter Fokus) nehmen die Wurfweite entlang des aktuellen Strahls bis zur ersten Flaeche: Fokus = Schaerfeebene auf der Wurfweite,
 * Zoom = Oeffnungswinkel so, dass der Lichtkreis dort den gewaehlten Radius hat. Punkt und Linien sind nur im Zielmodus sichtbar.
 * Die Werte gehen wie jede Bedienung ueber "set_fixture_values" in den PROGRAMMER (DMX, andere Geraete, Cue speichern) - die Simulation zeigt sie ueber die Live-Werte. */
import * as THREE from "three";

const MARKER_COLOR = 0xffb000;
const GRID_PAN = 24;                              // grobes Raster der Achsen (Anteil des Bereichs)
const GRID_TILT = 12;
const REFINE = 6;                                 // so viele beste Rasterpunkte werden fein abgeglichen
const TOLERANCE = 1.0;                            // Abweichung (Grad), ab der ein Ziel als nicht erreichbar gilt
const KEY = "oc-sim3d-aim";
const DEFAULTS = { radius: 0.5, light: true };

const loadPrefs = () => {
  try { return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY) || "{}") || {}) }; } catch (err) { return { ...DEFAULTS }; }
};
const savePrefs = (prefs) => { try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch (err) { /* kein Speicher */ } };

const angleOf = (axis, f) => (axis ? (axis.from !== undefined ? axis.from + f * (axis.to - axis.from) : axis.min + f * (axis.max - axis.min)) : 0);

/** Kann der Scheinwerfer zielen? Moving Head mit echtem 3D-Modell (Achsen aus der Datei) und Pan/Tilt. */
export const canAim = (entry) => !!entry && !!entry.built && !!entry.axes && !!entry.axes.pan && !!entry.axes.tilt && !!(entry.beams && entry.beams[0]);

const tmpPos = new THREE.Vector3();
const tmpQuat = new THREE.Quaternion();
const tmpScale = new THREE.Vector3();
const tmpDir = new THREE.Vector3();
const tmpWant = new THREE.Vector3();

/** Pan/Tilt (Anteile 0..1 der Achsbereiche), mit denen der Strahl des Kopfes auf `target` (Welt, Vector3) zeigt.
 *  current: {pan, tilt} in Prozent (aktuelle Stellung, zum Waehlen der naeheren Loesung) oder null. Rueckgabe {pan, tilt} in Prozent, error (Grad), distance (m), origin. */
export function solveAim(entry, target, current) {
  const beam = entry.beams[0].object;
  const built = entry.built;
  const before = built.getAngles();
  const { pan: panAxis, tilt: tiltAxis } = entry.axes;
  const cost = (fp, ft) => {
    built.setAngles(angleOf(panAxis, fp), angleOf(tiltAxis, ft));
    entry.group.updateMatrixWorld(true);
    beam.matrixWorld.decompose(tmpPos, tmpQuat, tmpScale);
    tmpDir.set(0, 0, -1).applyQuaternion(tmpQuat);
    tmpWant.copy(target).sub(tmpPos);
    const len = tmpWant.length();
    if (len < 1e-6) return 0;
    return Math.acos(Math.max(-1, Math.min(1, tmpDir.dot(tmpWant) / len)));
  };
  const cells = [];
  for (let i = 0; i <= GRID_PAN; i++) for (let j = 0; j <= GRID_TILT; j++) cells.push({ p: i / GRID_PAN, t: j / GRID_TILT, e: 0 });
  cells.forEach((c) => { c.e = cost(c.p, c.t); });
  cells.sort((a, b) => a.e - b.e);
  const found = [];
  for (const c of cells) {
    if (found.length >= REFINE) break;
    if (found.some((f) => Math.abs(f.p - c.p) <= 2 / GRID_PAN && Math.abs(f.t - c.t) <= 2 / GRID_TILT)) continue;       // gleiche Mulde nicht doppelt
    found.push({ p: c.p, t: c.t, e: c.e });
  }
  found.forEach((f) => {                                                // Feinabgleich: Koordinatensuche mit halbierter Schrittweite
    let step = 1 / GRID_PAN;
    for (let n = 0; n < 40 && step > 2e-6; n++) {
      let improved = false;
      for (const [dp, dt] of [[step, 0], [-step, 0], [0, step], [0, -step], [step, step], [-step, -step], [step, -step], [-step, step]]) {
        const p = Math.min(1, Math.max(0, f.p + dp));
        const t = Math.min(1, Math.max(0, f.t + dt));
        const e = cost(p, t);
        if (e < f.e - 1e-12) { f.p = p; f.t = t; f.e = e; improved = true; }
      }
      if (!improved) step /= 2;
    }
  });
  const best = Math.min(...found.map((f) => f.e));
  const good = found.filter((f) => f.e <= best + THREE.MathUtils.degToRad(0.05));
  let pick = good[0];
  if (good.length > 1 && current) {                                     // gleichwertige Loesungen: die mit dem kuerzesten Weg
    const cp = current.pan / 100;
    const ct = current.tilt / 100;
    const way = (f) => Math.abs(f.p - cp) * Math.abs(angleOf(panAxis, 1) - angleOf(panAxis, 0)) + Math.abs(f.t - ct) * Math.abs(angleOf(tiltAxis, 1) - angleOf(tiltAxis, 0));
    pick = good.reduce((a, b) => (way(b) < way(a) ? b : a));
  }
  cost(pick.p, pick.t);                                                 // Ursprung des Strahls bei der gewaehlten Stellung
  const origin = tmpPos.clone();
  built.setAngles(before.pan, before.tilt);                             // Modell zurueck in die Stellung vor dem Probieren
  entry.group.updateMatrixWorld(true);
  return { pan: pick.p * 100, tilt: pick.t * 100, error: THREE.MathUtils.radToDeg(pick.e), distance: target.distanceTo(origin), origin };
}

export function createAim(sim, ctx) {
  const { t, el, root } = ctx;
  const prefs = loadPrefs();
  let armed = false;
  let target = null;                       // {point: Vector3, normal: Vector3} - nur solange der Zielmodus an ist
  let result = null;                       // Rueckmeldung des letzten Zielens (Banner)
  let lastOrigins = [];
  const raycaster = new THREE.Raycaster();
  const notify = () => { if (window.OCSimAim) window.OCSimAim.notify(); };

  // ---- Markierung im Bild (nur im Zielmodus): Punkt und je Scheinwerfer eine Linie vom Strahlursprung zum Punkt
  const marker = new THREE.Group();
  marker.visible = false;
  marker.renderOrder = 998;
  const dotMaterial = new THREE.MeshBasicMaterial({ color: MARKER_COLOR, depthTest: false, depthWrite: false, transparent: true, opacity: 0.95 });
  const dot = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 12), dotMaterial);
  const halo = new THREE.Mesh(new THREE.RingGeometry(0.13, 0.17, 40), new THREE.MeshBasicMaterial({ color: MARKER_COLOR, depthTest: false, depthWrite: false, transparent: true, opacity: 0.85, side: THREE.DoubleSide }));
  const beamGeometry = new THREE.CylinderGeometry(1, 1, 1, 6, 1, true);              // Einheitsrohr entlang Y: je Linie skaliert und ausgerichtet
  const beamMaterial = new THREE.MeshBasicMaterial({ color: MARKER_COLOR, depthTest: false, depthWrite: false, transparent: true, opacity: 0.6 });
  const lineGroup = new THREE.Group();
  [dot, halo].forEach((m) => { m.renderOrder = 998; m.raycast = () => {}; });
  marker.add(dot, halo);
  sim.scene.add(marker, lineGroup);
  const yAxis = new THREE.Vector3(0, 1, 0);

  function drawMarker() {
    lineGroup.children.slice().forEach((m) => lineGroup.remove(m));
    if (!target) { marker.visible = false; sim.invalidate(); return; }
    marker.visible = true;
    marker.position.copy(target.point);
    halo.position.copy(target.normal).multiplyScalar(0.012);
    halo.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), target.normal);
    lastOrigins.forEach((origin) => {                                                  // eine Linie je Scheinwerfer: man sieht, von wo sie alle kommen
      const delta = target.point.clone().sub(origin);
      const length = delta.length();
      if (length < 0.01) return;
      const tube = new THREE.Mesh(beamGeometry, beamMaterial);
      tube.renderOrder = 997;
      tube.raycast = () => {};
      tube.position.copy(origin).addScaledVector(delta, 0.5);
      tube.quaternion.setFromUnitVectors(yAxis, delta.normalize());
      tube.scale.set(0.01, length, 0.01);
      lineGroup.add(tube);
    });
    sim.invalidate();
  }

  // ---- Banner im Bild (die Ansicht hat keine Seitenleiste): gleiche Gestalt wie die Modus-Leiste, ein Segment mit Text, eins zum Beenden
  const bar = el("div", "sim3d__aimbar");
  bar.hidden = true;
  const barText = el("span", "sim3d__aimbar-text", t("SIM3D_AIM_ARMED"));
  const barDone = el("button", "sim3d__aimbar-done");
  barDone.type = "button";
  barDone.dataset.act = "aim-cancel";
  barDone.title = t("SIM3D_AIM_FINISH_TIP");
  barDone.append(ctx.icon("check"), el("span", "", t("SIM3D_AIM_FINISH")));
  barDone.addEventListener("click", () => arm(false));
  const barMain = el("span", "sim3d__aimbar-main");
  barMain.append(ctx.icon("target"), barText);
  bar.append(barMain, barDone);
  root.appendChild(bar);

  // ---- Werte an den Programmer
  function push(entry, values) {
    const pct = (v) => Math.max(0, Math.min(100, v));
    const payload = { ids: [entry.id] };
    const shown = {};
    Object.entries(values).forEach(([key, v]) => {
      shown[key] = Math.round(pct(v) * 100) / 100;
      payload[key] = Math.round(pct(v) * 2.55);
      if (key === "pan" || key === "tilt") payload[key + "16"] = Math.round(pct(v) * 655.35);
    });
    ctx.send("set_fixture_values", payload);
    if (window.ProgrammerState && window.ProgrammerState.applyFromServer) window.ProgrammerState.applyFromServer({ [entry.id]: shown });         // Programmer-Panel nachfuehren (Fader, "angefasst")
    const cache = window.__fixturesLive || (window.__fixturesLive = {});
    cache[entry.id] = Object.assign(cache[entry.id] || {}, shown);                                                                                    // die Simulation faehrt sofort los (der Server bestaetigt gleich)
  }
  const liveChanged = () => document.dispatchEvent(new CustomEvent("fixtures-live-values", { detail: {} }));

  // ---- Punkt setzen: Pan/Tilt (und Licht an, wenn dunkel)
  function apply(ids) {
    if (!target) return null;
    const live = window.__fixturesLive || {};
    const done = [];
    let skipped = 0;
    let far = 0;
    const origins = [];
    ids.map((id) => ctx.entry(id)).filter(Boolean).forEach((entry) => {
      if (!canAim(entry)) { skipped += 1; return; }
      const cur = live[entry.id];
      const current = cur && cur.pan !== undefined && cur.tilt !== undefined ? { pan: cur.pan, tilt: cur.tilt } : null;
      const s = solveAim(entry, target.point, current);
      origins.push(s.origin);
      if (s.error > TOLERANCE) far += 1;
      const values = { pan: s.pan, tilt: s.tilt };
      if (prefs.light && !(cur && cur.dimmer > 0)) values.dimmer = 100;
      push(entry, values);
      done.push(s);
    });
    liveChanged();
    lastOrigins = origins;
    drawMarker();
    const throws = done.map((d) => d.distance);
    result = { aimed: done.length, skipped, far, minThrow: throws.length ? Math.min(...throws) : 0, maxThrow: throws.length ? Math.max(...throws) : 0 };
    barText.textContent = resultText();
    notify();
    return result;
  }

  const fmt = (v) => v.toFixed(1).replace(".", ",");
  /** Rueckmeldung fuer das Banner: Anzahl und Wurfweite (Laenge des Lichts). */
  function resultText() {
    if (!result) return t("SIM3D_AIM_ARMED");
    const parts = [t("SIM3D_AIM_DONE").split("{n}").join(String(result.aimed))];
    if (result.aimed) parts.push(t("SIM3D_AIM_THROW").split("{min}").join(fmt(result.minThrow)).split("{max}").join(fmt(result.maxThrow)));
    if (result.skipped) parts.push(t("SIM3D_AIM_SKIPPED").split("{n}").join(String(result.skipped)));
    if (result.far) parts.push(t("SIM3D_AIM_FAR").split("{n}").join(String(result.far)));
    return parts.join(" ");
  }

  function hit(ray) {
    raycaster.ray.copy(ray);
    raycaster.near = 0.01;
    raycaster.far = 1000;
    const h = raycaster.intersectObjects(ctx.targets(), false)[0];
    if (!h) return null;
    const normal = h.face ? h.face.normal.clone().applyMatrix3(new THREE.Matrix3().getNormalMatrix(h.object.matrixWorld)).normalize() : new THREE.Vector3(0, 0, 1);
    if (normal.dot(ray.direction) > 0) normal.negate();                        // die Seite, die man sieht
    return { point: h.point.clone(), normal };
  }

  /** Antippen im Zielmodus: Punkt setzen und die im Programmer gewaehlten Scheinwerfer darauf ausrichten. */
  function pick(ray) {
    const h = hit(ray);
    if (!h) return false;
    target = h;
    apply(ctx.selectedIds());
    return true;
  }

  // ---- Auto-Fokus / Auto-Zoom: Wurfweite = Entfernung vom Strahlursprung bis zur ersten Flaeche in Strahlrichtung (Stellung laut Live-Werten)
  function throwOf(entry) {
    const live = (window.__fixturesLive || {})[entry.id];
    const built = entry.built;
    const before = built.getAngles();
    const { pan, tilt } = entry.axes;
    if (live && live.pan !== undefined && live.tilt !== undefined) built.setAngles(angleOf(pan, live.pan / 100), angleOf(tilt, live.tilt / 100));
    entry.group.updateMatrixWorld(true);
    entry.beams[0].object.matrixWorld.decompose(tmpPos, tmpQuat, tmpScale);
    const origin = tmpPos.clone();
    const dir = tmpDir.set(0, 0, -1).applyQuaternion(tmpQuat).clone();
    built.setAngles(before.pan, before.tilt);
    entry.group.updateMatrixWorld(true);
    raycaster.set(origin, dir);
    raycaster.near = 0.01;
    raycaster.far = 1000;
    const h = raycaster.intersectObjects(ctx.targets(), false)[0];
    return h ? h.distance : null;
  }
  /** Welche Radien (m) des Lichtkreises sind auf die Wurfweite JEDES Geraets moeglich? Ein Geraet: {kind: "one", min, max}; mehrere: der Bereich, den alle erreichen ("all"), sonst die
   *  Spanne ueber alle ("span"); null, wenn kein Geraet zoomen kann oder keins eine Flaeche trifft. */
  function zoomInfo(ids) {
    const per = [];
    ids.map((id) => ctx.entry(id)).filter(Boolean).forEach((entry) => {
      if (!entry.built || !entry.axes || !entry.axes.pan || !entry.zoomRange || !(entry.beams && entry.beams[0])) return;
      const d = throwOf(entry);
      if (d === null) return;
      const limits = ctx.live.zoomLimits(entry.zoomRange);
      const half = (angle) => Math.max(0.3, d) * Math.tan(THREE.MathUtils.degToRad(angle) / 2);
      per.push({ min: half(limits.min), max: half(limits.max) });
    });
    if (!per.length) return null;
    if (per.length === 1) return { kind: "one", ...per[0] };
    const lo = Math.max(...per.map((p) => p.min));
    const hi = Math.min(...per.map((p) => p.max));
    return lo <= hi ? { kind: "all", min: lo, max: hi } : { kind: "span", min: Math.min(...per.map((p) => p.min)), max: Math.max(...per.map((p) => p.max)) };
  }
  /** kind "focus" | "zoom" (radius in m). Jedes Geraet rechnet mit SEINER Wurfweite. Rueckgabe {done, skipped (kann das nicht), miss (trifft keine Flaeche), clamped (Zoom am Anschlag)}. */
  function auto(kind, ids, radius) {
    const out = { done: 0, skipped: 0, miss: 0, clamped: 0 };
    ids.map((id) => ctx.entry(id)).filter(Boolean).forEach((entry) => {
      const able = !!entry.built && !!entry.axes && !!entry.axes.pan && !!(entry.beams && entry.beams[0]) && (kind === "focus" ? !!(entry.focusRange && entry.axes.focus) : !!entry.zoomRange);
      if (!able) { out.skipped += 1; return; }
      const d = throwOf(entry);
      if (d === null) { out.miss += 1; return; }
      const throwLength = Math.max(0.3, d);
      if (kind === "focus") push(entry, { focus: ctx.live.focusPctFor(entry.focusRange, throwLength).pct });
      else {
        const wanted = THREE.MathUtils.radToDeg(2 * Math.atan(radius / throwLength));
        const z = ctx.live.zoomPctFor(entry.zoomRange, wanted);
        if (Math.abs(z.angle - wanted) > 0.3) out.clamped += 1;
        push(entry, { zoom: z.pct });
      }
      out.done += 1;
    });
    if (out.done) liveChanged();
    return out;
  }

  const onKey = (e) => { if (e.key === "Escape" && armed) { e.preventDefault(); arm(false); } };
  /** Zielmodus ein/aus. Beim Beenden verschwinden Punkt und Linien. */
  function arm(on) {
    on = !!on;
    if (on === armed) return;
    armed = on;
    target = null;
    result = null;
    lastOrigins = [];
    drawMarker();
    barText.textContent = t("SIM3D_AIM_ARMED");
    sim.canvas.style.cursor = armed ? "crosshair" : "";
    bar.hidden = !armed;
    if (armed) document.addEventListener("keydown", onKey, true); else document.removeEventListener("keydown", onKey, true);
    notify();
  }

  function setRadius(value) {
    if (!Number.isFinite(value)) return;
    prefs.radius = Math.round(Math.min(20, Math.max(0.05, value)) * 100) / 100;
    savePrefs(prefs);
  }

  return {
    get armed() { return armed; },
    get target() { return target; },
    get result() { return result; },
    get lineCount() { return lineGroup.children.length; },
    prefs, arm, pick, apply, auto, zoomInfo, setRadius,
    dispose() {
      arm(false);
      sim.scene.remove(marker, lineGroup);
      dot.geometry.dispose(); halo.geometry.dispose(); halo.material.dispose(); dotMaterial.dispose(); beamGeometry.dispose(); beamMaterial.dispose();
      bar.remove();
    },
  };
}

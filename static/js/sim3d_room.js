/* 3D-Simulation: RAUM & LICHT. Beleuchtung des Raums und Anzeige-Einstellungen in einem kleinen Fenster (Knopf oben rechts; bleibt offen, damit man beim Einstellen zusehen kann).
 *
 * Licht im Raum (alles aus den Lichtquellen berechnet, die sich in sim.lightSources melden: () => ({lumens, candela, color, angle, position, axis, hit})):
 *   - Arbeitslicht: nur im Baumodus (zum Bauen und Testen). Grundlicht: die Beleuchtung des Raums selbst, gilt in Bauen und Ansicht (0 % = stockfinster).
 *   - Zurueckgeworfenes Licht (Raumlicht). Physik: "Mittelwert-Modell der Zwischenreflexion" (wie die Ulbricht-Kugel): Ein Raum mit Gesamtflaeche A und mittlerem Reflexionsgrad rho nimmt den
 *     Lichtstrom Phi auf; das mehrfach reflektierte Licht erzeugt ueberall die Beleuchtungsstaerke E = Phi * rho / (A * (1 - rho)). Das ist das gleichmaessige Umgebungslicht. Die
 *     Richtung kommt von den getroffenen Flaechen: Strahlen ueber den ganzen Kegel suchen die beleuchteten Flaechen (Farbe und Reflexion je Flaeche); aus ihnen entsteht ein Verlauf
 *     (Umgebungslicht erster Ordnung: heller auf Flaechen, die zu den beleuchteten Stellen zeigen, dunkler auf den abgewandten) und ein Farbstich (ein blauer Quader faerbt das
 *     Raumlicht blau). Bewusst KEINE virtuellen Punktlichter an den Treffern: sie erzeugten grelle Punkte, Glanzlichter und Farbkreise auf Koerpern und Waenden.
 *     Farben mischen sich: Lichtstrom und Reflexionsgrad werden je Farbkanal gerechnet (Lichtfarbe x Flaechenfarbe). Spiegelnde Flaechen (Metall, Spiegel) werfen den Strahl gerichtet weiter
 *     (ein virtueller Scheinwerfer in Spiegelrichtung, mit Schatten). Flaeche A und rho kommen aus der Buehne (Koerper), einer Raumhuelle um sie (Waende und Decke mit der Wandreflexion) und dem Boden.
 *   - Das Auge/die Kamera passt sich dem Dunkeln an: die indirekten Anteile werden mit einem festen Anpassungsfaktor (INDIRECT_BOOST) angehoben, sonst waere der Schimmer unsichtbar.
 *   - Spiegelungen glaenzender Oberflaechen (Umgebungs-Karte) folgen der Helligkeit des Raums: im Dunkeln spiegelt nichts.
 * Die Raum-Einstellungen gelten fuer alle Geraete: sie liegen auf dem Server (/api/sim-room, gemerkt in der App-Config) und werden per Ereignis "sim-stage" abgeglichen. Zuruecksetzen
 * (mit Rueckfrage) setzt alle Licht-Einstellungen auf den Standard.
 * Die Qualitaet bleibt pro Geraet. */
import * as THREE from "three";

const INDIRECT_BOOST = 10;               // Anpassung des Auges an das Dunkle (Faktor auf alle indirekten Anteile)
const BLEED_GAIN = 0.4;               // Staerke der Farbabstrahlung (Anteil der direkten Beleuchtung am getroffenen Punkt, ein Fleck der Groesse r)
const GRADIENT = 0.9;                 // Staerke des Verlaufs im Umgebungslicht (0 = gleichmaessig, 1 = vom abgewandten Rand bis doppelt so hell)
const ENV_SHARE = 0.6;                // Anteil der Raumhelligkeit, der in die Spiegelung glaenzender Oberflaechen eingeht (Objektreflexion bei 100 %)
const FIELDS = ["work", "house", "bounce", "shell", "reflect", "bleed", "exposure", "haze", "helpers"];
const DEFAULTS = { work: 100, house: 0, bounce: 0, shell: 50, reflect: 100, bleed: 60, exposure: 50, haze: 10, helpers: false };      // wie app/sim_stages.py ROOM_DEFAULTS
const MIN_ROOM = 10;                   // kleinste Raummasse der Huelle (Meter)
const MIN_HEIGHT = 5;

function injectStyle() {
  if (document.getElementById("sim3d-room-style")) return;
  const style = document.createElement("style");
  style.id = "sim3d-room-style";
  style.textContent = `
    .sim3d__room { position: absolute; top: calc(100% + 0.4rem); right: 0; width: min(23rem, calc(100cqw - 1rem)); max-height: 60vh; overflow-y: auto; overscroll-behavior: contain; touch-action: pan-y; -webkit-overflow-scrolling: touch; box-sizing: border-box; padding: 0.7rem;
      display: flex; flex-direction: column; gap: 0.5rem; background: color-mix(in srgb, var(--panel-bg) 96%, transparent); border: 1px solid var(--border-color);
      border-radius: var(--base-radius, 3px); color: var(--text-main); font-size: 0.85rem; }
    .sim3d__room[hidden] { display: none; }
    .sim3d__room-row { display: flex; align-items: center; gap: 0.5rem; min-height: 2.25rem; }
    .sim3d__room-row label { flex: 1 1 auto; color: var(--text-main); }
    .sim3d__room-hint { margin: 0; color: var(--secondary-text); font-size: 0.75rem; line-height: 1.35; }
    .sim3d__room > * { flex-shrink: 0; }
    .sim3d__room .sim3d__btn.sim3d__room-reset { align-self: stretch; flex: 0 0 auto; width: auto; justify-content: center; height: 2.5rem; margin-top: 0.25rem; gap: 0.5rem; font: inherit; }
    .sim3d__room input[type="checkbox"] { width: 1.3rem; height: 1.3rem; accent-color: var(--accent-color); }
    .sim3d__room .sim3d__slider[hidden] { display: none; }
  `;
  document.head.appendChild(style);
}

/** host: .sim3d-Wurzel, tools: Knopfleiste oben rechts. */
export function createRoom(sim, host, tools) {
  injectStyle();
  const state = { ...DEFAULTS };
  const uid = "r" + Math.random().toString(36).slice(2, 10);       // Kennung dieses Panels (sein Echo vom Server wird ignoriert)
  let mode = "view";
  sim.lightSources = sim.lightSources || [];

  // ------------------------------------------------------------------------------------------ Lichter
  const hemi = new THREE.HemisphereLight(0xffffff, 0x2c2c2e, 0);        // Arbeitslicht + Grundlicht (gleichmaessig)
  const sun = new THREE.DirectionalLight(0xffffff, 0);                  // Arbeitslicht: eine "Sonne" fuer Plastizitaet
  sun.position.set(-6, -8, 12);
  const bounce = new THREE.HemisphereLight(0xffffff, 0xffffff, 1);      // mehrfach zurueckgeworfenes Licht (gleichmaessig)
  sim.scene.add(hemi, sun, bounce);
  const pool = [];                                                       // je Quelle: ein spiegelnder Strahl (mit Schatten) fuer Metall/Spiegel
  const makeVirtual = () => {
    const light = new THREE.SpotLight(0xffffff, 0, 0, Math.PI / 2 * 0.98, 1, 2);
    light.shadow.mapSize.set(512, 512);                                  // der gerichtete Spiegel-Strahl darf nicht durch Gegenstaende hindurch leuchten
    light.shadow.bias = -0.0005;
    light.shadow.normalBias = 0.03;
    light.shadow.camera.near = 0.08;
    light.shadow.camera.far = 40;
    sim.scene.add(light, light.target);
    return light;
  };
  const dropVirtual = (l) => { sim.scene.remove(l, l.target); l.dispose(); if (l.shadow) l.shadow.dispose(); };
  function resizePool(count) {
    while (pool.length < count) pool.push({ specular: makeVirtual() });
    while (pool.length > count) dropVirtual(pool.pop().specular);
  }

  const listeners = [];
  let envScale = 1;
  let ambient = 0;
  let key = "";
  let info = null;
  let infoVersion = -1;
  const floorColor = new THREE.Color();
  const phi = new THREE.Color();
  const albedo = new THREE.Color();
  const tmp = new THREE.Vector3();
  const reflected = new THREE.Vector3();

  /** Raummodell: Flaeche A und mittlerer Reflexionsgrad (je Farbkanal) aus Koerpern, Boden und Raumhuelle. */
  function model(sources) {
    if (infoVersion !== sim.version || !info) { info = sim.roomInfo ? sim.roomInfo() : null; infoVersion = sim.version; }
    const min = info ? info.min : [-3, -3, 0];
    const max = info ? info.max : [3, 3, 2];
    let x0 = Math.min(min[0], -MIN_ROOM / 2), x1 = Math.max(max[0], MIN_ROOM / 2), y0 = Math.min(min[1], -MIN_ROOM / 2), y1 = Math.max(max[1], MIN_ROOM / 2), z1 = Math.max(max[2] + 2, MIN_HEIGHT);
    for (const s of sources) {
      x0 = Math.min(x0, s.position.x - 2); x1 = Math.max(x1, s.position.x + 2);
      y0 = Math.min(y0, s.position.y - 2); y1 = Math.max(y1, s.position.y + 2);
      z1 = Math.max(z1, s.position.z + 1.5);
    }
    const w = x1 - x0 + 2, d = y1 - y0 + 2, h = z1;                         // Huelle mit etwas Abstand um alles
    const floorArea = w * d;
    const shellArea = 2 * h * (w + d) + floorArea;                          // vier Waende + Decke
    const shell = state.shell / 100;
    floorColor.copy(sim.floor.material.color);
    const objArea = info ? info.area : 0;
    const total = shellArea + floorArea + objArea;
    const rho = [0, 0, 0];
    ["r", "g", "b"].forEach((c, i) => {
      const sum = shellArea * shell + floorArea * floorColor[c] + (info ? info.albedo[i] : 0);
      rho[i] = Math.min(0.95, sum / total);
    });
    return { area: total, rho };
  }

  /** Abstand des Spiegel-Strahls ueber der Flaeche (nie hinter die naechste Wand). */
  function offsetFor(s, hit) {
    const radius = hit.distance * Math.tan(Math.min(s.angle, 2.0) / 2) / Math.sqrt(s.rays);
    return Math.min(Math.max(0.5, Math.min(2.5, radius * 0.9)), hit.free * 0.5);
  }
  function refreshInfo() {
    if (infoVersion !== sim.version || !info) { info = sim.roomInfo ? sim.roomInfo() : null; infoVersion = sim.version; }
  }
  const sources = [];
  const centroid = new THREE.Vector3();
  const dirSum = new THREE.Vector3();
  const dirTmp = new THREE.Vector3();
  const tint = new THREE.Color();
  const viewInv = new THREE.Matrix4();
  /** Pro Bild (vor dem Zeichnen): Beleuchtung aus Modus, Einstellungen und Lichtquellen berechnen. Zeichnet nichts neu (Aenderungen kommen ueber sim.invalidate()). */
  function update() {
    sources.length = 0;
    for (const source of sim.lightSources) { const s = source(); if (s && s.lumens > 0) sources.push(s); }
    const work = mode !== "view" ? state.work / 100 : 0;
    const house = state.house / 100 * 0.6;
    hemi.intensity = work + house;
    sun.intensity = 1.4 * work;
    sim.renderer.toneMappingExposure = state.exposure / 100;
    sim.setHaze(state.haze / 100);                                        // Dunst: Dichte und Sichtbarkeit der Lichtkegel
    const boost = INDIRECT_BOOST * state.bounce / 100;
    // Spiegel-Strahlen (Metall/Spiegel) nur fuer Quellen, die so eine Flaeche treffen - die staerksten zuerst, begrenzt durch limits.maxSpecular (0 = unbegrenzt); der Vorrat waechst nur
    const specOf = (s) => { const h = s.hits[0]; return h.valid && boost > 0 ? (h.metalness > 0.5 ? h.metalness * (1 - 0.5 * h.roughness) : 0.04 * (1 - h.roughness)) : 0; };
    const ranked = [];
    sources.forEach((s, i) => { const v = specOf(s); if (v >= 0.08) ranked.push([v * s.candela, i]); });
    ranked.sort((a, b) => b[0] - a[0]);
    const maxSpecular = sim.limits.values.maxSpecular;
    const allowed = maxSpecular > 0 ? ranked.slice(0, maxSpecular) : ranked;
    if (allowed.length > pool.length) resizePool(Math.ceil(allowed.length / 2) * 2);
    const specSlot = new Map(allowed.map(([, i], k) => [i, k]));
    for (let k = allowed.length; k < pool.length; k++) { pool[k].specular.intensity = 0; if (pool[k].specular.castShadow) pool[k].specular.castShadow = false; }
    refreshInfo();
    if (info && info.area > 0) centroid.set((info.min[0] + info.max[0]) / 2, (info.min[1] + info.max[1]) / 2, Math.max(1, (info.min[2] + info.max[2]) / 2));
    else centroid.set(0, 0, 1);
    phi.setRGB(0, 0, 0);
    tint.setRGB(0, 0, 0);
    dirSum.set(0, 0, 0);
    let weightSum = 0;
    let patches = 0;
    sim.camera.updateMatrixWorld();
    viewInv.copy(sim.camera.matrixWorld).invert();
    const quota = Math.max(1, Math.floor(sim.bleed.pos.length / Math.max(1, sources.length)));     // Flecken je Lampe: das Budget gehoert allen, nicht den ersten zwei
    sources.forEach((s, i) => {
      phi.r += s.lumens * s.color.r; phi.g += s.lumens * s.color.g; phi.b += s.lumens * s.color.b;
      // beleuchtete Flaechen: Richtung (vom Raummittelpunkt aus gesehen) und Farbe des zurueckgeworfenen Lichts
      let valid = 0;
      for (let k = 0; k < s.rays; k++) if (s.hits[k].valid) valid++;
      const used = Math.max(1, Math.min(quota, valid));                               // so viele Flecken dieser Lampe werden im Shader gezeichnet (Mittelstrahl zuerst, dann gleichmaessig)
      const stride = valid / used;
      let seen = 0;
      let given = 0;
      for (let k = 0; k < s.rays; k++) {
        const h = s.hits[k];
        if (!h.valid) continue;
        const wanted = given < used && seen >= given * stride - 1e-6;                 // Flecken dieser Lampe, die einen Platz im Budget bekommen
        seen++;
        albedo.copy(h.color).multiplyScalar(1 - h.metalness);
        const share = s.lumens / s.rays;
        const w = share * (albedo.r * s.color.r + albedo.g * s.color.g + albedo.b * s.color.b) / 3;
        dirTmp.copy(h.point).sub(centroid);
        if (dirTmp.lengthSq() > 1e-6) { dirTmp.normalize(); dirSum.addScaledVector(dirTmp, w); }
        weightSum += w;
        tint.r += share * albedo.r * s.color.r; tint.g += share * albedo.g * s.color.g; tint.b += share * albedo.b * s.color.b;
        if (wanted && patches < sim.bleed.pos.length && state.bleed > 0) {                         // lokale Farbabstrahlung dieses beleuchteten Flecks (im Shader der Stage-Materialien)
          given++;
          const direct = Math.min(40, s.candela / Math.max(0.25, h.distance * h.distance));
          const radius = Math.max(0.4, h.distance * Math.tan(Math.min(s.angle, 2.0) / 2) / Math.sqrt(Math.min(s.rays, used + 0.5 * (s.rays - used))));
          const amp = BLEED_GAIN * (state.bleed / 100) * direct * Math.min(3, s.rays / used);
          tmp.copy(h.point).addScaledVector(h.normal, 0.05).applyMatrix4(viewInv);
          sim.bleed.pos[patches].set(tmp.x, tmp.y, tmp.z, radius);
          sim.bleed.col[patches].set(albedo.r * s.color.r * amp, albedo.g * s.color.g * amp, albedo.b * s.color.b * amp);
          patches += 1;
        }
      }
      // spiegelnd (Metall/Spiegel): der Mittelstrahl geht in Spiegelrichtung weiter; mit Schatten
      const hit = s.hits[0];
      const spec = specOf(s);
      const slotIndex = specSlot.get(i);
      const p = slotIndex !== undefined ? pool[slotIndex] : null;
      const on = !!p;
      if (p && p.specular.castShadow !== on) p.specular.castShadow = on;
      if (on) {
        tmp.copy(hit.point).addScaledVector(hit.normal, offsetFor(s, hit));
        reflected.copy(s.axis).addScaledVector(hit.normal, -2 * s.axis.dot(hit.normal));
        p.specular.position.copy(tmp);
        p.specular.target.position.copy(tmp).add(reflected);
        p.specular.target.updateMatrixWorld();
        p.specular.angle = Math.min(Math.PI / 2 * 0.98, s.angle / 2 * 1.15);
        p.specular.penumbra = 0.4;
        const tc = hit.metalness > 0.5 ? hit.color : albedo.setRGB(1, 1, 1);
        p.specular.color.setRGB(tc.r * s.color.r, tc.g * s.color.g, tc.b * s.color.b);
        p.specular.intensity = s.candela * spec;
      }
    });
    sim.bleed.count.value = patches;
    // Umgebungslicht: E = Phi * rho / (A (1 - rho)) je Farbkanal, mit Farbstich der beleuchteten Flaechen und Verlauf zu ihnen hin
    let avg = 0;
    if (sources.length && boost > 0) {
      const m = model(sources);
      const base = ["r", "g", "b"].map((c, i) => (phi[c] * m.rho[i] / (m.area * (1 - m.rho[i]))) * boost);
      const mean = (tint.r + tint.g + tint.b) / 3;
      const tone = mean > 1e-6 ? [tint.r / mean, tint.g / mean, tint.b / mean].map((v) => 1 + 0.35 * (Math.min(2.2, Math.max(0.35, v)) - 1)) : [1, 1, 1];
      const level = base.map((v, i) => Math.min(1.5, v * tone[i]));
      const f = weightSum > 0 ? Math.min(1, dirSum.length() / weightSum) : 0;       // 0 = von allen Seiten gleich, 1 = alles aus einer Richtung
      if (f > 0.01) bounce.position.copy(dirSum).normalize().multiplyScalar(10); else bounce.position.set(0, 0, 10);
      const g = GRADIENT * f;
      bounce.color.setRGB(level[0] * (1 + g), level[1] * (1 + g), level[2] * (1 + g));
      bounce.groundColor.setRGB(level[0] * (1 - g), level[1] * (1 - g), level[2] * (1 - g));
      avg = (level[0] + level[1] + level[2]) / 3;
    } else {
      bounce.color.setRGB(0, 0, 0);
      bounce.groundColor.setRGB(0, 0, 0);
    }
    ambient = avg;
    const scale = Math.min(1.5, (work + house + avg) * ENV_SHARE * state.reflect / 100);
    envScale = scale;
    const next = scale.toFixed(3);
    if (next !== key) { key = next; listeners.forEach((fn) => fn(scale)); }
  }
  sim.frameHooks.push(update);

  // ------------------------------------------------------------------------------------------ Abgleich mit dem Server
  let pushTimer = 0;
  function push() {
    clearTimeout(pushTimer);
    pushTimer = setTimeout(async () => {
      pushTimer = 0;
      try {
        await fetch("/api/sim-room", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ room: { ...state }, source: uid }) });
      } catch (err) { /* offline: bleibt lokal */ }
    }, 150);
  }
  function applyRemote(room) {
    if (!room || pushTimer) return;                                        // eigene, noch nicht gesendete Aenderung geht vor
    let changed = false;
    FIELDS.forEach((k) => { if (room[k] !== undefined && room[k] !== state[k]) { state[k] = room[k]; changed = true; } });
    if (changed) { applyHelpers(); paint(); sim.invalidate(); }
  }
  const onStage = (e) => {
    const { stage, source } = e.detail || {};
    if (stage && stage.room && source !== uid) applyRemote(stage.room);
  };
  document.addEventListener("sim-stage", onStage);

  function applyHelpers() {
    const on = mode !== "view" || state.helpers;
    (sim.helpers || []).forEach((o) => { o.visible = on; });
  }
  function change(field, value) {
    state[field] = value;
    if (field === "helpers") applyHelpers();
    paint();
    push();
    sim.invalidate();
  }

  // ------------------------------------------------------------------------------------------ Fenster
  const wrap = document.createElement("div");
  wrap.style.cssText = "display:inline-flex";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "sim3d__btn";
  button.dataset.act = "room";
  button.title = i18n("SIM3D_ROOM_TIP");
  button.setAttribute("aria-label", i18n("SIM3D_ROOM"));
  button.setAttribute("aria-pressed", "false");
  button.appendChild(Icons.svg("bulb"));
  const panel = document.createElement("div");
  panel.className = "sim3d__room";
  panel.hidden = true;
  wrap.append(button, panel);
  tools.insertBefore(wrap, tools.firstChild);

  const title = (k) => { const h = document.createElement("h4"); h.className = "sim3d__title"; h.textContent = i18n(k); return h; };
  const rows = {};
  function slider(id, labelKey, tipKey, max, min = 0) {
    const row = document.createElement("div");
    row.className = "sim3d__slider";
    const label = document.createElement("label");
    label.textContent = i18n(labelKey);
    label.title = i18n(tipKey);
    const range = document.createElement("input");
    range.type = "range";
    range.className = "sim3d__range";
    range.min = String(min);
    range.max = String(max);
    range.dataset.field = id;
    const value = document.createElement("span");
    value.className = "sim3d__slider-value";
    range.addEventListener("input", () => change(id, Number(range.value)));
    row.append(label, range, value);
    rows[id] = { row, range, value };
    return row;
  }
  const hint = document.createElement("p");
  hint.className = "sim3d__room-hint";
  hint.textContent = i18n("SIM3D_ROOM_HINT");
  const resetButton = document.createElement("button");
  resetButton.type = "button";
  resetButton.className = "sim3d__btn sim3d__btn--wide sim3d__btn--danger sim3d__room-reset";
  resetButton.dataset.act = "room-reset";
  resetButton.append(Icons.svg("refresh"), document.createTextNode(i18n("SIM3D_ROOM_RESET")));
  resetButton.title = i18n("SIM3D_ROOM_RESET_TIP");
  resetButton.addEventListener("click", async () => {
    const ok = await window._askLayoutConfirm({ title: i18n("SIM3D_ROOM_RESET_TITLE"), body: i18n("SIM3D_ROOM_RESET_BODY"), confirmKey: "SIM3D_ROOM_RESET" });
    if (!ok) return;
    FIELDS.filter((f) => f !== "helpers").forEach((f) => { state[f] = DEFAULTS[f]; });
    paint();
    push();
    sim.invalidate();
  });
  const helpersRow = document.createElement("div");
  helpersRow.className = "sim3d__room-row";
  const helpersLabel = document.createElement("label");
  helpersLabel.textContent = i18n("SIM3D_HELPERS");
  helpersLabel.title = i18n("SIM3D_HELPERS_TIP");
  const helpers = document.createElement("input");
  helpers.type = "checkbox";
  helpers.dataset.field = "helpers";
  helpers.addEventListener("change", () => change("helpers", helpers.checked));
  helpersLabel.addEventListener("click", () => helpers.click());
  helpersRow.append(helpersLabel, helpers);
  const qualityRow = document.createElement("div");
  qualityRow.className = "sim3d__room-row";
  const qualityLabel = document.createElement("label");
  qualityLabel.textContent = i18n("SIM3D_QUALITY_LABEL");
  qualityLabel.title = i18n("SIM3D_QUALITY_TIP");
  const qualitySelect = document.createElement("select");
  qualitySelect.className = "sim3d__select";
  qualitySelect.dataset.field = "quality";
  [["auto", "SIM3D_QUALITY_AUTO"], ["low", "SIM3D_QUALITY_LOW"], ["medium", "SIM3D_QUALITY_MEDIUM"], ["high", "SIM3D_QUALITY_HIGH"]].forEach(([id, k]) => {
    const o = document.createElement("option");
    o.value = id;
    o.textContent = i18n(k);
    qualitySelect.appendChild(o);
  });
  qualitySelect.addEventListener("change", () => sim.quality.setSetting(qualitySelect.value));
  qualityRow.append(qualityLabel, qualitySelect);
  // Grenzen des Lichtvorrats (je Geraet): 0 = unbegrenzt, es zaehlt dann nur, was die Grafikkarte kann
  const limitRows = {};
  const limitInfo = document.createElement("p");
  limitInfo.className = "sim3d__room-hint";
  function limitRow(key, labelKey, tipKey) {
    const row = document.createElement("div");
    row.className = "sim3d__room-row";
    const label = document.createElement("label");
    label.textContent = i18n(labelKey);
    label.title = i18n(tipKey);
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.className = "sim3d__select";
    input.style.flex = "0 0 5.5rem";
    input.style.width = "5.5rem";
    input.dataset.field = key;
    input.addEventListener("change", () => { sim.limits.set(key, input.value); paintLimits(); });
    row.append(label, input);
    limitRows[key] = input;
    return row;
  }
  function paintLimits() {
    const v = sim.limits.values;
    for (const key of Object.keys(limitRows)) if (document.activeElement !== limitRows[key]) limitRows[key].value = String(v[key]);
    const info = sim.limits.info || {};
    limitInfo.textContent = info.lights ? i18n("SIM3D_LIMIT_INFO").replace("{lights}", info.lights).replace("{shadows}", info.shadows).replace("{placed}", info.placed).replace("{gpuLights}", info.gpuLights).replace("{gpuShadows}", info.gpuShadows) : "";
  }
  const limitsReset = document.createElement("button");
  limitsReset.type = "button";
  limitsReset.className = "sim3d__btn sim3d__btn--wide";
  limitsReset.dataset.act = "limits-reset";
  limitsReset.textContent = i18n("SIM3D_LIMITS_RESET");
  limitsReset.addEventListener("click", () => { sim.limits.reset(); paintLimits(); });
  sim.limits.listeners.push(() => paintLimits());
  panel.append(
    title("SIM3D_ROOM_LIGHTING"),
    slider("work", "SIM3D_WORKLIGHT", "SIM3D_WORKLIGHT_TIP", 100),
    slider("house", "SIM3D_HOUSE", "SIM3D_HOUSE_TIP", 100),
    title("SIM3D_ROOM_BOUNCE"),
    slider("bounce", "SIM3D_BOUNCE", "SIM3D_BOUNCE_TIP", 300),
    slider("shell", "SIM3D_SHELL", "SIM3D_SHELL_TIP", 95),
    slider("bleed", "SIM3D_BLEED", "SIM3D_BLEED_TIP", 300),
    title("SIM3D_ROOM_IMAGE"),
    slider("reflect", "SIM3D_REFLECT", "SIM3D_REFLECT_TIP", 200),
    slider("exposure", "SIM3D_EXPOSURE", "SIM3D_EXPOSURE_TIP", 200, 50),
    slider("haze", "SIM3D_HAZE", "SIM3D_HAZE_TIP", 100),
    helpersRow, qualityRow,
    title("SIM3D_LIMITS"),
    limitRow("maxLights", "SIM3D_LIMIT_LIGHTS", "SIM3D_LIMIT_LIGHTS_TIP"),
    limitRow("maxShadows", "SIM3D_LIMIT_SHADOWS", "SIM3D_LIMIT_SHADOWS_TIP"),
    limitRow("maxSpecular", "SIM3D_LIMIT_SPECULAR", "SIM3D_LIMIT_SPECULAR_TIP"),
    limitInfo, limitsReset,
    resetButton,
    hint,
  );

  function paint() {
    FIELDS.filter((f) => f !== "helpers").forEach((f) => { rows[f].range.value = String(state[f]); rows[f].value.textContent = state[f] + " %"; });
    rows.work.row.hidden = mode === "view";                                // das Arbeitslicht gibt es nur im Baumodus
    helpers.checked = !!state.helpers;
    qualitySelect.value = sim.quality.setting;
    paintLimits();
  }
  const onQuality = () => { qualitySelect.value = sim.quality.setting; };
  sim.quality.listeners.push(onQuality);

  const toggle = (open) => {
    panel.hidden = !open;
    button.setAttribute("aria-pressed", String(open));
    button.classList.toggle("sim3d__btn--on", open);
    if (open) { paint(); fit(); }
  };
  /** Hoehe des Fensters an das Panel anpassen (es endet am unteren Rand des Panels; was nicht passt, scrollt). */
  function fit() {
    if (panel.hidden) return;
    panel.style.maxHeight = "";
    const bottom = host.getBoundingClientRect().bottom;
    const top = panel.getBoundingClientRect().top;
    panel.style.maxHeight = Math.max(140, Math.floor(bottom - top - 8)) + "px";
  }
  const fitObserver = new ResizeObserver(fit);
  fitObserver.observe(host);
  button.addEventListener("click", () => toggle(panel.hidden));
  const onKey = (e) => { if (e.key === "Escape" && !panel.hidden) { toggle(false); e.stopPropagation(); } };
  host.addEventListener("keydown", onKey);
  [wrap, panel].forEach((n) => n.addEventListener("dblclick", (e) => e.stopPropagation()));

  applyHelpers();
  paint();
  if (window.OCSimStages && window.OCSimStages.current && window.OCSimStages.current.room) applyRemote(window.OCSimStages.current.room);       // erst jetzt: applyRemote braucht das fertige Fenster

  return {
    get work() { return state.work; },
    get envScale() { return envScale; },
    get ambient() { return ambient; },
    get state() { return { ...state }; },
    get pool() { return pool; },
    setMode(next) { mode = next; applyHelpers(); paint(); sim.invalidate(); },
    onEnv(fn) { listeners.push(fn); },
    update,
    dispose() {
      document.removeEventListener("sim-stage", onStage);
      fitObserver.disconnect();
      host.removeEventListener("keydown", onKey);
      clearTimeout(pushTimer);
      const i = sim.frameHooks.indexOf(update);
      if (i >= 0) sim.frameHooks.splice(i, 1);
      const q = sim.quality.listeners.indexOf(onQuality);
      if (q >= 0) sim.quality.listeners.splice(q, 1);
      resizePool(0);
      sim.scene.remove(hemi, sun, bounce);
      wrap.remove();
    },
  };
}

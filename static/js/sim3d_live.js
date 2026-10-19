/* 3D-Simulation: LIVE-LICHT der Scheinwerfer. Die DMX-Werte der Show (Dimmer, Farbe, Pan/Tilt, Zoom) kommen vom Server als "fixtures_live" (abstrakte Werte je Scheinwerfer, aus dem DMX-Puffer;
 * app.js merkt den letzten Stand in window.__fixturesLive und meldet Aenderungen als Ereignis "fixtures-live-values"); hier wird daraus pro Bild gezeichnet:
 *   - Farbraeder (z. B. Color1): das rohe DMX-Byte kommt als "wheels" im Live-Strom; mit den Slots des Typs (/api/fixture-types/<Typ>/wheels, Bereiche DMX von-bis, Filterfarbe) ergibt
 *     sich die Farbe des gewaehlten Slots, die mit der RGB-/CMY-Farbe multipliziert wird (offen/weiss = unveraendert);
 *   - Shutter/Strobe: das rohe Byte (Shutter1) wird mit den Bereichen des Typs (/api/fixture-types/<Typ>/shutter: offen, Strobe, Puls, Zufall; Frequenz aus der Datei, sonst 1-12 Hz je nach
 *     Stellung im Bereich) zu einem Takt: das Licht blitzt (Gate), Kegel, Linse, Licht und Schatten folgen;
 *   - Fokus: aus dem Fokus-Wert und der Entfernung zur getroffenen Flaeche ergibt sich die Unschaerfe des Randes (Linsenradius x |1/Entfernung - 1/Schaerfeebene|, bezogen auf den
 *     halben Oeffnungswinkel): stimmt die Schaerfeebene mit der Wurfweite ueberein, ist der Rand scharf. Die Schaerfeebene kommt aus dem Bereich der Fokus-Funktion der Datei, wenn er in
 *     Metern angegeben ist, sonst gilt 2 ... 30 m ueber den Kanal (logarithmisch); ohne Fokus-Kanal bleibt die Kante mittelweich;
 *   - Pan/Tilt: die beweglichen Teile des 3D-Modells (Achsen aus der GDTF) drehen weich nach (Zeitkonstante, damit auch 10-25 Meldungen pro Sekunde fluessig aussehen);
 *   - Dimmer x Grand Master x Farbe: Leuchten der Linse und sichtbarer Lichtkegel (Nebel) an jeder Linse des Modells, in der Farbe des Scheinwerfers;
 *   - Zoom: Oeffnungswinkel (Bereich aus der GDTF), sonst der Winkel des Modells;
 *   - Licht auf den Flaechen: ein fester Vorrat an SpotLights (je Qualitaetsstufe, die ersten mit Schatten) wird jedes Bild den hellsten Scheinwerfern zugeteilt (stabil, damit nichts
 *     flackert); jeder zugeteilte Scheinwerfer ist auch eine Lichtquelle fuer das Raumlicht (sim.lightSources, siehe sim3d_room.js: zurueckgeworfenes Licht, Farbabstrahlung).
 * Lichtkegel: JEDER leuchtende Scheinwerfer mit einem Platz im Vorrat bekommt den volumetrischen Kegel (sim3d_spot.js: der Nebel wird entlang des Sehstrahls abgetastet; Tiefenbild der Buehne:
 * Waende und Gegenstaende unterbrechen den Nebel). Plaetze mit Schattenkarte werden zusaetzlich von deren Schatten geschnitten und enden hinter der fernsten Trefferflaeche (uCap); Plaetze
 * ohne Schattenkarte enden an den Flaechen, die die Strahlproben getroffen haben (uUseHits). So sehen gleich eingestellte Geraete gleich aus und kein Nebel geht durch eine Wand. Nur auf
 * Stufe 0 (Software) gibt es statt dessen den einfachen Fresnel-Kegel (additiv, tiefengetestet).
 * Gezeichnet wird nur, solange sich etwas aendert (sim.keepAlive), sonst ruht die Darstellung. */
import * as THREE from "three";
import { makeConeMaterial as makeVolumeMaterial } from "/static/js/sim3d_spot.js";

const deg = THREE.MathUtils.degToRad;
const BASE_CANDELA = 240;                 // Lichtstaerke bei voller Helligkeit (wie der fruehere Test-Scheinwerfer)
const BEAM_LENGTH = 20;                   // sichtbare Kegellaenge (Meter)
const MAX_BEAMS = 24;                     // Linsen je Geraet (LED-Leisten haben viele Pixel)
// Lichtvorrat: so viele SpotLights, wie Scheinwerfer platziert sind (in 4er-Schritten, damit nicht bei jedem neuen Geraet neu uebersetzt wird), begrenzt nur durch limits.values (0 = unbegrenzt) und
// die Grafikkarte (Texturen fuer die Schattenkarten, Shader-Konstanten) - nie durch die Qualitaetsstufe (die bestimmt nur Aufloesung, Schattenkarten-Groesse und Abtastschritte).
const TEXTURE_RESERVE = 4;                 // Textureinheiten, die nicht fuer Schattenkarten zur Verfuegung stehen (Umgebungs-Karte u. a.)
const VECTOR_BASE = 220;                   // geschaetzte Shader-Konstanten ohne Lichter; je Licht ca. 8, je Schattenlicht weitere 12
const MAX_MAPS = 3;                         // davon mit Lichtkarte fuer Gobo/Prisma (die ersten Schattenplaetze; jede Karte braucht eine Textureinheit mehr)
const STEPS = [8, 10, 14, 18, 24, 32];     // Abtastschritte des volumetrischen Nebels je Qualitaetsstufe
const MAX_RAYS = 9;
const MAP_SIZE = 640;                       // Kantenlaenge der Lichtkarte (Gobo/Prisma) in Pixeln
const MAX_SPIN = 1;                         // schnellste Drehung ohne Angabe in der Datei (Umdrehungen pro Sekunde)
const MAX_COPIES = 96;                      // Kopien aller Prismen zusammen
const SHAKE_HZ = 5;                         // Gobo-Wackeln
const SHAKE_DEG = 9;
const DEFAULT_PENUMBRA = 0.35;             // Kantenweichheit ohne Fokus-Kanal
const STROBE_DUTY = 0.35;                  // heller Anteil einer Strobe-Periode
const MIN_PENUMBRA = 0.004;                // schaerfste Kante (0 geht nicht: smoothstep mit gleichen Raendern ist undefiniert)
const FOCUS_NEAR = 2;                       // Schaerfeebene bei Fokus 0 % bzw. 100 % (Meter), wenn die Datei keine Meterangabe hat
const FOCUS_FAR = 30;
const LENS_OFF = new THREE.Color(0.55, 0.55, 0.57);                 // Linse im ausgeschalteten Zustand
const TAU = { dim: 0.05, color: 0.06, axis: 0.09, zoom: 0.12 };      // Zeitkonstanten der Glaettung (Sekunden)

/** Fresnel-Kegel wie in der Vorlage: Spitze bei z = 0, zeigt nach -z, weicher Rand, zur Ferne ausgeblendet. */
function makeBeamMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(1, 1, 1) }, uStrength: { value: 0 }, uSoft: { value: 1.7 }, uSharp: { value: 0 } },
    vertexShader: `
      varying vec3 vN; varying vec3 vV; varying float vT;
      void main() {
        vT = clamp(-position.z, 0.0, 1.0);
        vN = normalize(normalMatrix * normal);
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vV = -mv.xyz;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      uniform vec3 uColor; uniform float uStrength; uniform float uSoft; uniform float uSharp;
      varying vec3 vN; varying vec3 vV; varying float vT;
      void main() {
        float f = abs(dot(normalize(vN), normalize(vV)));
        float edge = mix(pow(f, uSoft), smoothstep(0.0, 0.05, f), uSharp);          // scharf gestellt: harte Kante an der Silhouette des Kegels
        float along = pow(clamp(1.0 - vT, 0.0, 1.0), 1.1) * smoothstep(0.0, 0.03, vT);
        float x = edge * along * uStrength;
        gl_FragColor = vec4(uColor * (0.7 * (1.0 - exp(-x / 0.7))), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  });
}

/** ctx: {entries(): Map der platzierten Scheinwerfer (entry.beams, entry.built, entry.axes, entry.group, entry.data), targets(): Koerper fuer Lichtstrahl-Treffer, haze(): Nebel 0..1} */
export function createLive(sim, ctx) {
  const coneGeometry = (() => {
    const g = new THREE.CylinderGeometry(1, 0.0001, 1, 40, 1, true);
    g.rotateX(-Math.PI / 2);                 // Achse Y -> -Z (breites Ende unten)
    g.translate(0, 0, -0.5);                 // Spitze bei 0, breites Ende (Radius 1) bei z = -1
    return g;
  })();
  const states = new Map();                  // Scheinwerfer-Id -> geglaettete Werte, Kegel
  const tmpPos = new THREE.Vector3();
  const tmpQuat = new THREE.Quaternion();
  const tmpScale = new THREE.Vector3();
  const tmpDir = new THREE.Vector3();
  const tmpUp = new THREE.Vector3();
  const tmpColor = new THREE.Color();
  const raycaster = new THREE.Raycaster();
  const normalMatrix = new THREE.Matrix3();
  const basisU = new THREE.Vector3();
  const basisV = new THREE.Vector3();
  const rayDir = new THREE.Vector3();
  const probeFrom = new THREE.Vector3();
  let last = performance.now();
  let destroyed = false;

  // ------------------------------------------------------------------------------------------ volumetrischer Kegel (Plaetze mit Schatten)
  const fullscreen = (() => {                                      // ein Dreieck ueber den ganzen Bildschirm: jedes Pixel rechnet den Schnitt seines Sehstrahls mit dem Kegel
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
    return g;
  })();
  let volumes = [];                                                // je Schattenplatz {mesh, material}
  let depthTarget = null;                                          // Tiefenbild der Buehne (halbe Aufloesung, ab Stufe 4 voll): der Nebel endet an sichtbaren Flaechen
  const depthMaterial = new THREE.MeshBasicMaterial({ colorWrite: false });
  const bufferSize = new THREE.Vector2();
  function buildVolumes(count) {
    volumes.forEach((v) => { sim.scene.remove(v.mesh); v.material.dispose(); });
    volumes = Array.from({ length: count }, () => {
      const material = makeVolumeMaterial();
      const mesh = new THREE.Mesh(fullscreen, material);
      mesh.frustumCulled = false;
      mesh.renderOrder = 3;
      mesh.visible = false;
      sim.scene.add(mesh);
      return { mesh, material };
    });
  }
  function depthPass() {
    const renderer = sim.renderer;
    renderer.getDrawingBufferSize(bufferSize);
    const scale = sim.quality.level >= 4 ? 1 : 0.5;
    const w = Math.max(1, Math.round(bufferSize.x * scale));
    const h = Math.max(1, Math.round(bufferSize.y * scale));
    if (!depthTarget || depthTarget.width !== w || depthTarget.height !== h) {
      if (depthTarget) { depthTarget.depthTexture.dispose(); depthTarget.dispose(); }
      depthTarget = new THREE.WebGLRenderTarget(w, h, { depthBuffer: true, depthTexture: new THREE.DepthTexture(w, h), minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false });
    }
    ctx.targets().forEach((m) => m.layers.enable(1));              // Ebene 1 = feste Koerper (Buehne + Boden)
    const scene = sim.scene;
    const camera = sim.camera;
    const saved = { target: renderer.getRenderTarget(), mask: camera.layers.mask, override: scene.overrideMaterial, background: scene.background, fog: scene.fog, shadows: renderer.shadowMap.enabled };
    camera.layers.set(1);
    scene.overrideMaterial = depthMaterial;
    scene.background = null;
    scene.fog = null;
    renderer.shadowMap.enabled = false;                             // verbraucht nicht die ausstehende Schattenkarte
    renderer.setRenderTarget(depthTarget);
    renderer.clear();
    renderer.render(scene, camera);
    renderer.setRenderTarget(saved.target);
    renderer.shadowMap.enabled = saved.shadows;
    scene.fog = saved.fog;
    scene.background = saved.background;
    scene.overrideMaterial = saved.override;
    camera.layers.mask = saved.mask;
    volumes.forEach((v) => {
      const u = v.material.uniforms;
      u.uDepth.value = depthTarget.depthTexture;
      u.uHasDepth.value = 1;
      u.uProjInv.value.copy(camera.projectionMatrixInverse);
      u.uRes.value.copy(bufferSize);
    });
  }
  const wheelCache = new Map();                                    // Typ -> Promise<Raeder des Typs>
  function loadWheels(typeId) {
    if (!typeId) return Promise.resolve([]);
    if (!wheelCache.has(typeId)) {
      wheelCache.set(typeId, fetch("/api/fixture-types/" + encodeURIComponent(typeId) + "/wheels").then((res) => (res.ok ? res.json() : [])).catch(() => []));
    }
    return wheelCache.get(typeId);
  }
  const isOpenSlot = (slot) => !slot || /^(open|offen|white|weiss|wei(ss|ß))/i.test(String(slot.name || ""));
  function findSlot(slots, value) {
    let best = null;
    let bestDistance = Infinity;
    for (const slot of slots) {
      if (value >= slot.dmx_from && value <= slot.dmx_to) return slot;
      const distance = Math.min(Math.abs(value - slot.dmx_from), Math.abs(value - slot.dmx_to));
      if (distance < bestDistance) { best = slot; bestDistance = distance; }
    }
    return bestDistance <= 2 ? best : null;
  }
  /** Farbfilter der Farbraeder aus den rohen Bytes: [r, g, b] 0..1 (1 = offen). */
  function wheelTint(entry, live, out) {
    out[0] = out[1] = out[2] = 1;
    if (!live || !live.wheels || !entry.wheelData) return;
    for (const wheel of entry.wheelData) {
      if (wheel.type !== "color") continue;
      const value = live.wheels[wheel.attribute_name];
      if (value === undefined || value === null) continue;
      const slot = findSlot(wheel.slots || [], value);
      if (!slot || isOpenSlot(slot) || !Array.isArray(slot.color)) continue;
      for (let i = 0; i < 3; i++) out[i] *= slot.color[i] / 255;
    }
  }
  const tint = [1, 1, 1];

  // ------------------------------------------------------------------------------------------ Gobo und Prisma: Muster in der Lichtkarte (SpotLight.map) des Platzes
  // Die Karte bildet den Oeffnungswinkel des Lichts auf ein Quadrat ab (wie die Schattenkarte): das Gobo fuellt den Lichtkreis, beim Prisma liegen die Kopien um die Achse und der
  // Winkel des Lichts wird entsprechend groesser. Jede Aenderung zeichnet die Karte neu (Canvas); die Flaechen (SpotLight.map) und der Nebel (sim3d_spot.js) lesen dieselbe Karte.
  const beamfxCache = new Map();                                   // Typ -> Promise<{Kanalattribut: {role, type, wheel, ranges}}>
  function loadBeamfx(typeId) {
    if (!typeId) return Promise.resolve({});
    if (!beamfxCache.has(typeId)) {
      beamfxCache.set(typeId, fetch("/api/fixture-types/" + encodeURIComponent(typeId) + "/beamfx").then((res) => (res.ok ? res.json() : {})).catch(() => ({})));
    }
    return beamfxCache.get(typeId);
  }
  let imageIds = 0;
  const imageCache = new Map();                                    // Bild-URL -> {id, img, ready}
  function imageFor(url) {
    let rec = imageCache.get(url);
    if (!rec) {
      rec = { id: ++imageIds, img: new Image(), ready: false };
      rec.img.onload = () => { rec.ready = true; sim.keepAlive(); };
      rec.img.src = url;
      imageCache.set(url, rec);
    }
    return rec;
  }
  const rangeAt = (ranges, v) => ranges.find((r) => v >= r.from && v <= r.to) || null;
  const lerp = (a, b, f) => a + (b - a) * f;
  function wheelFor(entry, attribute, channel) {
    const wheels = entry.wheelData || [];
    return wheels.find((w) => w.type === channel.type && w.name === channel.wheel) || wheels.find((w) => w.attribute_name === attribute) || null;
  }
  /** Drehwinkel (Grad) eines Rads aus seinem Dreh-/Positionskanal (gleiches Rad, gleiche Art): Position = Winkel, Dauerdrehung = Winkel waechst (Grad/s aus der Datei, sonst
   *  0-127 Winkel 0-360, 128-189 vorwaerts schnell -> langsam, 190-193 Stopp, 194-255 rueckwaerts langsam -> schnell bis MAX_SPIN). Setzt out.moving, solange sich etwas dreht. */
  function spinOf(entry, st, channel, bytes, dt, out) {
    for (const [attribute, ch] of Object.entries(entry.beamfx)) {
      if (ch.role !== "spin" || ch.type !== channel.type || ch.wheel !== channel.wheel) continue;
      const v = bytes[attribute];
      if (v === undefined || v === null) continue;
      const r = rangeAt(ch.ranges, v);
      if (!r) continue;
      const frac = (v - r.from) / Math.max(r.to - r.from, 1);
      const angles = st.fx.angle;
      let speed = 0;                                               // Umdrehungen pro Sekunde
      if (r.kind === "selectspin") {
        if (v < 128) angles[attribute] = (v / 127) * 360;
        else if (v < 190) speed = (1 - (v - 128) / 61) * MAX_SPIN;          // 128-189 vorwaerts, schnell -> langsam
        else if (v >= 194) speed = (-(v - 194) / 61) * MAX_SPIN;            // 194-255 rueckwaerts, langsam -> schnell (190-193 Stopp)
      } else if (r.kind === "index") {
        angles[attribute] = Math.abs(r.phys[1] - r.phys[0]) > 1.5 ? lerp(r.phys[0], r.phys[1], frac) : frac * 360;
      } else {
        speed = Math.max(-3, Math.min(3, lerp(r.phys[0], r.phys[1], frac) / 360));                           // Datei: Grad pro Sekunde
      }
      if (speed) { angles[attribute] = ((angles[attribute] || 0) + speed * 360 * dt) % 360; out.moving = true; }
      return angles[attribute] || 0;
    }
    return 0;
  }
  /** Gobo-Slot eines durchlaufenden Rads ("gobowheel rotation"): die Gobos des Rads nacheinander (Geschwindigkeit aus der Datei, sonst 0,5-5 Slots/s ueber den Bereich). */
  function scrollSlot(wheel, r, v, st, attribute, dt, out) {
    const list = wheel.slots.filter((s) => s.image && !isOpenSlot(s) && s.index !== r.slot);
    if (!list.length) return null;
    const frac = (v - r.from) / Math.max(r.to - r.from, 1);
    const p0 = r.phys[0];
    const p1 = r.phys[1];
    let rate;
    if (p0 === 0 && p1 === 0) rate = 0;                            // Stopp
    else if (Math.max(Math.abs(p0), Math.abs(p1)) > 1.5) rate = Math.sign(lerp(p0, p1, frac)) * Math.max(0.3, Math.min(6, Math.abs(lerp(p0, p1, frac)) / 20));
    else rate = 0.5 + 4.5 * frac;
    const scroll = st.fx.scroll;
    const n = list.length;
    scroll[attribute] = (((scroll[attribute] || 0) + rate * dt) % n + n) % n;
    if (rate) out.moving = true;
    return list[Math.floor(scroll[attribute]) % n];
  }
  const facetsOf = (name) => { const m = /(\d+)\s*[- ]?\s*(fold|facet)/i.exec(String(name || "")); return m ? +m[1] : 0; };
  /** Muster aus den rohen Bytes: {gobos: [{url, angle}], prism: {layers: [{n, linear, angle}], angle} | null} oder null (alles offen). Mehrere aktive Prismen hintereinander: jede Kopie des ersten wird vom zweiten noch einmal vervielfacht. */
  function resolvePattern(entry, st, live, dt, t, out) {
    const bytes = live && live.wheels;
    if (!bytes || !entry.beamfx || !entry.wheelData) return null;
    if (!st.fx) st.fx = { angle: {}, scroll: {} };
    const gobos = [];
    const prisms = [];
    for (const [attribute, ch] of Object.entries(entry.beamfx)) {
      if (ch.role !== "select") continue;
      const v = bytes[attribute];
      if (v === undefined || v === null) continue;
      const r = rangeAt(ch.ranges, v);
      if (!r) continue;
      const wheel = wheelFor(entry, attribute, ch);
      if (ch.type === "gobo") {
        if (!wheel) continue;
        const slot = r.kind === "scroll" ? scrollSlot(wheel, r, v, st, attribute, dt, out) : wheel.slots.find((s) => s.index === r.slot);
        if (!slot || isOpenSlot(slot) || !slot.image) continue;
        let angle = spinOf(entry, st, ch, bytes, dt, out);
        if (r.kind === "shake") { angle += Math.sin(t * Math.PI * 2 * SHAKE_HZ) * SHAKE_DEG; out.moving = true; }
        gobos.push({ url: slot.image, angle });
      } else if (!isOpenSlot(r)) {
        const slot = wheel && (wheel.slots.find((s) => s.index === r.slot) || wheel.slots[0]);
        prisms.push({ n: Math.max(2, (slot && slot.facets) || facetsOf(r.name) || 3), linear: /line/i.test((wheel ? wheel.name : "") + " " + r.name), angle: spinOf(entry, st, ch, bytes, dt, out) });
      }
    }
    let copies = 1;
    const layers = prisms.filter((layer) => (copies *= layer.n) <= MAX_COPIES);                       // zu viele Kopien: weitere Prismen weglassen
    const prism = layers.length ? { layers, angle: layers.reduce((sum, layer) => sum + layer.angle, 0) } : null;
    return gobos.length || prism ? { gobos, prism } : null;
  }
  /** Lage der Prismen-Kopien in Strahlradien (Mittelpunkte) und Ausdehnung des Musters (Abstand des aeussersten Mittelpunkts). */
  function prismRing(layer) {
    const a0 = deg(layer.angle);
    const centers = [];
    let extent;
    if (layer.linear) {
      const spacing = 1.3;
      extent = ((layer.n - 1) / 2) * spacing;
      for (let i = 0; i < layer.n; i++) { const x = (i - (layer.n - 1) / 2) * spacing; centers.push([x * Math.cos(a0), x * Math.sin(a0)]); }
    } else {
      extent = Math.min(2.4, Math.max(1.1, 0.58 / Math.sin(Math.PI / layer.n)));            // viele Facetten: dichter Ring, die Kopien ueberlappen
      for (let i = 0; i < layer.n; i++) { const a = a0 + (i / layer.n) * Math.PI * 2; centers.push([extent * Math.cos(a), extent * Math.sin(a)]); }
    }
    return { centers, extent };
  }
  function prismLayout(prism) {
    let centers = [[0, 0]];
    let extent = 0;
    for (const layer of prism.layers) {
      const ring = prismRing(layer);
      const next = [];
      for (const a of centers) for (const b of ring.centers) next.push([a[0] + b[0], a[1] + b[1]]);
      centers = next;
      extent += ring.extent;
    }
    return { centers, extent };
  }
  const maps = [];                                                 // je Platz mit Schatten: {canvas, ctx, tex, key}
  const scratchGobo = document.createElement("canvas");            // Zwischenspeicher: ein Gobo bzw. die Kopie des Musters
  const scratchMask = document.createElement("canvas");
  function makeMap() {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = MAP_SIZE;
    const ctx2 = canvas.getContext("2d");
    ctx2.fillStyle = "#fff";
    ctx2.fillRect(0, 0, MAP_SIZE, MAP_SIZE);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return { canvas, ctx: ctx2, tex, key: "open" };
  }
  function clearMap(rec) {
    if (rec.key === "open") return;
    rec.ctx.globalCompositeOperation = "source-over";
    rec.ctx.fillStyle = "#fff";
    rec.ctx.fillRect(0, 0, MAP_SIZE, MAP_SIZE);
    rec.key = "open";
    rec.tex.needsUpdate = true;
  }
  /** Das Gobo-Bild aufrecht, auf die Groesse gebracht, nachgeschaerft (Kontrast) und weichgezeichnet - nur neu bei anderer Groesse/Unschaerfe, nicht bei jeder Drehung. */
  function filteredGobo(rec, size, blur, contrast, hasFilter) {
    const key = size + "|" + blur + "|" + contrast;
    if (!rec.filt) rec.filt = { key: "", canvas: document.createElement("canvas") };
    const f = rec.filt;
    if (f.key !== key) {
      f.canvas.width = f.canvas.height = size;
      const fc = f.canvas.getContext("2d");
      fc.fillStyle = "#000";
      fc.fillRect(0, 0, size, size);
      if (hasFilter) fc.filter = "contrast(" + contrast + ") blur(" + blur + "px)";
      fc.drawImage(rec.img, 0, 0, size, size);
      fc.filter = "none";
      f.key = key;
    }
    return f.canvas;
  }
  /** Muster in die Karte zeichnen. penumbra = Unschaerfe (Fokus): weichzeichnen, scharf gestellt wird die Kante der (kleinen) Gobo-Bilder nachgeschaerft. */
  function paintMap(rec, pattern, penumbra, tanBeam, tanOuter) {
    const S = MAP_SIZE;
    const R = S / 2;
    const prism = pattern.prism;
    const layout = prism ? prismLayout(prism) : null;
    const rBeam = Math.max(8, R * Math.min(1, tanBeam / tanOuter));
    const blur = Math.round(Math.min(rBeam * 0.35, penumbra * rBeam * 0.55) * 2) / 2;
    const contrast = Math.round((1 + 3 * (1 - Math.min(1, penumbra / 0.12))) * 4) / 4;
    const images = pattern.gobos.map((g) => ({ rec: imageFor(g.url), angle: g.angle }));
    const key = [images.map((g) => g.rec.id + (g.rec.ready ? "" : "!") + ":" + Math.round(g.angle)).join(","), prism ? prism.layers.map((layer) => [layer.n, layer.linear ? 1 : 0, Math.round(layer.angle)].join("/")).join("+") : "-", blur, contrast, Math.round(rBeam)].join("|");
    if (key === rec.key) return;
    rec.key = key;
    const size = Math.max(16, Math.ceil(2 * rBeam));
    if (scratchGobo.width !== size) { scratchGobo.width = scratchGobo.height = size; }
    if (scratchMask.width !== size) { scratchMask.width = scratchMask.height = size; }
    const g = scratchGobo.getContext("2d");
    const m = scratchMask.getContext("2d");
    const hasFilter = "filter" in g;
    // 1) das Muster eines Strahls (Gobos uebereinander multipliziert; ohne Gobo ein heller Kreis)
    g.globalCompositeOperation = "source-over";
    g.filter = "none";
    if (images.length) {
      g.fillStyle = "#fff";
      g.fillRect(0, 0, size, size);
      for (const item of images) {
        if (!item.rec.ready) continue;
        m.globalCompositeOperation = "source-over";
        m.fillStyle = "#000";
        m.fillRect(0, 0, size, size);
        m.save();
        m.translate(size / 2, size / 2);
        m.rotate(deg(item.angle));
        m.drawImage(filteredGobo(item.rec, size, blur, contrast, hasFilter), -size / 2, -size / 2);
        m.restore();
        g.globalCompositeOperation = "multiply";
        g.drawImage(scratchMask, 0, 0);
        g.globalCompositeOperation = "source-over";
      }
    } else {
      g.fillStyle = "#000";
      g.fillRect(0, 0, size, size);
      if (hasFilter) g.filter = "blur(" + blur + "px)";
      g.fillStyle = "#fff";
      g.beginPath();
      g.arc(size / 2, size / 2, size / 2 - blur * 1.5 - 1, 0, Math.PI * 2);
      g.fill();
      g.filter = "none";
    }
    // 2) in die Karte: ein Strahl oder die Kopien des Prismas (jede Kopie dreht sich mit dem Prisma, die Helligkeit teilt sich auf)
    const c = rec.ctx;
    c.globalCompositeOperation = "source-over";
    c.fillStyle = "#000";
    c.fillRect(0, 0, S, S);
    if (!prism) {
      c.drawImage(scratchGobo, 0, 0, S, S);
    } else {
      c.globalCompositeOperation = "lighter";
      c.globalAlpha = Math.min(1, 1.3 / Math.sqrt(layout.centers.length));
      for (const [cx, cy] of layout.centers) {
        c.save();
        c.translate(R + cx * rBeam, R + cy * rBeam);
        c.rotate(deg(prism.angle));
        c.beginPath();
        c.arc(0, 0, rBeam, 0, Math.PI * 2);
        c.clip();
        c.drawImage(scratchGobo, -rBeam, -rBeam, 2 * rBeam, 2 * rBeam);
        c.restore();
      }
      c.globalAlpha = 1;
      c.globalCompositeOperation = "source-over";
    }
    rec.tex.needsUpdate = true;
  }

  // ------------------------------------------------------------------------------------------ Vorrat an Lichtern
  let level = -1;
  let lights = [];                           // SpotLight je Platz
  let slots = [];                            // je Platz: {id, source, key} oder null
  let sourceFns = [];
  function dropPool() {
    lights.forEach((l) => { sim.scene.remove(l, l.target); l.dispose(); if (l.shadow) l.shadow.dispose(); });
    sourceFns.forEach((fn) => { const i = sim.lightSources.indexOf(fn); if (i >= 0) sim.lightSources.splice(i, 1); });
    lights = [];
    slots = [];
    sourceFns = [];
    maps.forEach((rec) => rec && rec.tex.dispose());
    maps.length = 0;
    volumes.forEach((v) => { sim.scene.remove(v.mesh); v.material.dispose(); });
    volumes = [];
  }
  let shadowCount = 0;
  /** Wie viele Lichter/Schattenlichter/Lichtkarten gebraucht werden und die Grafikkarte tragen kann (Ergebnis auch in sim.limits.info fuer die Anzeige). */
  function wanted() {
    const limits = sim.limits;
    const v = limits.values;
    const gpu = limits.gpu;
    let placed = 0;
    for (const entry of ctx.entries().values()) if (!entry.data.hidden) placed++;
    placed = Math.max(1, placed);
    let lights = Math.max(4, Math.ceil(placed / 4) * 4);
    if (v.maxLights > 0) lights = Math.max(1, Math.min(lights, v.maxLights));
    const maps0 = MAX_MAPS;                      // nichts hier haengt von der Qualitaetsstufe ab: sie bestimmt nur Aufloesung, Schattenkarten-Groesse und Abtastschritte
    let shadows = v.maxShadows > 0 ? v.maxShadows : lights;
    const gpuShadows = Math.max(0, gpu.textures - TEXTURE_RESERVE - Math.min(maps0, lights));
    shadows = Math.min(shadows, lights, gpuShadows);
    const gpuLights = Math.max(2, Math.floor((gpu.vectors - VECTOR_BASE - 12 * shadows) / 8));
    lights = Math.max(1, Math.min(lights, gpuLights));
    shadows = Math.min(shadows, lights);
    const maps = Math.min(maps0, shadows);
    limits.info = { placed, lights, shadows, maps, gpuShadows, gpuLights };
    return { lights, shadows, maps };
  }
  function buildPool() {
    dropPool();
    level = sim.quality.level;
    const w = wanted();
    const count = w.lights;
    const shadows = w.shadows;
    shadowCount = shadows;
    const size = Math.min(1024, sim.quality.shadowSize);
    const mapCount = w.maps;
    for (let i = 0; i < count; i++) {
      const light = new THREE.SpotLight(0xffffff, 0, 0, deg(15), 0.35, 2);
      if (i < shadows) {
        light.castShadow = true;
        light.shadow.mapSize.set(size, size);
        light.shadow.bias = -0.0005;
        light.shadow.normalBias = size >= 1024 ? 0.02 : 0.03;
        light.shadow.camera.near = 0.15;
        light.shadow.camera.far = 40;
        if (i < mapCount) {
          const rec = makeMap();                                 // Lichtkarte fuer Gobo/Prisma (weiss = offen); gleich bleibende Shader, kein Neuaufbau beim ersten Gobo
          light.map = rec.tex;
          maps[i] = rec;
        }
      }
      sim.scene.add(light, light.target);
      lights.push(light);
      slots.push(null);
      const fn = () => (slots[i] ? slots[i].source : null);
      sourceFns.push(fn);
      sim.lightSources.push(fn);
    }
    buildVolumes(count);                                         // jeder Platz hat seinen volumetrischen Nebel: alle Scheinwerfer sehen gleich aus, in jeder Qualitaetsstufe
    sim.renderer.shadowMap.needsUpdate = true;
  }
  const onQuality = () => { if (sim.quality.level !== level) { buildPool(); sim.keepAlive(); } };
  sim.quality.listeners.push(onQuality);
  const onLimits = () => { buildPool(); sim.keepAlive(); };
  sim.limits.listeners.push(onLimits);
  buildPool();

  // ------------------------------------------------------------------------------------------ Hilfen
  function makeSource() {
    return { lumens: 0, candela: 0, angle: 0, color: new THREE.Color(), position: new THREE.Vector3(), axis: new THREE.Vector3(0, 0, -1), basisU: new THREE.Vector3(1, 0, 0), basisV: new THREE.Vector3(0, 1, 0), hits: Array.from({ length: MAX_RAYS }, () => ({ valid: false, distance: 1, free: 30, point: new THREE.Vector3(), normal: new THREE.Vector3(), color: new THREE.Color(), metalness: 0, roughness: 1 })), rays: 5 };
  }
  /** Flaechen, die der Strahl trifft (Mittelstrahl + Ring): Grundlage fuer Raumlicht und Farbabstrahlung (wie sim3d_spot.js). */
  function probeHits(source, reach) {
    const ring = 8;                                              // Strahlproben: Mittelstrahl + 8 - unabhaengig von der Qualitaetsstufe
    source.rays = ring + 1;
    basisU.set(0, 0, 1).cross(source.axis);
    if (basisU.lengthSq() < 1e-4) basisU.set(1, 0, 0).cross(source.axis);
    basisU.normalize();
    basisV.copy(source.axis).cross(basisU);
    source.basisU.copy(basisU);
    source.basisV.copy(basisV);
    const half = Math.min(source.angle, deg(120)) / 2 * 0.85;
    const targets = ctx.targets();
    for (let i = 0; i <= ring; i++) {
      const hit = source.hits[i];
      if (i === 0) rayDir.copy(source.axis);
      else {
        const phi = ((i - 1) / ring) * Math.PI * 2;
        rayDir.copy(source.axis).multiplyScalar(Math.cos(half)).addScaledVector(basisU, Math.sin(half) * Math.cos(phi)).addScaledVector(basisV, Math.sin(half) * Math.sin(phi));
      }
      raycaster.set(source.position, rayDir);
      raycaster.near = 0.05;
      raycaster.far = reach;
      const h = raycaster.intersectObjects(targets, false)[0];
      if (!h || !h.face) { hit.valid = false; continue; }
      const m = h.object.material;
      hit.valid = true;
      hit.distance = h.distance;
      hit.point.copy(h.point);
      hit.normal.copy(h.face.normal).applyMatrix3(normalMatrix.getNormalMatrix(h.object.matrixWorld)).normalize();
      if (hit.normal.dot(rayDir) > 0) hit.normal.negate();
      raycaster.set(probeFrom.copy(hit.point).addScaledVector(hit.normal, 0.05), hit.normal);
      raycaster.near = 0;
      raycaster.far = 30;
      const free = raycaster.intersectObjects(targets, false)[0];
      hit.free = free ? free.distance + 0.05 : 30;
      hit.color.copy(m.color);
      hit.metalness = m.metalness || 0;
      hit.roughness = m.roughness === undefined ? 1 : m.roughness;
    }
  }

  function ensureCones(entry, st) {
    const beams = entry.beams || [];
    if (st.beamsRef === beams) return;
    st.cones.forEach((c) => { sim.scene.remove(c.mesh); c.material.dispose(); });
    st.cones = beams.slice(0, MAX_BEAMS).map(() => {
      const material = makeBeamMaterial();
      const mesh = new THREE.Mesh(coneGeometry, material);
      mesh.frustumCulled = false;
      mesh.renderOrder = 3;
      mesh.visible = false;
      sim.scene.add(mesh);
      return { mesh, material };
    });
    st.beamsRef = beams;
  }
  function dropState(st) {
    st.cones.forEach((c) => { sim.scene.remove(c.mesh); c.material.dispose(); });
    st.cones = [];
  }
  // ---- Shutter/Strobe
  const shutterCache = new Map();                                  // Typ -> Promise<{Shutter1: [{from, to, kind, hz}]}>
  function loadShutter(typeId) {
    if (!typeId) return Promise.resolve({});
    if (!shutterCache.has(typeId)) {
      shutterCache.set(typeId, fetch("/api/fixture-types/" + encodeURIComponent(typeId) + "/shutter").then((res) => (res.ok ? res.json() : {})).catch(() => ({})));
    }
    return shutterCache.get(typeId);
  }
  /** Takt des Shutters aus dem rohen Byte und den Bereichen des Typs: {kind, hz} oder null (offen, geschlossen oder unbekannt: "geschlossen" bleibt bewusst sichtbar -
   *  OpenCue setzt den Shutter nicht selbst auf offen, ein Rohwert 0 wuerde jeden neuen Scheinwerfer verdunkeln). */
  function resolveShutter(entry, live) {
    const bytes = live && live.wheels;
    if (!bytes || !entry.shutterData) return null;
    for (const channel of ["Shutter1", "Shutter1Strobe"]) {
      const value = bytes[channel];
      const ranges = entry.shutterData[channel];
      if (value === undefined || value === null || !Array.isArray(ranges)) continue;
      const range = ranges.find((q) => value >= q.from && value <= q.to);
      if (!range || range.kind === "closed" || range.kind === "open") continue;
      const span = Math.max(range.to - range.from, 1);
      const hz = range.hz[0] + ((range.hz[1] - range.hz[0]) * (value - range.from)) / span;
      return { kind: range.kind, hz: Math.max(0.2, Math.min(hz, 30)) };
    }
    return null;
  }
  /** Gate 0..1 des Shutters zum Zeitpunkt t (Sekunden): Strobe = Rechteck (kurzer heller Anteil), Puls auf/ab = Rampe, Zufall = wechselnd.
   *  span > 0: Strobe als Mittel ueber das Bildintervall [t - span, t] - so geht kein Blitz zwischen zwei Bildern verloren (bei 20 Hz und 30 Bildern/s sonst Aliasing). */
  function shutterGate(strobe, t, seed, span = 0) {
    if (!strobe) return 1;
    if (strobe.kind === "strobe" && span > 0.002) {
      const total = (x) => Math.floor(x) * STROBE_DUTY + Math.min(x - Math.floor(x), STROBE_DUTY);        // aufsummierte helle Zeit (in Perioden)
      const p1 = t * strobe.hz;
      const p0 = p1 - span * strobe.hz;
      return (total(p1) - total(p0)) / (p1 - p0);
    }
    const phase = (t * strobe.hz) % 1;
    if (strobe.kind === "pulse_in") return phase;
    if (strobe.kind === "pulse_out") return 1 - phase;
    if (strobe.kind === "random") {
      const slot = Math.floor(t * strobe.hz * 2);
      const x = Math.sin(slot * 12.9898 + seed * 78.233) * 43758.5453;
      return x - Math.floor(x) > 0.5 ? 1 : 0;
    }
    return phase < STROBE_DUTY ? 1 : 0;
  }
  const hashOf = (id) => { let h = 0; for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 997; return h; };

  // ---- Fokus: Kantenweichheit des Lichtkegels aus Fokus-Wert, Wurfweite und Zoom
  function focalDistance(range, pct) {
    const f = Math.max(0, Math.min(1, pct / 100));
    if (range && Math.max(range.from, range.to) > 1.5 && Math.min(range.from, range.to) >= 0.2) return Math.max(0.3, range.from + (range.to - range.from) * f);        // Datei gibt Meter an
    return FOCUS_NEAR * Math.pow(FOCUS_FAR / FOCUS_NEAR, f);                                                                                              // sonst 2 ... 30 m, logarithmisch
  }
  /** Penumbra (0..1, Anteil des halben Oeffnungswinkels) fuer ein Geraet: aus der Unschaerfe am Rand, ca. Linsenradius x |1/d - 1/f| (Winkel im Bogenmass). */
  function penumbraFor(entry, st, beam, angleDeg) {
    if (st.focus === null || st.focus === undefined) return DEFAULT_PENUMBRA;
    const d = Math.max(0.5, st.throw || 8);
    const f = focalDistance(entry.focusRange, st.focus);
    const aperture = Math.max(beam && beam.radius ? beam.radius : 0.05, 0.03);
    const blur = aperture * Math.abs(1 / d - 1 / f);
    const half = Math.max(deg(angleDeg) / 2, 0.02);
    return Math.max(MIN_PENUMBRA, Math.min(0.95, MIN_PENUMBRA + (blur / half) * 3.5));        // Schaerfeebene = Wurfweite: Kante hart, davor und dahinter unscharf
  }

  /** Oeffnungswinkel (Grad) aus dem Zoom-Wert 0..100 % und den Abschnitten der Zoom-Funktion aus der GDTF (je Abschnitt linear zwischen den Winkeln am Anfang und am Ende). */
  function zoomAngle(range, pct) {
    const f = Math.max(0, Math.min(1, pct / 100));
    const segments = range.segments || [];
    for (const [from, to, a, b] of segments) {
      if (f >= from && f <= to) return to > from ? a + ((b - a) * (f - from)) / (to - from) : a;
    }
    if (segments.length && f < segments[0][0]) return segments[0][2];
    if (segments.length && f > segments[segments.length - 1][1]) return segments[segments.length - 1][3];
    return range.from + (range.to - range.from) * f;
  }
  const approach = (current, target, dt, tau) => {
    const next = current + (target - current) * (1 - Math.exp(-dt / tau));
    return Math.abs(target - next) < 0.0015 ? target : next;
  };

  // ------------------------------------------------------------------------------------------ pro Bild
  function update() {
    if (destroyed) return;
    const now = performance.now();
    const dt = Math.min(0.1, Math.max(0.001, (now - last) / 1000));
    last = now;
    if (sim.quality.level !== level) buildPool();
    else { const w = wanted(); if (w.lights !== lights.length || w.shadows !== shadowCount) buildPool(); }          // Scheinwerfer platziert/entfernt oder Grenze geaendert: Vorrat anpassen
    const haze = Math.max(0, Math.min(1, ctx.haze()));
    const gm = Math.max(0, Math.min(100, Number.isFinite(window.__grandMaster) ? window.__grandMaster : 100)) / 100;
    const blackout = window.__blackout ? 0 : 1;       // Blackout hat Vorrang: alles dunkel (der Server schickt dann keinen Dimmer-Wert, der Master steckt nicht mehr im Live-Strom)
    const cache = window.__fixturesLive || {};
    const entries = ctx.entries();
    let busy = false;
    const candidates = [];
    for (const [id, st] of states) if (!entries.has(id)) { dropState(st); states.delete(id); }          // Scheinwerfer von der Buehne genommen
    for (const [id, entry] of entries) {
      let st = states.get(id);
      if (!st) { st = { dim: 0, r: 1, g: 1, b: 1, pan: 50, tilt: 50, zoom: null, focus: null, throw: 8, fx: null, cones: [], beamsRef: null, appliedPan: null, appliedTilt: null, seed: hashOf(id) }; states.set(id, st); }
      ensureCones(entry, st);
      if (entry.data.hidden) { st.cones.forEach((c) => { c.mesh.visible = false; }); continue; }
      const live = cache[id];
      // Zielwerte: ohne Live-Eintrag ist der Scheinwerfer aus; hat das Geraet keinen Dimmer-Kanal (nur Farbe), zaehlt die Farbe
      const dimTarget = live ? (live.dimmer !== undefined ? live.dimmer / 100 : 1) * gm * blackout : 0;
      const color = live && live.color ? live.color : null;
      if (entry.modelType && st.wheelsFor !== entry.modelType) {                          // Farbraeder des Typs holen (einmal je Typ)
        st.wheelsFor = entry.modelType;
        const typeId = entry.modelType;
        loadWheels(typeId).then((wheels) => { if (entry.modelType === typeId) { entry.wheelData = Array.isArray(wheels) ? wheels : []; sim.keepAlive(); } });
      }
      if (entry.modelType && st.shutterFor !== entry.modelType) {                         // Shutter-Bereiche des Typs holen (einmal je Typ)
        st.shutterFor = entry.modelType;
        const typeId = entry.modelType;
        loadShutter(typeId).then((data) => { if (entry.modelType === typeId) { entry.shutterData = data && typeof data === "object" ? data : {}; sim.keepAlive(); } });
      }
      if (entry.modelType && st.beamfxFor !== entry.modelType) {                          // Gobo-/Prismenkanaele des Typs holen (einmal je Typ)
        st.beamfxFor = entry.modelType;
        const typeId = entry.modelType;
        loadBeamfx(typeId).then((data) => { if (entry.modelType === typeId) { entry.beamfx = data && typeof data === "object" ? data : {}; sim.keepAlive(); } });
      }
      wheelTint(entry, live, tint);
      const rTarget = (color ? color.r / 255 : 1) * tint[0];
      const gTarget = (color ? color.g / 255 : 1) * tint[1];
      const bTarget = (color ? color.b / 255 : 1) * tint[2];
      const panTarget = live && live.pan !== undefined ? live.pan : null;
      const tiltTarget = live && live.tilt !== undefined ? live.tilt : null;
      const zoomTarget = live && live.zoom !== undefined ? live.zoom : null;
      const before = st.dim + st.r + st.g + st.b + st.pan + st.tilt;
      st.dim = approach(st.dim, dimTarget, dt, TAU.dim);
      st.r = approach(st.r, rTarget, dt, TAU.color);
      st.g = approach(st.g, gTarget, dt, TAU.color);
      st.b = approach(st.b, bTarget, dt, TAU.color);
      if (panTarget !== null) st.pan = approach(st.pan, panTarget, dt, TAU.axis);
      if (tiltTarget !== null) st.tilt = approach(st.tilt, tiltTarget, dt, TAU.axis);
      if (zoomTarget !== null) st.zoom = st.zoom === null ? zoomTarget : approach(st.zoom, zoomTarget, dt, TAU.zoom);
      const focusTarget = live && live.focus !== undefined ? live.focus : null;
      if (focusTarget !== null) st.focus = st.focus === null ? focusTarget : approach(st.focus, focusTarget, dt, TAU.zoom);
      else st.focus = null;
      if (before !== st.dim + st.r + st.g + st.b + st.pan + st.tilt) busy = true;
      if ((panTarget !== null && st.pan !== panTarget) || (tiltTarget !== null && st.tilt !== tiltTarget) || (zoomTarget !== null && st.zoom !== zoomTarget) || (focusTarget !== null && st.focus !== focusTarget)) busy = true;
      if (entry.built && entry.axes && (panTarget !== null || tiltTarget !== null) && (st.pan !== st.appliedPan || st.tilt !== st.appliedTilt)) {      // Achsen: Prozent -> Winkel (Bereich aus der GDTF)
        const range = (axis, pct) => (axis ? (axis.from !== undefined ? axis.from + (pct / 100) * (axis.to - axis.from) : axis.min + (pct / 100) * (axis.max - axis.min)) : 0);       // DMX 0 = Wert "von" der Datei (auch umgekehrt: 270 ... -270)
        entry.built.setAngles(range(entry.axes.pan, st.pan), range(entry.axes.tilt, st.tilt));
        st.appliedPan = st.pan;
        st.appliedTilt = st.tilt;
      }
      entry.group.updateMatrixWorld(true);
      tmpColor.setRGB(st.r, st.g, st.b, THREE.SRGBColorSpace);
      const strobe = resolveShutter(entry, live);
      const gate = strobe ? shutterGate(strobe, now / 1000, st.seed, dt) : 1;
      if (strobe && st.dim > 0.004) busy = true;                                          // der Takt braucht jedes Bild
      const power = st.dim * gate;
      if (entry.built) {                                          // Linse leuchtet in der Farbe des Lichts
        entry.built.lensMaterial.emissive.copy(tmpColor);
        entry.built.lensMaterial.color.copy(tmpColor).lerp(LENS_OFF, 1 - Math.min(1, power * 4));
        entry.built.lensMaterial.emissiveIntensity = power * 2.2;
      }
      const patternState = { moving: false };
      const pattern = resolvePattern(entry, st, live, dt, now / 1000, patternState);        // Gobo/Prisma aus den DMX-Bytes
      if (patternState.moving && st.dim > 0.004) busy = true;
      const beams = entry.beams || [];
      let first = true;
      st.cones.forEach((cone, i) => {
        const beam = beams[i];
        if (!beam) { cone.mesh.visible = false; return; }
        let angle = beam.angle;
        if (entry.zoomRange && st.zoom !== null) angle = zoomAngle(entry.zoomRange, st.zoom);
        angle = Math.max(2, Math.min(120, angle));
        beam.object.matrixWorld.decompose(tmpPos, tmpQuat, tmpScale);
        tmpDir.set(0, 0, -1).applyQuaternion(tmpQuat);
        const visible = power > 0.004;
        cone.mesh.visible = visible;
        if (visible) {
          const length = BEAM_LENGTH;
          const radius = length * Math.tan(deg(angle) / 2);
          cone.mesh.position.copy(tmpPos);
          cone.mesh.quaternion.copy(tmpQuat);
          cone.mesh.scale.set(radius, radius, length);
          cone.material.uniforms.uColor.value.copy(tmpColor);
          const pen = penumbraFor(entry, st, beam, angle);
          cone.material.uniforms.uSoft.value = 0.9 + 2 * Math.max(0, Math.min(1, (pen - 0.12) / 0.7));       // weicher Rand bei Unschaerfe
          cone.material.uniforms.uSharp.value = 1 - Math.max(0, Math.min(1, (pen - 0.02) / 0.25));         // scharf: harte Kante
          cone.material.uniforms.uStrength.value = haze * power * 0.45 * (beams.length > 1 ? 1 / Math.sqrt(Math.min(beams.length, MAX_BEAMS)) : 1);
        }
        if (first && visible) {                                   // das erste Licht des Geraets bewirbt sich um einen Platz im Vorrat
          first = false;
          const extent = pattern && pattern.prism ? prismLayout(pattern.prism).extent : 0;
          const outer = extent ? Math.min(THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(deg(angle) / 2) * (extent + 1))), 166) : angle;        // das Prisma verbreitert den Lichtkegel um die Kopien
          candidates.push({ id, power, angle, outer, pattern, up: tmpUp.set(0, 1, 0).applyQuaternion(tmpQuat).clone(), pos: tmpPos.clone(), dir: tmpDir.clone(), color: tmpColor.clone(), cone, penumbra: penumbraFor(entry, st, beam, angle), st });
        }
      });
    }
    // Vorrat verteilen: die hellsten, bisherige Plaetze bleiben erhalten (kein Flackern)
    candidates.sort((a, b) => (b.pattern ? 1 : 0) - (a.pattern ? 1 : 0) || b.power - a.power || (a.id < b.id ? -1 : 1));          // Muster (Gobo/Prisma) brauchen einen Platz mit Schatten (nur dort gibt es eine Lichtkarte)
    const chosen = candidates.slice(0, lights.length);
    const free = [];
    const assigned = new Map();
    slots.forEach((slot, i) => {
      const keep = slot && chosen.find((c) => c.id === slot.id);
      if (keep) assigned.set(i, keep); else free.push(i);
    });
    chosen.forEach((c) => {
      if ([...assigned.values()].includes(c)) return;
      const i = free.shift();
      if (i !== undefined) assigned.set(i, c);
    });
    const mapCount = lights.filter((l) => l.map).length;
    const volumeCount = volumes.length;
    const bringForward = (limit) => {                                // Geraet mit Muster auf einem Platz ohne Karte (bzw. ohne Nebel-Kegel): mit einem Platz davor tauschen, der kein Muster braucht
      for (let i = limit; i < lights.length; i++) {
        const c = assigned.get(i);
        if (!c || !c.pattern) continue;
        for (let j = 0; j < limit; j++) {
          const other = assigned.get(j);
          if (!other || !other.pattern) { assigned.delete(i); assigned.delete(j); assigned.set(j, c); if (other) assigned.set(i, other); break; }
        }
      }
    };
    bringForward(mapCount);
    bringForward(Math.min(volumeCount, mapCount));
    let shadowsMoved = false;
    lights.forEach((light, i) => {
      const c = assigned.get(i);
      if (!c) {
        if (slots[i]) { slots[i] = null; if (light.castShadow) shadowsMoved = true; }
        light.intensity = 0;
        return;
      }
      let slot = slots[i];
      if (!slot || slot.id !== c.id) { slot = slots[i] = { id: c.id, source: makeSource(), key: "" }; if (light.castShadow) shadowsMoved = true; }
      const key = [c.pos.x, c.pos.y, c.pos.z, c.dir.x, c.dir.y, c.dir.z, c.angle, c.pattern && maps[i] ? c.outer : c.angle, c.up.x, c.up.y, c.up.z].map((v) => v.toFixed(3)).join(",");
      const moved = key !== slot.key;
      light.position.copy(c.pos);
      light.target.position.copy(c.pos).addScaledVector(c.dir, 10);
      light.target.updateMatrixWorld();
      light.color.copy(c.color);
      const usePattern = !!(c.pattern && maps[i]);                              // ohne Lichtkarte auf diesem Platz bleibt das Licht offen
      c.outerUsed = usePattern ? c.outer : c.angle;
      light.angle = Math.min(deg(c.outerUsed) / 2, 1.45);
      light.penumbra = usePattern && c.pattern.prism ? 0.01 : c.penumbra;       // mit Prisma bestimmt die Karte die Kanten, der aeussere Rand bleibt dahinter
      if (light.castShadow) {
        light.shadow.camera.up.copy(c.up);                                      // Bild des Gobos dreht sich mit dem Kopf (Pan/Tilt)
        const rec = maps[i];
        if (rec) {
          if (usePattern) paintMap(rec, c.pattern, c.penumbra, Math.tan(deg(c.angle) / 2), Math.tan(light.angle));
          else clearMap(rec);
        }
      }
      light.intensity = BASE_CANDELA * c.power;
      const source = slot.source;
      source.candela = BASE_CANDELA * c.power;
      source.angle = deg(c.angle);
      source.lumens = source.candela * 2 * Math.PI * (1 - Math.cos(Math.min(source.angle, deg(170)) / 2));
      source.color.copy(c.color);
      source.position.copy(c.pos);
      source.axis.copy(c.dir);
      if (moved || slot.version !== sim.version) {
        probeHits(source, 40);
        c.st.throw = source.hits[0].valid ? source.hits[0].distance : 12;
        slot.key = key;
        slot.version = sim.version;
        if (light.castShadow) shadowsMoved = true;
      }
    });
    // Jeder Platz: volumetrischer Kegel statt des einfachen (er sitzt an der Linse des zugeteilten Geraets). Plaetze mit Schattenkarte werden von ihr geschnitten, die anderen
    // enden an den Flaechen, die die Strahlproben getroffen haben - so geht der Nebel nirgends durch Waende, und alle Scheinwerfer sehen gleich aus.
    let volumeActive = false;
    let activeVolumes = 0;
    const anyLight = lights.find((l) => l.castShadow && l.shadow.map && l.shadow.map.depthTexture);
    const anyShadowTexture = anyLight ? anyLight.shadow.map.depthTexture : null;
    volumes.forEach((v, i) => { if (assigned.get(i) && lights[i]) activeVolumes++; });
    const stepScale = Math.min(1, 4 / Math.max(1, activeVolumes));                   // viele Kegel: weniger Schritte je Kegel
    volumes.forEach((v, i) => {
      const c = assigned.get(i);
      const light = lights[i];
      if (!c || !light) { v.mesh.visible = false; return; }
      c.cone.mesh.visible = false;
      v.mesh.visible = true;
      volumeActive = true;
      const u = v.material.uniforms;
      u.uColor.value.copy(c.color);
      u.uStrength.value = haze * c.power * 0.35;
      u.uSteps.value = Math.max(6, Math.round(STEPS[Math.max(0, Math.min(5, level))] * stepScale));
      u.uApex.value.copy(c.pos);
      u.uAxis.value.copy(c.dir);
      u.uK.value = Math.tan(deg(c.outerUsed || c.angle) / 2);
      u.uL.value = BEAM_LENGTH;
      u.uCosOuter.value = Math.cos(light.angle);
      u.uCosInner.value = Math.cos(light.angle * (1 - light.penumbra));
      u.uBias.value = light.shadow.bias;
      const shadowTexture = light.castShadow && light.shadow.map && light.shadow.map.depthTexture;
      u.uShadow.value = shadowTexture || anyShadowTexture;                          // ein Platz ohne Schatten bindet trotzdem eine echte Tiefentextur: ein leerer sampler2DShadow laesst den ganzen Durchlauf ausfallen (kein Nebel)
      u.uHasShadow.value = shadowTexture ? 1 : 0;
      if (shadowTexture) u.uShadowMat.value.copy(light.shadow.matrix);
      const src = slots[i] && slots[i].source;
      if (!shadowTexture && src) {                                                    // kein Schatten: Schnitt an den getroffenen Flaechen
        const ring = Math.max(1, Math.min(8, src.rays - 1));
        const half = Math.min(src.angle, deg(120)) / 2 * 0.85;
        const hitS = u.uHitS.value;
        for (let k = 0; k < 9; k++) {
          const h = src.hits[k];
          hitS[k] = k <= ring && h && h.valid ? Math.min(BEAM_LENGTH + 5, h.distance * (k === 0 ? 1 : Math.cos(half))) : BEAM_LENGTH + 5;
        }
        u.uRing.value = ring;
        u.uBasisU.value.copy(src.basisU);
        u.uBasisV.value.copy(src.basisV);
        u.uUseHits.value = 1;
      } else {
        u.uUseHits.value = 0;
      }
      u.uCap.value = 0;
      if (shadowTexture && src) {                                                     // mit Schattenkarte: der Schatten schneidet genau; zusaetzlich endet der Nebel hinter der fernsten Trefferflaeche, wenn alle Strahlproben etwas treffen (geschlossene Wand)
        const ring = Math.max(1, Math.min(8, src.rays - 1));
        const half = Math.min(src.angle, deg(120)) / 2 * 0.85;
        let far = 0;
        let all = true;
        for (let k = 0; k <= ring; k++) {
          const h = src.hits[k];
          if (!h || !h.valid) { all = false; break; }
          far = Math.max(far, h.distance * (k === 0 ? 1 : Math.cos(half)));
        }
        if (all && far > 0) u.uCap.value = far + 0.1;
      }
      const goboMap = maps[i];
      u.uHasGobo.value = c.pattern && goboMap ? 1 : 0;
      u.uGobo.value = goboMap ? goboMap.tex : null;
    });
    if (volumeActive) depthPass();
    if (shadowsMoved) sim.renderer.shadowMap.needsUpdate = true;
    if (busy) sim.keepAlive();
  }
  sim.frameHooks.unshift(update);                                 // vor dem Raumlicht: dessen Quellen sind dann aktuell

  const onLive = () => { if (!destroyed) sim.keepAlive(); };
  document.addEventListener("fixtures-live-values", onLive);

  /** Zoom-Wert (0..100 %), dessen Oeffnungswinkel dem gewuenschten am naechsten kommt (Umkehrung von zoomAngle; die Abschnitte sind je linear, daher fein abtasten). */
  function zoomPctFor(range, angleDeg) {
    let best = 0;
    let bestError = Infinity;
    for (let i = 0; i <= 1000; i++) {
      const error = Math.abs(zoomAngle(range, i / 10) - angleDeg);
      if (error < bestError) { bestError = error; best = i / 10; }
    }
    return { pct: best, angle: zoomAngle(range, best) };
  }
  /** Kleinster und groesster Oeffnungswinkel (Grad), den der Zoom des Geraets kann. */
  function zoomLimits(range) {
    let min = Infinity;
    let max = -Infinity;
    for (let i = 0; i <= 200; i++) { const a = zoomAngle(range, i / 2); min = Math.min(min, a); max = Math.max(max, a); }
    return { min, max };
  }
  /** Fokus-Wert (0..100 %), dessen Schaerfeebene der Wurfweite am naechsten kommt (Umkehrung von focalDistance). */
  function focusPctFor(range, distance) {
    let best = 0;
    let bestError = Infinity;
    for (let i = 0; i <= 1000; i++) {
      const error = Math.abs(Math.log(focalDistance(range, i / 10) / Math.max(0.3, distance)));
      if (error < bestError) { bestError = error; best = i / 10; }
    }
    return { pct: best, distance: focalDistance(range, best) };
  }

  return {
    /** Etwas hat sich geaendert (Grand Master, neues Modell, Scheinwerfer platziert): neu zeichnen. */
    touch() { sim.keepAlive(); },
    zoomPctFor, focusPctFor, zoomLimits,
    _test: { resolveShutter, shutterGate, focalDistance, penumbraFor, zoomAngle, resolvePattern, prismLayout, paintMap, maps: () => maps, states: () => states },
    dispose() {
      destroyed = true;
      document.removeEventListener("fixtures-live-values", onLive);
      const i = sim.frameHooks.indexOf(update);
      if (i >= 0) sim.frameHooks.splice(i, 1);
      const q = sim.quality.listeners.indexOf(onQuality);
      if (q >= 0) sim.quality.listeners.splice(q, 1);
      const lq = sim.limits.listeners.indexOf(onLimits);
      if (lq >= 0) sim.limits.listeners.splice(lq, 1);
      states.forEach(dropState);
      states.clear();
      dropPool();
      volumes.forEach((v) => { sim.scene.remove(v.mesh); v.material.dispose(); });
      volumes = [];
      if (depthTarget) { depthTarget.depthTexture.dispose(); depthTarget.dispose(); depthTarget = null; }
      depthMaterial.dispose();
      fullscreen.dispose();
      coneGeometry.dispose();
    },
  };
}

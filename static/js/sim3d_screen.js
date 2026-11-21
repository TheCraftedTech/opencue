// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* 3D-Simulation: Bildschirm (Typ "screen"). Eine duenne Tafel (Breite x Hoehe, wenige Millimeter dick) mit einem Bild oder Video aus der Medienbibliothek der Show auf der Vorderseite
 * (Vorderseite = Blick nach -Y, die Seite, auf die die Standardansicht schaut). Ein Video laeuft wie im Medien-Player-Panel: zum Timecode (OCTimecode) oder frei, mit Startzeit; dafuer
 * gibt es einen unsichtbaren Player (OCMedia.createPlayer in media_player.js). Die Farbe laesst sich anpassen: Helligkeit, Kontrast, Saettigung, Farbton, Toenung, Spiegeln.
 * Zwei Arten der Beleuchtung (data.emissive): AN = der Bildschirm leuchtet selbst (wie eine LED-Wand; kein Einfluss durch Raumlicht und Tonwert-Kurve), AUS = er ist wie eine Wand:
 * das Bild ist die Oberflaeche, und nur Scheinwerfer, Raumlicht und Reflexionen beleuchten es (mit Schatten). Daten im Buehnenobjekt:
 *   media (Medien-Id oder ""), fit (stretch | contain | cover), look {brightness, contrast, saturation (Prozent), hue (Grad), tint (#rrggbb), flip}, sync (timecode | free), tc_start_ms, loop, muted, emissive. */
import * as THREE from "three";

/** Gemeinsamer Farb- und Flaechen-Code beider Arten (selbstleuchtend: ShaderMaterial, Wand: MeshStandardMaterial mit eingehaengtem Code). */
const COMMON = `
  uniform float uHas; uniform float uPanel; uniform float uMedia; uniform float uFit; uniform float uFlip;
  uniform float uBright; uniform float uContrast; uniform float uSat; uniform float uHue; uniform vec3 uTint;
  vec3 scrGamma(vec3 c) { return mix(c * 12.92, 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }
  vec3 scrLinear(vec3 c) { return mix(c / 12.92, pow((max(c, vec3(0.0)) + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); }
  vec3 scrHue(vec3 c, float a) {                                      // Farbtondrehung im YIQ-Raum (Richtung wie CSS hue-rotate: +120 Grad macht Rot zu Gruen)
    const mat3 toYIQ = mat3(0.299, 0.596, 0.211, 0.587, -0.274, -0.523, 0.114, -0.322, 0.312);
    const mat3 fromYIQ = mat3(1.0, 1.0, 1.0, 0.956, -0.272, -1.106, 0.621, -0.647, 1.703);
    vec3 q = toYIQ * c;
    float cs = cos(a), sn = sin(a);
    q.yz = vec2(q.y * cs + q.z * sn, -q.y * sn + q.z * cs);
    return fromYIQ * q;
  }
  vec3 scrGrade(vec3 rgb) {                                           // Farbanpassung (rgb linear rein, linear raus; gerechnet wird in Anzeigewerten wie in einem Bildprogramm)
    vec3 c = scrGamma(rgb);
    c = scrHue(c, uHue);
    float l = dot(c, vec3(0.299, 0.587, 0.114));
    c = mix(vec3(l), c, uSat);
    c = (c - 0.5) * uContrast + 0.5;
    c = c * uBright * uTint;
    return scrLinear(clamp(c, 0.0, 1.0));
  }
  vec2 scrFit(vec2 uv, out float inside) {                            // Einpassen / Fuellen / Strecken; inside = 0 ausserhalb des Bildes (Rand)
    float r = uPanel / max(uMedia, 0.001);                            // Seitenverhaeltnis Tafel / Medium
    if (uFit > 0.5 && uFit < 1.5) { if (r > 1.0) uv.x = (uv.x - 0.5) * r + 0.5; else uv.y = (uv.y - 0.5) / r + 0.5; }       // einpassen (mit Raendern)
    else if (uFit > 1.5) { if (r > 1.0) uv.y = (uv.y - 0.5) / r + 0.5; else uv.x = (uv.x - 0.5) * r + 0.5; }                // fuellen (zuschneiden)
    inside = step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);
    return uv;
  }
  vec3 scrPlaceholder(vec2 uv) {                                      // kein Medium: ruhige dunkle Flaeche mit feinem Raster, damit man sieht, dass es ein Bildschirm ist
    vec2 g = abs(fract(uv * vec2(uPanel * 4.0, 4.0)) - 0.5);
    float line = 1.0 - smoothstep(0.46, 0.5, max(g.x, g.y));
    return scrLinear(vec3(0.07, 0.075, 0.09) + 0.05 * line);
  }`;

const VERT = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;

const FRAG = `
  uniform sampler2D uMap;
  varying vec2 vUv;
  ${COMMON}
  void main() {
    vec2 uv = vUv;
    if (uFlip > 0.5) uv.x = 1.0 - uv.x;
    float inside = 1.0;
    vec3 rgb;
    if (uHas > 0.5) { uv = scrFit(uv, inside); rgb = texture2D(uMap, clamp(uv, 0.0, 1.0)).rgb; }
    else rgb = scrPlaceholder(vUv);
    gl_FragColor = vec4(scrGrade(rgb) * inside, 1.0);
    #include <colorspace_fragment>
  }`;

/** Dasselbe als Ersatz fuer #include <map_fragment> im Standard-Material (Wand): das Ergebnis ist die Grundfarbe, die danach vom Licht beleuchtet wird. */
const MAP_FRAGMENT = `
  #ifdef USE_MAP
    vec2 sUv = vMapUv;
    if (uFlip > 0.5) sUv.x = 1.0 - sUv.x;
    float sInside = 1.0;
    vec3 sRgb;
    if (uHas > 0.5) { sUv = scrFit(sUv, sInside); sRgb = texture2D(map, clamp(sUv, 0.0, 1.0)).rgb; }
    else sRgb = scrPlaceholder(vMapUv);
    diffuseColor.rgb = scrGrade(sRgb) * sInside;
  #endif`;

const FITS = { stretch: 0, contain: 1, cover: 2 };
const EMPTY = (() => { const t = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1); t.needsUpdate = true; return t; })();
let planeGeometry = null;

/** Den Bildschirm-Belag zu einem Buehnenobjekt (entry: {id, data, group}) anlegen und an dessen Gruppe haengen. Rueckgabe: {update(), attach(entry), dispose(), mediaAspect, get hasMedia}. */
export function attachScreen(sim, entry) {
  planeGeometry = planeGeometry || new THREE.PlaneGeometry(1, 1);
  const uniforms = {
    uMap: { value: EMPTY }, uHas: { value: 0 }, uPanel: { value: 1.78 }, uMedia: { value: 1.78 }, uFit: { value: 0 }, uFlip: { value: 0 },
    uBright: { value: 1 }, uContrast: { value: 1 }, uSat: { value: 1 }, uHue: { value: 0 }, uTint: { value: new THREE.Vector3(1, 1, 1) },
  };
  const glowing = new THREE.ShaderMaterial({ uniforms, vertexShader: VERT, fragmentShader: FRAG, toneMapped: false, fog: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 });
  const wall = new THREE.MeshStandardMaterial({ map: EMPTY, color: 0xffffff, roughness: 0.88, metalness: 0, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 });
  if (sim.patchBleed) sim.patchBleed(wall);                              // auch die Wand nimmt das Farblicht der Scheinwerfer auf (wie jeder Koerper)
  const bleedHook = wall.onBeforeCompile;
  const bleedKey = wall.customProgramCacheKey ? wall.customProgramCacheKey() : "";
  wall.onBeforeCompile = (shader, renderer) => {
    if (bleedHook) bleedHook(shader, renderer);
    for (const key of Object.keys(uniforms)) if (key !== "uMap") shader.uniforms[key] = uniforms[key];
    shader.fragmentShader = shader.fragmentShader.replace("#include <common>", "#include <common>\n" + COMMON).replace("#include <map_fragment>", MAP_FRAGMENT);
  };
  wall.customProgramCacheKey = () => "screenwall|" + bleedKey;
  const mesh = new THREE.Mesh(planeGeometry, glowing);
  mesh.rotation.x = Math.PI / 2;                                        // Vorderseite zeigt nach -Y, oben ist +Z
  mesh.raycast = () => {};                                              // angeklickt wird die Tafel selbst
  mesh.renderOrder = 2;
  entry.group.add(mesh);

  let source = { id: "", kind: "" };                                    // was gerade geladen ist
  let player = null;
  let texture = null;
  let loader = null;
  let hasMedia = false;
  let mediaAspect = 0;
  let dead = false;

  const tint = new THREE.Color();
  function releaseSource() {
    if (loader) { loader.cancelled = true; loader = null; }
    if (player) { player.dispose(); player = null; }
    if (texture) { texture.dispose(); texture = null; }
    uniforms.uMap.value = EMPTY;
    wall.map = EMPTY;
    uniforms.uHas.value = 0;
    hasMedia = false;
    mediaAspect = 0;
  }
  function useTexture(tex, aspect) {
    texture = tex;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.minFilter = THREE.LinearFilter;
    tex.generateMipmaps = false;
    uniforms.uMap.value = tex;
    wall.map = tex;
    uniforms.uHas.value = 1;
    hasMedia = true;
    if (aspect) { mediaAspect = aspect; uniforms.uMedia.value = aspect; }
    sim.invalidate();
  }
  function loadSource(data) {
    releaseSource();
    source = { id: data.media, kind: "" };
    const meta = data.media ? window.OCMedia && OCMedia.get(data.media) : null;
    if (!meta || meta.missing) return;
    source.kind = meta.kind;
    if (meta.kind === "image") {
      const mine = loader = { cancelled: false };
      new THREE.TextureLoader().load(OCMedia.cachedUrl(meta.id) || OCMedia.url(meta.id), (tex) => {
        if (dead || mine.cancelled) { tex.dispose(); return; }
        loader = null;
        useTexture(tex, tex.image && tex.image.width ? tex.image.width / tex.image.height : 0);
      }, undefined, () => { /* nicht ladbar: Platzhalter bleibt */ });
    } else if (meta.kind === "video" && window.OCMedia && OCMedia.createPlayer) {
      player = OCMedia.createPlayer({ media_id: meta.id, sync: data.sync, tc_start_ms: data.tc_start_ms, loop: data.loop, muted: data.muted });
      const video = player.video;
      video.muted = !!data.muted;
      const tex = new THREE.VideoTexture(video);
      useTexture(tex, video.videoWidth ? video.videoWidth / video.videoHeight : 0);
      ["seeked", "loadeddata", "playing", "pause"].forEach((name) => video.addEventListener(name, () => { activeUntil = performance.now() + 900; sim.keepAlive(); }));
      video.addEventListener("loadedmetadata", () => { if (player && player.video === video && video.videoHeight) { mediaAspect = video.videoWidth / video.videoHeight; uniforms.uMedia.value = mediaAspect; sim.invalidate(); } });
    }
  }

  let activeUntil = 0;                                                  // nach einem Sprung (Timecode verschoben) noch kurz weiterzeichnen, damit das neue Standbild erscheint
  let lastPlayerKey = "";
  /** Aus den Daten des Objekts (Groesse, Medium, Darstellung, Farbe, Wiedergabe, Beleuchtung) alles auffrischen; guenstig, wird bei jeder Aenderung/jedem Ziehen gerufen. */
  function update() {
    const data = entry.data;
    const [w, t, h] = data.size;
    mesh.scale.set(w, h, 1);
    mesh.position.set(0, -t / 2 - 0.0008, h / 2);
    const emissive = data.emissive !== false;
    const wanted = emissive ? glowing : wall;
    if (mesh.material !== wanted) mesh.material = wanted;
    mesh.receiveShadow = !emissive;
    const u = uniforms;
    u.uPanel.value = w / Math.max(h, 1e-4);
    u.uFit.value = FITS[data.fit] || 0;
    const look = data.look || {};
    u.uBright.value = (look.brightness ?? 100) / 100;
    u.uContrast.value = (look.contrast ?? 100) / 100;
    u.uSat.value = (look.saturation ?? 100) / 100;
    u.uHue.value = ((look.hue ?? 0) * Math.PI) / 180;
    u.uFlip.value = look.flip ? 1 : 0;
    tint.set(look.tint || "#ffffff");
    const toGamma = (v) => (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);          // Toenung wirkt auf die Anzeigewerte (sRGB), wie in einem Bildprogramm
    u.uTint.value.set(toGamma(tint.r), toGamma(tint.g), toGamma(tint.b));
    if (source.id !== (data.media || "") || (data.media && !hasMedia && !loader && OCMedia.get(data.media) && !OCMedia.get(data.media).missing)) loadSource(data);
    if (player) {
      const key = [data.sync, data.tc_start_ms, data.loop, data.muted].join("|");
      if (key !== lastPlayerKey) {
        lastPlayerKey = key;
        player.setConfig({ sync: data.sync, tc_start_ms: data.tc_start_ms, loop: data.loop, muted: data.muted });
        player.video.muted = !!data.muted;
      }
    }
    sim.invalidate();
  }

  const unsubscribe = window.OCMedia ? OCMedia.subscribe(() => { if (!dead) update(); }) : () => {};          // die Medienliste hat sich geaendert (Medium kam dazu / fehlt)
  const hook = () => {                                                                                    // laufendes Video: weiterzeichnen; Seitenverhaeltnis nachtragen
    if (!player) return;
    const v = player.video;
    if (v.videoHeight && !mediaAspect) { mediaAspect = v.videoWidth / v.videoHeight; uniforms.uMedia.value = mediaAspect; }
    if ((!v.paused && !v.ended) || v.seeking || performance.now() < activeUntil) sim.keepAlive();
  };
  sim.frameHooks.push(hook);
  update();

  return {
    mesh, update,
    get hasMedia() { return hasMedia; },
    get mediaAspect() { return mediaAspect; },
    get player() { return player; },
    get material() { return mesh.material; },
    /** Neuer Objekt-Eintrag (nach dem Neuaufbau der Buehne uebernimmt der Belag die laufende Wiedergabe). */
    attach(next) { entry = next; entry.group.add(mesh); update(); },
    dispose() {
      dead = true;
      unsubscribe();
      const i = sim.frameHooks.indexOf(hook);
      if (i >= 0) sim.frameHooks.splice(i, 1);
      releaseSource();
      if (mesh.parent) mesh.parent.remove(mesh);
      glowing.dispose();
      wall.dispose();
    },
  };
}

/* Panel "3D-Simulation" (Schritt 1: Ansicht; Schritt 2: Baumodus, siehe sim3d_build.js): eine leere 3D-Buehne, die die ganze Panel-Flaeche fuellt - Boden mit Raster und ein Koordinatensystem (Z nach oben,
 * Meter: X rot, Y gruen, Z blau). Die Kamera laesst sich bewegen: Maus - links ziehen = drehen, rechts/Mitte ziehen = verschieben, Rad = zoomen;
 * Touch - ein Finger = drehen, zwei Finger = zoomen und verschieben (Pinch); Doppelklick oder der Pfeil-Knopf = Ansicht zuruecksetzen; der Vollbild-Knopf legt
 * die Buehne ueber die ganze Oberflaeche (eigenes Vollbild wie bei Video/Livestream, siehe fullscreen.js). Die Kamera darf bis auf den Boden herunter.
 * Leistung: gezeichnet wird nur bei Bedarf, die Schattenkarten nur bei Aenderungen der Szene (nicht beim Kamerafahren). Die Aufloesung folgt einem Pixelbudget (Megapixel), das je nach
 * Grafikkarte startet und sich im Modus "Auto" an die gemessene Bildrate anpasst; der Knopf unten links zeigt Bildrate/Grafikkarte und schaltet Niedrig/Mittel/Hoch um.
 * Aussehen wie die Vorlage (_old/3d-Bühne-Vorlage.html): ACES-Tonemapping, leichter Nebel, Schatten PCF. three.js liegt lokal in static/vendor/three (Import-Map in index.html). */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { attachBuilder } from "/static/js/sim3d_build.js";
import { createRoom } from "/static/js/sim3d_room.js";

/** Farbe eines Theme-Tokens (z. B. --surface-1) als THREE.Color: die Buehne folgt dem globalen Stil (neutrales Grau) statt eigener Blautoene. */
function themeColor(host, name, fallback) {
  try {
    const probe = document.createElement("div");
    probe.style.cssText = "position:absolute;visibility:hidden;color:var(" + name + ")";
    host.appendChild(probe);
    const value = getComputedStyle(probe).color;
    probe.remove();
    const color = new THREE.Color();
    color.setStyle(value);
    return color;
  } catch (err) {
    return new THREE.Color(fallback);
  }
}

// Helligkeitsumsetzung (Tonemapping) mit erhaltenem Farbton: nur der hellste Kanal wird weich begrenzt, die Verhaeltnisse der Kanaele bleiben. So macht Licht eine Flaeche nur heller und
// mischt kein Weiss in ihre Farbe (ACES/Neutral/Cineon bleichen ueberbelichtete Farben aus). Die Ueberschrift dafuer ist der "CustomToneMapping"-Platzhalter von three.js.
THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment.replace("vec3 CustomToneMapping( vec3 color ) { return color; }", `vec3 CustomToneMapping( vec3 color ) {
  color *= toneMappingExposure;
  float peak = max( color.r, max( color.g, color.b ) );
  const float knee = 0.55;
  if ( peak <= knee ) return color;
  float mapped = knee + ( 1.0 - knee ) * ( 1.0 - exp( -( peak - knee ) / ( 1.0 - knee ) ) );
  return color * ( mapped / peak );
}`);

// Farbabstrahlung (color bleeding): helle Flaechen strahlen etwas Licht in ihrer Farbe auf ihre Umgebung zurueck (ein blauer Quader faerbt die Waende neben sich bläulich). Rein diffus,
// ohne Glanzlicht und ohne Punktlicht (die ergaben grelle Punkte); jede Flaeche des Stage-Materials bekommt den Zusatz im Shader. Die Werte setzt sim3d_room.js je Bild (Ansichtsraum).
const BLEED_MAX = 48;
const BLEED_GLSL = `
{
  vec3 bleedPos = -vViewPosition;
  vec3 bleedLight = vec3( 0.0 );
  for ( int i = 0; i < 48; i ++ ) {
    if ( i >= uBleedCount ) break;
    vec3 toPatch = uBleedPos[ i ].xyz - bleedPos;
    float d2 = dot( toPatch, toPatch );
    float r2 = uBleedPos[ i ].w * uBleedPos[ i ].w;
    float facing = 0.05 + 0.95 * max( dot( geometryNormal, toPatch * inversesqrt( max( d2, 1e-6 ) ) ), 0.0 );
    bleedLight += uBleedCol[ i ] * ( r2 / ( d2 + r2 ) ) * facing;
  }
  reflectedLight.indirectDiffuse += bleedLight * BRDF_Lambert( material.diffuseColor );
}`;
const HOME = { position: [9, -11, 7], target: [0, 0, 0.8] };
const TOUCH = typeof matchMedia === "function" && matchMedia("(pointer: coarse)").matches;
const PIXEL_BUDGETS = [0.6, 1.0, 1.6, 2.4, 3.6, 5.5];  // Megapixel, auf die die Aufloesung begrenzt wird (Stufe 0 ... 5)
const AUTO_MAX = 4;                                    // "Auto" geht bis Stufe 4 (3,6 MP); Stufe 5 nur ueber "Hoch"
const MANUAL_LEVEL = { low: 1, medium: 2, high: 4 };
const QUALITY_STORE = "oc-sim3d-quality";
const LIMITS_STORE = "oc-sim3d-limits";
const LIMIT_DEFAULTS = { maxLights: 32, maxShadows: 0, maxSpecular: 8 };       // 0 = unbegrenzt (maxShadows 0 = so viele, wie die Grafikkarte kann)
const SHADOW_SIZES = [512, 512, 1024, 1024, 2048, 2048];       // Schattenkarte je Stufe
const MIN_CAMERA_Z = 0.05;                            // die Kamera darf bis knapp auf den Boden (Meter)

/** Grafikkarte erkennen (Name, Software-Rendering?, Startstufe) - ueber einen Wegwerf-Kontext, weil das Antialiasing vor dem echten Kontext feststehen muss. */
function probeGpu() {
  let name = "";
  try {
    const gl = document.createElement("canvas").getContext("webgl2") || document.createElement("canvas").getContext("webgl");
    const ext = gl && gl.getExtension("WEBGL_debug_renderer_info");
    name = ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : "";
    const lose = gl && gl.getExtension("WEBGL_lose_context");
    if (lose) lose.loseContext();
  } catch (err) { /* ohne Angabe: mittlere Stufe */ }
  const software = /swiftshader|llvmpipe|software|basic render|microsoft basic|softpipe/i.test(name);
  let start = 2;                                                              // unbekannt: vorsichtig (1,6 MP)
  if (software) start = 1;
  else if (/apple|nvidia|geforce|rtx|gtx|radeon rx|radeon pro|quadro/i.test(name)) start = 4;
  else if (/intel|uhd|iris|hd graphics|mali|adreno|powervr/i.test(name)) start = 1;
  if (TOUCH) start = Math.min(start, 4);
  return { name, software, start };
}

function injectStyle() {
  if (document.getElementById("sim3d-style")) return;
  const style = document.createElement("style");
  style.id = "sim3d-style";
  style.textContent = `
    [data-panel-type="sim3d"] .panel__content { padding: 0; display: flex; overflow: hidden; }
    .sim3d { container-type: inline-size; position: relative; flex: 1 1 auto; width: 100%; height: 100%; min-width: 0; min-height: 0; overflow: hidden; background: var(--bg); }
    .sim3d__canvas { display: block; position: absolute; inset: 0; width: 100%; height: 100%; touch-action: none; }
    .sim3d__tools { position: absolute; top: max(0.5rem, env(safe-area-inset-top)); right: max(0.5rem, env(safe-area-inset-right)); z-index: 2; display: flex; gap: 0.4rem; }
    .sim3d { --side: clamp(17rem, 38%, 28rem); outline: none; }
    .sim3d__tools { transition: right 0.28s ease; }
    .sim3d--build .sim3d__tools { right: calc(var(--side) + 0.5rem); }
    .sim3d__modes { position: absolute; top: max(0.5rem, env(safe-area-inset-top)); left: max(0.5rem, env(safe-area-inset-left)); z-index: 2; display: inline-flex;
      border: 1px solid var(--border-color); border-radius: var(--base-radius, 3px); overflow: hidden; background: color-mix(in srgb, var(--surface-1) 85%, transparent); }
    .sim3d__mode { display: inline-flex; align-items: center; gap: 0.35rem; min-height: 2.25rem; padding: 0 0.75rem; background: transparent; border: 0; border-right: 1px solid var(--border-color);
      color: var(--secondary-text); font: inherit; font-size: 0.9rem; cursor: pointer; white-space: nowrap; }
    .sim3d__mode:last-child { border-right: 0; }
    .sim3d__mode--on { background: var(--accent-color); color: var(--accent-ink, #000); font-weight: 600; }
    .sim3d__mode .ico { width: 1.15rem; height: 1.15rem; }
    .sim3d__side { position: absolute; top: 0; right: 0; bottom: 0; width: var(--side); z-index: 3; overflow: auto; box-sizing: border-box; padding: 0.6rem; display: flex; flex-direction: column; gap: 0.7rem;
      background: color-mix(in srgb, var(--panel-bg) 96%, transparent); border-left: 1px solid var(--border-color); color: var(--text-main); font-size: 0.85rem;
      transform: translateX(100%); transition: transform 0.28s ease; }
    .sim3d__side--in { transform: none; }
    .sim3d__side[hidden] { display: none; }
    .sim3d__group { display: flex; flex-direction: column; gap: 0.4rem; }
    .sim3d__title { margin: 0; font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--secondary-text); }
    .sim3d__add { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.4rem; }
    .sim3d__row { display: flex; gap: 0.4rem; align-items: center; }
    .sim3d__btn.sim3d__btn--wide { width: auto; flex: 1 1 0; gap: 0.45rem; padding: 0 0.6rem; height: 2.5rem; font: inherit; justify-content: flex-start; }
    .sim3d__btn.sim3d__btn--danger { color: var(--error, #e5484d); }
    .sim3d__list { list-style: none; margin: 0; padding: 0; border: 1px solid var(--border-color); border-radius: var(--base-radius, 3px); max-height: 12rem; overflow: auto; }
    .sim3d__item { display: flex; align-items: center; gap: 0.5rem; min-height: 2.5rem; padding: 0 0.6rem; border-bottom: 1px solid var(--border-color); cursor: pointer; }
    .sim3d__item:last-child { border-bottom: 0; }
    .sim3d__item--sel { background: var(--accent-soft, rgba(255, 176, 0, 0.2)); }
    .sim3d__item-name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sim3d__item-tag { font-size: 0.7rem; color: var(--secondary-text); }
    .sim3d__item--off .sim3d__item-name { opacity: 0.45; text-decoration: line-through; }
    .sim3d__eye { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; width: 2rem; height: 2rem; margin-right: -0.4rem; background: transparent; border: 0; color: var(--text-main); cursor: pointer; border-radius: var(--base-radius, 3px); }
    .sim3d__eye:hover { color: var(--accent-color); }
    .sim3d__item--off .sim3d__eye { color: var(--secondary-text); }
    .sim3d__eye .ico { width: 1.15rem; height: 1.15rem; }
    .sim3d__swatch { width: 0.9rem; height: 0.9rem; border-radius: 2px; border: 1px solid var(--border-color); flex: 0 0 auto; }
    .sim3d__empty, .sim3d__hint { color: var(--secondary-text); padding: 0.5rem 0.2rem; margin: 0; font-size: 0.8rem; }
    .sim3d__list .sim3d__empty { padding: 0.6rem; }
    .sim3d__grid { display: grid; grid-template-columns: 4.2rem repeat(3, minmax(0, 1fr)); gap: 0.25rem; align-items: center; }
    .sim3d__grid label { color: var(--secondary-text); font-size: 0.78rem; }
    .sim3d__field { display: inline-flex; align-items: center; gap: 0.15rem; min-width: 0; height: 2.5rem; padding: 0 0.3rem; box-sizing: border-box; background: var(--bg-color);
      border: 1px solid var(--border-color); border-radius: var(--base-radius, 3px); }
    .sim3d__field:focus-within { border-color: var(--accent-color); }
    .sim3d__num { flex: 1 1 auto; min-width: 0; width: 100%; height: 100%; padding: 0; border: 0; background: transparent; color: var(--text-main); font: inherit; text-align: right; outline: none; }
    .sim3d__axis, .sim3d__unit { flex: 0 0 auto; font-size: 0.68rem; color: var(--secondary-text); }
    .sim3d__text { flex: 1 1 auto; min-width: 0; height: 2.5rem; box-sizing: border-box; padding: 0 0.5rem; background: var(--bg-color); border: 1px solid var(--border-color);
      border-radius: var(--base-radius, 3px); color: var(--text-main); font: inherit; }
    .sim3d__color { flex: 0 0 3rem; width: 3rem; height: 2.5rem; padding: 0; border: 1px solid var(--border-color); background: transparent; border-radius: var(--base-radius, 3px); cursor: pointer; }
    @container (max-width: 40rem) { .sim3d__mode-label { display: none; } .sim3d__mode { padding: 0 0.6rem; } }
    .sim3d__btn { display: inline-flex; align-items: center; justify-content: center; width: 2.25rem; height: 2.25rem;
      background: color-mix(in srgb, var(--surface-1) 85%, transparent); border: 1px solid var(--border-color); border-radius: var(--base-radius, 3px); color: var(--text-main); cursor: pointer; }
    .sim3d__btn:hover { border-color: var(--accent-color); }
    .sim3d__btn .ico { width: 1.15rem; height: 1.15rem; }
    .sim3d__readout { position: absolute; z-index: 5; pointer-events: none; padding: 0.15rem 0.55rem; background: var(--surface-3); border: 1px solid var(--accent-color);
      border-radius: 1rem; color: #fff; font-size: 0.8rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .sim3d__readout[hidden] { display: none; }
    .sim3d__stage { display: flex; align-items: center; gap: 0.4rem; }
    .sim3d__stage-name { flex: 1 1 auto; min-width: 0; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sim3d__btn:disabled { opacity: 0.4; cursor: default; }
    .sim3d__btn { position: relative; }
    .sim3d__badge { display: none; position: absolute; top: -0.3rem; right: -0.3rem; width: 0.8rem; height: 0.8rem; border-radius: 50%; background: #e5484d; border: 2px solid var(--panel-bg); }
    .sim3d__btn.sim3d__btn--attention { background: var(--accent-color); border-color: var(--accent-color); color: var(--accent-ink, #1a1200); font-weight: 600; box-shadow: 0 0 0.9rem color-mix(in srgb, var(--accent-color) 55%, transparent); }
    .sim3d__btn--attention .sim3d__badge { display: block; }
    .sim3d__slider { display: grid; grid-template-columns: 7.2rem minmax(0, 1fr) 3.4rem; gap: 0.4rem; align-items: center; min-height: 2.25rem; }
    .sim3d__slider label { color: var(--secondary-text); font-size: 0.78rem; }
    .sim3d__slider-value { text-align: right; font-size: 0.78rem; font-variant-numeric: tabular-nums; }
    .sim3d__aimbar { position: absolute; z-index: 6; left: max(0.5rem, env(safe-area-inset-left)); top: calc(max(0.5rem, env(safe-area-inset-top)) + 2.25rem + 0.55rem); display: inline-flex; max-width: calc(100% - 1rem);
      border: 1px solid var(--accent-color); border-radius: var(--base-radius, 3px); overflow: hidden; background: color-mix(in srgb, var(--surface-1) 90%, transparent); color: var(--text-main); }
    .sim3d__aimbar[hidden] { display: none; }
    .sim3d__aimbar-main { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 2.25rem; padding: 0 0.8rem; font-size: 0.9rem; min-width: 0; }
    .sim3d__aimbar-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .sim3d__aimbar .ico { width: 1.15rem; height: 1.15rem; flex: 0 0 auto; }
    .sim3d__aimbar-main .ico { color: var(--accent-color); }
    .sim3d__aimbar-done { display: inline-flex; align-items: center; gap: 0.35rem; min-height: 2.25rem; padding: 0 0.85rem; border: 0; border-left: 1px solid var(--accent-color); background: var(--accent-color);
      color: var(--accent-ink, #000); font: inherit; font-size: 0.9rem; font-weight: 600; cursor: pointer; white-space: nowrap; }
    .sim3d__aimbar-done:hover { filter: brightness(1.08); }
    .sim3d__range { width: 100%; accent-color: var(--accent-color); height: 2rem; }
    .sim3d__btn.sim3d__btn--on { border-color: var(--accent-color); background: var(--accent-soft, rgba(255, 176, 0, 0.18)); }
    .sim3d__btn.sim3d__btn--blackout { color: var(--warn, #ffb000); }
    .sim3d__btn.sim3d__btn--blackout.sim3d__btn--on { color: var(--error, #e5484d); border-color: var(--error, #e5484d); background: color-mix(in srgb, var(--error, #e5484d) 16%, transparent); box-shadow: 0 0 0.7rem color-mix(in srgb, var(--error, #e5484d) 55%, transparent); }
    .sim3d__snap-label { color: var(--secondary-text); font-size: 0.8rem; }
    .sim3d__select { flex: 1 1 auto; min-width: 0; height: 2.5rem; padding: 0 0.4rem; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: var(--base-radius, 3px);
      color: var(--text-main); font: inherit; }
    .sim3d__quality { position: absolute; left: max(0.5rem, env(safe-area-inset-left)); bottom: max(0.5rem, env(safe-area-inset-bottom)); z-index: 2; min-height: 2rem; padding: 0 0.6rem;
      background: color-mix(in srgb, var(--surface-1) 80%, transparent); border: 1px solid var(--border-color); border-radius: var(--base-radius, 3px); color: var(--secondary-text);
      font: inherit; font-size: 0.72rem; font-variant-numeric: tabular-nums; cursor: pointer; white-space: nowrap; }
    .sim3d__quality:hover { border-color: var(--accent-color); color: var(--text-main); }
    .sim3d__quality--warn { border-color: #e5484d; color: #e5484d; }
    .sim3d__nogl { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; padding: 1rem; text-align: center; color: var(--secondary-text); }
  `;
  document.head.appendChild(style);
}

function createScene(host) {
  const gpu = probeGpu();
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: !gpu.software, powerPreference: "high-performance" });
  } catch (err) {
    return null;
  }
  const canvas = renderer.domElement;
  canvas.className = "sim3d__canvas";
  host.appendChild(canvas);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.CustomToneMapping;              // erhaelt den Farbton (siehe oben): Licht macht heller, mischt kein Weiss dazu
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;                        // Schattenkarten nur bei Aenderungen der Szene (invalidate), nicht bei jedem Kamerabild
  renderer.shadowMap.needsUpdate = true;

  const scene = new THREE.Scene();
  const bg = themeColor(host, "--bg", 0x0c0c0d);
  scene.background = bg;
  scene.fog = new THREE.FogExp2(bg, 0.004 + 0.4 * 0.016);       // leichter Dunst wie in der Vorlage (Dichte folgt dem Nebel-Regler des Scheinwerfers)
  const setHaze = (fraction) => {
    const density = 0.004 + Math.max(0, Math.min(1, fraction)) * 0.016;
    if (Math.abs(density - scene.fog.density) < 1e-6) return;          // unveraendert: kein neues Bild (wird aus dem Bildhaken aufgerufen)
    scene.fog.density = density;
    invalidate();
  };

  const bleed = { pos: Array.from({ length: BLEED_MAX }, () => new THREE.Vector4()), col: Array.from({ length: BLEED_MAX }, () => new THREE.Vector3()), count: { value: 0 } };
  const bleedUniforms = { uBleedPos: { value: bleed.pos }, uBleedCol: { value: bleed.col }, uBleedCount: bleed.count };
  const patchBleed = (material) => {
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, bleedUniforms);
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <common>", "#include <common>\nuniform vec4 uBleedPos[" + BLEED_MAX + "];\nuniform vec3 uBleedCol[" + BLEED_MAX + "];\nuniform int uBleedCount;")
        .replace("#include <lights_fragment_end>", "#include <lights_fragment_end>\n" + BLEED_GLSL);
    };
    material.customProgramCacheKey = () => "bleed" + BLEED_MAX;
    return material;
  };

  // Boden: dunkle Flaeche + Raster (1 m) in der XY-Ebene (Z nach oben)
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), patchBleed(new THREE.MeshStandardMaterial({ color: themeColor(host, "--surface-1", 0x161618), roughness: 0.95, metalness: 0 })));
  floor.position.z = -0.002;
  floor.receiveShadow = true;                           // faengt Schatten und Licht der Scheinwerfer
  scene.add(floor);
  const grid = new THREE.GridHelper(40, 40, themeColor(host, "--border-strong", 0x4a4a51), themeColor(host, "--border", 0x2a2a2e));
  grid.rotation.x = Math.PI / 2;
  scene.add(grid);
  const helpers = [grid];                                // Raster und Achsen (im Fenster "Raum & Licht" ausblendbar)

  // Koordinatensystem: X rot, Y gruen, Z blau (je 2 m, mit Spitze)
  const arrows = [[[1, 0, 0], 0xff4d4d], [[0, 1, 0], 0x4dff7a], [[0, 0, 1], 0x4d9dff]];
  for (const [dir, color] of arrows) {
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(...dir), new THREE.Vector3(0, 0, 0.003), 2, color, 0.35, 0.18);
    scene.add(arrow);
    helpers.push(arrow);
  }

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
  camera.up.set(0, 0, 1);
  camera.position.set(...HOME.position);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(...HOME.target);
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;
  controls.screenSpacePanning = true;                   // Verschieben folgt dem Bildschirm (auch bei der Zwei-Finger-Geste)
  controls.minDistance = 1;
  controls.maxDistance = 80;
  controls.maxPolarAngle = Math.PI * 0.56;              // bis knapp ueber den Boden und leicht nach oben schauen (die Kamera selbst bleibt ueber dem Boden, siehe frame())
  controls.rotateSpeed = 0.9;
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  controls.update();

  let wake = false;                                      // ein Bildhaken (Live-Licht) animiert noch: im naechsten Takt weiterzeichnen
  const sceneVersion = { n: 0 };                         // zaehlt Aenderungen der Szene (das Raummodell des Raumlichts wird nur dann neu berechnet)
  let destroyed = false;
  let raf = 0;
  let flight = 0;
  const onDestroy = [];
  const frameHooks = [];                                 // vor jedem Zeichnen aufgerufen (z. B. Griffe in Bildschirmgroesse halten)
  let shiftPx = 0;                                       // seitliche Bildverschiebung (Seitenleiste offen: die Mitte der Buehne rueckt in die Mitte des freien Bereichs)
  let shiftAnim = 0;
  const frame = () => {
    raf = 0;
    if (destroyed) return;
    if (!host.isConnected) { destroy(); return; }       // Panel wurde entfernt
    if (inflight.length >= 2) { invalidateView(); return; }       // die Grafikkarte hinkt hinterher: kein weiteres Bild vorbestellen (sonst staut sich Arbeit und alles haengt)
    const moving = controls.update();                    // true, solange die Daempfung noch nachlaeuft
    if (camera.position.z < MIN_CAMERA_Z) camera.position.z = MIN_CAMERA_Z;       // nicht unter den Boden: die Kamera gleitet am Boden entlang
    if (controls.target.z < 0) controls.target.z = 0;
    wake = false;
    frameHooks.forEach((fn) => fn());
    renderer.render(scene, camera);
    track();
    if (moving || wake) invalidateView();                // nie zwei Ketten: invalidateView plant nur, wenn noch nichts geplant ist (wake: ein Bildhaken animiert noch, z. B. Live-Licht)
  };
  const invalidateView = () => { if (!raf && !destroyed) raf = requestAnimationFrame(frame); };           // nur die Kamera hat sich bewegt: Schattenkarten bleiben
  const invalidate = () => { sceneVersion.n += 1; renderer.shadowMap.needsUpdate = true; invalidateView(); };                  // die Szene hat sich geaendert
  controls.addEventListener("change", invalidateView);
  controls.addEventListener("start", () => { interacting = true; clearTimeout(settle); });
  controls.addEventListener("end", () => { clearTimeout(settle); settle = setTimeout(() => { interacting = false; }, 300); });

  // Aufloesung: Pixelbudget (Megapixel) statt fester Skalierung. "Auto" misst die Bildrate waehrend der Bewegung und passt die Stufe an (selten, damit der Puffer nicht dauernd neu angelegt wird);
  // die Aufloesung bleibt waehrend der Bewegung gleich (Umschalten kostet auf manchen Grafikkarten ein spuerbares Haengen).
  let interacting = false;
  let settle = 0;
  let setting = "auto";                                  // auto | low | medium | high
  try { const saved = localStorage.getItem(QUALITY_STORE); if (saved === "low" || saved === "medium" || saved === "high") setting = saved; } catch (err) { /* ohne Speicher: Auto */ }
  let autoLevel = Math.min(gpu.start, AUTO_MAX);
  let autoCap = AUTO_MAX;                                // wird gesenkt, wenn eine hoehere Stufe nicht hielt
  const level = () => (setting === "auto" ? autoLevel : MANUAL_LEVEL[setting]);
  const quality = { get level() { return level(); }, get shadowSize() { return SHADOW_SIZES[level()]; }, get setting() { return setting; }, setSetting: (next) => setSetting(next), gpu, listeners: [] };
  // Grenzen des Lichtvorrats (je Geraet, gespeichert im Browser): wie viele Scheinwerfer gleichzeitig ihr eigenes Licht auf die Flaechen werfen, wie viele davon mit Schatten und wie viele
  // Spiegel-Strahlen (Metall/Spiegel). 0 = unbegrenzt - es zaehlt dann nur, was die Grafikkarte leisten kann (limits.gpu: Texturen und Shader-Konstanten); live.js meldet in limits.info,
  // was tatsaechlich gilt. Ohne Grenze bekommt jeder Scheinwerfer dieselbe Behandlung (Lichtfleck, Raumlicht-Anteil, Nebel, Schatten).
  const limits = (() => {
    const values = { ...LIMIT_DEFAULTS };
    try {
      const raw = JSON.parse(localStorage.getItem(LIMITS_STORE) || "{}");
      for (const key of Object.keys(LIMIT_DEFAULTS)) if (Number.isFinite(raw[key]) && raw[key] >= 0) values[key] = Math.floor(raw[key]);
    } catch (err) { /* ohne Speicher: Standard */ }
    const listeners = [];
    const save = () => { try { localStorage.setItem(LIMITS_STORE, JSON.stringify(values)); } catch (err) { /* ohne Speicher: gilt bis zum Neuladen */ } };
    const api = {
      values, listeners, info: {}, defaults: LIMIT_DEFAULTS,
      gpu: { textures: renderer.capabilities.maxTextures || 16, vectors: renderer.getContext().getParameter(renderer.getContext().MAX_FRAGMENT_UNIFORM_VECTORS) || 224 },
      set(key, value) {
        if (!(key in LIMIT_DEFAULTS)) return;
        const n = Math.max(0, Math.floor(Number(value)));
        values[key] = Number.isFinite(n) ? n : LIMIT_DEFAULTS[key];
        save();
        listeners.forEach((fn) => fn());
        invalidate();
      },
      reset() { Object.assign(values, LIMIT_DEFAULTS); save(); listeners.forEach((fn) => fn()); invalidate(); },
    };
    return api;
  })();
  const pixelRatio = (width, height) => {
    const budget = Math.sqrt((PIXEL_BUDGETS[level()] * 1e6) / Math.max(1, width * height));
    return Math.max(0.5, Math.min(window.devicePixelRatio || 1, budget));
  };
  const resize = () => {
    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);
    renderer.setPixelRatio(pixelRatio(width, height));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    applyShift(width, height);
    invalidate();
    if (qualityButton) paintQuality();                  // Aufloesung hat sich geaendert: Anzeige unten links nachziehen
  };
  const levelChanged = () => { ignoreFrames = 2; samples = []; slowRun = 0; resize(); quality.listeners.forEach((fn) => fn()); paintQuality(); };

  // Messung: Die Zeit zwischen "Bild abgeschickt" und "Grafikkarte fertig" (Fence) - nicht die Zeit, in der das Skript das Zeichnen nur bestellt (die war bei langsamen Karten winzig und zeigte Fantasiewerte).
  // Aus dem Abstand fertiger Bilder ergibt sich die echte Bildrate; Auto passt die Stufe daran an.
  const gl = renderer.getContext();
  const inflight = [];                                   // {sync, t}: abgeschickte, noch nicht fertige Bilder
  let pollTimer = 0;
  let lastDone = 0;                                      // Zeitpunkt des zuletzt fertigen Bildes
  let lastFps = 0;
  let lastFpsAt = 0;
  let samples = [];                                      // Bildzeiten (ms)
  let slowRun = 0;                                       // aufeinanderfolgende sehr langsame Bilder
  let goodWindows = 0;
  let lastStepUp = 0;
  let ignoreFrames = 0;                                  // nach Aufloesungswechsel/Shader-Aufbau zaehlen die ersten Bilder nicht
  let paintAt = 0;
  let fpsTimer = 0;
  function track() {
    if (typeof gl.fenceSync !== "function") return;
    const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
    if (!sync) return;
    gl.flush();
    inflight.push({ sync, t: performance.now() });
    if (!pollTimer) pollTimer = setTimeout(poll, 2);
  }
  function poll() {
    pollTimer = 0;
    if (destroyed) return;
    const now = performance.now();
    while (inflight.length) {
      const f = inflight[0];
      const done = gl.getSyncParameter(f.sync, gl.SYNC_STATUS) === gl.SIGNALED;
      if (!done && now - f.t < 4000) break;
      gl.deleteSync(f.sync);
      inflight.shift();
      if (done) frameDone(f.t, now);
    }
    if (inflight.length) pollTimer = setTimeout(poll, 2);
  }
  function frameDone(submitted, now) {
    // zusammenhaengende Bilder: Abstand zum vorigen fertigen Bild; nach einer Pause: Dauer dieses einen Bildes
    const gap = submitted - lastDone;
    const dt = gap < 60 ? now - lastDone : now - submitted;
    lastDone = now;
    if (ignoreFrames > 0) { ignoreFrames -= 1; return; }
    if (dt <= 0) return;
    samples.push(dt);
    slowRun = dt > 250 ? slowRun + 1 : 0;
    if (setting === "auto" && slowRun >= 2 && autoLevel > 0) { stepDown(now, dt > 500 ? 2 : 1); return; }     // sehr langsam (unter 4 Bilder/s): sofort runter, nicht erst nach einem Messfenster
    if (samples.length < 12) return;
    const sorted = samples.slice().sort((x, y) => x - y);
    const median = sorted[6];
    samples = [];
    lastFps = Math.round(1000 / median);
    lastFpsAt = now;
    clearTimeout(fpsTimer);
    fpsTimer = setTimeout(paintQuality, 2600);              // danach die Zahl wieder ausblenden
    if (setting === "auto") {
      if (median > 26 && autoLevel > 0) { stepDown(now, 1); return; }        // unter ~38 Bilder/s: eine Stufe runter
      goodWindows = median < 18.5 ? goodWindows + 1 : 0;
      if (goodWindows >= 6 && autoLevel < autoCap) {      // dauerhaft volle Bildrate: eine Stufe hoch
        autoLevel += 1;
        goodWindows = 0;
        lastStepUp = now;
        levelChanged();
        return;
      }
    }
    if (now - paintAt > 400) { paintAt = now; paintQuality(); }
  }
  function stepDown(now, steps) {
    if (now - lastStepUp < 12000) autoCap = Math.max(0, autoLevel - steps);       // kurz nach einem Hochschalten wieder zu langsam: diese Stufe haelt nicht
    autoLevel = Math.max(0, autoLevel - steps);
    goodWindows = 0;
    slowRun = 0;
    samples = [];
    levelChanged();
  }
  function applyShift(width = host.clientWidth, height = host.clientHeight) {
    if (Math.abs(shiftPx) > 0.5) camera.setViewOffset(width, height, shiftPx, 0, width, height);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  /** Bild seitlich verschieben (Pixel; positiv = Inhalt nach links), weich. */
  const setShift = (px, animate = true) => {
    cancelAnimationFrame(shiftAnim);
    const from = shiftPx;
    const start = performance.now();
    const step = (now) => {
      const t = animate ? Math.min(1, (now - start) / 280) : 1;
      const e = t * t * (3 - 2 * t);
      shiftPx = from + (px - from) * e;
      applyShift();
      invalidateView();
      if (t < 1) shiftAnim = requestAnimationFrame(step);
    };
    shiftAnim = requestAnimationFrame(step);
  };
  let qualityButton = null;
  const observer = new ResizeObserver(resize);
  observer.observe(host);

  // Knopf unten links: Bildrate, Aufloesung und Grafikkarte; Klick = Auto -> Niedrig -> Mittel -> Hoch
  qualityButton = document.createElement("button");
  qualityButton.type = "button";
  qualityButton.className = "sim3d__quality";
  host.appendChild(qualityButton);
  const QUALITY_KEYS = { auto: "SIM3D_QUALITY_AUTO", low: "SIM3D_QUALITY_LOW", medium: "SIM3D_QUALITY_MEDIUM", high: "SIM3D_QUALITY_HIGH" };
  function paintQuality() {
    const mp = (canvas.width * canvas.height) / 1e6;
    const parts = [i18n(QUALITY_KEYS[setting])];
    if (lastFps && performance.now() - lastFpsAt < 2500) parts.push(Math.min(lastFps, 240) + " FPS");
    parts.push(mp.toFixed(1).replace(".", i18n("SIM3D_DECIMAL")) + " MP");
    qualityButton.textContent = parts.join(" · ");
    qualityButton.classList.toggle("sim3d__quality--warn", gpu.software);
    qualityButton.title = i18n("SIM3D_QUALITY_TIP") + "\n" + (gpu.name || "?") + (gpu.software ? "\n" + i18n("SIM3D_QUALITY_SOFTWARE") : "");
  }
  const SETTINGS = ["auto", "low", "medium", "high"];
  function setSetting(next) {
    if (!SETTINGS.includes(next) || next === setting) return;
    setting = next;
    try { if (setting === "auto") localStorage.removeItem(QUALITY_STORE); else localStorage.setItem(QUALITY_STORE, setting); } catch (err) { /* nur eine Bequemlichkeit */ }
    lastFps = 0;
    goodWindows = 0;
    levelChanged();
  }
  qualityButton.addEventListener("click", () => setSetting(SETTINGS[(SETTINGS.indexOf(setting) + 1) % SETTINGS.length]));
  qualityButton.addEventListener("dblclick", (e) => e.stopPropagation());
  paintQuality();
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());

  // Ansicht zuruecksetzen (weich)
  const reset = () => {
    cancelAnimationFrame(flight);
    const fromPos = camera.position.clone();
    const fromTarget = controls.target.clone();
    const toPos = new THREE.Vector3(...HOME.position);
    const toTarget = new THREE.Vector3(...HOME.target);
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / 450);
      const e = t * t * (3 - 2 * t);
      camera.position.lerpVectors(fromPos, toPos, e);
      controls.target.lerpVectors(fromTarget, toTarget, e);
      controls.update();
      invalidateView();
      if (t < 1) flight = requestAnimationFrame(step);
    };
    flight = requestAnimationFrame(step);
  };
  canvas.addEventListener("dblclick", reset);

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    cancelAnimationFrame(raf);
    clearTimeout(pollTimer);
    clearTimeout(fpsTimer);
    inflight.forEach((f) => gl.deleteSync(f.sync));
    inflight.length = 0;
    cancelAnimationFrame(flight);
    cancelAnimationFrame(shiftAnim);
    clearTimeout(settle);
    onDestroy.forEach((fn) => fn());
    observer.disconnect();
    qualityButton.remove();
    controls.dispose();
    scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose()); });
    renderer.dispose();
    renderer.forceContextLoss();
    canvas.remove();
  }

  resize();
  paintQuality();
  return { scene, camera, controls, renderer, canvas, floor, reset, invalidate, invalidateView, destroy, onDestroy, frameHooks, setShift, setHaze, quality, limits, helpers, bleed, patchBleed, lightSources: [], keepAlive: () => { wake = true; invalidateView(); }, get version() { return sceneVersion.n; } };
}

function toolButton(icon, titleKey) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "sim3d__btn";
  button.title = i18n(titleKey);
  button.setAttribute("aria-label", i18n(titleKey));
  button.appendChild(Icons.svg(icon));
  return button;
}

function buildContent() {
  injectStyle();
  const root = document.createElement("div");
  root.className = "sim3d";
  const tools = document.createElement("div");
  tools.className = "sim3d__tools";
  const resetButton = toolButton("refresh", "SIM3D_RESET");
  const fullButton = toolButton("expand", "SIM3D_FULLSCREEN");
  // Blackout: zeigt ihn (gelb, solange er aktiv ist) und schaltet ihn um - neben der Lampe fuer Raum & Licht (die wird davor eingehaengt)
  const blackoutButton = toolButton("bulb", "BLACKOUT_TITLE");
  blackoutButton.classList.add("sim3d__btn--blackout");
  blackoutButton.setAttribute("aria-pressed", "false");
  blackoutButton.addEventListener("click", () => window.__panelAPI.sendToServer("set_blackout", {}));
  blackoutButton.addEventListener("dblclick", (e) => e.stopPropagation());
  let seenConnected = false;
  const syncBlackout = () => {
    if (root.isConnected) seenConnected = true;
    else if (seenConnected) { document.removeEventListener("blackout-changed", syncBlackout); return; }       // Panel wurde entfernt
    const on = !!window.__blackout;
    blackoutButton.replaceChildren(Icons.svg(on ? "bulb-off" : "bulb"));              // Licht an = gelbe Gluehbirne, Blackout = rot und durchgestrichen
    blackoutButton.classList.toggle("sim3d__btn--on", on);
    blackoutButton.setAttribute("aria-pressed", on ? "true" : "false");
    blackoutButton.title = i18n(on ? "BLACKOUT_ACTIVE" : "BLACKOUT_TITLE");
  };
  document.addEventListener("blackout-changed", syncBlackout);
  syncBlackout();
  tools.append(blackoutButton, resetButton, fullButton);
  root.appendChild(tools);
  root._sim3d = null;

  // Vollbild ueber die ganze Oberflaeche (eigenes Vollbild, siehe fullscreen.js); Knopf und Tooltip folgen dem Zustand
  const syncFull = (on) => {
    fullButton.replaceChildren(Icons.svg(on ? "collapse" : "expand"));
    const key = on ? "SIM3D_FULLSCREEN_EXIT" : "SIM3D_FULLSCREEN";
    fullButton.title = i18n(key);
    fullButton.setAttribute("aria-label", i18n(key));
  };
  fullButton.addEventListener("click", () => { if (window.OCFullscreen) OCFullscreen.toggle(root); });
  fullButton.addEventListener("dblclick", (e) => e.stopPropagation());
  root.addEventListener("ocfullscreen", (e) => syncFull(!!e.detail));

  // WebGL erst anlegen, wenn das Panel eine Groesse hat (es ist beim Aufbau noch nicht eingehaengt)
  const waiter = new ResizeObserver(() => {
    if (root._sim3d || !root.isConnected) return;
    if (root.clientWidth < 8 || root.clientHeight < 8) return;
    waiter.disconnect();
    const sim = createScene(root);
    if (!sim) {
      const msg = document.createElement("div");
      msg.className = "sim3d__nogl";
      msg.textContent = i18n("SIM3D_NO_WEBGL");
      root.appendChild(msg);
      return;
    }
    root._sim3d = sim;
    try {
      sim.room = createRoom(sim, root, tools);
    } catch (err) {                                                  // ein Fehler im Raum-Fenster darf Umschalter und Bauen nicht verhindern
      console.error("Raum & Licht konnte nicht aufgebaut werden:", err);
      sim.room = { work: 100, envScale: 1, ambient: 0, pool: [], setMode() {}, onEnv() {}, update() {}, dispose() {} };
    }
    sim.onDestroy.push(() => sim.room.dispose());
    root._builder = attachBuilder(root, sim);
    sim.onDestroy.push(() => root._builder && root._builder.dispose());
    resetButton.addEventListener("click", () => sim.reset());
  });
  waiter.observe(root);
  return root;
}

/** Der Server meldet Aenderungen der Scheinwerfer der Show: das Panel gleicht seine Scheinwerfer-Koerper und -Liste ab. */
function onMessage(panelEl, messageType) {
  const root = panelEl && panelEl.querySelector ? panelEl.querySelector(".sim3d") : null;
  const builder = root && root._builder;
  if (!builder) return;
  if (messageType === "grand_master_changed" && builder.liveChanged) builder.liveChanged();           // Grand Master wirkt auf die Helligkeit der Lichtkegel
  if ((messageType === "fixtures_changed" || messageType === "state_snapshot" || messageType === "show_loaded") && builder.fixturesChanged) builder.fixturesChanged();
}

export const plugin = { type: "sim3d", buildContent, onMessage };

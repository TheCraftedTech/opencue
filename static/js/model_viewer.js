/* 3D-Betrachter fuer Scheinwerfer-Modelle - gemeinsame 3D-Engine: three.js (lokal in static/vendor/three, MIT, kein Internet noetig).
 * Zeigt den Geometrie-Baum einer GDTF (Netze aus den 3D-Dateien oder Grundformen, vom Server aufbereitet: app/gdtf_model.py), mit Boden-Raster,
 * Schatten, Strahl-Kegel und Pan/Tilt zum Bewegen. Koordinaten wie in GDTF: Z nach oben, Meter, der Scheinwerfer haengt (Strahl nach -Z).
 * Bedienung (OrbitControls): ziehen = drehen, Mausrad / Zwei-Finger = zoomen, Rechtsklick- oder Umschalt-Ziehen / Zwei-Finger-Ziehen = verschieben,
 * Doppelklick = zuruecksetzen. Als ES-Modul geladen (Import-Map in index.html); stellt window.OCModelViewer bereit.
 * buildFixture() liefert ein Scheinwerfer-Objekt (Group) fuer beliebige Szenen: Grundlage fuer ein spaeteres 3D-Buehnen-Panel mit vielen Geraeten. */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const b64 = (text) => {
  const raw = atob(text);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return bytes.buffer;
};

const LENS_COLOR = 0xf5eecd;

/** Scheinwerfer als three.js-Objekt aus den Daten von /api/library/installed/<id>/model.
 * Gibt {group, axes, beamNodes, lensMaterial, setAngles(pan, tilt), setBeam(on), dispose()} zurueck; group liegt im GDTF-Koordinatensystem (Z oben).
 * beamNodes: die Linsen (Object3D, Strahl zeigt nach -Z, mit Oeffnungswinkel in Grad) - Grundlage der 3D-Buehne fuer Lichtkegel und Scheinwerfer-Licht. */
function buildFixture(data, options) {
  const opts = { castShadow: true, beam: true, beamMesh: true, shareGeometry: false, ...(options || {}) };
  const group = new THREE.Group();
  group.name = "fixture";
  const geometries = [];
  const materials = [];
  // shareGeometry (3D-Simulation: viele Geraete desselben Typs): die Netze werden einmal je Daten-Objekt entschluesselt und von allen Instanzen benutzt;
  // sie gehoeren dann nicht der Instanz (dispose() raeumt sie nicht ab, das macht disposeShared(data) am Ende).
  const decode = () => {
    const out = {};
    const owned = [];
    Object.entries(data.models || {}).forEach(([key, parts]) => {
      out[key] = parts.map((p) => {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(b64(p.pos)), 3));
        geometry.setAttribute("normal", new THREE.BufferAttribute(new Float32Array(b64(p.nrm)), 3));
        geometry.setIndex(new THREE.BufferAttribute(p.index_bits === 32 ? new Uint32Array(b64(p.idx)) : new Uint16Array(b64(p.idx)), 1));
        geometry.computeBoundingSphere();
        owned.push(geometry);
        return { geometry, color: new THREE.Color().setRGB(p.color[0], p.color[1], p.color[2], THREE.SRGBColorSpace), opacity: p.opacity };
      });
    });
    return { models: out, owned };
  };
  let models;
  if (opts.shareGeometry) {
    if (!data.__shared) Object.defineProperty(data, "__shared", { value: decode(), enumerable: false });
    models = data.__shared.models;
  } else {
    const decoded = decode();
    models = decoded.models;
    geometries.push(...decoded.owned);
  }

  const nodes = [];
  const byId = new Map();
  const beams = [];
  const beamNodes = [];
  const lensMaterial = new THREE.MeshStandardMaterial({ color: LENS_COLOR, emissive: LENS_COLOR, emissiveIntensity: 0.55, roughness: 0.25, metalness: 0, side: THREE.DoubleSide });
  materials.push(lensMaterial);
  const build = (node, parent) => {
    const object = new THREE.Group();
    object.name = node.name || node.type;
    object.matrixAutoUpdate = false;
    const base = new THREE.Matrix4().set(...node.matrix);            // GDTF: zeilenweise, Verschiebung in der letzten Spalte
    object.matrix.copy(base);
    parent.add(object);
    const entry = { id: node.id, object, base };
    nodes.push(entry);
    byId.set(node.id, entry);
    (models[node.model] || []).forEach((part) => {
      let material;
      if (node.beam) {
        material = lensMaterial;
      } else {
        material = new THREE.MeshStandardMaterial({ color: part.color, roughness: 0.52, metalness: 0.3, side: THREE.DoubleSide, transparent: part.opacity < 0.98, opacity: part.opacity });
        materials.push(material);
      }
      const mesh = new THREE.Mesh(part.geometry, material);
      mesh.castShadow = opts.castShadow && !node.beam;
      mesh.receiveShadow = true;
      object.add(mesh);
    });
    if (node.beam) {
      beamNodes.push({ object, angle: Math.min(Math.max(node.beam.angle || 20, 1), 160), radius: Math.max(node.beam.radius || 0.02, 0.01) });
      if (opts.beamMesh) {                                            // beamMesh: false (3D-Simulation zeichnet den Kegel selbst): keine Geometrie und kein Material
        const length = Math.max(Number(data.beam_length) || 0, 0.9);               // Strahl: Laenge etwa 3 Geraetehoehen, blendet nach hinten aus
        const r0 = Math.max(node.beam.radius || 0.02, 0.01);
        const half = (Math.min(Math.max(node.beam.angle || 20, 1), 160) * Math.PI) / 360;
        const r1 = r0 + length * Math.tan(half);
        const cone = new THREE.CylinderGeometry(r1, r0, length, 48, 1, true);   // Achse Y -> nach -Z drehen: oben (r0) am Beam-Knoten, unten (r1) weit weg
        cone.rotateX(Math.PI / 2);
        cone.translate(0, 0, -length / 2);
        geometries.push(cone);
        const positions = cone.getAttribute("position");
        const colors = new Float32Array(positions.count * 4);
        for (let i = 0; i < positions.count; i += 1) {                    // Farbverlauf: am Geraet hell (Alpha 0.34), nach hinten bis 0
          const t = Math.min(Math.max(-positions.getZ(i) / length, 0), 1);
          colors.set([1, 0.93, 0.7, 0.34 * (1 - t) * (1 - t)], i * 4);
        }
        cone.setAttribute("color", new THREE.BufferAttribute(colors, 4));
        const material = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
        materials.push(material);
        const mesh = new THREE.Mesh(cone, material);
        mesh.visible = opts.beam;
        object.add(mesh);
        beams.push(mesh);
      }
    }
    (node.children || []).forEach((child) => build(child, object));
  };
  build(data.root, group);

  const axes = data.axes || {};
  const angles = { pan: 0, tilt: 0 };
  const rot = new THREE.Matrix4();
  function apply() {
    const update = (node, angle, makeRotation) => {
      const entry = byId.get(node);
      if (!entry) return;
      entry.object.matrix.copy(entry.base).multiply(makeRotation(rot, THREE.MathUtils.degToRad(angle)));
      entry.object.matrixWorldNeedsUpdate = true;
    };
    if (axes.pan) update(axes.pan.node, angles.pan, (m, a) => m.makeRotationZ(a));      // Pan dreht um Z
    if (axes.tilt) update(axes.tilt.node, angles.tilt, (m, a) => m.makeRotationX(a));    // Tilt dreht um X
    group.updateMatrixWorld(true);
  }
  group.updateMatrixWorld(true);

  return {
    group,
    axes,
    beamNodes,
    lensMaterial,
    setAngles(pan, tilt) { angles.pan = Number(pan) || 0; angles.tilt = Number(tilt) || 0; apply(); },
    getAngles() { return { pan: angles.pan, tilt: angles.tilt }; },
    setBeam(on) { beams.forEach((m) => { m.visible = !!on; }); },
    dispose() {
      geometries.forEach((g) => g.dispose());
      materials.forEach((m) => m.dispose());
    },
  };
}

/** host: Element, in das ein <canvas> gelegt wird; data: Antwort von /model. Gibt null zurueck, wenn WebGL fehlt. */
function create(host, data, options) {
  const opts = { beam: true, grid: true, ...(options || {}) };
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  } catch (err) {
    return null;
  }
  const canvas = renderer.domElement;
  canvas.className = "mv__canvas";
  canvas.style.touchAction = "none";
  host.appendChild(canvas);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14161b);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment = pmrem.fromScene(room, 0.04);
  scene.environment = environment.texture;                          // weiches Studio-Licht fuer die Reflexe auf den Metallteilen
  scene.environmentIntensity = 0.9;

  const box = data.bounds || [-0.2, -0.2, -0.2, 0.2, 0.2, 0.2];
  const fixture = buildFixture({ ...data, beam_length: Math.hypot(box[3] - box[0], box[4] - box[1], box[5] - box[2]) * 1.6 }, { beam: opts.beam });
  scene.add(fixture.group);

  const center = new THREE.Vector3((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2);
  const radius = Math.max(Math.hypot(box[3] - box[0], box[4] - box[1], box[5] - box[2]) / 2, 0.05);

  // Licht und Schatten
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(center.x + radius * 2.2, center.y - radius * 3.2, center.z + radius * 4);
  key.target.position.copy(center);
  key.castShadow = true;
  key.shadow.mapSize.set(1536, 1536);
  const span = radius * 3.2;
  Object.assign(key.shadow.camera, { left: -span, right: span, top: span, bottom: -span, near: 0.01, far: radius * 14 });
  key.shadow.bias = -0.0004;
  key.shadow.radius = 3;
  scene.add(key, key.target);
  const rim = new THREE.DirectionalLight(0x9fb4ff, 0.7);
  rim.position.set(center.x - radius * 3, center.y + radius * 3, center.z + radius * 1.5);
  scene.add(rim);

  // Boden: Raster + Schattenfaenger + Achsen (X rot, Y gruen, Z blau)
  const gridZ = box[2] - radius * 0.08;
  const step = radius > 1 ? 0.5 : radius > 0.4 ? 0.1 : 0.05;
  const extent = Math.ceil((radius * 2.4) / step) * step;
  const floor = new THREE.Group();
  const grid = new THREE.GridHelper(extent * 2, Math.round((extent * 2) / step), 0x6b7080, 0x3a3e4a);
  grid.rotation.x = Math.PI / 2;
  grid.material.transparent = true;
  grid.material.opacity = 0.55;
  const shadowPlane = new THREE.Mesh(new THREE.PlaneGeometry(extent * 2, extent * 2), new THREE.ShadowMaterial({ opacity: 0.38 }));
  shadowPlane.receiveShadow = true;
  const axesHelper = new THREE.AxesHelper(Math.max(radius * 0.5, 0.1));
  axesHelper.position.set(0, 0, 0);
  floor.add(grid, shadowPlane);
  floor.position.z = gridZ;
  floor.visible = opts.grid;
  axesHelper.visible = opts.grid;
  scene.add(floor, axesHelper);

  // Kamera (Z oben) und Steuerung
  const camera = new THREE.PerspectiveCamera(40, 1, Math.max(radius * 0.02, 0.003), radius * 40);
  camera.up.set(0, 0, 1);
  const place = (az, el, dist) => {
    camera.position.set(center.x + dist * Math.cos(el) * Math.cos(az), center.y + dist * Math.cos(el) * Math.sin(az), center.z + dist * Math.sin(el));
    controls.target.copy(center);
    camera.lookAt(center);
    controls.update();
  };
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = false;                                  // gezeichnet wird nur bei Aenderung (spart Akku auf dem iPad)
  controls.minDistance = radius * 0.4;
  controls.maxDistance = radius * 14;
  controls.screenSpacePanning = true;
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  const home = { az: 0.75, el: 0.35, dist: radius * 2.8 };
  place(home.az, home.el, home.dist);

  let destroyed = false;
  let raf = 0;
  const draw = () => {
    raf = 0;
    if (destroyed) return;
    renderer.render(scene, camera);
  };
  const invalidate = () => { if (!raf && !destroyed) raf = requestAnimationFrame(draw); };
  controls.addEventListener("change", invalidate);

  function resize() {
    const rect = host.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    renderer.setSize(width, height, false);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    invalidate();
  }
  const observer = typeof ResizeObserver === "function" ? new ResizeObserver(resize) : null;
  if (observer) observer.observe(host); else window.addEventListener("resize", resize);
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  canvas.addEventListener("dblclick", () => api.resetView());

  const api = {
    canvas,
    stats: data.stats || {},
    axes: data.axes || {},
    setAngles(pan, tilt) { fixture.setAngles(pan, tilt); invalidate(); },
    setBeam(on) { fixture.setBeam(on); invalidate(); },
    setGrid(on) { floor.visible = !!on; axesHelper.visible = !!on; invalidate(); },
    resetView() { place(home.az, home.el, home.dist); invalidate(); },
    /** Ansicht von vorn/seitlich/oben (Z nach oben). */
    view(name) {
      const presets = { front: [-Math.PI / 2, 0.08], side: [0, 0.08], top: [-Math.PI / 2, 1.45], iso: [home.az, home.el] };
      const p = presets[name] || presets.iso;
      place(p[0], p[1], home.dist);
      invalidate();
    },
    resize,
    render() { renderer.render(scene, camera); },
    destroy() {
      destroyed = true;
      if (raf) cancelAnimationFrame(raf);
      if (observer) observer.disconnect(); else window.removeEventListener("resize", resize);
      controls.dispose();
      fixture.dispose();
      grid.geometry.dispose();
      grid.material.dispose();
      shadowPlane.geometry.dispose();
      shadowPlane.material.dispose();
      axesHelper.dispose();
      environment.dispose();
      pmrem.dispose();
      room.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    },
  };
  resize();
  return api;
}

/** Gibt die gemeinsam benutzten Netze (buildFixture mit shareGeometry) frei - erst aufrufen, wenn keine Instanz mehr gebraucht wird. */
function disposeShared(data) {
  if (data && data.__shared) data.__shared.owned.forEach((g) => g.dispose());
}

window.OCModelViewer = { create, buildFixture, disposeShared, THREE_REVISION: THREE.REVISION };

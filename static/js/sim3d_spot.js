/* 3D-Simulation: TEST-SCHEINWERFER. Ein einzelner Scheinwerfer, den man in die Buehne setzt und auf einen Punkt richtet, um Lichtkegel, Lichtkreis und Schatten auf
 * schraegen und gekruemmten Flaechen zu beurteilen. Er gehoert NICHT zur Show und nicht zur Buehne (wird nicht gespeichert, keine DMX-Werte): spaeter kommen die echten
 * Scheinwerfer der Show in eine eigene Datei bzw. einen eigenen Abschnitt, getrennt von den Koerpern.
 * Darstellung (nach der Vorlage _old/3d-Bühne-Vorlage.html): SpotLight mit Schattenkarte (weiche Kante = penumbra), sichtbarer Lichtkegel als Volumen (Nebel wird entlang des
 * Sehstrahls abgetastet, Schatten und Gegenstaende unterbrechen ihn), kleines Scheinwerfer-Modell. Bedienung im Baumodus: den Scheinwerfer ziehen
 * (verschiebt ihn, der Zielpunkt bleibt), die gelbe Kugel ziehen (zielt auf die Flaeche unter dem Finger), oder Zahlenfelder/Regler in der Seitenleiste. */
import * as THREE from "three";

const deg = THREE.MathUtils.degToRad;
const SPOT_CANDELA = 240;                                // Lichtstaerke bei voller Helligkeit (Candela)
const BEAM_LENGTH = 20;                                  // sichtbare Kegellaenge (Meter) wie in der Vorlage
const round = (v, d = 3) => Math.round(v * 10 ** d) / 10 ** d;

/** Volumetrischer Lichtkegel: Jeder Sehstrahl durch den Kegel wird in Schritten abgetastet (Dunst x Kegelform x "ist dieser Punkt vom Scheinwerfer beleuchtet?" aus der Schattenkarte).
 *  Dadurch unterbrechen Gegenstaende und ihre Schatten den Nebel wirklich. Der Strahl endet ausserdem an der naechsten sichtbaren Flaeche (Tiefenbild der Buehne).
 *  Gezeichnet wird ein einziges bildschirmfuellendes Dreieck (kein Huellen-Netz: dessen Dreieckskanten ergaben einzelne Luecken und Doppeltreffer = dunkle und weisse Punkte, und die
 *  Silhouette war ein Vieleck); jedes Pixel rechnet den Schnitt seines Sehstrahls mit dem Kegel selbst und verwirft Pixel ausserhalb. Ohne Tiefentest - die Verdeckung erledigt das Tiefenbild. */
export function makeConeMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(1, 1, 1) }, uStrength: { value: 0 }, uSteps: { value: 16 },
      uApex: { value: new THREE.Vector3() }, uAxis: { value: new THREE.Vector3(0, 0, 1) }, uK: { value: 0.3 }, uL: { value: 20 },
      uCosOuter: { value: 0.9 }, uCosInner: { value: 0.95 },
      uDepth: { value: null }, uHasDepth: { value: 0 }, uProjInv: { value: new THREE.Matrix4() }, uRes: { value: new THREE.Vector2(1, 1) },
      uShadow: { value: null }, uHasShadow: { value: 0 }, uShadowMat: { value: new THREE.Matrix4() }, uBias: { value: -0.0004 },
      uGobo: { value: null }, uHasGobo: { value: 0 },
      // Plaetze ohne Schattenkarte: der Nebel endet an den Flaechen, die die Strahlproben (Mittelstrahl + Ring) getroffen haben (axialer Abstand je Strahl)
      uUseHits: { value: 0 }, uCap: { value: 0 }, uHitS: { value: new Float32Array(9).fill(1e4) }, uRing: { value: 4 }, uBasisU: { value: new THREE.Vector3(1, 0, 0) }, uBasisV: { value: new THREE.Vector3(0, 1, 0) },
    },
    vertexShader: `
      varying vec2 vNdc;
      void main() {
        vNdc = position.xy;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }`,
    fragmentShader: `
      uniform vec3 uColor; uniform float uStrength; uniform int uSteps;
      uniform vec3 uApex; uniform vec3 uAxis; uniform float uK; uniform float uL;
      uniform float uCosOuter; uniform float uCosInner;
      uniform sampler2D uDepth; uniform float uHasDepth; uniform mat4 uProjInv; uniform vec2 uRes;
      uniform sampler2DShadow uShadow; uniform float uHasShadow; uniform mat4 uShadowMat; uniform float uBias;
      uniform sampler2D uGobo; uniform float uHasGobo;                // Lichtkarte des Platzes (Gobo/Prisma), gleiche Abbildung wie die Schattenkarte
      uniform float uCap; uniform float uUseHits; uniform float uHitS[9]; uniform int uRing; uniform vec3 uBasisU; uniform vec3 uBasisV;
      varying vec2 vNdc;

      // Abschnitt des Sehstrahls O + t*d im (endlichen) Kegel: x = Eintritt, y = Austritt (y <= x: kein Treffer)
      vec2 coneInterval(vec3 O, vec3 d) {
        float m = 1.0 + uK * uK;
        vec3 o = O - uApex;
        float co = dot(o, uAxis);
        float dd = dot(d, uAxis);
        float lo = 0.0;
        float hi = 1e9;
        if (abs(dd) < 1e-6) {
          if (co < 0.0 || co > uL) return vec2(1.0, 0.0);
        } else {
          float t0 = -co / dd;
          float t1 = (uL - co) / dd;
          lo = max(lo, min(t0, t1));
          hi = min(hi, max(t0, t1));
        }
        float qa = 1.0 - m * dd * dd;
        float qb = dot(o, d) - m * co * dd;
        float qc = dot(o, o) - m * co * co;
        if (abs(qa) < 1e-7) {
          if (abs(qb) < 1e-9) { if (qc > 0.0) return vec2(1.0, 0.0); }
          else {
            float tl = -qc / (2.0 * qb);
            if (qb > 0.0) hi = min(hi, tl); else lo = max(lo, tl);
          }
        } else {
          float disc = qb * qb - qa * qc;
          if (qa > 0.0 && disc < 0.0) return vec2(1.0, 0.0);
          if (disc > 0.0) {
            // stabile Form: q = -(b + sign(b) sqrt(disc)); Wurzeln q/a und c/q (vermeidet Ausloeschung bei fast parallelen Strahlen)
            float sq = sqrt(disc);
            float q = -(qb + (qb >= 0.0 ? sq : -sq));
            float ra = q / qa;
            float rb = abs(q) > 1e-12 ? qc / q : ra;
            float r1 = min(ra, rb);
            float r2 = max(ra, rb);
            if (qa > 0.0) { lo = max(lo, r1); hi = min(hi, r2); }
            else if (dd > 0.0) lo = max(lo, r2);
            else hi = min(hi, r1);
          }
        }
        return vec2(lo, hi);
      }

      void main() {
        vec3 O = cameraPosition;
        vec4 vp = uProjInv * vec4(vNdc, 1.0, 1.0);
        vec3 d = normalize(transpose(mat3(viewMatrix)) * (vp.xyz / vp.w));        // Sehstrahl dieses Pixels (Weltkoordinaten)
        vec2 iv = coneInterval(O, d);
        float tIn = max(iv.x, 0.0);
        float tOut = iv.y;
        vec2 uv = gl_FragCoord.xy / uRes;
        if (uHasDepth > 0.5) {
          float dep = texture2D(uDepth, uv).r;
          if (dep < 0.99999) {
            vec4 v = uProjInv * vec4(uv * 2.0 - 1.0, dep * 2.0 - 1.0, 1.0);
            tOut = min(tOut, length(v.xyz / v.w));
          }
        }
        if (!(tOut > tIn)) discard;                                   // auch NaN
        float jitter = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))));
        float dt = (tOut - tIn) / float(uSteps);
        float sum = 0.0;
        for (int i = 0; i < 48; i++) {
          if (i >= uSteps) break;
          vec3 p = O + d * (tIn + (float(i) + jitter) * dt);
          vec3 ap = p - uApex;
          float s = dot(ap, uAxis);
          float cosA = s / max(length(ap), 1e-4);
          float edge = smoothstep(uCosOuter, uCosInner, cosA);
          float along = pow(clamp(1.0 - s / uL, 0.0, 1.0), 1.1) * smoothstep(0.0, 0.5, s);
          float lit = 1.0;
          if (uHasShadow > 0.5) {
            vec4 sc = uShadowMat * vec4(p, 1.0);
            sc.xyz /= sc.w;
            if (sc.x > 0.0 && sc.x < 1.0 && sc.y > 0.0 && sc.y < 1.0 && sc.z < 1.0) lit = texture(uShadow, vec3(sc.xy, sc.z + uBias));
          }
          if (uCap > 0.0) lit *= 1.0 - smoothstep(uCap, uCap + 0.25, s);          // Plaetze mit Schattenkarte: hinter der am weitesten entfernten getroffenen Flaeche (alle Strahlen treffen) gibt es keinen Nebel mehr (Wand)
          if (uUseHits > 0.5) {
            // keine Schattenkarte: der Nebel hinter der getroffenen Flaeche (Wand, Gegenstand) entfaellt - Abstand je Richtung aus den Strahlproben, zwischen den Richtungen verlaufend
            vec3 rv = ap - s * uAxis;
            float rho = clamp(length(rv) / max(s * uK, 1e-4), 0.0, 1.0);
            float ang = atan(dot(rv, uBasisV), dot(rv, uBasisU));
            float f = (ang < 0.0 ? ang + 6.2831853 : ang) / 6.2831853 * float(uRing);
            int i0 = int(floor(f));
            float fr = f - float(i0);
            i0 = i0 % uRing;
            float dRing = mix(uHitS[1 + i0], uHitS[1 + (i0 + 1) % uRing], fr);
            float limit = mix(uHitS[0], dRing, rho);
            lit *= 1.0 - smoothstep(limit - 0.05, limit + 0.25, s);
          }
          if (uHasGobo > 0.5) {
            vec4 gc = uShadowMat * vec4(p, 1.0);
            vec2 guv = gc.xy / gc.w;
            lit *= (gc.w > 0.0 && guv.x > 0.0 && guv.x < 1.0 && guv.y > 0.0 && guv.y < 1.0) ? texture(uGobo, guv).r : 0.0;
          }
          sum += edge * along * lit * dt;
        }
        float x = max(sum * uStrength, 0.0);
        gl_FragColor = vec4(uColor * (0.5 * (1.0 - exp(-x / 0.5))), 1.0);       // saturiert weich: laengs des Strahls (langer Weg durch den Nebel) wird es nie weiss
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  });
}

/** ctx: {meshes(): Koerper der Buehne (Strahl trifft sie), floor, startDrag(drag, event), say(text, event), select(id), snap(), refreshSide(), tools: {el, t, numberRow, section, iconButton}} */
export function createTestSpot(sim, ctx) {
  const { el, t, numberRow, section, iconButton } = ctx.tools;
  const data = { position: [0, 0, 5], target: [0, 0, 0], angle: 30, soft: 40, level: 100, haze: 40, reach: 40, color: "#fff4e0" };
  let exists = false;
  let group = null;
  let light = null;
  let cone = null;
  let coneMat = null;
  let pick = null;
  let marker = null;
  let aimLine = null;
  let lens = null;
  let visible = false;                  // Hilfsgriffe (Zielkugel, Linie) nur im Baumodus
  const uid = "s" + Math.random().toString(36).slice(2, 10);       // Kennung dieses Panels (sein Echo vom Server wird ignoriert)
  let pushTimer = 0;
  let applying = false;                 // eine Aenderung von einem anderen Geraet wird gerade uebernommen (nicht zurueckschicken)

  const coneGeometry = (() => {                                            // ein Dreieck, das den ganzen Bildschirm ueberdeckt (Koordinaten direkt im Bildraum)
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
    return g;
  })();
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x2b2b2f, roughness: 0.6, metalness: 0.4 });
  const lensMaterial = new THREE.MeshStandardMaterial({ color: 0xfff4e0, emissive: 0xfff4e0, emissiveIntensity: 1.4, roughness: 0.3 });
  const geometries = [];
  const mesh = (g, m, x = 0, y = 0, z = 0) => { geometries.push(g); const o = new THREE.Mesh(g, m); o.position.set(x, y, z); return o; };
  const raycaster = new THREE.Raycaster();
  const tmp = new THREE.Vector3();
  const apex = new THREE.Vector3();
  const axis = new THREE.Vector3();
  const bufferSize = new THREE.Vector2();
  const normalMatrix = new THREE.Matrix3();
  const MAX_RAYS = 9;
  const hits = Array.from({ length: MAX_RAYS }, () => ({ valid: false, distance: 1, free: 30, point: new THREE.Vector3(), normal: new THREE.Vector3(), color: new THREE.Color(), metalness: 0, roughness: 1 }));     // getroffene Flaechen (fuer das zurueckgeworfene Licht)
  const sourceInfo = { lumens: 0, candela: 0, angle: 0, color: null, position: null, axis: null, hits, rays: 1 };
  let hitKey = "";
  const rayDir = new THREE.Vector3();
  const basisU = new THREE.Vector3();
  const basisV = new THREE.Vector3();
  const tmpPoint = new THREE.Vector3();
  const apexNow = new THREE.Vector3();
  const axisNow = new THREE.Vector3(0, 0, 1);
  const sourceColor = new THREE.Color();
  const STEPS = [8, 10, 14, 18, 24, 32];                  // Abtastschritte des Nebels je Qualitaetsstufe
  let depthTarget = null;                                 // Tiefenbild der Buehne (halbe Aufloesung; ab Stufe 4 voll): der Nebel endet an sichtbaren Flaechen
  const depthMaterial = new THREE.MeshBasicMaterial({ colorWrite: false });

  function create() {
    group = new THREE.Group();
    // Modell: Strahl zeigt nach +Z (lookAt richtet +Z auf den Zielpunkt)
    const head = mesh(new THREE.CylinderGeometry(0.13, 0.17, 0.4, 24), bodyMaterial, 0, 0, -0.05);
    head.rotation.x = Math.PI / 2;
    const back = mesh(new THREE.BoxGeometry(0.3, 0.26, 0.18), bodyMaterial, 0, 0, -0.32);
    lens = mesh(new THREE.CylinderGeometry(0.115, 0.115, 0.02, 24), lensMaterial, 0, 0, 0.16);
    lens.rotation.x = Math.PI / 2;
    const yoke = mesh(new THREE.BoxGeometry(0.42, 0.04, 0.04), bodyMaterial, 0, 0.2, -0.1);
    group.add(head, back, lens, yoke);
    pick = mesh(new THREE.SphereGeometry(0.4, 10, 8), new THREE.MeshBasicMaterial({ visible: false }));
    pick.userData.spot = "body";
    group.add(pick);
    coneMat = makeConeMaterial();
    cone = new THREE.Mesh(coneGeometry, coneMat);
    cone.frustumCulled = false;
    cone.position.z = 0.17;
    group.add(cone);
    light = new THREE.SpotLight(0xffffff, 0, 40, deg(15), 0.4, 2);
    light.castShadow = true;
    light.shadow.mapSize.set(sim.quality.shadowSize, sim.quality.shadowSize);
    light.shadow.bias = -0.0004;
    light.shadow.normalBias = sim.quality.shadowSize >= 2048 ? 0.012 : sim.quality.shadowSize >= 1024 ? 0.02 : 0.03;
    light.shadow.camera.near = 0.3;
    light.position.set(0, 0, 0.17);
    group.add(light);
    sim.scene.add(group, light.target);
    marker = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), new THREE.MeshBasicMaterial({ color: 0xffd400, depthTest: false, transparent: true, opacity: 0.95 }));
    marker.renderOrder = 30;
    marker.userData.spot = "aim";
    const hit = new THREE.Mesh(new THREE.SphereGeometry(2.2, 8, 6), new THREE.MeshBasicMaterial({ visible: false }));
    hit.userData.spot = "aim";
    marker.add(hit);
    marker.userData.hit = hit;
    sim.scene.add(marker);
    const lineGeometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, 0, 1)]);
    aimLine = new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({ color: 0xffd400, transparent: true, opacity: 0.45, depthTest: false }));
    aimLine.renderOrder = 29;
    sim.scene.add(aimLine);
    sim.quality.listeners.push(applyShadowSize);
    sim.lightSources.push(source);
    sim.frameHooks.push(update);
    sim.frameHooks.push(depthPass);
  }

  /** Lichtquelle fuers Raumlicht (siehe sim3d_room.js): Lichtstrom, Farbe, Lage und die vom Strahl getroffene Flaeche. */
  function source() {
    if (!exists) return null;
    const candela = SPOT_CANDELA * data.level / 100;
    const solid = 2 * Math.PI * (1 - Math.cos(deg(Math.min(data.angle, 170) / 2)));
    sourceInfo.lumens = candela * solid;
    sourceInfo.candela = candela;
    sourceInfo.angle = deg(data.angle);
    sourceInfo.color = sourceColor.set(data.color);
    sourceInfo.position = apexNow;
    sourceInfo.axis = axisNow;
    return sourceInfo;
  }

  /** Schattenkarte der Qualitaetsstufe anpassen (neu anlegen). */
  function applyShadowSize() {
    if (!light) return;
    const size = sim.quality.shadowSize;
    light.shadow.normalBias = size >= 2048 ? 0.012 : size >= 1024 ? 0.02 : 0.03;           // feinere Karte: kleinerer Versatz (weniger Licht, das hinter duenne Waende lugt)
    if (light.shadow.mapSize.x === size) return;
    light.shadow.mapSize.set(size, size);
    if (light.shadow.map) { light.shadow.map.dispose(); light.shadow.map = null; }
    sim.renderer.shadowMap.needsUpdate = true;
  }

  /** Tiefenbild der festen Koerper (Buehne + Boden) aus Sicht der Kamera - nur fuer den Nebel. */
  function depthPass() {
    if (!exists || !cone.visible) return;
    const renderer = sim.renderer;
    renderer.getDrawingBufferSize(bufferSize);
    const scale = sim.quality.level >= 4 ? 1 : 0.5;
    const w = Math.max(1, Math.round(bufferSize.x * scale));
    const h = Math.max(1, Math.round(bufferSize.y * scale));
    if (!depthTarget || depthTarget.width !== w || depthTarget.height !== h) {
      if (depthTarget) { depthTarget.depthTexture.dispose(); depthTarget.dispose(); }
      depthTarget = new THREE.WebGLRenderTarget(w, h, { depthBuffer: true, depthTexture: new THREE.DepthTexture(w, h), minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false });
    }
    ctx.meshes().forEach((m) => m.layers.enable(1));
    ctx.floor.layers.enable(1);
    const scene = sim.scene;
    const camera = sim.camera;
    const saved = { target: renderer.getRenderTarget(), mask: camera.layers.mask, override: scene.overrideMaterial, background: scene.background, fog: scene.fog, shadows: renderer.shadowMap.enabled };
    camera.layers.set(1);
    scene.overrideMaterial = depthMaterial;
    scene.background = null;
    scene.fog = null;
    renderer.shadowMap.enabled = false;               // verbraucht nicht die ausstehende Schattenkarte
    renderer.setRenderTarget(depthTarget);
    renderer.clear();
    renderer.render(scene, camera);
    renderer.setRenderTarget(saved.target);
    renderer.shadowMap.enabled = saved.shadows;
    scene.fog = saved.fog;
    scene.background = saved.background;
    scene.overrideMaterial = saved.override;
    camera.layers.mask = saved.mask;
    const u = coneMat.uniforms;
    u.uDepth.value = depthTarget.depthTexture;
    u.uHasDepth.value = 1;
    u.uProjInv.value.copy(camera.projectionMatrixInverse);
    u.uRes.value.copy(bufferSize);
  }

  /** Flaechen, die der Strahl trifft: ein Mittelstrahl und ein Ring von Strahlen nahe am Kegelrand (so werden auch Seitenflaechen und Kanten erfasst, nicht nur die Flaeche unter der Mitte).
   *  Jede getroffene Flaeche wirft einen Teil des Lichts zurueck (siehe sim3d_room.js). Neu berechnet wird nur, wenn sich die Szene geaendert hat. */
  function probeHits() {
    const ring = sim.quality.level >= 3 ? 8 : 4;
    const key = sim.version + ":" + ring;
    if (key === hitKey) return;
    hitKey = key;
    sourceInfo.rays = ring + 1;
    basisU.set(0, 0, 1).cross(axisNow);
    if (basisU.lengthSq() < 1e-4) basisU.set(1, 0, 0).cross(axisNow);
    basisU.normalize();
    basisV.copy(axisNow).cross(basisU);
    const half = deg(Math.min(data.angle, 120) / 2) * 0.85;
    const targets = [...ctx.meshes(), ctx.floor];
    for (let i = 0; i <= ring; i++) {
      const hit = hits[i];
      if (i === 0) rayDir.copy(axisNow);
      else {
        const phi = ((i - 1) / ring) * Math.PI * 2;
        rayDir.copy(axisNow).multiplyScalar(Math.cos(half)).addScaledVector(basisU, Math.sin(half) * Math.cos(phi)).addScaledVector(basisV, Math.sin(half) * Math.sin(phi));
      }
      raycaster.set(apexNow, rayDir);
      raycaster.near = 0.05;
      raycaster.far = data.reach;
      const h = raycaster.intersectObjects(targets, false)[0];
      if (!h || !h.face) { hit.valid = false; continue; }
      const m = h.object.material;
      hit.valid = true;
      hit.distance = h.distance;
      hit.point.copy(h.point);
      hit.normal.copy(h.face.normal).applyMatrix3(normalMatrix.getNormalMatrix(h.object.matrixWorld)).normalize();
      if (hit.normal.dot(rayDir) > 0) hit.normal.negate();
      raycaster.set(tmpPoint.copy(hit.point).addScaledVector(hit.normal, 0.05), hit.normal);        // freie Strecke vor der Flaeche (bis zur naechsten Wand)
      raycaster.near = 0;
      raycaster.far = 30;
      const free = raycaster.intersectObjects(targets, false)[0];
      hit.free = free ? free.distance + 0.05 : 30;
      hit.color.copy(m.color);
      hit.metalness = m.metalness || 0;
      hit.roughness = m.roughness === undefined ? 1 : m.roughness;
    }
  }

  // ------------------------------------------------------------------------------------------ Abgleich mit dem Server (alle Geraete sehen denselben Scheinwerfer)
  function changed() {
    update();
    sim.invalidate();
    if (!applying) schedulePush();
  }
  function schedulePush() {
    clearTimeout(pushTimer);
    pushTimer = setTimeout(async () => {
      pushTimer = 0;
      const spot = exists ? JSON.parse(JSON.stringify(data)) : null;
      try {
        await fetch("/api/sim-spot", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ spot, source: uid }) });
      } catch (err) { /* offline: bleibt lokal */ }
    }, 120);
  }
  /** Stand vom Server (anderes Geraet, Laden einer Show, Start): Scheinwerfer anlegen, aendern oder entfernen. */
  function applyRemote(spot) {
    if (spot === undefined || pushTimer) return;                          // eigene, noch nicht gesendete Aenderung geht vor
    applying = true;
    try {
      if (!spot) {
        if (exists) { if (ctx.selectedIsSpot()) ctx.select(null); remove_(); ctx.refreshSide(); }
        return;
      }
      const same = JSON.stringify({ ...data }) === JSON.stringify({ ...data, ...spot });
      if (exists && same) return;
      const created = !exists;
      if (created) { create(); exists = true; }
      Object.assign(data, spot);
      update();
      sim.invalidate();
      syncFields();
      ctx.refreshSide();
      if (created) ctx.refreshSide();
    } finally {
      applying = false;
    }
  }
  const onStage = (e) => {
    const { stage, source } = e.detail || {};
    if (stage && source !== uid) applyRemote(stage.spot);
  };
  document.addEventListener("sim-stage", onStage);

  function update() {
    if (!exists) return;
    group.position.set(...data.position);
    group.lookAt(new THREE.Vector3(...data.target));
    group.updateMatrixWorld(true);
    const color = new THREE.Color(data.color);
    const level = data.level / 100;
    light.color.copy(color);
    light.intensity = SPOT_CANDELA * level;                        // Candela; die Vorlage nutzt 1500 bei sehr dunklen Flaechen - unsere hellgrauen Standardfarben brauchen weniger
    light.angle = deg(data.angle / 2);
    light.penumbra = 0.12 + 0.7 * (data.soft / 100);
    light.distance = data.reach;
    light.shadow.camera.far = data.reach;
    light.target.position.set(...data.target);
    light.target.updateMatrixWorld();
    lens.material.emissiveIntensity = 0.15 + 1.4 * level;
    lens.material.color.copy(color);
    lens.material.emissive.copy(color);
    const length = Math.min(data.reach, BEAM_LENGTH);
    cone.visible = level > 0.01 && data.haze > 0;
    const u = coneMat.uniforms;
    u.uColor.value.copy(color);
    u.uStrength.value = (data.haze / 100) * level * 0.35;
    u.uSteps.value = STEPS[sim.quality.level];
    apex.set(0, 0, 0.17).applyMatrix4(group.matrixWorld);
    axis.set(0, 0, 1).transformDirection(group.matrixWorld);
    apexNow.copy(apex);
    axisNow.copy(axis);
    probeHits();
    u.uProjInv.value.copy(sim.camera.projectionMatrixInverse);
    u.uApex.value.copy(apex);
    u.uAxis.value.copy(axis);
    u.uK.value = Math.tan(deg(Math.min(data.angle, 120) / 2));
    u.uL.value = length;
    u.uCosOuter.value = Math.cos(light.angle);
    u.uCosInner.value = Math.cos(light.angle * (1 - light.penumbra));       // wie die Kante des Lichts auf den Flaechen
    u.uBias.value = light.shadow.bias;
    const shadowTexture = light.shadow.map && light.shadow.map.depthTexture;
    u.uShadow.value = shadowTexture || null;
    u.uHasShadow.value = shadowTexture ? 1 : 0;
    if (shadowTexture) u.uShadowMat.value.copy(light.shadow.matrix);
    sim.setHaze(data.haze / 100);
    // Hilfsgriffe: Zielkugel und Linie (nur im Baumodus, Bildschirmgroesse konstant)
    marker.visible = visible;
    aimLine.visible = visible;
    if (visible) {
      marker.position.set(...data.target);
      marker.scale.setScalar(Math.max(sim.camera.position.distanceTo(marker.position) * 0.008, 0.04));
      const pts = aimLine.geometry.attributes.position;
      pts.setXYZ(0, ...data.position);
      pts.setXYZ(1, ...data.target);
      pts.needsUpdate = true;
      aimLine.geometry.computeBoundingSphere();
    }
  }

  // ------------------------------------------------------------------------------------------ Zeigerbedienung (vom Baumodus aufgerufen)
  /** Trifft der Strahl den Scheinwerfer oder die Zielkugel? -> "body" | "aim" | null */
  function hitTest(ray) {
    if (!exists) return null;
    raycaster.ray.copy(ray);
    raycaster.near = 0.01;
    raycaster.far = 1000;
    const targets = visible ? [marker.userData.hit, pick] : [pick];
    const hit = raycaster.intersectObjects(targets, false)[0];
    return hit ? hit.object.userData.spot : null;
  }
  function begin(kind, ray, e) {
    if (kind === "body") {
      const z0 = data.position[2];
      const q = planeZ(ray, z0) || new THREE.Vector3(...data.position);
      ctx.startDrag({ type: "spot", kind, z0, offset: [data.position[0] - q.x, data.position[1] - q.y], moved: false }, e);
    } else {
      ctx.startDrag({ type: "spot", kind, moved: false }, e);
    }
  }
  function planeZ(ray, z) {
    if (Math.abs(ray.direction.z) < 1e-4) return null;
    const s = (z - ray.origin.z) / ray.direction.z;
    return s > 0 ? ray.origin.clone().addScaledVector(ray.direction, s) : null;
  }
  function move(drag, ray, e) {
    drag.moved = true;
    const snap = ctx.snap();
    const snapTo = (v) => (snap ? Math.round(v / snap) * snap : v);
    if (drag.kind === "body") {
      const q = planeZ(ray, drag.z0);
      if (!q) return;
      data.position = [round(snapTo(q.x + drag.offset[0])), round(snapTo(q.y + drag.offset[1])), data.position[2]];
      ctx.say(`X ${round(data.position[0], 2)}   Y ${round(data.position[1], 2)} m`, e);
    } else {                                                          // zielen: auf die Flaeche unter dem Zeiger (Koerper oder Boden), sonst auf die Hoehe des Ziels
      raycaster.set(ray.origin, ray.direction);
      raycaster.near = 0.01;
      raycaster.far = 1000;
      const hit = raycaster.intersectObjects([...ctx.meshes(), ctx.floor], false)[0];
      const point = hit ? hit.point : planeZ(ray, data.target[2]);
      if (!point) return;
      data.target = [round(point.x), round(point.y), round(Math.max(0, point.z))];
      ctx.say(`${t("SIM3D_SPOT_AIM")}: X ${round(data.target[0], 2)}  Y ${round(data.target[1], 2)}  Z ${round(data.target[2], 2)} m`, e);
    }
    changed();
    syncFields();
  }

  // ------------------------------------------------------------------------------------------ Seitenleiste
  let fields = null;
  function syncFields() {
    if (!fields) return;
    const set = (row, values) => row._inputs.forEach((input, i) => { if (document.activeElement !== input) input.value = String(round(values[i])); });
    set(fields.position, data.position);
    set(fields.target, data.target);
  }

  function slider(label, key, min, max, step, unit) {
    const row = el("div", "sim3d__slider");
    const l = el("label", "", label);
    const input = el("input", "sim3d__range");
    input.type = "range";
    input.min = String(min);
    input.max = String(max);
    input.step = String(step);
    input.value = String(data[key]);
    const value = el("span", "sim3d__slider-value", data[key] + " " + unit);
    input.addEventListener("input", () => { data[key] = Number(input.value); value.textContent = data[key] + " " + unit; changed(); });
    row.append(l, input, value);
    return row;
  }

  /** Abschnitt "Testscheinwerfer" der Seitenleiste. */
  function renderSection(selected) {
    fields = null;
    const group_ = section(t("SIM3D_SPOT"));
    if (!exists) {
      const add = iconButton("spot", t("SIM3D_SPOT_ADD"), "", () => { add_(); ctx.select("spot"); ctx.refreshSide(); });
      add.dataset.act = "spot-add";
      add.title = t("SIM3D_SPOT_TIP");
      group_.appendChild(add);
      return group_;
    }
    const open = iconButton("spot", selected ? t("SIM3D_SPOT_SELECTED") : t("SIM3D_SPOT_SELECT"), selected ? "sim3d__btn--on" : "", () => ctx.select(selected ? null : "spot"));
    open.dataset.act = "spot-select";
    group_.appendChild(open);
    if (!selected) return group_;
    fields = {
      position: numberRow(t("SIM3D_POSITION"), data.position, (v) => { data.position = v; changed(); }, { step: 0.5 }),
      target: numberRow(t("SIM3D_SPOT_AIM"), data.target, (v) => { data.target = v; changed(); }, { step: 0.5, tip: t("SIM3D_SPOT_AIM_TIP") }),
    };
    const color = el("input", "sim3d__color");
    color.type = "color";
    color.value = data.color;
    color.title = t("SIM3D_COLOR");
    color.addEventListener("input", () => { data.color = color.value; changed(); });
    const colorRow = el("div", "sim3d__row");
    colorRow.append(el("label", "sim3d__snap-label", t("SIM3D_COLOR")), color);
    const remove = iconButton("trash", t("SIM3D_SPOT_REMOVE"), "sim3d__btn--danger", () => { remove_(); ctx.select(null); ctx.refreshSide(); });
    remove.dataset.act = "spot-remove";
    group_.append(fields.position, fields.target, slider(t("SIM3D_SPOT_ANGLE"), "angle", 5, 90, 1, "°"), slider(t("SIM3D_SPOT_SOFT"), "soft", 0, 100, 1, "%"),
      slider(t("SIM3D_SPOT_LEVEL"), "level", 0, 100, 1, "%"), slider(t("SIM3D_SPOT_HAZE"), "haze", 0, 100, 1, "%"), slider(t("SIM3D_SPOT_REACH"), "reach", 5, 100, 1, "m"), colorRow, remove);
    return group_;
  }

  function add_() {
    if (exists) return;
    create();
    exists = true;
    const target = sim.controls.target;
    data.target = [round(target.x), round(target.y), 0];
    data.position = [round(target.x + 3), round(target.y - 3), 5];
    changed();
  }
  function remove_() {
    if (!exists) return;
    exists = false;
    sim.scene.remove(group, light.target, marker, aimLine);
    const si = sim.lightSources.indexOf(source);
    if (si >= 0) sim.lightSources.splice(si, 1);
    [update, depthPass].forEach((fn) => { const i = sim.frameHooks.indexOf(fn); if (i >= 0) sim.frameHooks.splice(i, 1); });
    const q = sim.quality.listeners.indexOf(applyShadowSize);
    if (q >= 0) sim.quality.listeners.splice(q, 1);
    if (depthTarget) { depthTarget.depthTexture.dispose(); depthTarget.dispose(); depthTarget = null; }
    light.dispose();
    if (light.shadow) light.shadow.dispose();
    geometries.forEach((g) => g.dispose());
    marker.geometry.dispose();
    marker.material.dispose();
    marker.userData.hit.geometry.dispose();
    aimLine.geometry.dispose();
    aimLine.material.dispose();
    coneMat.dispose();
    geometries.length = 0;
    group = light = cone = coneMat = pick = marker = aimLine = lens = null;
    sim.invalidate();
    if (!applying) schedulePush();
  }

  try {                                                              // Stand vom Server beim Start (ein Fehler hier darf das Panel nicht blockieren)
    if (window.OCSimStages && window.OCSimStages.current && window.OCSimStages.current.spot !== undefined) applyRemote(window.OCSimStages.current.spot);
  } catch (err) {
    console.error("Test-Scheinwerfer: Start-Stand nicht uebernommen:", err);
  }

  return {
    get exists() { return exists; },
    data, hitTest, begin, move, renderSection, syncFields,
    /** Pfeiltasten: Scheinwerfer auf der Bodenebene verschieben (Ziel bleibt). */
    nudge(dx, dy) { if (!exists) return; data.position = [round(data.position[0] + dx), round(data.position[1] + dy), data.position[2]]; changed(); syncFields(); },
    setVisibleHelpers(on) { visible = !!on; if (exists) { update(); sim.invalidate(); } },
    dispose() { document.removeEventListener("sim-stage", onStage); clearTimeout(pushTimer); applying = true; remove_(); coneGeometry.dispose(); bodyMaterial.dispose(); lensMaterial.dispose(); depthMaterial.dispose(); },
    _api: { add: add_, remove: remove_, update },
  };
}

/*
 * OpenCue website – demo/stage3d.js
 * The real 3D stage of the live demo, built with three.js (vendor/three/three-lite.js, loaded before this file).
 * A rock stage with a drum kit, a singer, speaker stacks and a lighting truss; the fixtures hang on the truss as
 * simple models (moving heads and wash pars) with a light cone, a real spot light (soft shadows) and haze.
 * The scene is based on the stand-alone 3D stage test of the program's author.
 *
 *   var stage = new OCDemo.Stage3D(containerEl, show, { ui: true });
 *   stage.render(show.output(now));          // call once per frame
 *   stage.camera("front" | "top" | "side" | "rig");
 *
 * Fixtures are taken from show.fixtures (type "par" or "mh"); position, colour and level come from show.output().
 * Pan and tilt arrive as percent and are turned into a floor target point; the moving head then swings to it
 * with limited speed, like a real one (see aimAt()).
 */
(function (g) {
  "use strict";

  var D = g.OCDemo = g.OCDemo || {};
  var T = g.THREE;
  if (!T) { return; }

  var TRUSS_Y = 6, TRUSS_Z = -1.4;          // height and depth of the lighting truss (metres)
  var BEAM_LEN = 20;                        // length of the visible light cone
  var SPOT_GAIN = { mh: 520, par: 250 };   // spot light intensity at full level (the wide pars overlap, so they get less)
  var PAN_RANGE = 270, TILT_RANGE = 120;    // degrees each way
  var PAN_SPEED = 210, TILT_SPEED = 150;    // degrees per second
  var WORLD_X = 8.4;                        // fixture.x (-1..1) -> metres along the truss
  var HEAD_DROP = 0.3 + 0.62;               // from truss axis down to the pivot of the head

  var CAMERAS = {
    front: { p: [0, 4.2, 17.5], t: [0, 2.7, 0] },
    top:   { p: [0, 24, 0.01],  t: [0, 0, 0] },
    side:  { p: [17.5, 5, 3],   t: [0, 2.8, 0] },
    rig:   { p: [-6.5, 6.4, 7.5], t: [1.5, 4.8, -1.4] }
  };

  function rad(d) { return d * Math.PI / 180; }
  function deg(r) { return r * 180 / Math.PI; }
  function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }
  function lerp(a, b, k) { return a + (b - a) * k; }
  function damp(a, b, rate, dt) { return lerp(a, b, 1 - Math.exp(-rate * dt)); }

  D.Stage3D = Stage3D;
  Stage3D.supported = function () {
    try {
      var c = document.createElement("canvas");
      return !!(g.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
    } catch (e) { return false; }
  };

  // ------------------------------------------------------------------ textures, materials, shapes

  function tileTexture(rx, ry, line, fill) {
    var c = document.createElement("canvas");
    c.width = c.height = 256;
    var x = c.getContext("2d");
    x.fillStyle = fill; x.fillRect(0, 0, 256, 256);
    x.strokeStyle = line; x.lineWidth = 3; x.strokeRect(0, 0, 256, 256);
    var tex = new T.CanvasTexture(c);
    tex.wrapS = tex.wrapT = T.RepeatWrapping;
    tex.repeat.set(rx, ry);
    tex.colorSpace = T.SRGBColorSpace;
    tex.anisotropy = 8;
    return tex;
  }

  // the visible light cone: bright in the middle (seen head-on), fading to the edges and along its length
  function beamMaterial() {
    return new T.ShaderMaterial({
      transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending,
      uniforms: { uColor: { value: new T.Color("#ffffff") }, uOpacity: { value: 0 } },
      vertexShader: [
        "varying vec3 vN; varying vec3 vV; varying float vT;",
        "void main() {",
        "  vT = -position.y;",
        "  vN = normalize(normalMatrix * normal);",
        "  vec4 mv = modelViewMatrix * vec4(position, 1.0);",
        "  vV = -mv.xyz;",
        "  gl_Position = projectionMatrix * mv;",
        "}"
      ].join("\n"),
      fragmentShader: [
        "uniform vec3 uColor; uniform float uOpacity;",
        "varying vec3 vN; varying vec3 vV; varying float vT;",
        "void main() {",
        "  float f = abs(dot(normalize(vN), normalize(vV)));",
        "  float edge = pow(f, 1.7);",
        "  float along = pow(clamp(1.0 - vT, 0.0, 1.0), 1.1) * smoothstep(0.0, 0.025, vT);",
        "  float a = edge * along * uOpacity;",
        "  gl_FragColor = vec4(uColor * a, 1.0);",
        "  #include <tonemapping_fragment>",
        "  #include <colorspace_fragment>",
        "}"
      ].join("\n")
    });
  }

  var down = new T.Vector3(0, -1, 0);

  function rod(a, b, radius, material) {
    var d = new T.Vector3().subVectors(b, a);
    var m = new T.Mesh(new T.CylinderGeometry(radius, radius, d.length(), 6), material);
    m.position.copy(a).addScaledVector(d, 0.5);
    m.quaternion.setFromUnitVectors(down.clone().negate(), d.clone().normalize());
    m.castShadow = true;
    return m;
  }

  function truss(length, y, z, material) {
    var group = new T.Group(), x0 = -length / 2, r = 0.25;
    var V = function (x, yy, zz) { return new T.Vector3(x, yy, zz); };
    [-r, r].forEach(function (sy) { [-r, r].forEach(function (sz) {
      group.add(rod(V(x0, y + sy, z + sz), V(-x0, y + sy, z + sz), 0.035, material));
    }); });
    var n = Math.round(length / 0.5);
    for (var i = 0; i < n; i++) {
      var a = x0 + i * (length / n), b = x0 + (i + 1) * (length / n), up = i % 2 === 0;
      [-r, r].forEach(function (u) { group.add(rod(V(a, y + (up ? -r : r), z + u), V(b, y + (up ? r : -r), z + u), 0.018, material)); });
      [-r, r].forEach(function (u) { group.add(rod(V(a, y + u, z - r), V(b, y + u, z + r), 0.012, material)); });
    }
    return group;
  }

  // ------------------------------------------------------------------ the stage

  function buildStage(scene) {
    var stage = new T.Group();
    scene.add(stage);

    var mat = {
      case: new T.MeshStandardMaterial({ color: 0x4a4a4a, roughness: 0.7, metalness: 0.1 }),
      brass: new T.MeshStandardMaterial({ color: 0xc9a84a, roughness: 0.35, metalness: 0.35 }),
      steel: new T.MeshStandardMaterial({ color: 0x9a9a9a, roughness: 0.5, metalness: 0.2 })
    };
    function add(mesh, x, y, z) {
      mesh.position.set(x, y, z); mesh.castShadow = true; mesh.receiveShadow = true;
      stage.add(mesh);
      return mesh;
    }
    var box = function (w, h, d) { return new T.BoxGeometry(w, h, d); };
    var cyl = function (rt, rb, h, s) { return new T.CylinderGeometry(rt, rb, h, s); };

    // deck, ground and back wall
    var deck = new T.Mesh(box(14, 0.5, 8.6), new T.MeshStandardMaterial({ map: tileTexture(14, 8.6, "#2b2b2b", "#4a4a4a"), roughness: 0.42, metalness: 0.15 }));
    deck.position.set(0, -0.25, 0); deck.receiveShadow = true; stage.add(deck);
    var ground = new T.Mesh(new T.PlaneGeometry(120, 120), new T.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.85, metalness: 0 }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.5; ground.receiveShadow = true; stage.add(ground);
    var wall = new T.Mesh(new T.PlaneGeometry(16, 6.6), new T.MeshStandardMaterial({ map: tileTexture(20, 8.25, "#242424", "#3a3a3a"), roughness: 0.75, metalness: 0 }));
    wall.position.set(0, 3.3, -4.4); wall.receiveShadow = true; stage.add(wall);

    // speaker stacks
    [-6.1, 6.1].forEach(function (x) {
      add(new T.Mesh(box(1.1, 1.3, 1), mat.case), x, 0.65, -0.6);
      add(new T.Mesh(box(1, 1.1, 0.9), mat.case), x, 1.85, -0.6);
    });

    // drum kit on a riser
    add(new T.Mesh(box(3.2, 0.35, 2.4), mat.case), 0, 0.175, -2.8);
    var kick = add(new T.Mesh(cyl(0.42, 0.42, 0.5, 28), mat.case), 0, 0.85, -2.3);
    kick.rotation.x = Math.PI / 2;
    [[-0.55, -2.85], [0.1, -2.9], [0.85, -2.6]].forEach(function (p) {
      add(new T.Mesh(cyl(0.28, 0.28, 0.24, 24), mat.case), p[0], 1.2, p[1]);
    });
    [[-1.1, 1.6, -3], [1.35, 1.75, -2.9], [-0.1, 1.9, -3.4]].forEach(function (c) {
      add(new T.Mesh(cyl(0.02, 0.02, c[1] - 0.35, 6), mat.steel), c[0], 0.35 + (c[1] - 0.35) / 2, c[2]);
      add(new T.Mesh(cyl(0.42, 0.42, 0.015, 32), mat.brass), c[0], c[1], c[2]);
    });

    // singer with a mic stand
    add(new T.Mesh(new T.CapsuleGeometry(0.24, 0.95, 6, 16), new T.MeshStandardMaterial({ color: 0x555555, roughness: 0.8 })), 0, 1.15, 1.9);
    add(new T.Mesh(new T.SphereGeometry(0.19, 20, 16), new T.MeshStandardMaterial({ color: 0x777777, roughness: 0.7 })), 0, 2.02, 1.9);
    add(new T.Mesh(cyl(0.015, 0.015, 1.6, 6), mat.steel), 0.45, 0.8, 2.3);

    // floor monitors
    [-2.2, 2.2].forEach(function (x) {
      var m = add(new T.Mesh(box(0.9, 0.35, 0.55), mat.case), x, 0.175, 3.3);
      m.rotation.x = -0.35; m.position.y = 0.3;
    });

    // truss with its stands
    stage.add(truss(15, TRUSS_Y, TRUSS_Z, mat.steel));
    [-7.2, 7.2].forEach(function (x) {
      var h = TRUSS_Y + 0.2;
      var pole = new T.Mesh(cyl(0.09, 0.09, h, 10), mat.steel);
      pole.position.set(x, h / 2 - 0.2, TRUSS_Z); pole.castShadow = true; stage.add(pole);
      var foot = new T.Mesh(box(0.7, 0.05, 0.7), mat.steel);
      foot.position.set(x, 0.025, TRUSS_Z); stage.add(foot);
    });
    return stage;
  }

  // ------------------------------------------------------------------ fixtures

  var partGeo = null;
  function geometries() {
    if (partGeo) { return partGeo; }
    var beam = new T.CylinderGeometry(0, 1, 1, 64, 1, true);
    beam.translate(0, -0.5, 0);                      // apex at the origin, opening downwards
    partGeo = {
      clamp: new T.BoxGeometry(0.34, 0.22, 0.34),
      plate: new T.BoxGeometry(1, 0.1, 0.5),
      arm: new T.BoxGeometry(0.1, 0.95, 0.34),
      moverHead: new T.CylinderGeometry(0.34, 0.3, 0.72, 32),
      parHead: new T.CylinderGeometry(0.3, 0.27, 0.5, 32),
      back: new T.BoxGeometry(0.5, 0.34, 0.5),
      lens: new T.CircleGeometry(0.27, 32),
      ring: new T.TorusGeometry(0.3, 0.03, 8, 40),
      beam: beam
    };
    return partGeo;
  }

  // one fixture: clamp, yoke (pan), head (tilt), light cone and spot light
  function makeFixture(def, lights, quality) {
    var geo = geometries();
    var isMover = def.type === "mh";
    var x = def.x * WORLD_X;
    var body = new T.MeshStandardMaterial({ color: 0x6a6a6a, roughness: 0.5, metalness: 0.2 });
    var headMat = new T.MeshStandardMaterial({ color: 0x4a4a4a, roughness: 0.45, metalness: 0.2 });
    var ringMat = new T.MeshStandardMaterial({ color: 0x888888, roughness: 0.4, metalness: 0.2 });
    var lensMat = new T.MeshBasicMaterial({ color: 0x000000, toneMapped: false });
    var beamMat = beamMaterial();

    var root = new T.Group();
    root.position.set(x, TRUSS_Y - 0.3, TRUSS_Z);
    var clampM = new T.Mesh(geo.clamp, body); clampM.position.y = 0.2;

    var yoke = new T.Group();
    var plate = new T.Mesh(geo.plate, body); plate.position.y = -0.05;
    var armL = new T.Mesh(geo.arm, body); armL.position.set(-0.46, -0.52, 0);
    var armR = new T.Mesh(geo.arm, body); armR.position.set(0.46, -0.52, 0);

    var head = new T.Group(); head.position.y = -0.62;
    var headBody = new T.Mesh(isMover ? geo.moverHead : geo.parHead, headMat);
    var back = new T.Mesh(geo.back, headMat); back.position.y = isMover ? 0.38 : 0.3;
    var ring = new T.Mesh(geo.ring, ringMat); ring.rotation.x = Math.PI / 2; ring.position.y = isMover ? -0.355 : -0.255;
    var lens = new T.Mesh(geo.lens, lensMat); lens.rotation.x = Math.PI / 2; lens.position.y = isMover ? -0.362 : -0.262;
    var beam = new T.Mesh(geo.beam, beamMat);
    beam.position.y = isMover ? -0.37 : -0.27; beam.renderOrder = 2; beam.frustumCulled = false;
    head.add(headBody, back, ring, lens, beam);
    yoke.add(plate, armL, armR, head);
    root.add(clampM, yoke);
    lights.add(root);

    var spot = new T.SpotLight(0xffffff, 0, 0, rad(11), 0.4, 2);
    var shadows = isMover && quality !== "low";
    spot.castShadow = shadows;
    if (shadows) {
      spot.shadow.mapSize.set(1024, 1024);
      spot.shadow.bias = -4e-4;
      spot.shadow.camera.near = 0.6; spot.shadow.camera.far = 40;
    }
    lights.add(spot, spot.target);

    var pickables = [headBody, back, plate, armL, armR, clampM];
    pickables.forEach(function (m) { m.userData.fid = def.fid; });

    var fx = {
      fid: def.fid, mover: isMover, x: x, root: root, yoke: yoke, head: head, beam: beam, beamMat: beamMat,
      lensMat: lensMat, ringMat: ringMat, spot: spot, pickables: pickables,
      origin: new T.Vector3(x, TRUSS_Y - HEAD_DROP, TRUSS_Z),
      pan: 0, tilt: 0, placed: false, dim: 0, zoom: isMover ? 22 : 44, color: new T.Color(0xffffff),
      fixedTarget: isMover ? null : new T.Vector3(def.x * 3.2, 0.4, 0.9)
    };
    fx.dispose = function () {
      lights.remove(root, spot, spot.target);
      spot.dispose();
      [beamMat, lensMat, ringMat, body, headMat].forEach(function (m) { m.dispose(); });
    };
    return fx;
  }

  var tmpDir = new T.Vector3();
  // pan/tilt (degrees) that point the head at a world position; picks the nearest of the two equivalent solutions
  function aimAt(fx, target) {
    var e = tmpDir.subVectors(target, fx.origin).normalize();
    var pan0 = deg(Math.atan2(-e.x, -e.z)) - 180;
    var tilt0 = deg(Math.acos(clamp(-e.y, -1, 1)));
    var best = [0, 0], bestCost = Infinity;
    [[pan0, tilt0], [pan0 + 180, -tilt0]].forEach(function (c) {
      if (Math.abs(c[1]) > TILT_RANGE) { return; }
      for (var k = -2; k <= 2; k++) {
        var p = c[0] + 360 * k;
        if (p < -PAN_RANGE || p > PAN_RANGE) { continue; }
        var cost = Math.abs(p - fx.pan) + 0.5 * Math.abs(c[1] - fx.tilt);
        if (cost < bestCost) { bestCost = cost; best = [p, c[1]]; }
      }
    });
    return best;
  }

  // ------------------------------------------------------------------ the stage widget

  function Stage3D(container, show, opts) {
    this.container = container;
    this.show = show;
    this.opts = opts || {};
    this.haze = 0.55;
    this.last = null;
    this.visible = true;
    this.frames = 0; this.slowTime = 0;
    this.selectionKey = "";
    this.transition = null;
    this.fixtures = [];

    var quality = this.opts.quality || ((g.matchMedia && g.matchMedia("(pointer: coarse)").matches) ? "low" : "high");
    this.quality = quality;

    var renderer = this.renderer = new T.WebGLRenderer({ antialias: quality !== "low", powerPreference: "high-performance" });
    renderer.setPixelRatio(quality === "low" ? 1 : Math.min(g.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = quality !== "low";
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.85;
    this.canvas = renderer.domElement;
    this.canvas.className = "s3-canvas";
    container.insertBefore(this.canvas, container.firstChild);

    var scene = this.scene = new T.Scene();
    scene.background = new T.Color(0x000000);
    scene.fog = new T.FogExp2(0x000000, 0.012);

    var camera = this.cam = new T.PerspectiveCamera(42, 1, 0.1, 200);
    camera.position.set.apply(camera.position, CAMERAS.front.p);
    // the page must stay scrollable: the wheel only zooms the stage with Ctrl (or a trackpad pinch)
    renderer.domElement.addEventListener("wheel", function (e) { if (!(e.ctrlKey || e.metaKey)) { e.stopImmediatePropagation(); } }, { passive: true });
    var controls = this.controls = new T.OrbitControls(camera, renderer.domElement);
    if (this.opts.zoom === false) { controls.enableZoom = false; }
    controls.target.set.apply(controls.target, CAMERAS.front.t);
    controls.enableDamping = true; controls.dampingFactor = 0.07;
    controls.minDistance = 3; controls.maxDistance = 36;
    controls.maxPolarAngle = rad(88);
    controls.autoRotateSpeed = 0.9;
    this.interacted = false;
    var self = this;
    controls.addEventListener("start", function () { self.interacted = true; self.transition = null; self._orbitButton(false); self._hideHint(); });

    scene.add(new T.AmbientLight(0xffffff, 0.6));
    var key = new T.DirectionalLight(0x8a9fff, 0.9);
    key.position.set(-6, 9, 12);
    scene.add(key);

    buildStage(scene);
    this.lights = new T.Group();
    scene.add(this.lights);
    show.fixtures.forEach(function (def) { self.fixtures.push(makeFixture(def, self.lights, quality)); });
    this.byFid = {};
    this.fixtures.forEach(function (f) { self.byFid[f.fid] = f; });
    this.setHaze(this.haze);

    if (this.opts.ui !== false) { this._buildUi(); }

    // picking: a short click on a fixture selects it
    var ray = new T.Raycaster(), ndc = new T.Vector2(), down0 = null;
    this.canvas.addEventListener("pointerdown", function (e) { down0 = { x: e.clientX, y: e.clientY, t: performance.now() }; });
    this.canvas.addEventListener("pointerup", function (e) {
      if (!down0) { return; }
      var moved = Math.hypot(e.clientX - down0.x, e.clientY - down0.y), quick = performance.now() - down0.t < 450;
      down0 = null;
      if (moved > 5 || !quick || self.opts.pick === false) { return; }
      var r = self.canvas.getBoundingClientRect();
      ndc.set((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      var hits = ray.intersectObjects(self.fixtures.reduce(function (a, f) { return a.concat(f.pickables); }, []), false);
      if (hits.length) { self.show.select([hits[0].object.userData.fid], e.shiftKey || e.ctrlKey || e.metaKey ? "toggle" : "replace"); }
    });

    if (g.ResizeObserver) { new g.ResizeObserver(function () { self.resize(); }).observe(container); }
    else { g.addEventListener("resize", function () { self.resize(); }); }
    if (g.IntersectionObserver) { new g.IntersectionObserver(function (en) { self.visible = en[0].isIntersecting; }).observe(container); }
    this.resize();
    this.camera("front", true);
    if (this.opts.sway) { controls.autoRotate = false; }
  }

  Stage3D.prototype.resize = function () {
    var w = this.container.clientWidth || 1, h = this.container.clientHeight || 1;
    this.renderer.setSize(w, h, false);
    this.canvas.style.width = "100%"; this.canvas.style.height = "100%";
    this.cam.aspect = w / h;
    this.cam.updateProjectionMatrix();
    this.w = w; this.h = h;
  };

  Stage3D.prototype.setHaze = function (v) {
    this.haze = clamp(v, 0, 1);
    this.scene.fog.density = 0.004 + this.haze * 0.016;
  };

  // distance multiplier so the whole truss still fits in a narrow container
  Stage3D.prototype._fit = function () {
    var a = (this.w || 1) / (this.h || 1);
    return a < 1.55 ? Math.min(2.1, 1.55 / a) : 1;
  };

  Stage3D.prototype.camera = function (name, instant) {
    var c = CAMERAS[name];
    if (!c) { return; }
    var target = new T.Vector3().fromArray(c.t);
    var pos = new T.Vector3().fromArray(c.p);
    var f = name === "top" ? 1 : this._fit();
    pos.sub(target).multiplyScalar(f).add(target);
    this.transition = instant ? null : {
      t: 0, dur: 1.1, p0: this.cam.position.clone(), t0: this.controls.target.clone(), p1: pos, t1: target
    };
    if (instant) { this.cam.position.copy(pos); this.controls.target.copy(target); this.controls.update(); }
    this.controls.autoRotate = false;
    this._orbitButton(false);
    this.preset = name;
    this._markCamera(name);
  };

  // ------------------------------------------------------------------ frame

  Stage3D.prototype.render = function (out) {
    this.last = out;
    if (!this.visible || document.hidden) { this.prev = null; return; }
    var now = performance.now();
    var dt = this.prev ? Math.min((now - this.prev) / 1000, 0.05) : 0.016;
    this.prev = now;
    this.time = (this.time || 0) + dt;

    // camera transition and gentle sway (home page)
    if (this.transition) {
      var tr = this.transition;
      tr.t += dt / tr.dur;
      var s = Math.min(1, tr.t), k = s < 0.5 ? 2 * s * s : 1 - Math.pow(-2 * s + 2, 2) / 2;
      this.cam.position.lerpVectors(tr.p0, tr.p1, k);
      this.controls.target.lerpVectors(tr.t0, tr.t1, k);
      if (s >= 1) { this.transition = null; }
    } else if (this.opts.sway && !this.interacted) {
      var c = CAMERAS.front, f = this._fit(), a = Math.sin(this.time * 0.18) * 0.32;
      var base = new T.Vector3().fromArray(c.p), tg = new T.Vector3().fromArray(c.t);
      var off = base.sub(tg).multiplyScalar(f);
      var cosA = Math.cos(a), sinA = Math.sin(a);
      this.cam.position.set(tg.x + off.x * cosA + off.z * sinA, tg.y + off.y + Math.sin(this.time * 0.13) * 0.5, tg.z - off.x * sinA + off.z * cosA);
      this.controls.target.copy(tg);
    }
    this.controls.update();

    for (var i = 0; i < out.length; i++) {
      var fx = this.byFid[out[i].fid];
      if (fx) { this._updateFixture(fx, out[i], dt); }
    }
    this._updateSelection();
    this._updateTags();
    this.renderer.render(this.scene, this.cam);
    this._governor(dt);
  };

  var tmpColor = new T.Color(), tmpPos = new T.Vector3(), tmpDir2 = new T.Vector3(), tmpTarget = new T.Vector3();

  Stage3D.prototype._updateFixture = function (fx, o, dt) {
    var panT, tiltT;
    if (fx.fixedTarget) {
      if (!fx.placed) { var fixedAim = aimAt(fx, fx.fixedTarget); fx.pan = fixedAim[0]; fx.tilt = fixedAim[1]; }
      panT = fx.pan; tiltT = fx.tilt;
    } else {
      tmpTarget.set(lerp(-6.5, 6.5, o.pan / 100), 0.2, lerp(-3, 7, o.tilt / 100));
      var aim = aimAt(fx, tmpTarget);
      panT = clamp(aim[0], -PAN_RANGE, PAN_RANGE); tiltT = clamp(aim[1], -TILT_RANGE, TILT_RANGE);
      if (!fx.placed) { fx.pan = panT; fx.tilt = tiltT; }
    }
    fx.placed = true;
    fx.pan += clamp(panT - fx.pan, -PAN_SPEED * dt, PAN_SPEED * dt);
    fx.tilt += clamp(tiltT - fx.tilt, -TILT_SPEED * dt, TILT_SPEED * dt);
    fx.yoke.rotation.y = rad(fx.pan) + Math.PI;
    fx.head.rotation.x = rad(fx.tilt);

    tmpColor.setRGB(o.r, o.g, o.b);
    fx.color.lerp(tmpColor, 1 - Math.exp(-12 * dt));
    fx.dim = damp(fx.dim, o.level, 14, dt);

    var half = rad(fx.zoom / 2);
    var spread = BEAM_LEN * Math.tan(half);
    fx.beam.scale.set(spread, BEAM_LEN, spread);
    fx.beamMat.uniforms.uColor.value.copy(fx.color);
    fx.beamMat.uniforms.uOpacity.value = fx.dim * this.haze * (fx.mover ? 0.46 : 0.34);
    fx.lensMat.color.copy(fx.color).multiplyScalar(fx.dim * 1.6).addScalar(0.02);

    fx.root.updateMatrixWorld(true);
    fx.head.getWorldPosition(tmpPos);
    tmpDir2.set(0, -1, 0).transformDirection(fx.head.matrixWorld);
    fx.spot.position.copy(tmpPos).addScaledVector(tmpDir2, 0.36);
    fx.spot.target.position.copy(tmpPos).addScaledVector(tmpDir2, 10);
    fx.spot.target.updateMatrixWorld();
    fx.spot.color.copy(fx.color);
    fx.spot.angle = half;
    fx.spot.intensity = fx.dim * (fx.mover ? SPOT_GAIN.mh : SPOT_GAIN.par);
  };

  Stage3D.prototype._updateSelection = function () {
    if (this.opts.selection === false) { return; }
    var key = this.show.selection.join(",");
    if (key === this.selectionKey) { return; }
    this.selectionKey = key;
    var sel = this.show.selection;
    this.fixtures.forEach(function (fx) {
      var on = sel.indexOf(fx.fid) >= 0;
      fx.ringMat.color.set(on ? 0xffb000 : 0x777777);
      fx.ringMat.emissive.set(on ? 0x554400 : 0x000000);
    });
    if (this.tags) {
      this.fixtures.forEach(function (fx) { this.tags[fx.fid].classList.toggle("sel", sel.indexOf(fx.fid) >= 0); }, this);
    }
  };

  // quality governor: if the first seconds are slow, drop shadows and pixel ratio once
  Stage3D.prototype._governor = function (dt) {
    if (this.degraded || this.frames > 240) { return; }
    this.frames += 1;
    if (this.frames > 30) { this.slowTime += dt; }
    if (this.frames === 150) {
      var avg = this.slowTime / 120;
      if (avg > 0.045) {
        this.degraded = true;
        this.renderer.setPixelRatio(1);
        this.renderer.shadowMap.enabled = false;
        this.fixtures.forEach(function (f) { f.spot.castShadow = false; });
        this.resize();
        if (this.opts.onSlow) { this.opts.onSlow(avg); }
      }
    }
  };

  // ------------------------------------------------------------------ overlay: number tags, camera buttons, haze

  function T_(key, en) { return g.OC ? g.OC.t(key, en) : en; }

  Stage3D.prototype._buildUi = function () {
    var self = this, c = this.container;
    var tags = this.tags = {};
    var tagLayer = document.createElement("div"); tagLayer.className = "s3-tags";
    this.fixtures.forEach(function (fx) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "s3-tag"; b.textContent = String(fx.fid);
      b.setAttribute("aria-label", "Fixture " + fx.fid);
      b.addEventListener("click", function (e) { self.show.select([fx.fid], e.shiftKey || e.ctrlKey || e.metaKey ? "toggle" : "replace"); });
      tagLayer.appendChild(b); tags[fx.fid] = b;
    });
    c.appendChild(tagLayer);

    var bar = document.createElement("div"); bar.className = "s3-bar";
    var cams = document.createElement("div"); cams.className = "s3-cams";
    this.camButtons = {};
    [["front", "Front"], ["top", "Top"], ["side", "Side"], ["rig", "Rig"]].forEach(function (p) {
      var b = document.createElement("button"); b.type = "button"; b.setAttribute("data-cam", p[0]); b.setAttribute("aria-pressed", "false");
      b.setAttribute("data-k", "demo.s3." + p[0]); b.setAttribute("data-en", p[1]); b.textContent = T_("demo.s3." + p[0], p[1]);
      b.addEventListener("click", function () { self.camera(p[0]); });
      cams.appendChild(b); self.camButtons[p[0]] = b;
    });
    if (D.fs && D.fs.enabled()) {
      var fsBtn = document.createElement("button");
      fsBtn.type = "button"; fsBtn.className = "s3-fs-btn"; fsBtn.setAttribute("data-k", "demo.s3.fullscreen"); fsBtn.setAttribute("data-en", "Fullscreen");
      fsBtn.textContent = T_("demo.s3.fullscreen", "Fullscreen");
      fsBtn.addEventListener("click", function () { D.fs.toggle(c); });
      cams.appendChild(fsBtn);
      this._buildFsBar();
    }
    var orbit = this.orbitBtn = document.createElement("button");
    orbit.type = "button"; orbit.setAttribute("aria-pressed", "false"); orbit.setAttribute("data-k", "demo.s3.orbit"); orbit.setAttribute("data-en", "Orbit");
    orbit.textContent = T_("demo.s3.orbit", "Orbit");
    orbit.addEventListener("click", function () {
      var on = !self.controls.autoRotate;
      self.controls.autoRotate = on; self.transition = null; self._orbitButton(on);
    });
    cams.appendChild(orbit);

    var haze = document.createElement("label"); haze.className = "s3-haze";
    var hl = document.createElement("span"); hl.setAttribute("data-k", "demo.s3.haze"); hl.setAttribute("data-en", "Haze"); hl.textContent = T_("demo.s3.haze", "Haze");
    var slider = document.createElement("input"); slider.type = "range"; slider.min = "0"; slider.max = "100"; slider.value = String(Math.round(this.haze * 100));
    slider.addEventListener("input", function () { self.setHaze(slider.value / 100); });
    haze.appendChild(hl); haze.appendChild(slider);
    bar.appendChild(cams); bar.appendChild(haze);
    c.appendChild(bar);

    var hint = this.hint = document.createElement("p"); hint.className = "s3-hint";
    var touch = !!(g.matchMedia && g.matchMedia("(pointer: coarse)").matches);
    var hintKey = touch ? "demo.s3.hintTouch" : "demo.s3.hint";
    hint.setAttribute("data-k", hintKey);
    hint.setAttribute("data-en", touch ? "Drag to orbit · pinch to zoom · tap a fixture to select it" : "Drag to orbit · Ctrl + scroll to zoom · click a fixture to select it");
    hint.textContent = T_(hintKey, hint.getAttribute("data-en"));
    c.appendChild(hint);
    setTimeout(function () { self._hideHint(); }, 9000);

    if (g.OC && g.OC.onLang) {
      g.OC.onLang(function () {
        c.querySelectorAll("[data-k]").forEach(function (el) { el.textContent = T_(el.getAttribute("data-k"), el.getAttribute("data-en")); });
      });
    }
  };

  // in fullscreen the stage is on its own: a small bar plays the cue list and exits fullscreen (Space = Go, Backspace = Back, B = blackout)
  Stage3D.prototype._buildFsBar = function () {
    var self = this, c = this.container, show = this.show;
    var bar = document.createElement("div"); bar.className = "s3-fsbar";
    function btn(cls, key, en, fn) {
      var b = document.createElement("button"); b.type = "button"; b.className = cls;
      b.setAttribute("data-k", key); b.setAttribute("data-en", en); b.textContent = T_(key, en);
      b.addEventListener("click", fn); bar.appendChild(b); return b;
    }
    btn("", "demo.back", "Back", function () { show.back(); });
    var label = document.createElement("span"); label.className = "s3-fscue"; bar.appendChild(label);
    btn("go", "demo.go", "Go", function () { show.goNext(); });
    btn("", "demo.blackout", "Blackout", function () { show.setBlackout(); });
    btn("", "demo.s3.exitFs", "Exit fullscreen", function () { D.fs.toggle(c); });
    c.appendChild(bar);

    function refresh() {
      var cue = show.activeCue();
      label.textContent = cue ? "Cue " + D.fmtNum(cue.number) + " · " + cue.name : "–";
    }
    show.on("active", refresh); refresh();
    D.fs.onChange(function () { c.classList.toggle("is-fs", D.fs.element() === c); self.resize(); });
    document.addEventListener("keydown", function (e) {
      if (D.fs.element() !== c) { return; }
      if (e.key === " " || e.key === "Enter") { e.preventDefault(); show.goNext(); }
      else if (e.key === "Backspace") { e.preventDefault(); show.back(); }
      else if (e.key === "b" || e.key === "B") { show.setBlackout(); }
    });
  };

  Stage3D.prototype._hideHint = function () { if (this.hint) { this.hint.classList.add("gone"); } };
  Stage3D.prototype._orbitButton = function (on) { if (this.orbitBtn) { this.orbitBtn.setAttribute("aria-pressed", on ? "true" : "false"); } };
  Stage3D.prototype._markCamera = function (name) {
    if (!this.camButtons) { return; }
    Object.keys(this.camButtons).forEach(function (k) { this.camButtons[k].setAttribute("aria-pressed", k === name ? "true" : "false"); }, this);
  };

  var tagPos = new T.Vector3();
  Stage3D.prototype._updateTags = function () {
    if (!this.tags) { return; }
    var w = this.w, h = this.h;
    this.fixtures.forEach(function (fx) {
      var el = this.tags[fx.fid];
      tagPos.set(fx.x, TRUSS_Y + 0.45, TRUSS_Z).project(this.cam);
      var visible = tagPos.z < 1;
      el.style.display = visible ? "" : "none";
      if (visible) {
        el.style.transform = "translate(" + ((tagPos.x * 0.5 + 0.5) * w).toFixed(1) + "px," + ((-tagPos.y * 0.5 + 0.5) * h).toFixed(1) + "px) translate(-50%,-100%)";
      }
    }, this);
  };

  Stage3D.prototype.dispose = function () {
    this.fixtures.forEach(function (f) { f.dispose(); });
    this.renderer.dispose();
    if (this.canvas.parentNode) { this.canvas.parentNode.removeChild(this.canvas); }
  };
})(window);

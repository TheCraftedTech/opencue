/*
 * OpenCue website – demo/show.js
 * The model behind the live demo: fixtures, selection, programmer, cue list with fades, executor,
 * effects, grand master and blackout. It is a deliberately small version of what the real program does
 * (see app/state_manager.py, app/cue_engine.py) and has no UI: the panels (ui.js), the stage (stage.js)
 * and the home page's hero all talk to this one object.
 *
 * All values are percent (0..100). Pan and tilt are percent of the fixture's range.
 */
(function (g) {
  "use strict";

  var OC = g.OCDemo = g.OCDemo || {};

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, k) { return a + (b - a) * k; }
  function round1(v) { return Math.round(v * 10) / 10; }

  var KEYS = ["dimmer", "r", "g", "b", "pan", "tilt"];
  var DEFAULTS = { dimmer: 0, r: 100, g: 100, b: 100, pan: 50, tilt: 33 };

  var TYPES = {
    par: { id: "par", label: "Generic RGBW par", keys: ["dimmer", "r", "g", "b"] },
    mh:  { id: "mh",  label: "Generic moving head", keys: ["dimmer", "r", "g", "b", "pan", "tilt"] }
  };

  // name -> [r, g, b] in percent. Order = order of the colour chips in the programmer.
  var COLORS = [
    { id: "red",     rgb: [100, 0, 0] },
    { id: "amber",   rgb: [100, 62, 4] },
    { id: "yellow",  rgb: [100, 92, 0] },
    { id: "green",   rgb: [0, 100, 0] },
    { id: "cyan",    rgb: [0, 100, 100] },
    { id: "blue",    rgb: [8, 24, 100] },
    { id: "magenta", rgb: [100, 0, 100] },
    { id: "white",   rgb: [100, 100, 100] }
  ];

  function hsv(h, s, v) {
    var i = Math.floor(h * 6), f = h * 6 - i;
    var p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
    switch (i % 6) {
      case 0: return [v, t, p];
      case 1: return [q, v, p];
      case 2: return [p, v, t];
      case 3: return [p, q, v];
      case 4: return [t, p, v];
      default: return [v, p, q];
    }
  }

  // i = index among the fixtures running the effect, n = how many, t = seconds
  var EFFECTS = [
    { id: "rainbow", cat: "color", ensure: 80, apply: function (i, n, t) {
        var c = hsv((t * 0.12 + i / n) % 1, 1, 1);
        return { r: c[0] * 100, g: c[1] * 100, b: c[2] * 100 };
      } },
    { id: "chase", cat: "dimmer", ensure: 0, apply: function (i, n, t) {
        var d = ((t * 1.1 - i / n) % 1 + 1) % 1;
        return { dimmer: clamp(100 * (1 - d * 2.6), 6, 100) };
      } },
    { id: "pulse", cat: "dimmer", ensure: 0, apply: function (i, n, t) {
        return { dimmer: 18 + 82 * (0.5 + 0.5 * Math.sin(Math.PI * 2 * (t * 0.6 - i * 0.05))) };
      } },
    { id: "fire", cat: "color", ensure: 70, apply: function (i, n, t) {
        var k = 0.5 + 0.25 * Math.sin(t * 7.3 + i * 2.1) + 0.15 * Math.sin(t * 13.1 + i * 5.7) + 0.1 * Math.sin(t * 29 + i);
        return { r: 100, g: 14 + 26 * k, b: 0, dimmer: 55 + 45 * k };
      } },
    { id: "circle", cat: "position", ensure: 0, keys: ["pan", "tilt"], apply: function (i, n, t) {
        var a = Math.PI * 2 * (t * 0.22 + i / n);
        return { pan: 50 + 34 * Math.cos(a), tilt: 34 + 22 * Math.sin(a) };
      } }
  ];

  function fixtureDefs() {
    return [
      { fid: 1, name: "Par 1",  type: "par", x: -0.78, row: 0 },
      { fid: 2, name: "Par 2",  type: "par", x: -0.26, row: 0 },
      { fid: 3, name: "Par 3",  type: "par", x: 0.26,  row: 0 },
      { fid: 4, name: "Par 4",  type: "par", x: 0.78,  row: 0 },
      { fid: 5, name: "Mover 1", type: "mh", x: -0.52, row: 1 },
      { fid: 6, name: "Mover 2", type: "mh", x: 0.52,  row: 1 }
    ];
  }

  function Show() {
    this.fixtures = fixtureDefs();
    this.byFid = {};
    var self = this;
    this.fixtures.forEach(function (f) { self.byFid[f.fid] = f; });

    this.groups = [
      { id: 1, name: "Pars",   fids: [1, 2, 3, 4] },
      { id: 2, name: "Movers", fids: [5, 6] },
      { id: 3, name: "All",    fids: [1, 2, 3, 4, 5, 6] }
    ];

    this.cueListName = "Default";
    this.cues = this._defaultCues();
    this.activeIdx = 0;
    this.selection = [];
    this.programmer = {};
    this.fx = {};
    this.mix = 100;
    this.master = 100;
    this.blackout = false;
    this.paused = false;
    this.fade = null;
    this.base = {};
    this._l = {};
    this._applyCue(this.cues[0], true);
  }

  Show.TYPES = TYPES;
  Show.COLORS = COLORS;
  Show.EFFECTS = EFFECTS;
  Show.KEYS = KEYS;

  Show.prototype.now = function () { return (g.performance || Date).now(); };

  Show.prototype.on = function (name, fn) { (this._l[name] = this._l[name] || []).push(fn); };
  Show.prototype.emit = function (name, data) {
    (this._l[name] || []).forEach(function (fn) { try { fn(data); } catch (e) { console.error(e); } });
  };

  // -------------------------------------------------------------- default show

  Show.prototype._blankLook = function () {
    var look = {};
    this.fixtures.forEach(function (f) { look[f.fid] = JSON.parse(JSON.stringify(DEFAULTS)); });
    return look;
  };

  Show.prototype._defaultCues = function () {
    var self = this;
    function mk(number, name, fade, spec) {
      var look = self._blankLook();
      Object.keys(spec).forEach(function (fid) { Object.keys(spec[fid]).forEach(function (k) { look[fid][k] = spec[fid][k]; }); });
      return { number: number, name: name, fade: fade, delay: 0, trigger: "Go", values: look };
    }
    function pars(v, extra) {
      var o = {};
      [1, 2, 3, 4].forEach(function (id) { o[id] = Object.assign({}, v, extra && extra[id]); });
      return o;
    }
    function merge(a, b) { var o = Object.assign({}, a); Object.keys(b).forEach(function (k) { o[k] = Object.assign({}, a[k], b[k]); }); return o; }
    var amber = { r: 100, g: 62, b: 4 }, blue = { r: 8, g: 24, b: 100 }, mag = { r: 100, g: 0, b: 90 }, cyan = { r: 0, g: 90, b: 100 };

    return [
      mk(1, "Warm wash", 2, merge(pars(Object.assign({ dimmer: 62 }, amber)), { 5: { dimmer: 0 }, 6: { dimmer: 0 } })),
      mk(2, "Blue night", 2, merge(pars(Object.assign({ dimmer: 78 }, blue)), {
        5: { dimmer: 60, r: 40, g: 70, b: 100, pan: 26, tilt: 40 },
        6: { dimmer: 60, r: 40, g: 70, b: 100, pan: 74, tilt: 40 } })),
      mk(3, "Magenta cross", 1.5, merge(pars(Object.assign({ dimmer: 92 }, mag), { 2: cyan, 4: cyan }), {
        5: { dimmer: 80, r: 100, g: 100, b: 100, pan: 76, tilt: 34 },
        6: { dimmer: 80, r: 100, g: 100, b: 100, pan: 24, tilt: 34 } })),
      mk(4, "Full", 1, merge(pars({ dimmer: 100, r: 100, g: 96, b: 88 }), {
        5: { dimmer: 100, r: 100, g: 96, b: 88, pan: 42, tilt: 32 },
        6: { dimmer: 100, r: 100, g: 96, b: 88, pan: 58, tilt: 32 } })),
      mk(5, "Blackout", 2, {})
    ].map(function (c) {
      if (c.number === 5) { Object.keys(c.values).forEach(function (fid) { c.values[fid].dimmer = 0; }); }
      return c;
    });
  };

  // -------------------------------------------------------------- queries

  Show.prototype.fixture = function (fid) { return this.byFid[fid] || null; };

  Show.prototype.has = function (fid, key) {
    var f = this.byFid[fid];
    return !!f && TYPES[f.type].keys.indexOf(key) >= 0;
  };

  // value of one key as seen on the stage (programmer wins over playback), without master and effects
  Show.prototype.value = function (fid, key) {
    var p = this.programmer[fid];
    if (p && p[key] !== undefined) { return p[key]; }
    return this.base[fid] ? this.base[fid][key] : DEFAULTS[key];
  };

  Show.prototype.programmed = function (fid, key) {
    var p = this.programmer[fid];
    return !!(p && p[key] !== undefined);
  };

  // value shown on the faders: that of the first selected fixture that has the key
  Show.prototype.selectionValue = function (key) {
    for (var i = 0; i < this.selection.length; i++) {
      if (this.has(this.selection[i], key)) { return this.value(this.selection[i], key); }
    }
    return null;
  };

  Show.prototype.selectionHas = function (key) {
    var self = this;
    return this.selection.some(function (fid) { return self.has(fid, key); });
  };

  Show.prototype.groupByRef = function (ref) {
    var s = String(ref).toLowerCase();
    for (var i = 0; i < this.groups.length; i++) {
      if (String(this.groups[i].id) === s || this.groups[i].name.toLowerCase() === s) { return this.groups[i]; }
    }
    return null;
  };

  Show.prototype.cueByNumber = function (n) {
    for (var i = 0; i < this.cues.length; i++) { if (Math.abs(this.cues[i].number - n) < 1e-9) { return i; } }
    return -1;
  };

  Show.prototype.nextIdx = function () {
    var n = this.activeIdx + 1;
    return n < this.cues.length ? n : -1;
  };

  Show.prototype.activeCue = function () { return this.activeIdx >= 0 ? this.cues[this.activeIdx] : null; };

  // 0..1 while a fade is running, else null
  Show.prototype.fadeProgress = function () {
    var f = this.fade;
    if (!f) { return null; }
    var at = this.paused ? f.pausedAt : this.now();
    return f.dur > 0 ? clamp((at - f.start) / f.dur, 0, 1) : 1;
  };

  // -------------------------------------------------------------- selection and programmer

  Show.prototype.select = function (fids, mode) {
    var cur = this.selection.slice();
    var list = fids.filter(function (id) { return !!this.byFid[id]; }, this);
    if (mode === "add") { list.forEach(function (id) { if (cur.indexOf(id) < 0) { cur.push(id); } }); }
    else if (mode === "remove") { cur = cur.filter(function (id) { return list.indexOf(id) < 0; }); }
    else if (mode === "toggle") { list.forEach(function (id) { var i = cur.indexOf(id); if (i < 0) { cur.push(id); } else { cur.splice(i, 1); } }); }
    else { cur = list; }
    cur.sort(function (a, b) { return a - b; });
    this.selection = cur;
    this.emit("selection", cur);
  };

  Show.prototype.clearSelection = function () { this.select([], "replace"); };

  Show.prototype.setProgrammer = function (key, value, fids) {
    var self = this;
    var v = clamp(Number(value), 0, 100);
    var targets = (fids || this.selection).filter(function (fid) { return self.has(fid, key); });
    targets.forEach(function (fid) {
      var p = self.programmer[fid] = self.programmer[fid] || {};
      p[key] = v;
    });
    if (targets.length) { this.emit("programmer", { key: key }); }
    return targets.length;
  };

  Show.prototype.setColor = function (name, fids) {
    var c = COLORS.filter(function (x) { return x.id === String(name).toLowerCase(); })[0];
    if (!c) { return -1; }
    var n = 0;
    n += this.setProgrammer("r", c.rgb[0], fids);
    this.setProgrammer("g", c.rgb[1], fids);
    this.setProgrammer("b", c.rgb[2], fids);
    return n;
  };

  Show.prototype.clearProgrammer = function () {
    this.programmer = {};
    this.emit("programmer", {});
  };

  // [pan, tilt] in percent for the first and the second moving head of the selection
  Show.POSITIONS = {
    center:   [[50, 33], [50, 33]],
    left:     [[16, 36], [16, 36]],
    right:    [[84, 36], [84, 36]],
    cross:    [[78, 34], [22, 34]],
    audience: [[38, 90], [62, 90]]
  };

  Show.prototype.applyPosition = function (id) {
    var self = this, spec = Show.POSITIONS[id];
    var movers = this.selection.filter(function (fid) { return self.has(fid, "pan"); });
    if (!spec || !movers.length) { return 0; }
    movers.forEach(function (fid, i) {
      var v = spec[i % spec.length];
      self.setProgrammer("pan", v[0], [fid]);
      self.setProgrammer("tilt", v[1], [fid]);
    });
    return movers.length;
  };

  Show.prototype.hasProgrammer = function () { return Object.keys(this.programmer).length > 0; };

  // -------------------------------------------------------------- effects

  Show.prototype.effect = function (id) {
    return EFFECTS.filter(function (e) { return e.id === id; })[0] || null;
  };

  // assigns (or toggles off, when every target already runs it) an effect on the selection
  Show.prototype.toggleEffect = function (id, fids) {
    var eff = this.effect(id);
    if (!eff) { return 0; }
    var self = this;
    var targets = (fids || this.selection).filter(function (fid) {
      return !eff.keys || eff.keys.every(function (k) { return self.has(fid, k); });
    });
    if (!targets.length) { return 0; }
    var allOn = targets.every(function (fid) { return self.fx[fid] === id; });
    targets.forEach(function (fid) { if (allOn) { delete self.fx[fid]; } else { self.fx[fid] = id; } });
    this.emit("fx", {});
    return allOn ? -targets.length : targets.length;
  };

  Show.prototype.clearEffects = function () {
    this.fx = {};
    this.emit("fx", {});
  };

  Show.prototype.effectOn = function (id) {
    var self = this;
    return Object.keys(this.fx).some(function (fid) { return self.fx[fid] === id; });
  };

  // -------------------------------------------------------------- cues and playback

  Show.prototype.look = function () {
    var look = {}, self = this;
    this.fixtures.forEach(function (f) {
      var v = {};
      KEYS.forEach(function (k) { v[k] = round1(self.value(f.fid, k)); });
      look[f.fid] = v;
    });
    return look;
  };

  Show.prototype._applyCue = function (cue, instant) {
    var to = JSON.parse(JSON.stringify(cue.values));
    if (instant || !cue.fade) {
      this.base = to;
      this.fade = null;
    } else {
      var from = JSON.parse(JSON.stringify(this.base));
      this.fade = { from: from, to: to, start: this.now(), dur: cue.fade * 1000, delay: (cue.delay || 0) * 1000, pausedAt: 0 };
    }
    this.paused = false;
    // manual (programmer) values are kept: like on a real console they stay until cleared
  };

  Show.prototype.goIndex = function (idx) {
    var cue = this.cues[idx];
    if (!cue) { return null; }
    this.activeIdx = idx;
    this._applyCue(cue, false);
    this.emit("active", cue);
    return cue;
  };

  Show.prototype.goNext = function () {
    var n = this.nextIdx();
    return n < 0 ? null : this.goIndex(n);
  };

  Show.prototype.back = function () {
    var p = this.activeIdx - 1;
    return p < 0 ? null : this.goIndex(p);
  };

  Show.prototype.pause = function () {
    if (!this.fade) { return null; }
    if (this.paused) {
      this.fade.start += this.now() - this.fade.pausedAt;
      this.paused = false;
    } else {
      this.fade.pausedAt = this.now();
      this.paused = true;
    }
    this.emit("active", this.activeCue());
    return this.paused ? "paused" : "resumed";
  };

  // release: no active cue, dimmers fade to zero
  Show.prototype.stop = function () {
    var to = JSON.parse(JSON.stringify(this.base));
    Object.keys(to).forEach(function (fid) { to[fid].dimmer = 0; });
    this.fade = { from: JSON.parse(JSON.stringify(this.base)), to: to, start: this.now(), dur: 1000, delay: 0, pausedAt: 0 };
    this.paused = false;
    this.activeIdx = -1;
    this.emit("active", null);
  };

  Show.prototype.store = function (number, name) {
    var idx = this.cueByNumber(number);
    var created = idx < 0;
    var cue = {
      number: number,
      name: name || ("Cue " + OC.fmtNum(number)),
      fade: created ? 1 : this.cues[idx].fade,
      delay: created ? 0 : this.cues[idx].delay,
      trigger: "Go",
      values: this.look()
    };
    if (!created && !name) { cue.name = this.cues[idx].name; }
    if (created) {
      this.cues.push(cue);
      this.cues.sort(function (a, b) { return a.number - b.number; });
    } else {
      this.cues[idx] = cue;
    }
    this.emit("cues", {});
    return { cue: cue, created: created };
  };

  Show.prototype.updateActive = function () {
    var cue = this.activeCue();
    if (!cue) { return null; }
    cue.values = this.look();
    this.emit("cues", {});
    return cue;
  };

  Show.prototype.deleteCue = function (number) {
    var idx = this.cueByNumber(number);
    if (idx < 0) { return null; }
    var removed = this.cues.splice(idx, 1)[0];
    if (this.activeIdx === idx) { this.activeIdx = -1; }
    else if (this.activeIdx > idx) { this.activeIdx -= 1; }
    this.emit("cues", {});
    this.emit("active", this.activeCue());
    return removed;
  };

  Show.prototype.labelCue = function (number, name) {
    var idx = this.cueByNumber(number);
    if (idx < 0) { return null; }
    this.cues[idx].name = name;
    this.emit("cues", {});
    return this.cues[idx];
  };

  Show.prototype.nextFreeNumber = function () {
    var max = 0;
    this.cues.forEach(function (c) { if (c.number > max) { max = c.number; } });
    return Math.floor(max) + 1;
  };

  Show.prototype.setMix = function (v) { this.mix = clamp(v, 0, 100); this.emit("mix", this.mix); };
  Show.prototype.setMaster = function (v) { this.master = clamp(v, 0, 100); this.emit("master", this.master); };
  Show.prototype.setBlackout = function (on) { this.blackout = on === undefined ? !this.blackout : !!on; this.emit("blackout", this.blackout); };

  // -------------------------------------------------------------- per-frame

  Show.prototype.tick = function (now) {
    var f = this.fade;
    if (!f) { return; }
    var at = this.paused ? f.pausedAt : now;
    var elapsed = at - f.start - (f.delay || 0);
    var k = f.dur > 0 ? clamp(elapsed / f.dur, 0, 1) : 1;
    var self = this;
    Object.keys(f.to).forEach(function (fid) {
      var b = self.base[fid] = self.base[fid] || {};
      KEYS.forEach(function (key) { b[key] = lerp(f.from[fid][key], f.to[fid][key], k); });
    });
    if (k >= 1 && !this.paused) { this.fade = null; this.emit("active", this.activeCue()); }
  };

  // final levels for the stage: effects and manual values applied, then grand master and blackout
  Show.prototype.output = function (now) {
    var t = now / 1000, self = this;

    // index of each fixture among the fixtures that run the same effect
    var counts = {}, order = {};
    this.fixtures.forEach(function (f) {
      var id = self.fx[f.fid];
      if (!id) { return; }
      counts[id] = (counts[id] || 0) + 1;
      order[f.fid] = counts[id] - 1;
    });

    return this.fixtures.map(function (f) {
      var base = self.base[f.fid] || DEFAULTS;
      var v = {};
      KEYS.forEach(function (k) { v[k] = base[k]; });
      v.dimmer *= self.mix / 100;

      var id = self.fx[f.fid];
      if (id) {
        var eff = self.effect(id);
        if (eff.ensure && v.dimmer < 5) { v.dimmer = eff.ensure; }
        var o = eff.apply(order[f.fid], counts[id], t);
        Object.keys(o).forEach(function (k) { v[k] = o[k]; });
      }
      var p = self.programmer[f.fid];
      if (p) { Object.keys(p).forEach(function (k) { v[k] = p[k]; }); }

      var level = self.blackout ? 0 : clamp(v.dimmer, 0, 100) / 100 * self.master / 100;
      return {
        fid: f.fid, type: f.type, x: f.x, row: f.row, level: level,
        r: clamp(v.r, 0, 100) / 100, g: clamp(v.g, 0, 100) / 100, b: clamp(v.b, 0, 100) / 100,
        pan: clamp(v.pan, 0, 100), tilt: clamp(v.tilt, 0, 100), dimmer: clamp(v.dimmer, 0, 100)
      };
    });
  };

  // Fullscreen API with the old WebKit names as fallback (iPhones have none: enabled() is then false)
  OC.fs = {
    enabled: function () { return !!(document.fullscreenEnabled || document.webkitFullscreenEnabled); },
    element: function () { return document.fullscreenElement || document.webkitFullscreenElement || null; },
    toggle: function (el) {
      if (OC.fs.element()) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); }
      else { var req = el.requestFullscreen || el.webkitRequestFullscreen; if (req) { req.call(el); } }
    },
    onChange: function (fn) { document.addEventListener("fullscreenchange", fn); document.addEventListener("webkitfullscreenchange", fn); }
  };

  OC.fmtNum = function (n) { return Number.isInteger(n) ? String(n) : String(round1(n)); };
  OC.clamp = clamp;
  OC.Show = Show;
})(window);

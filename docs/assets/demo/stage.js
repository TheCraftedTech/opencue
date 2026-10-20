/*
 * OpenCue website – demo/stage.js
 * A light-weight stand-in for the program's 3D simulation: a stage with two trusses, fixtures, light
 * cones and light pools, drawn with a simple perspective on a 2D canvas (no libraries, no WebGL).
 * Moving heads follow pan and tilt; selected fixtures get the yellow selection frame of the real program.
 *
 *   var stage = new OCDemo.Stage(canvas, show, { selection: true });
 *   stage.start();                  // own animation loop (used on the home page)
 *   stage.render(show.output(now))  // or draw one frame yourself (used by the demo page)
 */
(function (g) {
  "use strict";

  var OC = g.OCDemo = g.OCDemo || {};

  function lerp(a, b, k) { return a + (b - a) * k; }
  function rgba(r, gr, b, a) { return "rgba(" + Math.round(r) + "," + Math.round(gr) + "," + Math.round(b) + "," + Math.max(0, Math.min(1, a)).toFixed(3) + ")"; }

  function Stage(canvas, show, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.show = show;
    this.opts = opts || {};
    this.w = 0; this.h = 0; this.dpr = 1;
    this.visible = true;
    this.running = false;
    this.last = null;
    var self = this;
    this.resize();
    if (g.ResizeObserver) { new g.ResizeObserver(function () { self.resize(); }).observe(canvas); }
    else { g.addEventListener("resize", function () { self.resize(); }); }
    if (g.IntersectionObserver) {
      new g.IntersectionObserver(function (entries) { self.visible = entries[0].isIntersecting; }).observe(canvas);
    }
  }

  Stage.prototype.resize = function () {
    var r = this.canvas.getBoundingClientRect();
    var dpr = Math.min(g.devicePixelRatio || 1, 2);
    var w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (this.canvas.width !== Math.round(w * dpr) || this.canvas.height !== Math.round(h * dpr)) {
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
    }
    this.w = w; this.h = h; this.dpr = dpr;
    if (this.last) { this.render(this.last); }
  };

  Stage.prototype.start = function () {
    if (this.running) { return; }
    this.running = true;
    var self = this;
    function frame() {
      if (!self.running) { return; }
      if (self.visible && !document.hidden) {
        var now = self.show.now();
        self.show.tick(now);
        self.render(self.show.output(now));
      }
      g.requestAnimationFrame(frame);
    }
    g.requestAnimationFrame(frame);
  };

  Stage.prototype.stop = function () { this.running = false; };

  // geometry: world x in [-1, 1] across the stage, z in [0, 1] from the front edge to the back wall
  Stage.prototype._geometry = function () {
    var W = this.w, H = this.h;
    var horizon = H * 0.5;
    var cx = W / 2, halfW = W * 0.47;
    return {
      W: W, H: H, horizon: horizon, cx: cx, halfW: halfW,
      u: Math.max(0.55, Math.min(1.5, W / 960)),
      proj: function (x, z) {
        var s = lerp(1, 0.42, z);
        return { x: cx + x * s * halfW, y: lerp(H * 0.95, horizon + H * 0.02, z), s: s };
      }
    };
  };

  Stage.prototype.render = function (out) {
    this.last = out;
    var ctx = this.ctx, geo = this._geometry();
    var W = geo.W, H = geo.H, u = geo.u, horizon = geo.horizon, proj = geo.proj;

    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, W, H);

    // back wall and floor
    var wall = ctx.createLinearGradient(0, 0, 0, horizon);
    wall.addColorStop(0, "#060607"); wall.addColorStop(1, "#111115");
    ctx.fillStyle = wall; ctx.fillRect(0, 0, W, horizon);
    var floor = ctx.createLinearGradient(0, horizon, 0, H);
    floor.addColorStop(0, "#101013"); floor.addColorStop(1, "#050506");
    ctx.fillStyle = floor; ctx.fillRect(0, horizon, W, H - horizon);

    ctx.strokeStyle = "rgba(255,255,255,0.035)"; ctx.lineWidth = 1;
    ctx.beginPath();
    for (var wx = 1; wx < 12; wx++) { ctx.moveTo(Math.round(wx * W / 12) + 0.5, 0); ctx.lineTo(Math.round(wx * W / 12) + 0.5, horizon); }
    ctx.stroke();

    ctx.strokeStyle = "rgba(255,255,255,0.05)";
    ctx.beginPath();
    for (var gx = -1; gx <= 1.001; gx += 0.25) { var a = proj(gx, 0), b = proj(gx, 1); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); }
    for (var gz = 0; gz <= 1.001; gz += 0.2) { var l = proj(-1, gz), r = proj(1, gz); ctx.moveTo(l.x, l.y); ctx.lineTo(r.x, r.y); }
    ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.05)"; ctx.fillRect(0, horizon, W, 1);

    // ambient glow on the wall: the mix of everything that is lit
    var sr = 0, sg = 0, sb = 0, sl = 0;
    out.forEach(function (f) { sr += f.r * f.level; sg += f.g * f.level; sb += f.b * f.level; sl += f.level; });
    if (sl > 0.02) {
      var amb = ctx.createRadialGradient(geo.cx, horizon * 0.9, 0, geo.cx, horizon * 0.9, W * 0.55);
      var k = Math.min(1, sl / 2.5);
      amb.addColorStop(0, rgba(sr / sl * 255, sg / sl * 255, sb / sl * 255, 0.22 * k));
      amb.addColorStop(1, rgba(sr / sl * 255, sg / sl * 255, sb / sl * 255, 0));
      ctx.fillStyle = amb; ctx.fillRect(0, 0, W, horizon + 6);
    }

    // trusses
    this._truss(geo, H * 0.05, geo.halfW * 1.0, 4 * u);
    this._truss(geo, H * 0.165, geo.halfW * 0.82, 3 * u);

    var self = this;
    var selected = this.opts.selection ? this.show.selection : [];

    // beams and pools (additive)
    ctx.globalCompositeOperation = "lighter";
    out.forEach(function (f) { if (f.level > 0.004) { self._beam(geo, f); } });
    ctx.globalCompositeOperation = "source-over";

    // fixture bodies on top
    out.forEach(function (f) { self._body(geo, f, selected.indexOf(f.fid) >= 0); });
  };

  Stage.prototype._truss = function (geo, y, half, th) {
    var ctx = this.ctx;
    ctx.fillStyle = "#1f1f24";
    ctx.fillRect(geo.cx - half, y, half * 2, th);
    ctx.fillStyle = "#3a3a42";
    ctx.fillRect(geo.cx - half, y, half * 2, 1);
    ctx.fillStyle = "#17171b";
    ctx.fillRect(geo.cx - half, y + th, half * 2, 1);
  };

  Stage.prototype._source = function (geo, f) {
    var par = f.row === 0;
    var y = par ? geo.H * 0.05 + 9 * geo.u : geo.H * 0.165 + 14 * geo.u;
    var x = geo.cx + f.x * geo.halfW * (par ? 0.92 : 0.82 * 0.92);
    return { x: x, y: y, par: par };
  };

  Stage.prototype._target = function (geo, f) {
    var tx, z, rx;
    if (f.type === "mh") {
      tx = lerp(-0.95, 0.95, f.pan / 100);
      z = lerp(0.1, 0.92, f.tilt / 100);
      var p = geo.proj(tx, z);
      rx = geo.W * 0.052 * p.s;
      return { x: p.x, y: p.y, rx: rx, ry: rx * 0.3 };
    }
    tx = f.x * 0.6; z = 0.5;
    var q = geo.proj(tx, z);
    rx = geo.W * 0.112 * q.s;
    return { x: q.x, y: q.y, rx: rx, ry: rx * 0.3 };
  };

  Stage.prototype._beam = function (geo, f) {
    var ctx = this.ctx, u = geo.u;
    var s = this._source(geo, f), t = this._target(geo, f);
    var L = Math.pow(f.level, 0.8);
    var r = f.r * 255, gr = f.g * 255, b = f.b * 255;
    var w0 = (s.par ? 8 : 4.5) * u;

    // cone
    var grad = ctx.createLinearGradient(0, s.y, 0, t.y);
    grad.addColorStop(0, rgba(r, gr, b, 0.5 * L));
    grad.addColorStop(1, rgba(r, gr, b, 0.1 * L));
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(s.x - w0, s.y); ctx.lineTo(s.x + w0, s.y);
    ctx.lineTo(t.x + t.rx, t.y); ctx.lineTo(t.x - t.rx, t.y);
    ctx.closePath(); ctx.fill();

    // brighter core
    var core = ctx.createLinearGradient(0, s.y, 0, t.y);
    core.addColorStop(0, rgba(r, gr, b, 0.35 * L));
    core.addColorStop(1, rgba(r, gr, b, 0.04 * L));
    ctx.fillStyle = core;
    ctx.beginPath();
    ctx.moveTo(s.x - w0 * 0.4, s.y); ctx.lineTo(s.x + w0 * 0.4, s.y);
    ctx.lineTo(t.x + t.rx * 0.45, t.y); ctx.lineTo(t.x - t.rx * 0.45, t.y);
    ctx.closePath(); ctx.fill();

    // light pool on the floor
    ctx.save();
    ctx.translate(t.x, t.y);
    ctx.scale(1, t.ry / t.rx);
    var pool = ctx.createRadialGradient(0, 0, 0, 0, 0, t.rx * 1.15);
    pool.addColorStop(0, rgba(r, gr, b, 0.85 * L));
    pool.addColorStop(0.55, rgba(r, gr, b, 0.34 * L));
    pool.addColorStop(1, rgba(r, gr, b, 0));
    ctx.fillStyle = pool;
    ctx.beginPath(); ctx.arc(0, 0, t.rx * 1.15, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    // lens glow
    var glow = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, 20 * u);
    glow.addColorStop(0, rgba(Math.min(255, r + 80), Math.min(255, gr + 80), Math.min(255, b + 80), 0.9 * L));
    glow.addColorStop(1, rgba(r, gr, b, 0));
    ctx.fillStyle = glow;
    ctx.beginPath(); ctx.arc(s.x, s.y, 20 * u, 0, Math.PI * 2); ctx.fill();
  };

  Stage.prototype._body = function (geo, f, selected) {
    var ctx = this.ctx, u = geo.u;
    var s = this._source(geo, f);
    var lens = f.level > 0.004
      ? rgba(80 + f.r * 175, 80 + f.g * 175, 80 + f.b * 175, 0.35 + 0.65 * f.level)
      : "#101013";

    ctx.lineWidth = 1;
    if (s.par) {
      ctx.fillStyle = "#1c1c21"; ctx.strokeStyle = "#3d3d45";
      ctx.beginPath(); ctx.rect(s.x - 9 * u, s.y - 8 * u, 18 * u, 11 * u); ctx.fill(); ctx.stroke();
      ctx.fillStyle = lens;
      ctx.beginPath(); ctx.ellipse(s.x, s.y + 3 * u, 8 * u, 3 * u, 0, 0, Math.PI * 2); ctx.fill();
    } else {
      ctx.strokeStyle = "#3d3d45"; ctx.fillStyle = "#1c1c21";
      ctx.beginPath(); ctx.rect(s.x - 5 * u, s.y - 14 * u, 10 * u, 5 * u); ctx.fill(); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(s.x - 9 * u, s.y - 9 * u); ctx.lineTo(s.x - 9 * u, s.y + 1 * u);
      ctx.moveTo(s.x + 9 * u, s.y - 9 * u); ctx.lineTo(s.x + 9 * u, s.y + 1 * u);
      ctx.moveTo(s.x - 9 * u, s.y - 9 * u); ctx.lineTo(s.x + 9 * u, s.y - 9 * u);
      ctx.stroke();
      ctx.fillStyle = "#1c1c21";
      ctx.beginPath(); ctx.arc(s.x, s.y - 2 * u, 7 * u, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = lens;
      ctx.beginPath(); ctx.arc(s.x, s.y - 2 * u, 4.5 * u, 0, Math.PI * 2); ctx.fill();
    }

    if (this.opts.labels !== false) {
      ctx.font = "600 " + Math.round(10 * u) + "px Consolas, 'Cascadia Mono', monospace";
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      ctx.fillStyle = selected ? "#ffe600" : "#80808b";
      ctx.fillText(String(f.fid), s.x, s.y + (s.par ? 8 : 9) * u);
    }

    if (selected) {
      var pad = 13 * u;
      var top = s.par ? s.y - 11 * u : s.y - 17 * u;
      ctx.strokeStyle = "#ffe600"; ctx.lineWidth = 2;
      ctx.shadowColor = "rgba(255,230,0,0.5)"; ctx.shadowBlur = 8;
      ctx.strokeRect(s.x - pad, top, pad * 2, (s.par ? 29 : 36) * u);
      ctx.shadowBlur = 0;
    }
  };

  OC.Stage = Stage;
})(window);

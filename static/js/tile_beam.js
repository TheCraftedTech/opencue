// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Scheinwerfer-Kacheln (Scheinwerfersteuerung): runde Strahl-Vorschau (window.OCTileBeam).
 * Statt einer einfarbigen Flaeche zeigt die Kachel eines beweglichen Scheinwerfers (Pan/Tilt, Gobo, Farbrad ...) den Lichtkreis. Gezeigt wird nur, was sich SICHER aus der GDTF-Datei
 * und dem DMX-Stand ergibt:
 *   - Farbe: RGB / CMY des Scheinwerfers, mit dem Filter des Farbrads (Color1/Color2) multipliziert;
 *   - Helligkeit: Staerke des Lichts (0 % = dunkler Kreis, aber mit einem Ring in der eingestellten Farbe);
 *   - Gobo: das Muster des gewaehlten Slots (Bild aus der GDTF) in dieser Farbe, mehrere Raeder uebereinander;
 *   - Shutter: geschlossen = gestrichelter Rand, Strobe/Puls/Zufall = kleines Blitz-Symbol.
 * Bewusst NICHT gezeigt (nicht sicher abzubilden): Drehung der Gobos, durchlaufende Gobo-Raeder, Prisma, Zoom, Fokus, Frost, Iris. Es gibt keine Animation.
 * Die rohen Radwerte kommen aus dem Live-Strom (window.__fixturesLive[id].wheels, DMX-Puffer); die Slots/Bereiche des Typs aus /api/fixture-types/<Typ>/wheels|beamfx|shutter
 * (einmal je Typ). Neu gezeichnet wird nur bei geaendertem Aussehen (Schluessel) und wenn die Kachel wieder sichtbar wird (anderer Reiter: Groesse 0).
 * Aufruf: OCTileBeam.draw(kachel, id, programmerWerte, dimmerProzent). Meldet fertig geladene Typen/Bilder als Ereignis "tilebeam-data" ({type}). */
(function () {
  "use strict";
  const TAU = Math.PI * 2;
  const types = new Map();             // Typ -> {ready, wheels, beamfx, shutter}
  const images = new Map();            // URL -> {img, ready}
  const isOpen = (s) => !s || /^(open|offen|white|weiss|wei(ss|ß))/i.test(String(s.name || ""));
  const rangeAt = (ranges, v) => (ranges || []).find((r) => v >= r.from && v <= r.to) || null;

  // ------------------------------------------------------------------------------------------ Daten je Typ
  function typeData(typeId) {
    let rec = types.get(typeId);
    if (rec) return rec;
    rec = { ready: false, wheels: [], beamfx: {}, shutter: {} };
    types.set(typeId, rec);
    const get = (part, fallback) => fetch("/api/fixture-types/" + encodeURIComponent(typeId) + "/" + part).then((r) => (r.ok ? r.json() : fallback)).catch(() => fallback);
    Promise.all([get("wheels", []), get("beamfx", {}), get("shutter", {})]).then(([wheels, beamfx, shutter]) => {
      rec.wheels = Array.isArray(wheels) ? wheels : [];
      rec.beamfx = beamfx && typeof beamfx === "object" ? beamfx : {};
      rec.shutter = shutter && typeof shutter === "object" ? shutter : {};
      rec.ready = true;
      document.dispatchEvent(new CustomEvent("tilebeam-data", { detail: { type: typeId } }));
    });
    return rec;
  }
  document.addEventListener("fixture-library-changed", () => types.clear());

  function imageFor(url) {
    let rec = images.get(url);
    if (!rec) {
      rec = { img: new Image(), ready: false };
      rec.img.onload = () => { rec.ready = true; document.dispatchEvent(new CustomEvent("tilebeam-data", { detail: { type: null } })); };
      rec.img.src = url;
      images.set(url, rec);
    }
    return rec;
  }

  // ------------------------------------------------------------------------------------------ Aussehen aus den rohen Werten
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
  function wheelFor(rec, attribute, ch) {
    return rec.wheels.find((w) => w.type === ch.type && w.name === ch.wheel) || rec.wheels.find((w) => w.attribute_name === attribute) || null;
  }

  /** Aussehen: {rgb, gobos: [Bild-URL], closed, strobe} */
  function look(rec, live, p) {
    const out = { rgb: [255, 255, 255], gobos: [], closed: false, strobe: false };
    const c = p && p.color;
    if (c) out.rgb = [c.r, c.g, c.b];
    const bytes = live && live.wheels;
    if (!rec.ready || !bytes) return out;
    for (const wheel of rec.wheels) {                           // Farbfilter der Farbraeder
      if (wheel.type !== "color") continue;
      const v = bytes[wheel.attribute_name];
      if (v === undefined || v === null) continue;
      const slot = findSlot(wheel.slots || [], v);
      if (!slot || isOpen(slot) || !Array.isArray(slot.color)) continue;
      for (let i = 0; i < 3; i++) out.rgb[i] = Math.round(out.rgb[i] * slot.color[i] / 255);
    }
    for (const [attribute, ranges] of Object.entries(rec.shutter)) {          // Shutter: zu / Strobe
      const v = bytes[attribute];
      if (v === undefined || v === null) continue;
      const r = rangeAt(ranges, v);
      if (!r) continue;
      if (r.kind === "closed") out.closed = true;
      else if (r.kind !== "open") out.strobe = true;
    }
    for (const [attribute, ch] of Object.entries(rec.beamfx)) {               // Gobos: nur feste Slots (auch wackelnd = dasselbe Muster), keine durchlaufenden Raeder
      if (ch.role !== "select" || ch.type !== "gobo") continue;
      const v = bytes[attribute];
      if (v === undefined || v === null) continue;
      const r = rangeAt(ch.ranges, v);
      if (!r || r.kind === "scroll") continue;
      const wheel = wheelFor(rec, attribute, ch);
      const slot = wheel && wheel.slots.find((s) => s.index === r.slot);
      if (slot && !isOpen(slot) && slot.image) out.gobos.push(slot.image);
    }
    return out;
  }

  // ------------------------------------------------------------------------------------------ Zeichnen
  const scratch = { beam: document.createElement("canvas"), mask: document.createElement("canvas") };
  const sized = (canvas, n) => { if (canvas.width !== n || canvas.height !== n) { canvas.width = n; canvas.height = n; } return canvas.getContext("2d"); };

  /** Licht des Strahls in scratch.beam: Gobos uebereinander multipliziert (hell = Licht), ohne Gobo ein heller Kreis; danach mit der Farbe multipliziert. */
  function paintBeam(n, L) {
    const g = sized(scratch.beam, n);
    g.globalCompositeOperation = "source-over";
    if (!L.gobos.length) {
      g.fillStyle = "#000";
      g.fillRect(0, 0, n, n);
      g.fillStyle = "#fff";
      g.beginPath();
      g.arc(n / 2, n / 2, n / 2 - 0.5, 0, TAU);
      g.fill();
    } else {
      const m = sized(scratch.mask, n);
      g.fillStyle = "#fff";
      g.fillRect(0, 0, n, n);
      for (const url of L.gobos) {
        const rec = imageFor(url);
        if (!rec.ready) continue;
        m.globalCompositeOperation = "source-over";
        m.fillStyle = "#000";
        m.fillRect(0, 0, n, n);
        m.drawImage(rec.img, 0, 0, n, n);
        g.globalCompositeOperation = "multiply";
        g.drawImage(scratch.mask, 0, 0);
        g.globalCompositeOperation = "source-over";
      }
    }
    g.globalCompositeOperation = "multiply";
    g.fillStyle = "rgb(" + L.rgb.join(",") + ")";
    g.fillRect(0, 0, n, n);
    g.globalCompositeOperation = "source-over";
  }

  function paint(canvas, L, dimPct) {
    const W = canvas.width;
    const H = canvas.height;
    const c = canvas.getContext("2d");
    c.clearRect(0, 0, W, H);
    const cx = W / 2;
    const cy = H / 2;
    const R = Math.max(4, Math.min(W, H) / 2 - 1);
    c.beginPath();
    c.arc(cx, cy, R, 0, TAU);
    c.fillStyle = "#0b0b0d";
    c.fill();
    if (L.closed) {
      c.setLineDash([R * 0.18, R * 0.14]);
      c.strokeStyle = "rgba(255,255,255,.35)";
      c.lineWidth = Math.max(1, R * 0.06);
      c.beginPath();
      c.arc(cx, cy, R - c.lineWidth, 0, TAU);
      c.stroke();
      c.setLineDash([]);
    } else {
      const n = Math.max(8, Math.ceil(2 * R));
      paintBeam(n, L);
      c.save();
      c.beginPath();
      c.arc(cx, cy, R, 0, TAU);
      c.clip();
      c.globalCompositeOperation = "lighter";
      c.globalAlpha = Math.max(0, Math.min(1, dimPct / 100));                            // Licht x Helligkeit: bei 0 % bleibt nur der dunkle Kreis
      c.drawImage(scratch.beam, cx - n / 2, cy - n / 2);
      c.restore();
    }
    c.strokeStyle = "rgba(255,255,255,.16)";
    c.lineWidth = 1;
    c.beginPath();
    c.arc(cx, cy, R - 0.5, 0, TAU);
    c.stroke();
    const ringAlpha = Math.max(0, 1 - dimPct / 100) * 0.9;                // Farbe eingestellt, aber dunkel: Ring in dieser Farbe ("Farbe hinterlegt", nicht schwarz)
    if (!L.closed && ringAlpha > 0.03 && L.rgb[0] + L.rgb[1] + L.rgb[2] > 24) {
      c.strokeStyle = "rgba(" + L.rgb.join(",") + "," + ringAlpha.toFixed(2) + ")";
      c.lineWidth = Math.max(2, R * 0.1);
      c.beginPath();
      c.arc(cx, cy, R - c.lineWidth / 2, 0, TAU);
      c.stroke();
    }
    if (L.strobe) {                                            // kleiner Blitz oben rechts
      const u = R * 0.34;
      const bx = cx + R * 0.52;
      const by = cy - R * 0.5;
      c.beginPath();
      [[0, -1], [-0.55, 0.1], [-0.02, 0.1], [-0.25, 1], [0.55, -0.25], [0.06, -0.25]].forEach(([x, y], i) => (i ? c.lineTo(bx + x * u, by + y * u) : c.moveTo(bx + x * u, by + y * u)));
      c.closePath();
      c.fillStyle = "rgba(255,255,255,.92)";
      c.strokeStyle = "rgba(0,0,0,.7)";
      c.lineWidth = 1;
      c.fill();
      c.stroke();
    }
  }

  // ------------------------------------------------------------------------------------------ Kachel
  function draw(tile, id, p, dimPct) {
    const colorEl = tile.querySelector(".fxprog-tile__color");
    if (!colorEl) return;
    let canvas = tile._beamCanvas;
    if (!canvas) {
      canvas = document.createElement("canvas");
      tile._beamCanvas = canvas;
      colorEl.classList.add("fxprog-tile__color--round");
      colorEl.style.background = "";
      colorEl.style.boxShadow = "";                       // ein Ring der eckigen Ansicht (vor dem Laden der Geraetetypen) darf nicht stehen bleiben
      colorEl.appendChild(canvas);
      // Reiter ohne Kacheln (z. B. "Farbe") blenden das Raster aus: dann ist der Canvas 0 gross und es wird nichts gezeichnet. Wird er wieder sichtbar, sofort den neuesten Stand zeichnen.
      if (typeof ResizeObserver === "function") new ResizeObserver(() => { if (tile._beamRedraw) tile._beamRedraw(); }).observe(canvas);
    }
    const render = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (!w || !h) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const st = tile._beam || (tile._beam = { key: "" });
      const L = look(typeData(tile.dataset.fxType || ""), (window.__fixturesLive || {})[id], p);
      const key = [w, h, dpr, L.rgb.join(","), Math.round(dimPct / 4), L.closed ? 1 : 0, L.strobe ? 1 : 0, L.gobos.map((u) => u + (imageFor(u).ready ? "" : "!")).join(",")].join("|");
      if (key === st.key) return;
      st.key = key;
      const cw = Math.round(w * dpr);
      const ch = Math.round(h * dpr);
      if (canvas.width !== cw || canvas.height !== ch) { canvas.width = cw; canvas.height = ch; }
      paint(canvas, L, dimPct);
    };
    tile._beamRedraw = render;
    render();
  }

  window.OCTileBeam = { draw };
})();

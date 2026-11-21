// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* Panel "Timeline-Editor" (Typ timeline): der grafische Zeitleisten-Editor fuer alles, was zu einer Zeit des globalen Timecodes passiert.
 *
 *   | Lineal                                                                |   <- Klicken / Ziehen = zur Zeit springen
 *   | Cue-Liste 1  | Cue 1 ▸    Cue 2 ▸        Cue 3 ▸                      |   <- Cues mit Ausloeser "Timecode": Marken verschieben
 *   | Befehle 1    |   Blackout Off ▸        Effect Off ▸                    |   <- Befehlsspuren: Befehle zu Zeiten (gehoeren zur Show)
 *   | Lied.mp3     | ▁▂▅▇▅▂▁▁▃▆█▆▃▁▁▂▄▆▄▂▁   (Wellenform)                    |   <- Toene VON SELBST: alle Medien-Player, die zum Timecode abspielen
 *   | Cues ohne Zeit: [Cue 4] [Cue 5]  ... auf die Zeitleiste ziehen oder "Cue hier setzen"                      |
 *
 *  - Der Abspielkopf ist der globale Timecode (app/timecode.py, OCTimecode): Start / Pause / Spulen / Springen wirken auf alle Geraete und Panels; eine LTC- oder MIDI-Quelle fuehrt ihn von aussen.
 *  - Toene: Jeder Medien-Player (Modus "Timecode", Medium gewaehlt, Startzeit) erscheint von selbst als Tonspur mit Wellenform (OCMedia.sources(); dazu GET /api/timeline/sources fuer Player auf anderen
 *    Geraeten). Die Startmarke der Tonspur laesst sich ziehen = die Startzeit des Medien-Players aendern. Zusaetzlich: "Ton hinzufuegen" (eigener Ton dieser Timeline).
 *  - Marke = Cue mit Ausloeser "timecode" (cue.timecode_ms, WS `update_cue`). Befehl = Eintrag einer Befehlsspur (state.timeline_tracks, WS `set_timeline_tracks`); der Server fuehrt ihn aus,
 *    wenn der Timecode VORWAERTS durch seine Zeit laeuft (app/server.py _timecode_cross), genau wie bei Cues.
 *  - Aufnehmen wie am Pult: Musik abspielen, bei jedem Einsatz "Cue hier setzen" (Enter): der gewaehlte Cue bekommt die aktuelle Zeit, dann ist der naechste dran.
 *  - Spulen: Tasten oder Knoepfe (+-5 s, zur vorigen / naechsten Marke, rueckwaerts abspielen), Pfeiltasten (1 s / Umschalt 10 s / Alt 1 Bild), J / K / L, Lineal und Wellenform ziehen.
 * Klassisches Skript, laeuft nach timecode.js und media_player.js. */
(function () {
  "use strict";

  const OC = () => window.OCTimecode;
  const t = (key, vars) => {
    let s = typeof i18n === "function" ? i18n(key) : key;
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split("{" + k + "}").join(String(v));
    return s;
  };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const send = (type, payload) => { if (window.__panelAPI && window.__panelAPI.sendToServer) window.__panelAPI.sendToServer(type, payload); };
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const MAX_MS = 100 * 3600 * 1000;
  const PPS_MIN = 2, PPS_MAX = 600, PPS_DEFAULT = 40;                          // Pixel je Sekunde
  const COLORS = ["#4fa3ff", "#ffb000", "#34d96b", "#ff5a7a", "#b07cff", "#2ed3c6"];
  const SNAPS = [["0", "TL_SNAP_OFF"], ["10", "TL_SNAP_10"], ["40", "TL_SNAP_FRAME"], ["100", "TL_SNAP_100"], ["1000", "TL_SNAP_1S"]];
  const STEPS = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200];
  const JUMP_MS = 5000;
  const peakCache = new Map();                                                 // Medium-ID -> {data: Uint8Array, pps, duration_ms} | "loading" | {error}
  const views = new Set();
  const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

  const fmtShort = (ms, fine) => {
    const total = Math.max(0, ms) / 1000;
    const h = Math.floor(total / 3600), m = Math.floor(total / 60) % 60, s = Math.floor(total) % 60;
    const frac = fine ? "." + String(Math.min(9, Math.round((total - Math.floor(total)) * 10))) : "";
    return (h ? h + ":" + String(m).padStart(2, "0") : String(m)) + ":" + String(s).padStart(2, "0") + frac;
  };
  const cuelists = () => Object.values((typeof client !== "undefined" && client.state && client.state.cuelists) || {});
  const activeListId = () => (client.state && client.state.active_cuelist_id) || "";
  const cmdTracks = () => ((typeof client !== "undefined" && client.state && client.state.timeline_tracks) || []);
  const numText = (n) => String(Math.round(Number(n) * 1000) / 1000);
  const hasTime = (cue) => cue.trigger === "timecode" && cue.timecode_ms !== null && cue.timecode_ms !== undefined;
  const fromB64 = (text) => { const bin = atob(text); const out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i); return out; };
  const mediaOf = (id) => (window.OCMedia && id ? window.OCMedia.get(id) : null);

  async function loadPeaks(mediaId) {
    if (!mediaId) return null;
    const have = peakCache.get(mediaId);
    if (have && have !== "loading") return have;
    if (have === "loading") return null;
    peakCache.set(mediaId, "loading");
    try {
      const res = await fetch(`/api/media/${encodeURIComponent(mediaId)}/peaks`);
      const data = await res.json();
      const entry = res.ok ? { data: fromB64(data.data), pps: data.pps || 100, duration_ms: data.duration_ms || 0 } : { error: data.error || "failed", message: data.message || "" };
      peakCache.set(mediaId, entry);
      return entry;
    } catch (err) {
      const entry = { error: "network", message: String(err && err.message || err) };
      peakCache.set(mediaId, entry);
      return entry;
    }
  }

  function iconButton(icon, key, onClick, extra) {
    const b = el("button", "tl__btn" + (extra ? " " + extra : ""));
    b.type = "button";
    if (icon) b.appendChild(Icons.svg(icon));
    b.addEventListener("click", onClick);
    b.dataset.i18nTip = key;
    b.title = t(key);
    b.setAttribute("aria-label", t(key));
    return b;
  }

  // ------------------------------------------------------------------------------------------------ Panel
  function buildPanel(panel) {
    const view = {
      root: el("div", "tl"),
      mc: Object.assign({ tracks: [], audio_on: true, volume: 100, snap_ms: 10, follow: true }, panel.module_config || {}),
      pps: PPS_DEFAULT,
      list: "",                                                                // gewaehlte Cue-Liste (Tablett + "Cue hier setzen")
      cue: "",                                                                 // gewaehlter Cue
      track: "",                                                               // gewaehlte Befehlsspur
      cmd: "",                                                                 // gewaehlter Befehl
      audio: [],                                                               // Tonspuren: {key, media_id, start_ms, origin, editable, trackId}
      remoteSources: [],                                                       // Antwort von /api/timeline/sources
      players: new Map(),                                                      // eigene Tonspur-Id -> {player, media_id}
      drag: null,
      labelW: 0,
      raf: 0,
    };
    const root = view.root;
    root.tabIndex = 0;
    root.dataset.panelId = panel.id || "";
    // Altbestand: ein einzelner Ton (media_id / audio_start_ms) wird zu einer eigenen Tonspur
    if (view.mc.media_id && !(view.mc.tracks || []).length) view.mc.tracks = [{ id: uid(), media_id: view.mc.media_id, start_ms: Number(view.mc.audio_start_ms) || 0 }];

    // ---- Werkzeugleiste
    const bar = el("div", "tl__bar");
    const transport = el("div", "tl__group");
    const bStop = iconButton("skip-start", "TC_RESET", () => OC().stop());
    const bPrev = iconButton("marker-prev", "TL_PREV_CUE", () => view.jumpMarker(-1));
    const bBack = iconButton("rewind", "TL_BACK_5", () => view.jump(-JUMP_MS));
    const bRev = iconButton("play-reverse", "TC_PLAY_REVERSE", () => OC().play(-1));
    const bPause = iconButton("pause", "TC_PAUSE", () => OC().pause());
    const bPlay = iconButton("play", "TC_PLAY", () => OC().play(1), "tl__btn--play");
    const bFwd = iconButton("forward", "TL_FWD_5", () => view.jump(JUMP_MS));
    const bNext = iconButton("marker-next", "TL_NEXT_CUE", () => view.jumpMarker(1));
    transport.append(bStop, bPrev, bBack, bRev, bPause, bPlay, bFwd, bNext);
    const time = el("div", "tl__time", "00:00:00.000");
    time.setAttribute("role", "timer");
    const source = el("span", "tl__src");
    time.appendChild(source);
    const zoom = el("div", "tl__group");
    const bOut = iconButton("zoom-out", "TL_ZOOM_OUT", () => view.zoomBy(1 / 1.5));
    const bIn = iconButton("zoom-in", "TL_ZOOM_IN", () => view.zoomBy(1.5));
    const bFit = iconButton("fit", "TL_FIT", () => view.fit());
    const bFollow = iconButton("follow", "TL_FOLLOW", () => { view.mc.follow = !view.mc.follow; view.saveConfig({ follow: view.mc.follow }); view.paintToggles(); }, "tl__btn--toggle");
    zoom.append(bOut, bIn, bFit, bFollow);
    const snapWrap = el("label", "tl__field");
    const snapLabel = el("span", "tl__field-label", t("TL_SNAP"));
    const snap = el("select", "tl__select");
    SNAPS.forEach(([value, key]) => { const o = el("option", "", t(key)); o.value = value; o.dataset.i18n = key; snap.appendChild(o); });
    snap.value = String(view.mc.snap_ms);
    snap.addEventListener("change", () => { view.mc.snap_ms = parseInt(snap.value, 10) || 0; view.saveConfig({ snap_ms: view.mc.snap_ms }); });
    snapWrap.append(snapLabel, snap);
    const setHere = el("button", "tl__btn tl__btn--set");
    setHere.type = "button";
    setHere.append(Icons.svg("record"), el("span", "", t("TL_SET_HERE")));
    setHere.title = t("TL_SET_HERE_TIP");
    setHere.addEventListener("click", () => view.assignHere());
    const addCmd = el("button", "tl__btn");
    addCmd.type = "button";
    addCmd.append(Icons.svg("terminal"), el("span", "", t("TL_ADD_CMD")));
    addCmd.title = t("TL_ADD_CMD_TIP");
    addCmd.addEventListener("click", () => view.addCommandHere());
    const addTrack = iconButton("plus", "TL_ADD_TRACK", () => view.addTrack());
    bar.append(transport, time, zoom, snapWrap, setHere, addCmd, addTrack);

    // ---- Tonspur-Zeile
    const audioBar = el("div", "tl__bar tl__bar--audio");
    const audioLabel = el("span", "tl__field-label", t("TL_AUDIO"));
    const addAudio = el("button", "tl__btn");
    addAudio.type = "button";
    addAudio.append(Icons.svg("music"), el("span", "", t("TL_AUDIO_ADD")));
    addAudio.title = t("TL_AUDIO_ADD_TIP");
    addAudio.addEventListener("click", async () => {
      if (!window.OCMedia) return;
      const meta = await window.OCMedia.choose(["audio", "video"]);
      if (!meta) return;
      const tracks = (view.mc.tracks || []).concat([{ id: uid(), media_id: meta.id, start_ms: 0 }]);
      view.saveConfig({ tracks });
      view.refreshAudio();
    });
    const bMute = iconButton("volume", "TL_AUDIO_ON", () => { view.mc.audio_on = !view.mc.audio_on; view.saveConfig({ audio_on: view.mc.audio_on }); view.applyPlayers(); view.paintToggles(); }, "tl__btn--toggle");
    const autoHint = el("span", "tl__hint", t("TL_AUDIO_AUTO_HINT"));
    audioBar.append(audioLabel, addAudio, bMute, autoHint);

    // ---- Spuren
    const scroller = el("div", "tl__scroller");
    const rows = el("div", "tl__rows");
    const playhead = el("div", "tl__playhead");
    scroller.append(rows);
    rows.appendChild(playhead);

    // ---- Tablett: Cues ohne Zeit
    const tray = el("div", "tl__tray");
    const trayHead = el("div", "tl__tray-head");
    const trayChips = el("div", "tl__tray-chips");
    tray.append(trayHead, trayChips);

    // ---- Eingabefenster fuer Befehle / Startzeiten
    const pop = el("div", "tl__pop");
    pop.hidden = true;

    root.append(bar, audioBar, scroller, tray, pop);
    Object.assign(view, { bar, scroller, rows, playhead, tray, trayHead, trayChips, time, source, snap, bMute, bFollow, bPlay, bPause, bStop, setHere, addCmd, addAudio, audioLabel, snapLabel, autoHint, pop });

    // ---- Beschriftungen (Sprachwechsel)
    const iconButtons = [bStop, bPrev, bBack, bRev, bPause, bPlay, bFwd, bNext, bOut, bIn, bFit, bFollow, bMute, addTrack];
    view.labels = () => {
      snapLabel.textContent = t("TL_SNAP");
      audioLabel.textContent = t("TL_AUDIO");
      autoHint.textContent = t("TL_AUDIO_AUTO_HINT");
      setHere.lastChild.textContent = t("TL_SET_HERE");
      setHere.title = t("TL_SET_HERE_TIP");
      addCmd.lastChild.textContent = t("TL_ADD_CMD");
      addCmd.title = t("TL_ADD_CMD_TIP");
      addAudio.lastChild.textContent = t("TL_AUDIO_ADD");
      addAudio.title = t("TL_AUDIO_ADD_TIP");
      snap.querySelectorAll("option").forEach((o) => { o.textContent = t(o.dataset.i18n); });
      iconButtons.forEach((b) => { const key = b.dataset.i18nTip; b.title = t(key); b.setAttribute("aria-label", t(key)); });
      view.rebuild();
    };

    // ---- Hilfsfunktionen der Ansicht
    view.length = () => {
      let end = 20000;
      cuelists().forEach((cl) => cl.cues.forEach((c) => { if (hasTime(c)) end = Math.max(end, c.timecode_ms); }));
      cmdTracks().forEach((tr) => tr.events.forEach((e) => { end = Math.max(end, e.ms); }));
      view.audio.forEach((a) => { const p = peakCache.get(a.media_id); const d = (p && p.duration_ms) || (mediaOf(a.media_id) && mediaOf(a.media_id).duration_ms) || 0; end = Math.max(end, a.start_ms + d); });
      end = Math.max(end, OC().position());
      return end + 15000;
    };
    view.contentEnd = () => view.length() - 15000;
    view.trackWidth = () => Math.ceil(view.length() * view.pps / 1000);
    view.msAt = (clientX) => {
      const track = rows.querySelector(".tl__track");
      if (!track) return 0;
      return clamp((clientX - track.getBoundingClientRect().left) / view.pps * 1000, 0, MAX_MS);
    };
    view.snapMs = (ms) => { const s = view.mc.snap_ms || 0; return clamp(s > 0 ? Math.round(ms / s) * s : Math.round(ms), 0, MAX_MS); };
    view.saveConfig = (patch) => {
      view.mc = Object.assign({}, view.mc, patch);
      const panelEl = root.closest("[data-panel-id]");
      const id = panelEl && panelEl.dataset.panelId;
      if (id && !String(id).startsWith("win-")) send("update_panel", { id, module_config: view.mc });
    };
    view.paintToggles = () => {
      bFollow.classList.toggle("tl__btn--on", !!view.mc.follow);
      bMute.classList.toggle("tl__btn--on", !!view.mc.audio_on);
      bMute.replaceChildren(Icons.svg(view.mc.audio_on ? "volume" : "volume-off"));
    };

    // ---- Spulen
    view.basePosition = () => { const p = view.pendingSeek; return p && performance.now() - p.at < 600 ? p.ms : OC().position(); };     // schnelle Folge von Klicks: vom zuletzt gewuenschten Ziel aus weiter (der Server antwortet erst gleich)
    view.seekTo = (ms) => { const target = clamp(ms, 0, MAX_MS); view.pendingSeek = { ms: target, at: performance.now() }; OC().seek(target); };
    view.jump = (deltaMs) => view.seekTo(view.basePosition() + deltaMs);
    view.markerTimes = () => {
      const times = new Set();
      cuelists().forEach((cl) => cl.cues.forEach((c) => { if (hasTime(c)) times.add(c.timecode_ms); }));
      cmdTracks().forEach((tr) => tr.events.forEach((e) => times.add(e.ms)));
      return [...times].sort((a, b) => a - b);
    };
    view.jumpMarker = (dir) => {
      const pos = view.basePosition();
      const times = view.markerTimes();
      const target = dir > 0 ? times.find((x) => x > pos + 1) : [...times].reverse().find((x) => x < pos - (OC().state.running ? 400 : 1));
      view.seekTo(target !== undefined ? target : (dir > 0 ? view.contentEnd() : 0));
    };

    // ---- Zoom
    /** Zoomen so, dass die Zeit anchorMs genau unter der Bildschirmstelle anchorX (Pixel im Sichtbereich) bleibt. */
    view.zoomAt = (value, anchorMs, anchorX) => {
      const next = clamp(value, PPS_MIN, PPS_MAX);
      if (next === view.pps && anchorX === undefined) return;
      const sc = view.scroller;
      view.pps = next;
      view.layout();
      sc.scrollLeft = Math.max(0, anchorMs * next / 1000 + view.labelWidth() - anchorX);
      view.draw();
      view.movePlayhead();
    };
    view.savePps = () => { try { localStorage.setItem("opencue.timeline.pps", String(Math.round(view.pps))); } catch (err) { /* privates Fenster */ } };
    view.setPps = (value, anchorX) => {
      const next = clamp(value, PPS_MIN, PPS_MAX);
      if (next === view.pps) return;
      const anchor = anchorX === undefined ? view.scroller.clientWidth / 2 : anchorX;
      view.zoomAt(next, view.msAtScroll(anchor), anchor);
      view.savePps();
    };
    view.msAtScroll = (xInViewport) => (view.scroller.scrollLeft + xInViewport - view.labelWidth()) / view.pps * 1000;
    view.labelWidth = () => { const l = rows.querySelector(".tl__label"); return l ? l.offsetWidth : 0; };
    view.zoomBy = (factor, anchorX) => view.setPps(view.pps * factor, anchorX);
    view.fit = () => {
      const usable = Math.max(120, view.scroller.clientWidth - view.labelWidth() - 24);
      const end = Math.max(10000, view.contentEnd());
      view.pps = clamp(usable / (end / 1000 * 1.03), PPS_MIN, PPS_MAX);
      view.layout();
      view.scroller.scrollLeft = 0;
      view.draw();
      view.movePlayhead();
    };

    // ---- Tonspuren bestimmen (aus den Medien-Playern + eigene)
    view.computeAudio = () => {
      const list = [];
      const seen = new Set();
      const add = (item) => { const key = item.media_id + "@" + item.start_ms; if (seen.has(key)) return; seen.add(key); list.push(item); };
      ((window.OCMedia && window.OCMedia.sources()) || []).forEach((s) => add({ key: s.key, media_id: s.media_id, start_ms: s.tc_start_ms, origin: s.origin === "screen" ? "screen" : "player", editable: s.editable, ref: s.key }));
      view.remoteSources.forEach((s) => add({ key: "r" + s.panel_id, media_id: s.media_id, start_ms: s.tc_start_ms, origin: "remote", editable: false }));
      (view.mc.tracks || []).forEach((tr) => add({ key: "own" + tr.id, media_id: tr.media_id, start_ms: Number(tr.start_ms) || 0, origin: "own", editable: true, trackId: tr.id }));
      view.audio = list;
    };
    view.refreshAudio = () => {
      view.computeAudio();
      view.audio.forEach((a) => { if (!peakCache.get(a.media_id)) loadPeaks(a.media_id).then(() => { view.layout(); view.scheduleDraw(); view.paintWaveMessages(); }); });
      view.applyPlayers();
      view.rebuild();
    };
    view.fetchRemoteSources = async () => {
      try {
        const res = await fetch("/api/timeline/sources");
        if (!res.ok) return;
        const data = await res.json();
        const local = (window.OCMedia && window.OCMedia.sources()) || [];
        const next = (data.sources || []).filter((s) => !local.some((l) => l.panel_id && l.panel_id === s.panel_id));
        if (JSON.stringify(next) !== JSON.stringify(view.remoteSources)) { view.remoteSources = next; view.refreshAudio(); }
      } catch (err) { /* offline */ }
    };
    // eigene Tonspuren spielen ueber unsichtbare Player (die Medien-Player der Quellen spielen selbst)
    view.applyPlayers = () => {
      const want = new Map((view.mc.tracks || []).map((tr) => [tr.id, tr]));
      view.players.forEach((entry, id) => { if (!want.has(id)) { entry.player.dispose(); view.players.delete(id); } });
      want.forEach((tr, id) => {
        if (!window.OCMedia || !window.OCMedia.createPlayer || !tr.media_id) return;
        const cfg = { media_id: tr.media_id, sync: "timecode", tc_start_ms: Number(tr.start_ms) || 0, loop: false, muted: !view.mc.audio_on, volume: view.mc.volume == null ? 100 : view.mc.volume };
        const have = view.players.get(id);
        if (have && have.media_id === tr.media_id) { have.player.setConfig(cfg); return; }
        if (have) have.player.dispose();
        view.players.set(id, { player: window.OCMedia.createPlayer(cfg, { internal: true }), media_id: tr.media_id });
      });
    };
    // Browser erlauben Ton erst nach einer Bedienung: die erste Beruehrung des Panels "entsperrt" die eigenen Player
    view.unlock = () => {
      if (view.unlocked || !view.players.size) return;
      view.unlocked = true;
      view.players.forEach((entry) => {
        try { const v = entry.player.video; const p = v.play(); if (p && p.then) p.then(() => { if (!OC().state.running) v.pause(); }).catch(() => { view.unlocked = false; }); } catch (err) { view.unlocked = false; }
      });
    };
    root.addEventListener("pointerdown", view.unlock, true);

    // ---- Aufbau der Spuren
    view.rebuild = () => {
      const lists = cuelists();
      if (!view.list || !lists.some((l) => l.id === view.list)) view.list = activeListId() || (lists[0] && lists[0].id) || "";
      const tracks = cmdTracks();
      if (view.track && !tracks.some((x) => x.id === view.track)) { view.track = ""; view.cmd = ""; }
      const keepLeft = view.scroller.scrollLeft;
      rows.querySelectorAll(".tl__row, .tl__empty").forEach((n) => n.remove());
      view.closePop();
      const ruler = el("div", "tl__row tl__row--ruler");
      const rulerLabel = el("div", "tl__label tl__label--ruler");
      const rulerTrack = el("div", "tl__track tl__track--ruler");
      const rulerCanvas = el("canvas", "tl__canvas");
      rulerTrack.appendChild(rulerCanvas);
      ruler.append(rulerLabel, rulerTrack);
      rows.insertBefore(ruler, playhead);
      view.rulerCanvas = rulerCanvas;
      view.scrub(rulerTrack);

      if (!lists.length) rows.insertBefore(el("div", "tl__empty", t("TL_NO_LISTS")), playhead);
      lists.forEach((cl, index) => {
        const row = el("div", "tl__row tl__row--lane");
        row.dataset.list = cl.id;
        const label = el("button", "tl__label tl__label--list" + (cl.id === view.list ? " tl__label--sel" : ""));
        label.type = "button";
        label.style.setProperty("--tl-c", COLORS[index % COLORS.length]);
        label.textContent = cl.name || t("TL_LIST");
        label.title = cl.name || "";
        label.addEventListener("click", () => { view.list = cl.id; view.cue = ""; view.rebuild(); });
        const track = el("div", "tl__track tl__track--lane");
        track.style.setProperty("--tl-c", COLORS[index % COLORS.length]);
        track.dataset.list = cl.id;
        row.append(label, track);
        rows.insertBefore(row, playhead);
        view.laneCues(cl, track);
        view.bindTrack(track, cl.id);
      });

      tracks.forEach((tr, index) => view.commandLane(tr, index));

      if (!view.audio.length) {
        const row = el("div", "tl__row tl__row--wave tl__row--none");
        row.append(el("div", "tl__label tl__label--wave", t("TL_AUDIO")), el("div", "tl__track tl__track--none", t("TL_AUDIO_NONE_LANE")));
        rows.insertBefore(row, playhead);
      }
      view.audio.forEach((a, index) => view.audioLane(a, index));

      view.layout();
      view.scroller.scrollLeft = keepLeft;
      view.drawTray();
      view.draw();
      view.movePlayhead();
      view.paintWaveMessages();
    };

    view.laneCues = (cl, track) => {
      const active = ((client.state && client.state.active_cue_ids) || {})[cl.id];
      const timed = cl.cues.filter(hasTime).sort((a, b) => a.timecode_ms - b.timecode_ms || a.number - b.number);
      timed.forEach((cue) => {
        const node = el("div", "tl__cue");
        node.tabIndex = 0;
        node.dataset.cue = cue.id;
        node.dataset.list = cl.id;
        node.dataset.ms = String(cue.timecode_ms);
        node.style.left = Math.round(cue.timecode_ms * view.pps / 1000) + "px";
        const flag = el("span", "tl__cue-flag");
        flag.textContent = numText(cue.number) + (cue.name ? " " + cue.name : "");
        node.appendChild(flag);
        node.title = t("TL_CUE_TIP", { n: numText(cue.number), name: cue.name || "", tc: OC().fmt(cue.timecode_ms) });
        if (cue.id === view.cue) node.classList.add("tl__cue--sel");
        if (cue.id === active) node.classList.add("tl__cue--active");
        node.addEventListener("pointerdown", (e) => {
          view.list = cl.id;
          if (view.cue !== cue.id) { rows.querySelectorAll(".tl__cue--sel").forEach((n) => n.classList.remove("tl__cue--sel")); view.cue = cue.id; node.classList.add("tl__cue--sel"); view.drawTray(); }
          view.dragMarker(e, node, { ms: cue.timecode_ms, tip: (ms) => t("TL_CUE_TIP", { n: numText(cue.number), name: cue.name || "", tc: OC().fmt(ms) }), commit: (ms) => view.place(cl.id, cue.id, ms), seek: () => OC().seek(cue.timecode_ms) });
        });
        node.addEventListener("keydown", (e) => view.markerKey(e, cue.timecode_ms, (ms) => view.place(cl.id, cue.id, ms)));
        track.appendChild(node);
      });
    };

    // ---- Befehlsspuren
    view.commandLane = (tr, index) => {
      const color = COLORS[(index + 3) % COLORS.length];
      const row = el("div", "tl__row tl__row--cmd");
      row.dataset.track = tr.id;
      const label = el("div", "tl__label tl__label--cmd" + (tr.id === view.track ? " tl__label--sel" : ""));
      label.style.setProperty("--tl-c", color);
      const name = el("button", "tl__label-name", tr.name);
      name.type = "button";
      name.title = tr.name;
      name.addEventListener("click", () => { view.track = tr.id; view.cmd = ""; rows.querySelectorAll(".tl__label--cmd").forEach((n) => n.classList.toggle("tl__label--sel", n === label)); });
      name.addEventListener("dblclick", () => view.openPop("track", { track: tr }, label));
      const del = el("button", "tl__mini");
      del.type = "button";
      del.appendChild(Icons.svg("close"));
      del.title = t("TL_TRACK_DELETE");
      let armed = 0;
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        if (typeof _askDelete === "function") {                       // Standard-Dialog statt "nochmal klicken"
          _askDelete("other", { title: t("TL_TRACK_DELETE_TITLE"), body: t("TL_TRACK_DELETE_BODY", { name: tr.name || "" }), confirmKey: "FX_DELETE_CONFIRM" }).then((ok) => { if (ok) view.saveTracks(cmdTracks().filter((x) => x.id !== tr.id)); });
          return;
        }
        view.saveTracks(cmdTracks().filter((x) => x.id !== tr.id));
      });
      label.append(name, del);
      const track = el("div", "tl__track tl__track--cmd");
      track.style.setProperty("--tl-c", color);
      track.dataset.track = tr.id;
      row.append(label, track);
      rows.insertBefore(row, playhead);
      tr.events.forEach((ev) => {
        const node = el("div", "tl__cmd");
        node.tabIndex = 0;
        node.dataset.event = ev.id;
        node.dataset.ms = String(ev.ms);
        node.style.left = Math.round(ev.ms * view.pps / 1000) + "px";
        node.appendChild(el("span", "tl__cue-flag", ev.command || t("TL_CMD_EMPTY")));
        node.title = t("TL_CMD_TIP", { tc: OC().fmt(ev.ms), cmd: ev.command || "" });
        if (ev.id === view.cmd) node.classList.add("tl__cmd--sel");
        node.addEventListener("pointerdown", (e) => {
          view.track = tr.id;
          if (view.cmd !== ev.id) { rows.querySelectorAll(".tl__cmd--sel").forEach((n) => n.classList.remove("tl__cmd--sel")); view.cmd = ev.id; node.classList.add("tl__cmd--sel"); }
          view.dragMarker(e, node, { ms: ev.ms, tip: (ms) => t("TL_CMD_TIP", { tc: OC().fmt(ms), cmd: ev.command || "" }), commit: (ms) => view.updateEvent(tr.id, ev.id, { ms }), seek: () => OC().seek(ev.ms), dbl: () => view.openPop("cmd", { track: tr, event: ev }, node) });
        });
        node.addEventListener("keydown", (e) => {
          if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); e.stopPropagation(); view.deleteEvent(tr.id, ev.id); return; }
          if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); view.openPop("cmd", { track: tr, event: ev }, node); return; }
          view.markerKey(e, ev.ms, (ms) => view.updateEvent(tr.id, ev.id, { ms }));
        });
        track.appendChild(node);
      });
      track.addEventListener("pointerdown", (e) => { if (e.target === track && !view.pinching) { view.track = tr.id; view.cmd = ""; rows.querySelectorAll(".tl__label--cmd").forEach((n) => n.classList.toggle("tl__label--sel", n === label)); OC().seek(view.msAt(e.clientX)); } });
      track.addEventListener("dblclick", (e) => { if (e.target === track) view.addCommandAt(tr.id, view.snapMs(view.msAt(e.clientX))); });
    };
    view.saveTracks = (tracks) => {
      tracks.forEach((tr) => tr.events.sort((a, b) => a.ms - b.ms || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)));          // gleiche Reihenfolge wie beim Server (dann ist sein Echo "unveraendert")
      client.state.timeline_tracks = tracks;                                   // sofort zeigen, der Server bestaetigt gleich
      send("set_timeline_tracks", { tracks });
      view.rebuild();
    };
    view.addTrack = () => {
      const tracks = JSON.parse(JSON.stringify(cmdTracks()));
      const track = { id: uid(), name: t("TL_TRACK_DEFAULT", { n: tracks.length + 1 }), events: [] };
      tracks.push(track);
      view.track = track.id;
      view.saveTracks(tracks);
    };
    view.addCommandAt = (trackId, ms) => {
      const tracks = JSON.parse(JSON.stringify(cmdTracks()));
      let track = tracks.find((x) => x.id === trackId);
      if (!track) { track = { id: uid(), name: t("TL_TRACK_DEFAULT", { n: tracks.length + 1 }), events: [] }; tracks.push(track); }
      const ev = { id: uid(), ms: Math.round(ms), command: "" };
      track.events.push(ev);
      view.track = track.id;
      view.cmd = ev.id;
      view.saveTracks(tracks);
      const node = rows.querySelector(`.tl__cmd[data-event="${ev.id}"]`);
      const tr = cmdTracks().find((x) => x.id === track.id);
      if (node && tr) view.openPop("cmd", { track: tr, event: tr.events.find((x) => x.id === ev.id) || ev }, node);
    };
    view.addCommandHere = () => view.addCommandAt(view.track || (cmdTracks()[0] && cmdTracks()[0].id) || "", view.snapMs(OC().position()));
    view.updateEvent = (trackId, eventId, patch) => {
      const tracks = JSON.parse(JSON.stringify(cmdTracks()));
      const track = tracks.find((x) => x.id === trackId);
      const ev = track && track.events.find((x) => x.id === eventId);
      if (!ev) return;
      Object.assign(ev, patch);
      track.events.sort((a, b) => a.ms - b.ms);
      view.saveTracks(tracks);
    };
    view.deleteEvent = async (trackId, eventId) => {
      const tracks = JSON.parse(JSON.stringify(cmdTracks()));
      const track = tracks.find((x) => x.id === trackId);
      if (!track) return;
      const found = track.events.find((x) => x.id === eventId);
      if (found && typeof _askDelete === "function" && !(await _askDelete("other", { title: t("TL_EVENT_DELETE_TITLE"), body: t("TL_EVENT_DELETE_BODY", { name: String(found.command || "").slice(0, 60) }), confirmKey: "FX_DELETE_CONFIRM" }))) return;
      track.events = track.events.filter((x) => x.id !== eventId);
      if (view.cmd === eventId) view.cmd = "";
      view.saveTracks(tracks);
    };

    // ---- Eingabefenster (Befehl / Startzeit / Spurname)
    view.closePop = () => { pop.hidden = true; pop.textContent = ""; };
    view.openPop = (kind, ref, anchor) => {
      pop.textContent = "";
      const field = (labelKey, input) => { const f = el("label", "tl__pop-field"); f.append(el("span", "tl__field-label", t(labelKey)), input); pop.appendChild(f); return input; };
      const input = (value, mono) => { const i = el("input", "tl__input tl__input--wide" + (mono ? " tl__input--mono" : "")); i.type = "text"; i.autocomplete = "off"; i.spellcheck = false; i.value = value; i.addEventListener("keydown", (e) => { if (pop.onkeydown) pop.onkeydown(e); e.stopPropagation(); }); return i; };
      const buttons = el("div", "tl__pop-buttons");
      const ok = el("button", "tl__btn tl__btn--primary", t("TL_POP_OK"));
      ok.type = "button";
      let apply = () => {};
      let first = null;
      if (kind === "cmd") {
        const timeIn = field("TL_CMD_TIME", input(OC().fmt(ref.event.ms), true));
        const cmdIn = field("TL_CMD_COMMAND", input(ref.event.command));
        cmdIn.placeholder = t("TL_CMD_PLACEHOLDER");
        first = cmdIn;
        apply = () => {
          const ms = OC().parse(timeIn.value);
          view.updateEvent(ref.track.id, ref.event.id, { ms: ms === null ? ref.event.ms : ms, command: cmdIn.value.trim() });
        };
        const del = el("button", "tl__btn", t("TL_CMD_DELETE"));
        del.type = "button";
        del.addEventListener("click", () => { view.closePop(); view.deleteEvent(ref.track.id, ref.event.id); });
        buttons.append(del);
        pop.appendChild(el("p", "tl__pop-hint", t("TL_CMD_HINT")));
      } else if (kind === "audio") {
        const timeIn = field("TL_AUDIO_START", input(OC().fmt(ref.lane.start_ms), true));
        first = timeIn;
        apply = () => { const ms = OC().parse(timeIn.value); if (ms !== null) view.setAudioStart(ref.lane, ms); };
      } else if (kind === "track") {
        const nameIn = field("TL_TRACK_RENAME", input(ref.track.name));
        first = nameIn;
        apply = () => { const tracks = JSON.parse(JSON.stringify(cmdTracks())); const tr = tracks.find((x) => x.id === ref.track.id); if (tr && nameIn.value.trim()) { tr.name = nameIn.value.trim(); view.saveTracks(tracks); } };
      }
      const closeNow = () => { view.closePop(); };
      ok.addEventListener("click", () => { closeNow(); apply(); });
      const cancel = el("button", "tl__btn", t("TL_POP_CANCEL"));
      cancel.type = "button";
      cancel.addEventListener("click", closeNow);
      buttons.append(cancel, ok);
      pop.appendChild(buttons);
      pop.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); closeNow(); apply(); } else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeNow(); } };
      pop.hidden = false;
      const rr = root.getBoundingClientRect();
      const ar = anchor.getBoundingClientRect();
      pop.style.left = Math.round(clamp(ar.left - rr.left, 8, Math.max(8, rr.width - pop.offsetWidth - 8))) + "px";
      pop.style.top = Math.round(clamp(ar.bottom - rr.top + 4, 8, Math.max(8, rr.height - pop.offsetHeight - 8))) + "px";
      if (first) { first.focus(); first.select(); }
    };

    // ---- Tonspuren-Zeilen
    view.audioLane = (lane, index) => {
      const row = el("div", "tl__row tl__row--wave");
      row.dataset.audio = lane.key;
      const media = mediaOf(lane.media_id);
      const label = el("div", "tl__label tl__label--wave");
      const name = el("span", "tl__label-text", media ? media.name : t("TL_AUDIO_MISSING"));
      name.title = (media ? media.name : "") + " (" + t("TL_SRC_" + lane.origin.toUpperCase()) + ")";
      const tag = el("span", "tl__tag", t("TL_SRC_" + lane.origin.toUpperCase()));
      label.append(name, tag);
      if (lane.origin === "own") {
        const del = el("button", "tl__mini");
        del.type = "button";
        del.appendChild(Icons.svg("close"));
        del.title = t("TL_AUDIO_CLEAR");
        del.addEventListener("click", () => { view.saveConfig({ tracks: (view.mc.tracks || []).filter((x) => x.id !== lane.trackId) }); view.refreshAudio(); });
        label.appendChild(del);
      }
      const track = el("div", "tl__track tl__track--wave");
      const canvas = el("canvas", "tl__canvas");
      canvas._lane = lane;
      const msg = el("div", "tl__wave-msg");
      msg._lane = lane;
      const flag = el("div", "tl__astart" + (lane.editable ? " tl__astart--edit" : ""));
      flag.dataset.ms = String(lane.start_ms);
      flag.style.left = Math.round(lane.start_ms * view.pps / 1000) + "px";
      flag.appendChild(Icons.svg("music"));
      flag.title = lane.editable ? t("TL_AUDIO_START_EDIT") : t("TL_AUDIO_START_LOCKED");
      if (lane.editable) {
        flag.addEventListener("pointerdown", (e) => view.dragMarker(e, flag, { ms: lane.start_ms, tip: (ms) => t("TL_AUDIO_START_TIP", { tc: OC().fmt(ms) }), commit: (ms) => view.setAudioStart(lane, ms), seek: () => OC().seek(lane.start_ms), dbl: () => view.openPop("audio", { lane }, flag) }));
      }
      track.append(canvas, msg, flag);
      row.append(label, track);
      rows.insertBefore(row, playhead);
      view.scrub(track, flag);
    };
    view.setAudioStart = (lane, ms) => {
      const start = Math.max(0, Math.round(ms));
      if (lane.origin === "own") {
        view.saveConfig({ tracks: (view.mc.tracks || []).map((x) => (x.id === lane.trackId ? Object.assign({}, x, { start_ms: start }) : x)) });
        view.applyPlayers();
      } else if (window.OCMedia && lane.ref) window.OCMedia.setSourceStart(lane.ref, start);
      lane.start_ms = start;
      view.refreshAudio();
    };

    view.layout = () => {
      const width = view.trackWidth();
      rows.style.setProperty("--tl-w", width + "px");
      rows.querySelectorAll(".tl__track").forEach((n) => { n.style.width = width + "px"; });
      rows.querySelectorAll(".tl__cue, .tl__cmd, .tl__astart").forEach((n) => { n.style.left = Math.round(Number(n.dataset.ms) * view.pps / 1000) + "px"; });
      rows.querySelectorAll(".tl__track--lane, .tl__track--cmd").forEach((track) => {
        const items = [...track.querySelectorAll(".tl__cue, .tl__cmd")].sort((a, b) => Number(a.dataset.ms) - Number(b.dataset.ms));
        items.forEach((n, i) => { const nx = items[i + 1]; n.style.maxWidth = nx ? Math.max(18, Math.round((Number(nx.dataset.ms) - Number(n.dataset.ms)) * view.pps / 1000) - 3) + "px" : ""; });
      });
      view.labelW = view.labelWidth();
    };

    // ---- Zeichnen (nur der sichtbare Ausschnitt: Lineal und Wellenformen)
    view.draw = () => { view.drawRuler(); view.drawWaves(); };
    view.scheduleDraw = () => { if (view.raf) return; view.raf = requestAnimationFrame(() => { view.raf = 0; view.draw(); }); };
    const colors = () => { const cs = getComputedStyle(root); return { text: cs.getPropertyValue("--text-3").trim() || "#888", line: cs.getPropertyValue("--border-strong").trim() || "#555", accent: cs.getPropertyValue("--accent").trim() || "#fb0", wave: cs.getPropertyValue("--text-2").trim() || "#aaa" }; };
    const sizeCanvas = (canvas, height) => {
      const sc = view.scroller;
      const w = Math.max(10, sc.clientWidth - view.labelWidth());
      const ratio = window.devicePixelRatio || 1;
      if (canvas.width !== Math.round(w * ratio) || canvas.height !== Math.round(height * ratio)) { canvas.width = Math.round(w * ratio); canvas.height = Math.round(height * ratio); canvas.style.width = w + "px"; canvas.style.height = height + "px"; }
      canvas.style.transform = `translateX(${sc.scrollLeft}px)`;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, w, height);
      return { ctx, w, h: height };
    };
    view.drawRuler = () => {
      const canvas = view.rulerCanvas;
      if (!canvas || !canvas.isConnected) return;
      const { ctx, w, h } = sizeCanvas(canvas, canvas.parentElement.clientHeight || 26);
      const c = colors();
      const scrollLeft = view.scroller.scrollLeft;
      const step = STEPS.find((s) => s * view.pps >= 84) || STEPS[STEPS.length - 1];
      const minor = [5, 4, 2].find((n) => step * view.pps / n >= 9 && (step / n) * 1000 % 1 < 0.001) || 1;
      const t0 = Math.floor(scrollLeft / view.pps / (step / minor)) * (step / minor);
      ctx.font = "11px ui-monospace, Consolas, monospace";
      ctx.textBaseline = "top";
      for (let time = t0; time * view.pps - scrollLeft < w + 80; time += step / minor) {
        const x = Math.round(time * view.pps - scrollLeft) + 0.5;
        const major = Math.abs(time / step - Math.round(time / step)) < 1e-6;
        ctx.strokeStyle = major ? c.text : c.line;
        ctx.beginPath(); ctx.moveTo(x, major ? h - 12 : h - 6); ctx.lineTo(x, h); ctx.stroke();
        if (major) { ctx.fillStyle = c.text; ctx.fillText(fmtShort(time * 1000, step < 1), x + 3, 3); }
      }
    };
    view.drawWaves = () => {
      const c = colors();
      const scrollLeft = view.scroller.scrollLeft;
      rows.querySelectorAll(".tl__row--wave canvas").forEach((canvas) => {
        const lane = canvas._lane;
        if (!lane || !canvas.isConnected) return;
        const { ctx, w, h } = sizeCanvas(canvas, canvas.parentElement.clientHeight || 70);
        const peaks = peakCache.get(lane.media_id);
        if (!peaks || !peaks.data) return;
        const mid = h / 2;
        ctx.fillStyle = c.wave;
        const perPx = peaks.pps / view.pps;
        for (let px = 0; px < w; px += 1) {
          const seconds = (scrollLeft + px) / view.pps - lane.start_ms / 1000;
          if (seconds < 0) continue;
          const i0 = Math.floor(seconds * peaks.pps);
          if (i0 >= peaks.data.length) break;
          const i1 = Math.min(peaks.data.length, Math.max(i0 + 1, Math.ceil(i0 + perPx)));
          let max = 0;
          for (let i = i0; i < i1; i += 1) if (peaks.data[i] > max) max = peaks.data[i];
          const amp = Math.sqrt(max / 255) * (h / 2 - 2);
          ctx.fillRect(px, mid - amp, 1, Math.max(1, amp * 2));
        }
        // Cue- und Befehlsmarken als feine Linien ueber die Wellenform (damit man sieht, was wo einsetzt)
        ctx.strokeStyle = c.accent;
        ctx.globalAlpha = 0.45;
        rows.querySelectorAll(".tl__cue, .tl__cmd").forEach((n) => {
          const x = Number(n.dataset.ms) * view.pps / 1000 - scrollLeft;
          if (x < -2 || x > w + 2) return;
          ctx.beginPath(); ctx.moveTo(Math.round(x) + 0.5, 0); ctx.lineTo(Math.round(x) + 0.5, h); ctx.stroke();
        });
        ctx.globalAlpha = 1;
      });
    };
    view.paintWaveMessages = () => {
      rows.querySelectorAll(".tl__wave-msg").forEach((msg) => {
        const lane = msg._lane;
        const p = lane ? peakCache.get(lane.media_id) : null;
        let text = "";
        if (!lane || !lane.media_id) text = "";
        else if (!p || p === "loading") text = t("TL_WAVE_LOADING");
        else if (p.error) text = p.error === "ffmpeg_missing" ? t("TL_WAVE_FFMPEG") : t("TL_WAVE_FAIL", { reason: p.message || p.error });
        msg.textContent = text;
        msg.hidden = !text;
      });
    };

    // ---- Abspielkopf
    view.movePlayhead = () => {
      const pos = OC().position();
      const x = view.labelWidth() + pos * view.pps / 1000;
      playhead.style.transform = `translateX(${Math.round(x)}px)`;
      if (view.time.firstChild && view.time.firstChild.nodeType === 3) view.time.firstChild.nodeValue = OC().fmt(pos);
      else view.time.insertBefore(document.createTextNode(OC().fmt(pos)), view.source);
      return pos;
    };
    view.tick = () => {
      view.raf2 = 0;
      if (!root.isConnected) return;
      const pos = view.movePlayhead();
      const s = OC().state;
      if (s.running && view.mc.follow && !view.drag) {
        const sc = view.scroller;
        const x = pos * view.pps / 1000 - sc.scrollLeft;
        const usable = sc.clientWidth - view.labelWidth();
        if (x > usable * 0.88 || x < 0) sc.scrollLeft = Math.max(0, pos * view.pps / 1000 - usable * 0.25);
      }
      if (s.running) view.raf2 = requestAnimationFrame(view.tick);
    };
    view.kick = () => { if (!view.raf2) view.raf2 = requestAnimationFrame(view.tick); };
    view.paintState = () => {
      const s = OC().state;
      bPlay.classList.toggle("tl__btn--on", s.running && s.direction > 0);
      bRev.classList.toggle("tl__btn--on", s.running && s.direction < 0);
      bPause.classList.toggle("tl__btn--on", !s.running && s.position_ms > 0);
      view.source.textContent = s.source === "ltc" ? "LTC" : (s.source === "midi" ? "MTC" : "");
      view.source.hidden = !s.source;
      root.classList.toggle("tl--recording", s.running);
      view.kick();
      view.movePlayhead();
    };

    // ---- Springen (Lineal und Wellenform)
    view.scrub = (track, except) => {
      let down = false;
      let last = 0;
      const go = (e) => { const now = performance.now(); if (now - last < 30) return; last = now; OC().seek(view.msAt(e.clientX)); };
      track.addEventListener("pointerdown", (e) => { if ((e.button !== undefined && e.button !== 0) || view.pinching || (except && e.target.closest && e.target.closest(".tl__astart"))) return; down = true; track.setPointerCapture(e.pointerId); go(e); e.preventDefault(); });
      track.addEventListener("pointermove", (e) => { if (down) go(e); });
      const end = (e) => { if (!down) return; down = false; OC().seek(view.msAt(e.clientX)); };
      track.addEventListener("pointerup", end);
      track.addEventListener("pointercancel", () => { down = false; });
    };
    view.bindTrack = (track, listId) => {
      track.addEventListener("pointerdown", (e) => {
        if (e.target !== track || view.pinching) return;
        if (view.list !== listId) { view.list = listId; view.cue = ""; view.drawTray(); rows.querySelectorAll(".tl__label--list").forEach((n) => n.classList.toggle("tl__label--sel", n.parentElement.dataset.list === listId)); rows.querySelectorAll(".tl__cue--sel").forEach((n) => n.classList.remove("tl__cue--sel")); }
        OC().seek(view.msAt(e.clientX));
      });
      track.addEventListener("dragover", (e) => { if (view.dragChip && view.dragChip.list === listId) { e.preventDefault(); track.classList.add("tl__track--drop"); } });
      track.addEventListener("dragleave", () => track.classList.remove("tl__track--drop"));
      track.addEventListener("drop", (e) => {
        track.classList.remove("tl__track--drop");
        if (!view.dragChip || view.dragChip.list !== listId) return;
        e.preventDefault();
        view.place(listId, view.dragChip.cue, view.snapMs(view.msAt(e.clientX)));
        view.dragChip = null;
      });
    };

    // ---- Marken verschieben (Cues, Befehle, Tonstart): gleiches Ziehen fuer alle
    view.place = (listId, cueId, ms) => send("update_cue", { cuelist_id: listId, cue_id: cueId, trigger: "timecode", timecode_ms: Math.round(ms) });
    view.dragMarker = (e, node, cfg) => {
      if (e.button !== undefined && e.button !== 0) return;
      e.stopPropagation();
      node.setPointerCapture(e.pointerId);
      view.drag = { node, startX: e.clientX, startMs: cfg.ms, ms: cfg.ms, moved: false, id: e.pointerId };
      const move = (ev) => {
        const d = view.drag;
        if (!d || ev.pointerId !== d.id) return;
        const dx = ev.clientX - d.startX;
        if (!d.moved && Math.abs(dx) < 4) return;
        d.moved = true;
        let ms = d.startMs + dx / view.pps * 1000;
        ms = ev.shiftKey ? clamp(Math.round(ms), 0, MAX_MS) : view.snapMs(ms);
        d.ms = ms;
        node.dataset.ms = String(ms);
        node.style.left = Math.round(ms * view.pps / 1000) + "px";
        node.classList.add("tl__marker--drag");
        node.title = cfg.tip(ms);
        const sc = view.scroller;                                               // am Rand mitscrollen
        const rect = sc.getBoundingClientRect();
        if (ev.clientX > rect.right - 30) sc.scrollLeft += 14; else if (ev.clientX < rect.left + view.labelWidth() + 30) sc.scrollLeft -= 14;
      };
      const up = (ev) => {
        const d = view.drag;
        if (!d || ev.pointerId !== d.id) return;
        node.removeEventListener("pointermove", move);
        node.removeEventListener("pointerup", up);
        node.removeEventListener("pointercancel", up);
        view.drag = null;
        node.classList.remove("tl__marker--drag");
        if (d.moved && Math.round(d.ms) !== Math.round(d.startMs)) cfg.commit(d.ms);
        else if (d.moved) { node.dataset.ms = String(d.startMs); node.style.left = Math.round(d.startMs * view.pps / 1000) + "px"; }
        else if (ev.detail >= 2 && cfg.dbl) cfg.dbl();
        else if (ev.detail >= 2 && cfg.seek) cfg.seek();                       // Doppelklick: dorthin springen
        view.scheduleDraw();
      };
      node.addEventListener("pointermove", move);
      node.addEventListener("pointerup", up);
      node.addEventListener("pointercancel", up);
    };
    view.markerKey = (e, ms, commit) => {
      const step = (view.mc.snap_ms || 10) * (e.shiftKey ? 10 : 1);
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault(); e.stopPropagation();
        commit(clamp(ms + (e.key === "ArrowLeft" ? -step : step), 0, MAX_MS));
      } else if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); OC().seek(ms); }
    };

    // ---- "Cue hier setzen": gewaehlten Cue auf die Abspielposition legen, dann den naechsten waehlen
    view.nextTarget = () => {
      const cl = cuelists().find((l) => l.id === view.list);
      if (!cl || !cl.cues.length) return null;
      const sorted = cl.cues.slice().sort((a, b) => a.number - b.number);
      if (view.cue) { const own = sorted.find((c) => c.id === view.cue); if (own) return { cl, cue: own, sorted }; }
      const free = sorted.find((c) => !hasTime(c));
      return free ? { cl, cue: free, sorted } : null;
    };
    view.assignHere = () => {
      const target = view.nextTarget();
      if (!target) { if (window._showToast) window._showToast(t("TL_NOTHING_TO_SET"), "info", 3500); return; }
      const ms = view.snapMs(OC().position());
      view.place(target.cl.id, target.cue.id, ms);
      const index = target.sorted.findIndex((c) => c.id === target.cue.id);
      const next = target.sorted.slice(index + 1).find((c) => !hasTime(c)) || target.sorted[index + 1];
      view.cue = next ? next.id : "";
      view.flash = target.cue.id;
    };

    // ---- Tablett
    view.drawTray = () => {
      const cl = cuelists().find((l) => l.id === view.list);
      trayChips.textContent = "";
      trayHead.textContent = cl ? t("TL_TRAY_TITLE", { name: cl.name || "" }) : "";
      if (!cl) return;
      const free = cl.cues.filter((c) => !hasTime(c)).sort((a, b) => a.number - b.number);
      if (!free.length) { trayChips.appendChild(el("span", "tl__tray-empty", cl.cues.length ? t("TL_TRAY_EMPTY") : t("TL_TRAY_NO_CUES"))); return; }
      free.forEach((cue) => {
        const chip = el("button", "tl__chip" + (cue.id === view.cue ? " tl__chip--sel" : ""));
        chip.type = "button";
        chip.draggable = true;
        chip.textContent = numText(cue.number) + (cue.name ? " " + cue.name : "");
        chip.title = t("TL_CHIP_TIP");
        chip.addEventListener("click", () => { view.cue = view.cue === cue.id ? "" : cue.id; view.drawTray(); rows.querySelectorAll(".tl__cue--sel").forEach((n) => n.classList.remove("tl__cue--sel")); });
        chip.addEventListener("dragstart", (e) => { view.dragChip = { list: cl.id, cue: cue.id }; if (e.dataTransfer) { e.dataTransfer.setData("text/plain", cue.id); e.dataTransfer.effectAllowed = "move"; } });
        chip.addEventListener("dragend", () => { view.dragChip = null; rows.querySelectorAll(".tl__track--drop").forEach((n) => n.classList.remove("tl__track--drop")); });
        trayChips.appendChild(chip);
      });
    };

    // ---- Zoom mit Mausrad / zwei Fingern
    scroller.addEventListener("wheel", (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      const rect = scroller.getBoundingClientRect();
      view.zoomBy(e.deltaY < 0 ? 1.18 : 1 / 1.18, e.clientX - rect.left);
    }, { passive: false });
    const touches = new Map();
    let pinch = null;
    scroller.addEventListener("pointerdown", (e) => {
      if (e.pointerType !== "touch") return;
      touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (touches.size === 2) {
        const [a, b] = [...touches.values()];
        const rect = scroller.getBoundingClientRect();
        // Die Zeit unter der Mitte der beiden Finger wird beim Start MERKEN und bleibt unter der Fingermitte (kein Neuberechnen je Schritt: das liess die Ansicht hin und her springen)
        pinch = { dist: Math.hypot(a.x - b.x, a.y - b.y) || 1, pps: view.pps, anchorMs: view.msAtScroll((a.x + b.x) / 2 - rect.left), frame: 0 };
        view.pinching = true;
      }
    }, true);
    const applyPinch = () => {
      if (!pinch) return;
      pinch.frame = 0;
      const [a, b] = [...touches.values()];
      if (!a || !b) return;
      const rect = scroller.getBoundingClientRect();
      view.zoomAt(pinch.pps * (Math.hypot(a.x - b.x, a.y - b.y) / pinch.dist), pinch.anchorMs, (a.x + b.x) / 2 - rect.left);       // Zoom UND Verschieben mit den zwei Fingern
    };
    scroller.addEventListener("pointermove", (e) => {
      if (!touches.has(e.pointerId)) return;
      touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pinch && touches.size === 2 && !pinch.frame) pinch.frame = requestAnimationFrame(applyPinch);              // hoechstens einmal je Bild
    }, true);
    // Mit zwei Fingern darf der Browser nicht selbst scrollen / zoomen (sonst arbeiten er und wir gegeneinander: die Ansicht wackelt nach links und rechts)
    scroller.addEventListener("touchmove", (e) => { if (e.touches.length >= 2 || view.pinching) e.preventDefault(); }, { passive: false });
    const lift = (e) => { touches.delete(e.pointerId); if (touches.size < 2) { if (pinch) { if (pinch.frame) cancelAnimationFrame(pinch.frame); view.savePps(); } pinch = null; setTimeout(() => { view.pinching = false; }, 120); } };
    scroller.addEventListener("pointerup", lift, true);
    scroller.addEventListener("pointercancel", lift, true);
    scroller.addEventListener("scroll", () => { view.scheduleDraw(); view.movePlayhead(); }, { passive: true });

    // ---- Tastatur im Panel (Spulen wie in einem Schnittprogramm)
    root.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || tag === "BUTTON") return;
      if (e.ctrlKey || e.metaKey) return;
      const onMarker = e.target && e.target.classList && (e.target.classList.contains("tl__cue") || e.target.classList.contains("tl__cmd"));
      let used = true;
      const key = e.key;
      if (key === " ") { OC().state.running ? OC().pause() : OC().play(1); }
      else if (key === "Enter" && !onMarker) view.assignHere();
      else if ((key === "ArrowLeft" || key === "ArrowRight") && !onMarker) view.jump((key === "ArrowLeft" ? -1 : 1) * (e.altKey ? 40 : (e.shiftKey ? 10000 : 1000)));
      else if (e.altKey) used = false;
      else if (key === "+" || key === "=") view.zoomBy(1.5);
      else if (key === "-" || key === "_") view.zoomBy(1 / 1.5);
      else if (key === "Home") view.seekTo(0);
      else if (key === "End") view.seekTo(view.contentEnd());
      else if (key === "[") view.jumpMarker(-1);
      else if (key === "]") view.jumpMarker(1);
      else if (key.toLowerCase() === "j") OC().play(-1);
      else if (key.toLowerCase() === "k") OC().pause();
      else if (key.toLowerCase() === "l") OC().play(1);
      else if (key.toLowerCase() === "f") view.fit();
      else if (key.toLowerCase() === "c") view.addCommandHere();
      else if ((key === "Delete" || key === "Backspace") && view.cmd && !onMarker) view.deleteEvent(view.track, view.cmd);
      else if (key === "Escape") view.closePop();
      else used = false;
      if (used) { e.preventDefault(); e.stopPropagation(); }
    });

    // ---- Anbindung
    try { const saved = parseFloat(localStorage.getItem("opencue.timeline.pps")); if (saved >= PPS_MIN && saved <= PPS_MAX) { view.pps = saved; view.hasZoom = true; } } catch (err) { /* privates Fenster */ }
    view.unsub = OC().subscribe(() => { if (root.isConnected) view.paintState(); });
    view.onSources = () => { if (root.isConnected) view.refreshAudio(); };
    document.addEventListener("oc-media-sources", view.onSources);
    view.ticks = 0;
    view.watch = setInterval(() => {
      if (!root.isConnected) {
        clearInterval(view.watch);
        document.removeEventListener("oc-media-sources", view.onSources);
        if (view.unsub) view.unsub();
        view.players.forEach((entry) => entry.player.dispose());
        view.players.clear();
        views.delete(view);
        return;
      }
      if (view.labelW !== view.labelWidth() || view.lastWidth !== view.scroller.clientWidth) { view.lastWidth = view.scroller.clientWidth; view.labelW = view.labelWidth(); view.scheduleDraw(); }
      view.ticks += 1;
      if (view.ticks % 10 === 0) view.fetchRemoteSources();                     // Player auf anderen Geraeten: alle paar Sekunden nachsehen
    }, 400);
    views.add(view);
    view.paintToggles();
    requestAnimationFrame(() => {
      view.computeAudio();
      view.rebuild();
      if (!view.hasZoom) view.fit();
      view.paintState();
      view.refreshAudio();
      view.fetchRemoteSources();
    });
    return root;
  }

  function viewOf(panelEl) { for (const v of views) if (panelEl.contains(v.root)) return v; return null; }

  window.__panelPlugins.register({
    type: "timeline",
    buildContent: buildPanel,
    onMessage(panelEl, type, payload) {
      const v = viewOf(panelEl);
      if (!v) return;
      if (type === "timeline_tracks_changed") {
        const next = (payload && payload.tracks) || [];
        const same = JSON.stringify(next) === JSON.stringify(cmdTracks());             // Echo der eigenen Aenderung: nichts neu zeichnen (ein offenes Eingabefenster soll offen bleiben)
        if (client.state) client.state.timeline_tracks = next;
        if (!same || v.pop.hidden) v.rebuild();
      } else if (type === "cuelists_changed" || type === "state_snapshot") {
        const flash = v.flash;
        v.flash = null;
        v.rebuild();
        if (flash) { const node = v.rows.querySelector(`.tl__cue[data-cue="${flash}"]`); if (node) { node.classList.add("tl__cue--flash"); setTimeout(() => node.classList.remove("tl__cue--flash"), 700); } }
      } else if (type === "media_changed") setTimeout(() => v.refreshAudio(), 0);
      else if (type === "panels_changed") setTimeout(() => v.fetchRemoteSources(), 300);
      else if (type === "language_changed") v.labels();
    },
    onModuleConfigChanged(panelEl, mc) {
      const v = viewOf(panelEl);
      if (!v) return;
      v.mc = Object.assign({}, v.mc, mc || {});
      v.paintToggles();
      v.refreshAudio();
    },
  });
  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.timeline = "PANEL_TIMELINE";
  window.OCTimeline = { views };
})();

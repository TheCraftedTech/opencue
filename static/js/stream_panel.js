/* Livestream-Panel (Kamera) - Client-Seite.
 *  - OCStreams: die Stream-Quellen dieses Computers (Name, Adresse, Typ, Zugangsdaten). Das Passwort bleibt auf dem Server (verschluesselt);
 *    die Clients sehen nur 'hat Passwort'. Quellen mit Passwort laufen immer ueber den Server (/api/streams/<id>/...).
 *  - OCCameras: die Kameras am HAUPTGERAET (dem Computer, auf dem das Programm laeuft). Die Liste und das Bild kommen immer von dort
 *    (/api/cameras, MJPEG), auf jedem Geraet gleich - ein iPad im Netz sieht dieselben Kameras und bekommt das Bild vom Hauptgeraet gestreamt.
 *  - Panel "stream": zeigt eine Quelle (MJPEG, Video, HLS, WebRTC/WHEP) oder eine Kamera am Hauptgeraet. Pausieren trennt die Verbindung;
 *    der Zustand wird im Layout gespeichert (das Panel startet beim naechsten Mal genauso; jedes Geraet hat sein eigenes Layout).
 *    Neu verbinden, Vollbild. Verbindet sich nach Fehlern selbst neu (Rueckzug 2-30 s), fuellt das Panel bis zum Rand.
 * Laeuft nach app.js und icons.js. */
(function () {
  "use strict";

  const t = (key, vars) => {
    let s = i18n(key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const RETRY_SECONDS = [2, 4, 8, 15, 30];
  const NO_RETRY = new Set(["STREAM_ERR_NO_FFMPEG", "STREAM_ERR_CAM_UNSUPPORTED", "STREAM_ERR_CAM_DENIED", "STREAM_ERR_SCHEME"]);    // Wiederholen aendert nichts
  const STALL_MS = 12000;

  // ------------------------------------------------------------------------------------------------------ Quellen
  let sources = [];
  const listeners = new Set();

  function ingest(list) {
    sources = Array.isArray(list) ? list : [];
    listeners.forEach((fn) => { try { fn(sources); } catch (e) { console.error(e); } });
  }

  function errorKey(code) {
    return {
      invalid_url: "STREAM_ERR_INVALID_URL", unsupported_scheme: "STREAM_ERR_SCHEME", invalid_name: "STREAM_ERR_NAME", self: "STREAM_ERR_SELF",
      invalid_type: "STREAM_ERR_TYPE", too_many: "STREAM_ERR_TOO_MANY", auth: "STREAM_ERR_AUTH", not_found: "STREAM_ERR_NOT_FOUND",
      network: "STREAM_ERR_NETWORK", upstream: "STREAM_ERR_UPSTREAM", foreign_host: "STREAM_ERR_FOREIGN", busy: "STREAM_ERR_BUSY",
      no_ffmpeg: "STREAM_ERR_NO_FFMPEG", no_camera: "STREAM_ERR_CAM_NONE", in_use: "STREAM_ERR_CAM_BUSY", permission: "STREAM_ERR_CAM_DENIED",
      camera_failed: "STREAM_ERR_CAM_FAILED", unsupported_os: "STREAM_ERR_CAM_UNSUPPORTED",
    }[code] || "STREAM_ERR_GENERIC";
  }

  async function call(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
      return { ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) };
    } catch (e) {
      return { ok: false, status: 0, data: { error: "network" } };
    }
  }

  const proxied = (row) => !!(row.proxy || row.has_password);
  // c = Kennung des Panels (+ Zaehler): jedes Panel hat seine eigene Verbindung zum Server (der Browser teilt sonst gleiche Bild-Adressen
  // zwischen Panels, dann haetten Pause und Betrachterzahl je nach Browser ein anderes Verhalten)
  const liveUrl = (row, token) => (proxied(row) ? `/api/streams/${encodeURIComponent(row.id)}/live${token ? "?c=" + token : ""}` : row.url);
  const hlsUrl = (row) => (proxied(row) ? `/api/streams/${encodeURIComponent(row.id)}/hls` : row.url);

  // ---- Dialog 'Quelle anlegen/bearbeiten'
  let editResolver = null;
  let editing = null;
  const $ = (id) => document.getElementById(id);

  function editSource(existing) {
    return new Promise(async (resolve) => {
      if (!$("stream-source-ok")) { resolve(null); return; }
      editing = existing || null;
      const info = await call("GET", "/api/streams");
      const canStore = !info.ok || info.data.password_storage !== false;
      $("stream-source-title").textContent = t(existing ? "STREAM_SRC_TITLE_EDIT" : "STREAM_SRC_TITLE_NEW");
      $("stream-source-name").value = existing ? existing.name : "";
      $("stream-source-url").value = existing ? existing.url : "";
      $("stream-source-type").value = existing ? existing.type : "auto";
      $("stream-source-user").value = existing ? existing.user : "";
      $("stream-source-password").value = "";
      $("stream-source-password").placeholder = existing && existing.has_password ? t("STREAM_SRC_PW_KEEP") : "";
      $("stream-source-clearpw").checked = false;
      $("stream-source-clearpw-row").hidden = !(existing && existing.has_password);
      $("stream-source-proxy").checked = existing ? !!existing.proxy : false;
      $("stream-source-pwnote").hidden = canStore;
      $("stream-source-test-result").textContent = "";
      $("stream-source-test-result").className = "sp-dialog__result";
      refreshSourceHints();
      editResolver = resolve;
      Modal._hooks["stream-source"] = () => { if (editResolver) { const r = editResolver; editResolver = null; r(null); } };
      Modal.open("stream-source");
      setTimeout(() => $("stream-source-name").focus(), 60);
    });
  }

  /** Hinweise im Dialog: RTSP geht nicht im Browser; mit Passwort laeuft die Quelle immer ueber den Server. */
  function refreshSourceHints() {
    const url = $("stream-source-url").value.trim().toLowerCase();
    $("stream-source-rtsp").hidden = !/^(rtsps?|rtmps?):/.test(url);
    const pw = !!$("stream-source-password").value || (editing && editing.has_password && !$("stream-source-clearpw").checked);
    const proxy = $("stream-source-proxy");
    if (pw) proxy.checked = true;
    proxy.disabled = !!pw;
  }

  function sourceBody() {
    const body = {
      name: $("stream-source-name").value, url: $("stream-source-url").value, type: $("stream-source-type").value,
      user: $("stream-source-user").value, proxy: $("stream-source-proxy").checked,
    };
    if (editing) body.id = editing.id;
    const pw = $("stream-source-password").value;
    if (pw) body.password = pw;
    else if (editing && $("stream-source-clearpw").checked) body.password = "";
    return body;
  }

  async function finishEdit() {
    const ok = $("stream-source-ok");
    ok.disabled = true;
    const res = await call("POST", "/api/streams", sourceBody());
    ok.disabled = false;
    if (!res.ok) { _showToast(errorKey(res.data.error), "warn", 5000); return; }
    const resolve = editResolver;
    editResolver = null;
    delete Modal._hooks["stream-source"];
    Modal.close("stream-source");
    if (resolve) resolve(res.data.source);
  }

  async function testSource() {
    const out = $("stream-source-test-result");
    const btn = $("stream-source-test");
    btn.disabled = true;
    out.className = "sp-dialog__result";
    out.textContent = t("STREAM_SRC_TESTING");
    const body = sourceBody();
    const res = await call("POST", "/api/streams/test", { id: body.id, url: body.url, type: body.type, user: body.user, password: body.password || undefined });
    btn.disabled = false;
    if (res.ok) {
      out.className = "sp-dialog__result sp-dialog__result--ok";
      out.textContent = t(res.data.status ? "STREAM_SRC_TEST_OK" : "STREAM_SRC_TEST_OK_NOSTATUS", { type: t("STREAM_TYPE_" + String(res.data.resolved_type || "video").toUpperCase()), status: res.data.status });
    } else {
      out.className = "sp-dialog__result sp-dialog__result--bad";
      out.textContent = t(errorKey(res.data.error));
    }
  }

  // ---- Dialog 'Quelle entfernen'
  let removeResolver = null;
  function askRemove(row) {
    return new Promise((resolve) => {
      const ok = $("stream-remove-ok");
      if (!ok) { resolve(false); return; }
      $("stream-remove-name").textContent = row.name;
      removeResolver = resolve;
      Modal._hooks["stream-remove"] = () => { if (removeResolver) { const r = removeResolver; removeResolver = null; r(false); } };
      Modal.open("stream-remove");
      setTimeout(() => ok.focus(), 50);
    });
  }

  const OCStreams = {
    get sources() { return sources; },
    get: (id) => sources.find((s) => s.id === id) || null,
    editSource,
    /** Fragt nach und entfernt dann; false = abgebrochen. */
    async confirmRemove(id) {
      const row = OCStreams.get(id);
      if (!row || !(await askRemove(row))) return false;
      const res = await call("DELETE", `/api/streams/${encodeURIComponent(id)}`);
      if (res.ok) _showToast(t("STREAM_REMOVED", { name: row.name }), "ok", 3500, true);
      return res.ok;
    },
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    errorKey,
  };
  window.OCStreams = OCStreams;

  // ---- Kameras am Hauptgeraet (die Liste kommt immer vom Server, nie vom Browser des jeweiligen Geraets)
  let cameras = { loaded: false, supported: true, ffmpeg: true, devices: [] };
  const cameraListeners = new Set();

  async function loadCameras(force) {
    if (cameras.loaded && !force) return cameras;
    const res = await call("GET", "/api/cameras" + (force ? "?refresh=1" : ""));
    if (res.ok) {
      cameras = { loaded: true, supported: res.data.supported !== false, ffmpeg: !!res.data.ffmpeg, devices: Array.isArray(res.data.devices) ? res.data.devices : [] };
      cameraListeners.forEach((fn) => { try { fn(cameras); } catch (e) { console.error(e); } });
    }
    return cameras;
  }

  const OCCameras = {
    get state() { return cameras; },
    load: loadCameras,
    subscribe(fn) { cameraListeners.add(fn); return () => cameraListeners.delete(fn); },
  };
  window.OCCameras = OCCameras;

  client.registerModule("streams", {
    onMessage(message) {
      if (message.type === "state_snapshot" && message.payload) ingest(message.payload.stream_sources);
      else if (message.type === "stream_sources_changed") ingest(message.payload.sources);
    },
  });

  function wireDialogs() {
    const ok = $("stream-source-ok");
    if (!ok) return;
    ok.addEventListener("click", finishEdit);
    $("stream-source-test").addEventListener("click", testSource);
    ["stream-source-url", "stream-source-password"].forEach((id) => $(id).addEventListener("input", refreshSourceHints));
    $("stream-source-clearpw").addEventListener("change", refreshSourceHints);
    ["stream-source-name", "stream-source-url", "stream-source-user", "stream-source-password"].forEach((id) => {
      $(id).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); finishEdit(); } });
    });
    $("stream-remove-ok").addEventListener("click", () => {
      const resolve = removeResolver;
      removeResolver = null;
      delete Modal._hooks["stream-remove"];
      Modal.close("stream-remove");
      if (resolve) resolve(true);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wireDialogs);
  else wireDialogs();

  // ------------------------------------------------------------------------------------------------------ Panel
  const wraps = new Set();
  let timer = 0;

  function saveConfig(wrap, patch) {
    const panelEl = OCFullscreen.panelOf(wrap);
    if (!panelEl) return;
    const next = { ...wrap._sp.mc, ...patch };
    wrap._sp.mc = next;
    window.__panelAPI.sendToServer("update_panel", { id: panelEl.dataset.panelId, module_config: next });
    applyConfig(wrap);
  }

  function toggleFullscreen(wrap) {
    OCFullscreen.toggle(wrap);
  }

  function setBarButtonIcon(button, name) {
    const current = button.firstChild;
    if (current && current.classList && current.classList.contains("ico--" + name)) return;
    button.textContent = "";
    button.appendChild(Icons.svg(name));
  }

  const QUALITIES = ["low", "medium", "high", "max"];
  const quality = (mc) => (QUALITIES.includes(mc.quality) ? mc.quality : "medium");
  /** Pause: steht in den Panel-Einstellungen (mc.paused) und wird mit dem Layout des jeweiligen Geraets gespeichert (jedes Geraet hat sein eigenes). */
  const wantPaused = (s) => !!s.mc.paused;
  const hostCam = (mc) => (typeof mc.source === "string" && mc.source.startsWith("cam:") ? mc.source.slice(4) : "");
  const hasSource = (mc) => !!mc.source && mc.source !== "camera";          // "camera" war der fruehere Browser-Kamera-Modus (gibt es nicht mehr)

  function sourceLabel(s) {
    const cam = hostCam(s.mc);
    if (cam) {
      const dev = OCCameras.state.devices.find((d) => d.id === cam);
      return (dev && dev.name) || s.mc.camera_label || t("STREAM_CAM_HOST");
    }
    const row = OCStreams.get(s.mc.source);
    return row ? row.name : "";
  }

  /** Zeigt je nach Zustand: Platzhalter (keine Quelle), Verbinden/Fehler mit Wiederholen, Pause, Antippen-Hinweis, 'Live'-Marke, Leiste. */
  function render(wrap) {
    const s = wrap._sp;
    const idle = s.state === "idle";
    const paused = s.state === "paused";
    const kind = s.kind;
    s.empty.hidden = !idle;
    s.pausedBox.hidden = !paused;
    s.status.hidden = !(s.state === "connecting" || s.state === "error");
    s.statusIcon.hidden = s.state !== "error";
    s.retry.hidden = s.state !== "error";
    s.statusText.textContent = s.state === "error" ? t(s.errorKey) : t("STREAM_CONNECTING");
    s.statusSub.textContent = s.state === "error" && s.retryAt ? t("STREAM_RETRY_IN", { s: Math.max(0, Math.ceil((s.retryAt - Date.now()) / 1000)) }) : "";
    s.statusSub.hidden = !s.statusSub.textContent;
    s.unlock.hidden = !(s.state === "playing" && s.blocked);
    s.live.hidden = s.state !== "playing";
    s.bar.hidden = idle;
    s.name.textContent = sourceLabel(s);
    s.mute.hidden = !(kind === "video" || kind === "hls" || kind === "webrtc");
    s.pause.hidden = idle;
    setBarButtonIcon(s.pause, paused ? "play" : "pause");
    s.pause.classList.toggle("sp__btn--on", paused);
    s.pause.title = t(paused ? "STREAM_RESUME" : "STREAM_PAUSE");
    s.pause.setAttribute("aria-label", s.pause.title);
    s.pause.setAttribute("aria-pressed", paused ? "true" : "false");
    wrap.style.setProperty("--sp-fit", s.mc.fit === "cover" ? "cover" : "contain");
    if (s.media && s.media.tagName === "VIDEO") s.media.muted = !!s.mc.muted;
    setBarButtonIcon(s.mute, s.mc.muted ? "volume-off" : "volume");
    s.mute.classList.toggle("sp__btn--on", !!s.mc.muted);
    s.mute.title = t(s.mc.muted ? "STREAM_UNMUTE" : "STREAM_MUTE");
    s.mute.setAttribute("aria-label", s.mute.title);
    s.mute.setAttribute("aria-pressed", s.mc.muted ? "true" : "false");
    wrap.dataset.state = s.state;
  }

  /** Alles abbauen, was zu einer Verbindung gehoert (Element, Peer-Verbindung). */
  function stop(wrap) {
    const s = wrap._sp;
    s.gen += 1;
    if (s.abort) { try { s.abort.abort(); } catch (e) { /* schon beendet */ } s.abort = null; }
    if (s.pc) { try { s.pc.close(); } catch (e) { /* schon geschlossen */ } s.pc = null; }
    if (s.media) {
      if (s.media.tagName === "VIDEO") { s.media.pause(); s.media.srcObject = null; s.media.removeAttribute("src"); s.media.load(); }
      else s.media.removeAttribute("src");
      s.media.remove();
      s.media = null;
    }
    s.blocked = false;
  }

  function fail(wrap, key, retry) {
    const s = wrap._sp;
    stop(wrap);
    clearTimeout(s.retryTimer);
    s.state = "error";
    s.errorKey = key;
    s.retryAt = 0;
    if (retry !== false && !NO_RETRY.has(key) && s.mc.reconnect) {
      const wait = RETRY_SECONDS[Math.min(s.attempt, RETRY_SECONDS.length - 1)];
      s.attempt += 1;
      s.retryAt = Date.now() + wait * 1000;
      s.retryTimer = setTimeout(() => start(wrap), wait * 1000);
    }
    render(wrap);
  }

  /** Beim Laden ueber den Server liefert dieser den Grund (falsches Passwort, nicht erreichbar ...); ein Bild/Video meldet nur 'Fehler'. */
  async function failWithReason(wrap, gen, url, fallbackKey) {
    const s = wrap._sp;
    let key = fallbackKey;
    if (url.startsWith("/api/")) {
      const abort = new AbortController();
      try {
        const res = await fetch(url, { signal: abort.signal });
        if (!res.ok) key = errorKey((await res.json().catch(() => ({}))).error);
        abort.abort();
      } catch (e) { /* bleibt bei der allgemeinen Meldung */ }
    }
    if (gen === s.gen) fail(wrap, key);
  }

  function playing(wrap, gen) {
    const s = wrap._sp;
    if (gen !== s.gen) return;
    s.attempt = 0;
    s.lastProgress = performance.now();
    if (s.state !== "playing") { s.state = "playing"; render(wrap); }
  }

  function newVideo(wrap, gen) {
    const s = wrap._sp;
    const video = document.createElement("video");
    video.className = "sp__media";
    video.playsInline = true;
    video.autoplay = true;
    video.disablePictureInPicture = true;
    video.muted = !!s.mc.muted;
    video.addEventListener("playing", () => playing(wrap, gen));
    video.addEventListener("timeupdate", () => { s.lastProgress = performance.now(); });
    s.stage.insertBefore(video, s.stage.firstChild);
    s.media = video;
    return video;
  }

  function play(wrap, gen, video) {
    const promise = video.play();
    if (promise && promise.catch) {
      promise.catch((err) => {
        if (gen !== wrap._sp.gen) return;
        if (err && err.name === "NotAllowedError") { wrap._sp.blocked = true; wrap._sp.state = "playing"; render(wrap); }
      });
    }
  }

  function startMjpeg(wrap, gen, url) {
    const s = wrap._sp;
    const img = document.createElement("img");
    img.className = "sp__media";
    img.alt = "";
    img.draggable = false;
    img.addEventListener("load", () => playing(wrap, gen));
    img.addEventListener("error", () => { if (gen === s.gen) failWithReason(wrap, gen, url, "STREAM_ERR_LOAD"); });
    s.stage.insertBefore(img, s.stage.firstChild);
    s.media = img;
    img.src = url;
  }

  function startVideo(wrap, gen, row, hls) {
    const s = wrap._sp;
    if (hls && !document.createElement("video").canPlayType("application/vnd.apple.mpegurl")) { fail(wrap, "STREAM_ERR_HLS_UNSUPPORTED", false); return; }
    const url = hls ? hlsUrl(row) : liveUrl(row);
    const video = newVideo(wrap, gen);
    video.addEventListener("error", () => { if (gen === s.gen) failWithReason(wrap, gen, url, "STREAM_ERR_LOAD"); });
    video.addEventListener("ended", () => { if (gen === s.gen) fail(wrap, "STREAM_ERR_ENDED"); });
    video.src = url;
    play(wrap, gen, video);
  }

  function iceComplete(pc, maxMs) {
    return new Promise((resolve) => {
      if (pc.iceGatheringState === "complete") { resolve(); return; }
      const done = () => { pc.removeEventListener("icegatheringstatechange", check); clearTimeout(timeout); resolve(); };
      const check = () => { if (pc.iceGatheringState === "complete") done(); };
      const timeout = setTimeout(done, maxMs);
      pc.addEventListener("icegatheringstatechange", check);
    });
  }

  async function startWebrtc(wrap, gen, row) {
    const s = wrap._sp;
    if (!window.RTCPeerConnection) { fail(wrap, "STREAM_ERR_WEBRTC_UNSUPPORTED", false); return; }
    const video = newVideo(wrap, gen);
    const pc = new RTCPeerConnection({ iceServers: [] });
    s.pc = pc;
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });
    const stream = new MediaStream();
    video.srcObject = stream;
    pc.ontrack = (event) => { stream.addTrack(event.track); play(wrap, gen, video); };
    pc.onconnectionstatechange = () => {
      if (gen !== s.gen) return;
      if (pc.connectionState === "failed" || pc.connectionState === "closed") fail(wrap, "STREAM_ERR_WEBRTC");
    };
    try {
      await pc.setLocalDescription(await pc.createOffer());
      await iceComplete(pc, 2000);
      if (gen !== s.gen) return;
      const res = await fetch(`/api/streams/${encodeURIComponent(row.id)}/whep`, { method: "POST", headers: { "Content-Type": "application/sdp" }, body: pc.localDescription.sdp });
      if (gen !== s.gen) return;
      if (!res.ok) { fail(wrap, errorKey((await res.json().catch(() => ({}))).error)); return; }
      const answer = await res.text();
      if (gen !== s.gen) return;
      await pc.setRemoteDescription({ type: "answer", sdp: answer });
    } catch (e) {
      if (gen === s.gen) fail(wrap, "STREAM_ERR_WEBRTC");
    }
  }

  function start(wrap) {
    const s = wrap._sp;
    clearTimeout(s.retryTimer);
    stop(wrap);
    const gen = s.gen;
    s.retryAt = 0;
    s.kind = "";
    s.camSeq = -1;
    s.pollFails = 0;
    s.polling = false;
    s.token = `${s.id}-${++s.starts}`;
    s.sig = signature(s.mc);
    if (!hasSource(s.mc)) { s.state = "idle"; render(wrap); return; }
    if (wantPaused(s)) { s.state = "paused"; render(wrap); return; }
    s.state = "connecting";
    const cam = hostCam(s.mc);
    if (cam) {                                    // Kamera am Hauptgeraet: der Server schickt das Bild (MJPEG), auf jedem Geraet gleich
      s.kind = "mjpeg";
      render(wrap);
      startMjpeg(wrap, gen, `/api/cameras/${encodeURIComponent(cam)}/live?c=${s.token}&q=${quality(s.mc)}`);
      return;
    }
    const row = OCStreams.get(s.mc.source);
    if (!row) { fail(wrap, "STREAM_ERR_SOURCE_GONE", false); return; }
    s.kind = row.resolved_type;
    render(wrap);
    if (s.kind === "mjpeg") startMjpeg(wrap, gen, liveUrl(row, s.token));
    else if (s.kind === "hls") startVideo(wrap, gen, row, true);
    else if (s.kind === "webrtc") startWebrtc(wrap, gen, row);
    else startVideo(wrap, gen, row, false);
  }

  /** Aenderungen, die eine neue Verbindung brauchen (Quelle, Adresse/Typ/Zugang der Quelle). */
  function signature(mc) {
    const row = mc.source && !hostCam(mc) && mc.source !== "camera" ? OCStreams.get(mc.source) : null;
    return JSON.stringify([mc.source || "", hostCam(mc) ? quality(mc) : "", row ? [row.url, row.resolved_type, row.proxy, row.has_password, row.user] : null]);
  }

  function applyConfig(wrap) {
    const s = wrap._sp;
    if (signature(s.mc) !== s.sig) start(wrap);                               // andere Quelle/Qualitaet: neu verbinden
    else applyPause(wrap);
  }

  /** Passt die Verbindung an den gewuenschten Pausen-Zustand an. */
  function applyPause(wrap) {
    const s = wrap._sp;
    const want = wantPaused(s);
    if (want && s.state !== "paused") {
      clearTimeout(s.retryTimer);
      stop(wrap);
      s.state = "paused";
      s.retryAt = 0;
    } else if (!want && s.state === "paused") {
      s.attempt = 0;
      start(wrap);
      return;
    }
    render(wrap);
  }

  /** Pause setzen: wird im Layout gespeichert - so startet das Panel nach einem Neustart genauso. */
  function setPaused(wrap, value) {
    saveConfig(wrap, { paused: value });
    applyPause(wrap);
  }

  function togglePause(wrap) {
    setPaused(wrap, !wantPaused(wrap._sp));
  }

  function reconnectNow(wrap) {
    const s = wrap._sp;
    s.attempt = 0;
    if (wantPaused(s)) setPaused(wrap, false);
    else start(wrap);
  }

  /** Kamera am Hauptgeraet: laeuft sie noch und kommen neue Bilder? (Ein abgebrochener Bildstrom meldet der Browser sonst nicht.) */
  async function pollCamera(wrap) {
    const s = wrap._sp;
    const id = hostCam(s.mc);
    if (!id || s.polling) return;
    const gen = s.gen;
    s.polling = true;
    const res = await call("GET", `/api/cameras/${encodeURIComponent(id)}/status`);
    s.polling = false;
    if (gen !== s.gen) return;
    const d = res.data || {};
    if (!res.ok) {
      s.pollFails += 1;
      if (s.pollFails >= 2) fail(wrap, "STREAM_ERR_NETWORK");
      return;
    }
    s.pollFails = 0;
    if (d.state === "running") {
      if (d.seq !== s.camSeq) { s.camSeq = d.seq; s.camSeqAt = Date.now(); }
      else if (Date.now() - s.camSeqAt > 8000) fail(wrap, "STREAM_ERR_STALLED");
    } else {
      fail(wrap, d.error ? errorKey(d.error) : "STREAM_ERR_CAM_LOST");
    }
  }

  async function chooseSourceMenu(wrap, x, y) {
    const info = await loadCameras(false);
    const cams = info.devices.map((d) => ({ label: t("STREAM_CAM_ITEM", { name: d.name }), onClick: () => saveConfig(wrap, { source: "cam:" + d.id, camera_label: d.name, paused: false }) }));
    const rows = OCStreams.sources.map((row) => ({ label: row.name, onClick: () => saveConfig(wrap, { source: row.id, camera_label: "", paused: false }) }));
    const entries = [...cams];
    if (cams.length && rows.length) entries.push({ separator: true });
    entries.push(...rows);
    if (entries.length) entries.push({ separator: true });
    entries.push({ label: t("STREAM_NEW_SOURCE"), onClick: async () => { const created = await editSource(null); if (created) saveConfig(wrap, { source: created.id, camera_label: "", paused: false }); } });
    ContextMenu.show(x, y, entries);
  }

  function openPanelMenu(wrap, x, y) {
    const s = wrap._sp;
    const entries = [];
    entries.push({ label: t("STREAM_CHOOSE"), onClick: () => chooseSourceMenu(wrap, x, y) });
    const row = hasSource(s.mc) && !hostCam(s.mc) ? OCStreams.get(s.mc.source) : null;
    if (row) entries.push({ label: t("STREAM_CTX_EDIT_SOURCE", { name: row.name }), onClick: () => editSource(row) });
    if (hasSource(s.mc)) {
      entries.push({ label: t(wantPaused(s) ? "STREAM_RESUME" : "STREAM_PAUSE"), onClick: () => togglePause(wrap) });
      entries.push({ label: t("STREAM_RECONNECT_NOW"), onClick: () => reconnectNow(wrap) });
    }
    entries.push({ separator: true });
    if (hostCam(s.mc)) {
      QUALITIES.forEach((q) => entries.push({
        label: t("STREAM_CTX_QUALITY", { q: t("STREAM_QS_" + q.toUpperCase()) }) + (quality(s.mc) === q ? ` (${t("STREAM_CURRENT")})` : ""),
        onClick: () => saveConfig(wrap, { quality: q }),
      }));
      entries.push({ separator: true });
    }
    if (!s.mute.hidden) entries.push({ label: t(s.mc.muted ? "STREAM_UNMUTE" : "STREAM_MUTE"), onClick: () => saveConfig(wrap, { muted: !s.mc.muted }) });
    entries.push({ label: t(s.mc.fit === "cover" ? "STREAM_FIT_TO_CONTAIN" : "STREAM_FIT_TO_COVER"), onClick: () => saveConfig(wrap, { fit: s.mc.fit === "cover" ? "contain" : "cover" }) });
    entries.push({ label: t(s.mc.reconnect ? "STREAM_AUTO_OFF" : "STREAM_AUTO_ON"), onClick: () => saveConfig(wrap, { reconnect: !s.mc.reconnect }) });
    entries.push({ label: t(OCFullscreen.isFull(wrap) ? "STREAM_FULLSCREEN_EXIT" : "STREAM_FULLSCREEN"), onClick: () => toggleFullscreen(wrap) });
    ContextMenu.show(x, y, entries);
  }

  /** Einmal pro Sekunde: Panels, die aus der Seite genommen wurden, abbauen (Verbindung freigeben); Haenger erkennen; Wartezeit anzeigen;
   * alle 3 s bei Kameras am Hauptgeraet nachsehen, ob sie noch Bilder liefern. */
  let tick = 0;
  function ensureTimer() {
    if (timer) return;
    timer = setInterval(() => {
      tick += 1;
      for (const wrap of [...wraps]) {
        const s = wrap._sp;
        if (!wrap.isConnected) {
          if (!wrap._wasConnected) continue;
          s.gone = (s.gone || 0) + 1;
          if (s.gone >= 3) { clearTimeout(s.retryTimer); stop(wrap); wraps.delete(wrap); }
          continue;
        }
        wrap._wasConnected = true;
        s.gone = 0;
        if (s.state === "error" && s.retryAt) render(wrap);
        else if (s.state === "playing" && hostCam(s.mc)) { if (tick % 3 === 0) pollCamera(wrap); }
        else if (s.state === "playing" && (s.kind === "video" || s.kind === "hls" || s.kind === "webrtc") && !s.blocked
          && s.media && !s.media.paused && performance.now() - s.lastProgress > STALL_MS) fail(wrap, "STREAM_ERR_STALLED");
      }
      if (!wraps.size) { clearInterval(timer); timer = 0; }
    }, 1000);
  }

  function buildPanel(panel) {
    const wrap = el("div", "sp");
    const stage = el("div", "sp__stage");
    const empty = el("div", "sp__empty");
    empty.appendChild(Icons.svg("camera", "sp__empty-icon"));
    const emptyText = el("div", "sp__empty-text");
    const pick = el("button", "sp__pick");
    pick.type = "button";
    empty.append(emptyText, pick);
    const pausedBox = el("div", "sp__empty sp__paused");
    pausedBox.appendChild(Icons.svg("pause", "sp__empty-icon"));
    const pausedText = el("div", "sp__empty-text");
    const resume = el("button", "sp__pick");
    resume.type = "button";
    resume.append(Icons.svg("play"), el("span"));
    pausedBox.append(pausedText, resume);
    const status = el("div", "sp__status");
    const statusIcon = Icons.svg("alert", "sp__status-icon");
    const statusText = el("div", "sp__status-text");
    const statusSub = el("div", "sp__status-sub");
    const retry = el("button", "sp__pick sp__retry");
    retry.type = "button";
    retry.append(Icons.svg("refresh"), el("span"));
    status.append(statusIcon, statusText, statusSub, retry);
    const unlock = el("button", "sp__unlock");
    unlock.type = "button";
    unlock.append(Icons.svg("play"), el("span"));
    const live = el("div", "sp__live");
    live.append(el("span", "sp__live-dot"), el("span", "sp__live-text"));
    const bar = el("div", "sp__bar");
    const name = el("span", "sp__name");
    const mute = el("button", "sp__btn");
    mute.type = "button";
    const pause = el("button", "sp__btn sp__pause");
    pause.type = "button";
    const reload = el("button", "sp__btn");
    reload.type = "button";
    reload.appendChild(Icons.svg("refresh"));
    const full = el("button", "sp__btn");
    full.type = "button";
    full.appendChild(Icons.svg("expand"));
    bar.append(name, el("span", "sp__spacer"), mute, pause, reload, full);
    stage.append(empty, pausedBox, status, live, unlock, bar);
    wrap.appendChild(stage);

    wrap._sp = { mc: { source: "", camera_label: "", muted: true, fit: "contain", reconnect: true, paused: false, quality: "medium", ...(panel && panel.module_config) }, stage, empty, emptyText, pick, pausedBox, status, statusIcon, statusText, statusSub, retry, unlock, live, bar, name, mute, pause,
      media: null, pc: null, abort: null, gen: 0, state: "idle", kind: "", errorKey: "", retryAt: 0, retryTimer: 0, attempt: 0, blocked: false, lastProgress: 0, sig: "",
      camSeq: -1, camSeqAt: 0, pollFails: 0, polling: false, id: Math.random().toString(36).slice(2, 8), starts: 0, token: "" };
    const relabel = () => {
      emptyText.textContent = t("STREAM_EMPTY");
      pick.textContent = t("STREAM_CHOOSE");
      pausedText.textContent = t("STREAM_PAUSED");
      resume.querySelector("span").textContent = t("STREAM_RESUME");
      retry.querySelector("span").textContent = t("STREAM_RETRY");
      unlock.querySelector("span").textContent = t("STREAM_UNLOCK");
      live.querySelector(".sp__live-text").textContent = t("STREAM_LIVE");
      reload.title = t("STREAM_RECONNECT_NOW");
      reload.setAttribute("aria-label", reload.title);
      full.title = t(OCFullscreen.isFull(wrap) ? "STREAM_FULLSCREEN_EXIT" : "STREAM_FULLSCREEN");
      full.setAttribute("aria-label", full.title);
      render(wrap);
    };
    wrap._relabel = relabel;
    relabel();
    const onTranslated = () => {
      if (wrap.isConnected) wrap._wasConnected = true;
      if (!wrap.isConnected && wrap._wasConnected && !OCFullscreen.isFull(wrap)) { document.removeEventListener("i18n-applied", onTranslated); return; }
      relabel();
    };
    document.addEventListener("i18n-applied", onTranslated);

    pick.addEventListener("click", () => { const r = pick.getBoundingClientRect(); chooseSourceMenu(wrap, r.left, r.bottom); });
    retry.addEventListener("click", () => reconnectNow(wrap));
    reload.addEventListener("click", () => reconnectNow(wrap));
    pause.addEventListener("click", () => togglePause(wrap));
    resume.addEventListener("click", () => togglePause(wrap));
    full.addEventListener("click", () => toggleFullscreen(wrap));
    wrap.addEventListener("ocfullscreen", (event) => {                   // Symbol und Beschriftung folgen dem Zustand
      setBarButtonIcon(full, event.detail ? "collapse" : "expand");
      relabel();
    });
    mute.addEventListener("click", () => saveConfig(wrap, { muted: !wrap._sp.mc.muted }));
    unlock.addEventListener("click", () => {
      const s = wrap._sp;
      s.blocked = false;
      if (s.media && s.media.tagName === "VIDEO") s.media.play().catch(() => {});
      render(wrap);
    });
    stage.addEventListener("dblclick", (e) => {
      if (typeof isEditMode !== "undefined" && isEditMode) return;
      if (!e.target.closest("button")) toggleFullscreen(wrap);
    });
    wrap.addEventListener("contextmenu", (event) => {
      if (typeof isEditMode !== "undefined" && isEditMode) return;       // im Bearbeiten-Modus gilt das Panel-Menue
      event.preventDefault();
      openPanelMenu(wrap, event.clientX, event.clientY);
    });

    wraps.add(wrap);
    ensureTimer();
    const stopListening = OCStreams.subscribe(() => {
      if (!wrap.isConnected && wrap._wasConnected) { stopListening(); return; }
      applyConfig(wrap);
    });
    const stopCameras = OCCameras.subscribe(() => {
      if (!wrap.isConnected && wrap._wasConnected) { stopCameras(); return; }
      render(wrap);
    });
    start(wrap);
    return wrap;
  }

  // Erste Bedienung irgendwo auf der Seite: blockierte Wiedergabe (Browser-Regel gegen Autoplay mit Ton) wieder freigeben
  document.addEventListener("pointerdown", () => {
    wraps.forEach((wrap) => {
      const s = wrap._sp;
      if (s && s.blocked && s.media && s.media.tagName === "VIDEO") { s.blocked = false; s.media.play().catch(() => {}); render(wrap); }
    });
  }, { capture: true });

  // ---------------------------------------------------------------------------------------- Eigenschaften-Dialog
  function buildProps(moduleConfig, api) {
    const mc = { source: "", camera_label: "", muted: true, fit: "contain", reconnect: true, paused: false, quality: "medium", ...(moduleConfig || {}) };
    const frag = document.createDocumentFragment();
    const field = (labelKey, control, id) => {
      const row = el("div", "modal__field");
      const label = el("label");
      if (id) label.htmlFor = id;
      label.dataset.i18n = labelKey;
      label.textContent = api.i18n(labelKey);
      row.append(label, control);
      frag.appendChild(row);
      return row;
    };
    const toggle = (id, labelKey, checked) => {
      const row = el("div", "modal__field modal__field--checkbox");
      const tgl = makeToggleSwitch(id, checked);
      const label = el("label");
      label.htmlFor = id;
      label.dataset.i18n = labelKey;
      label.textContent = api.i18n(labelKey);
      row.append(tgl.label, label);
      frag.appendChild(row);
    };
    const iconButton = (id, icon, labelKey) => {
      const b = el("button", "modal__button modal__button--icon");
      b.type = "button";
      b.id = id;
      b.append(Icons.svg(icon), el("span", "", api.i18n(labelKey)));
      return b;
    };

    // Quelle: Kameras am Hauptgeraet (Liste vom Server, auf jedem Geraet gleich) und Stream-Quellen
    const source = el("select", "modal__input");
    source.id = "sp-prop-source";
    const fillSource = (keep) => {
      const wanted = keep !== undefined ? keep : mc.source;
      source.textContent = "";
      const none = el("option", "", api.i18n("STREAM_PROP_NONE"));
      none.value = "";
      source.appendChild(none);
      const devices = OCCameras.state.devices;
      const savedCam = wanted.startsWith("cam:") && !devices.some((d) => "cam:" + d.id === wanted);
      if (devices.length || savedCam) {
        const group = document.createElement("optgroup");
        group.label = api.i18n("STREAM_CAM_GROUP");
        devices.forEach((d) => {
          const o = el("option", "", d.name);
          o.value = "cam:" + d.id;
          o.dataset.label = d.name;
          group.appendChild(o);
        });
        if (savedCam) {
          const o = el("option", "", `${mc.camera_label || api.i18n("STREAM_CAM_HOST")} (${api.i18n("STREAM_CAM_MISSING")})`);
          o.value = wanted;
          o.dataset.label = mc.camera_label || "";
          group.appendChild(o);
        }
        source.appendChild(group);
      }
      if (OCStreams.sources.length) {
        const group = document.createElement("optgroup");
        group.label = api.i18n("STREAM_SRC_GROUP");
        OCStreams.sources.forEach((row) => {
          const o = el("option", "", row.name);
          o.value = row.id;
          group.appendChild(o);
        });
        source.appendChild(group);
      }
      source.value = wanted;
      if (source.value !== wanted) source.value = "";
    };
    fillSource();
    field("STREAM_PROP_SOURCE", source, "sp-prop-source");

    const buttons = el("div", "mp-prop__upload");
    const addBtn = iconButton("sp-prop-new", "plus", "STREAM_PROP_NEW");
    const editBtn = iconButton("sp-prop-edit", "edit", "STREAM_PROP_EDIT");
    const delBtn = iconButton("sp-prop-remove", "trash", "STREAM_PROP_REMOVE");
    const scanBtn = iconButton("sp-prop-scan", "refresh", "STREAM_PROP_SCAN");
    buttons.append(addBtn, editBtn, delBtn, scanBtn);
    frag.appendChild(buttons);
    const kindHint = el("div", "mp-prop__hint");
    kindHint.id = "sp-prop-kind";
    const camHint = el("div", "mp-prop__hint");
    camHint.id = "sp-prop-cam-hint";
    frag.append(kindHint, camHint);

    // Pausen-Zustand bleibt erhalten; eine andere Quelle hebt die Pause auf
    const pausedKeep = el("input");
    pausedKeep.type = "hidden";
    pausedKeep.id = "sp-prop-paused";
    pausedKeep.value = mc.paused ? "1" : "0";
    frag.appendChild(pausedKeep);

    // Qualitaet der Kamera am Hauptgeraet (gilt nur dafuer)
    const qualitySelect = el("select", "modal__input");
    qualitySelect.id = "sp-prop-quality";
    [["low", "STREAM_Q_LOW"], ["medium", "STREAM_Q_MEDIUM"], ["high", "STREAM_Q_HIGH"], ["max", "STREAM_Q_MAX"]].forEach(([v, k]) => { const o = el("option", "", api.i18n(k)); o.value = v; qualitySelect.appendChild(o); });
    qualitySelect.value = QUALITIES.includes(mc.quality) ? mc.quality : "medium";
    const qualityRow = field("STREAM_PROP_QUALITY", qualitySelect, "sp-prop-quality");
    const qualityHint = el("div", "mp-prop__hint", api.i18n("STREAM_Q_HINT"));
    qualityHint.id = "sp-prop-quality-hint";
    frag.appendChild(qualityHint);

    const camState = () => {
      const c = OCCameras.state;
      camHint.textContent = !c.loaded ? "" : !c.supported ? api.i18n("STREAM_CAM_UNSUPPORTED") : !c.ffmpeg ? api.i18n("STREAM_CAM_NO_FFMPEG") : !c.devices.length ? api.i18n("STREAM_CAM_NONE_FOUND") : "";
      camHint.hidden = !camHint.textContent;
    };
    const refreshButtons = () => {
      const id = source.value;
      const cam = id.startsWith("cam:");
      const row = id && !cam ? OCStreams.get(id) : null;
      editBtn.disabled = delBtn.disabled = !row;
      kindHint.textContent = cam ? `${api.i18n("STREAM_VIA_HOST")} \u00B7 ${api.i18n("STREAM_TYPE_MJPEG")}`
        : row ? `${api.i18n("STREAM_TYPE_" + String(row.resolved_type).toUpperCase())}${proxied(row) ? " \u00B7 " + api.i18n("STREAM_VIA_SERVER") : ""}` : "";
      kindHint.hidden = !kindHint.textContent;
      qualityRow.hidden = qualityHint.hidden = !cam;
      pausedKeep.value = id === mc.source && mc.paused ? "1" : "0";
      camState();
    };
    source.addEventListener("change", refreshButtons);
    refreshButtons();

    scanBtn.addEventListener("click", async () => {
      scanBtn.disabled = true;
      await loadCameras(true);
      scanBtn.disabled = false;
    });
    const stopCams = OCCameras.subscribe(() => {
      if (!document.body.contains(source)) { stopCams(); return; }
      fillSource(source.value);
      refreshButtons();
    });
    loadCameras(false);

    addBtn.addEventListener("click", async () => {
      const created = await OCStreams.editSource(null);
      if (created) { fillSource(created.id); refreshButtons(); }
    });
    editBtn.addEventListener("click", async () => {
      const row = OCStreams.get(source.value);
      if (!row) return;
      await OCStreams.editSource(row);
      fillSource(row.id);
      refreshButtons();
    });
    delBtn.addEventListener("click", async () => {
      const row = OCStreams.get(source.value);
      if (row && (await OCStreams.confirmRemove(row.id))) { fillSource(""); refreshButtons(); }
    });
    const stop = OCStreams.subscribe(() => {
      if (!document.body.contains(source)) { stop(); return; }
      fillSource(source.value);
      refreshButtons();
    });

    toggle("sp-prop-muted", "STREAM_PROP_MUTED", !!mc.muted);
    toggle("sp-prop-reconnect", "STREAM_PROP_RECONNECT", !!mc.reconnect);
    const fit = el("select", "modal__input");
    fit.id = "sp-prop-fit";
    [["contain", "STREAM_FIT_CONTAIN"], ["cover", "STREAM_FIT_COVER"]].forEach(([v, k]) => { const o = el("option", "", api.i18n(k)); o.value = v; fit.appendChild(o); });
    fit.value = mc.fit === "cover" ? "cover" : "contain";
    field("STREAM_PROP_FIT", fit, "sp-prop-fit");
    return frag;
  }

  function readProps() {
    const val = (id) => { const node = document.getElementById(id); return node ? node.value : ""; };
    const chk = (id) => { const node = document.getElementById(id); return node ? node.checked : false; };
    const select = document.getElementById("sp-prop-source");
    const picked = select && select.selectedOptions[0];
    const camera = val("sp-prop-source").startsWith("cam:");
    return {
      source: val("sp-prop-source"), camera_label: camera && picked ? picked.dataset.label || "" : "",
      paused: val("sp-prop-paused") === "1", quality: QUALITIES.includes(val("sp-prop-quality")) ? val("sp-prop-quality") : "medium",
      muted: chk("sp-prop-muted"), reconnect: chk("sp-prop-reconnect"), fit: val("sp-prop-fit") === "cover" ? "cover" : "contain",
    };
  }

  window.__panelPlugins.register({
    type: "stream",
    buildContent: buildPanel,
    onModuleConfigChanged(panelEl, mc) {
      const wrap = OCFullscreen.query(panelEl, ".sp");
      if (!wrap) return;
      wrap._sp.mc = { ...wrap._sp.mc, ...mc };
      applyConfig(wrap);
    },
    onMessage(panelEl, messageType) {
      if (messageType === "language_changed") {
        const wrap = OCFullscreen.query(panelEl, ".sp");
        if (wrap && wrap._relabel) wrap._relabel();
      }
    },
    buildPropertiesPane: buildProps,
    readPropertiesPane: readProps,
  });

  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.stream = "PANEL_STREAM";
})();

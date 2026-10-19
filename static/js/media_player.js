/* Video-/Audio-Player-Panel + Medien der Show - Client-Seite.
 *  - OCMedia: die Medien der Show (nur Metadaten; die Datei kommt von GET /api/media/<id>), Importieren (hochladen = Kopie in den lokalen Medien-Ordner), Entfernen.
 *  - Panel "media_player": spielt ein Medium der Show. Modus "timecode": laeuft synchron zum globalen Timecode (OCTimecode),
 *    beginnt bei Timecode tc_start_ms; Modus "free": ganz normaler Player mit eigenen Bedienelementen (Vollbild, Spulen).
 *    Der Player fuellt das Panel bis zum Rand (kein Innenabstand); den Titel blendet man in den Panel-Eigenschaften aus.
 * Laeuft nach app.js, icons.js und timecode.js. */
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
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const OC = () => window.OCTimecode;
  const ACCEPT = "video/*,audio/*,.mp4,.m4v,.webm,.ogg,.ogv,.wav,.mp3,.flac,.aac,.m4a,.mov";

  // ------------------------------------------------------------------------------------------------------ Medien
  let items = {};
  let mediaDir = "";
  let maxBytes = 1024 * 1024 * 1024;
  const listeners = new Set();

  function ingest(media) {
    items = media && typeof media === "object" ? media : {};
    listeners.forEach((fn) => { try { fn(items); } catch (e) { console.error(e); } });
  }

  function errorKey(code) {
    return {
      too_large: "MEDIA_ERR_TOO_LARGE", invalid_type: "MEDIA_ERR_TYPE", invalid_file: "MEDIA_ERR_EMPTY", not_found: "MEDIA_ERR_NOT_FOUND",
    }[code] || "MEDIA_ERR_GENERIC";
  }

  /** Dauer einer Datei in ms (aus den Metadaten; null wenn der Browser sie nicht lesen kann). */
  function probeDuration(file) {
    return new Promise((resolve) => {
      const probe = document.createElement("video");
      const url = URL.createObjectURL(file);
      const done = (value) => { URL.revokeObjectURL(url); probe.removeAttribute("src"); resolve(value); };
      probe.preload = "metadata";
      probe.onloadedmetadata = () => done(Number.isFinite(probe.duration) ? Math.round(probe.duration * 1000) : null);
      probe.onerror = () => done(null);
      setTimeout(() => done(null), 4000);
      probe.src = url;
    });
  }

  /** Datei hochladen (mit Fortschritt; der Server kopiert sie in den lokalen Medien-Ordner). Loest mit den Metadaten auf. */
  async function upload(file, onProgress) {
    if (file.size > maxBytes) throw { code: "too_large" };
    const duration = await probeDuration(file);
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/media/upload");
      xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name));
      if (duration !== null) xhr.setRequestHeader("X-Duration-Ms", String(duration));
      xhr.setRequestHeader("Content-Type", "application/octet-stream");
      if (xhr.upload && onProgress) xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
      xhr.onload = () => {
        let data = {};
        try { data = JSON.parse(xhr.responseText); } catch (e) { /* leere Antwort */ }
        if (xhr.status >= 200 && xhr.status < 300 && data.media) resolve(data.media);
        else reject({ code: data.error || "generic", message: data.message || "" });
      };
      xhr.onerror = () => reject({ code: "network" });
      xhr.send(file);
    });
  }

  async function call(method, url, body) {
    try {
      const res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
      return { ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) };
    } catch (e) {
      return { ok: false, status: 0, data: { error: "network" } };
    }
  }

  // ---- Kleine Dialoge (feste Dialoge in index.html)
  let startResolver = null;

  /** Fragt eine Startzeit ab (Dialog 'media-start'); loest mit ms oder null (abgebrochen). kind: 'video' | 'audio'. */
  function askStart(currentMs, kind) {
    return new Promise((resolve) => {
      const input = document.getElementById("media-start-input");
      if (!input) { resolve(null); return; }
      const audio = kind === "audio";
      document.getElementById("media-start-title").textContent = t(audio ? "MEDIA_START_TITLE_AUDIO" : "MEDIA_START_TITLE_VIDEO");
      document.getElementById("media-start-question").textContent = t("MEDIA_START_QUESTION", { kind: t(audio ? "MEDIA_KIND_AUDIO" : "MEDIA_KIND_VIDEO") });
      document.getElementById("media-start-now").textContent = t("MEDIA_START_NOW", { tc: OC().fmt(Math.floor(OC().position())) });
      input.value = OC().fmt(currentMs || 0);
      input.classList.remove("tcp__input--bad");
      startResolver = resolve;
      Modal._hooks["media-start"] = () => { if (startResolver) { const r = startResolver; startResolver = null; r(null); } };
      Modal.open("media-start");
      setTimeout(() => { input.focus(); input.select(); }, 50);
    });
  }

  function finishStart() {
    const input = document.getElementById("media-start-input");
    const ms = OC().parse(input.value);
    if (ms === null) { input.classList.add("tcp__input--bad"); _showToast("TC_ERR_PARSE", "warn", 3000); return; }
    const resolve = startResolver;
    startResolver = null;
    delete Modal._hooks["media-start"];
    Modal.close("media-start");
    if (resolve) resolve(ms);
  }

  // ---- Medium hinzufuegen: Datei waehlen -> in den lokalen Medien-Ordner hochladen
  /** Oeffnet die Dateiauswahl und laedt die gewaehlte Datei hoch. Loest mit den Metadaten oder null (abgebrochen/Fehler). */
  function importFlow(onProgress) {
    return new Promise((resolve) => {
      const input = document.getElementById("media-import-file");
      if (!input) { resolve(null); return; }
      input.value = "";
      let settled = false;
      const done = (value) => { if (!settled) { settled = true; resolve(value); } };
      input.onchange = async () => {
        const chosen = input.files && input.files[0] ? input.files[0] : null;
        if (!chosen) { done(null); return; }
        try {
          done(await upload(chosen, onProgress));
        } catch (err) {
          _showToast(errorKey(err.code), "warn", 5000);
          done(null);
        }
      };
      input.oncancel = () => done(null);
      input.click();
    });
  }

  /** Bestaetigungsdialog 'Medium entfernen' mit den Folgen je nach Speicherart; loest mit true/false. */
  function askRemove(meta) {
    return new Promise((resolve) => {
      const ok = document.getElementById("media-remove-ok");
      if (!ok) { resolve(false); return; }
      document.getElementById("media-remove-name").textContent = meta.name;
      document.getElementById("media-remove-body").textContent = t("MEDIA_REMOVE_BODY_COPY");
      document.getElementById("media-remove-note").textContent = "";
      removeResolver = resolve;
      Modal._hooks["media-remove"] = () => { if (removeResolver) { const r = removeResolver; removeResolver = null; r(false); } };
      Modal.open("media-remove");
      setTimeout(() => ok.focus(), 50);
    });
  }
  let removeResolver = null;

  const OCMedia = {
    get items() { return items; },
    get dir() { return mediaDir; },
    get maxBytes() { return maxBytes; },
    get: (id) => items[id] || null,
    url: (id) => `/api/media/${encodeURIComponent(id)}`,
    upload,
    update: (id, fields) => call("PATCH", `/api/media/${encodeURIComponent(id)}`, fields),
    importFlow,
    /** Fragt mit dem Dialog nach und entfernt dann; false = abgebrochen. */
    async confirmRemove(id) {
      const meta = items[id];
      if (!meta || !(await askRemove(meta))) return false;
      await OCMedia.remove(id);
      return true;
    },
    async remove(id) {
      const res = await call("DELETE", `/api/media/${encodeURIComponent(id)}`);
      if (res.ok) {
        const d = res.data;
        _showToast(d.file_deleted ? t("MEDIA_REMOVED_DELETED") : d.kept === "other_show" ? t("MEDIA_REMOVED_OTHER", { show: d.show || "" }) : t("MEDIA_REMOVED"), "ok", 4500, true);
      }
      return res;
    },
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    errorKey,
  };
  window.OCMedia = OCMedia;

  client.registerModule("media", {
    onMessage(message) {
      if (message.type === "state_snapshot" && message.payload) {
        mediaDir = message.payload.media_dir || mediaDir;
        if (message.payload.media_max_bytes) maxBytes = message.payload.media_max_bytes;
        ingest(message.payload.media);
      } else if (message.type === "media_changed") {
        ingest(message.payload.media);
        if (typeof _setDirty === "function" && message.payload.is_dirty !== undefined) _setDirty(message.payload.is_dirty !== false);
      }
    },
  });

  const size = (bytes) => (bytes >= 1073741824 ? `${(bytes / 1073741824).toFixed(2)} GB` : bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);
  const clock = (sec) => { const s = Math.max(0, Math.floor(sec)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

  // ------------------------------------------------------------------------------------------------------ Panel
  const wraps = new Set();
  let timer = 0;

  function ensureTimer() {
    if (timer) return;
    timer = setInterval(() => {
      for (const w of [...wraps]) { if (!w.isConnected) { wraps.delete(w); continue; } syncOne(w); }
      if (!wraps.size) { clearInterval(timer); timer = 0; }
    }, 100);
  }

  function saveConfig(wrap, patch) {
    const panelEl = OCFullscreen.panelOf(wrap);
    if (!panelEl) return;
    const next = { ...wrap._mp.mc, ...patch };
    wrap._mp.mc = next;
    window.__panelAPI.sendToServer("update_panel", { id: panelEl.dataset.panelId, module_config: next });
    renderState(wrap);
  }

  function requestPlay(wrap) {
    const s = wrap._mp;
    const promise = s.video.play();
    if (promise && promise.catch) {
      promise.then(() => { if (s.blocked) { s.blocked = false; renderState(wrap); } })
        .catch((err) => { if (err && err.name === "NotAllowedError") { s.blocked = true; renderState(wrap); } });
    }
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

  /** Zeigt je nach Medium/Zustand: Platzhalter, Fehler, Hinweis 'Tippen zum Aktivieren', Statuszeile. */
  function renderState(wrap) {
    const s = wrap._mp;
    const media = s.media;
    const hasVideo = !!media && !media.missing && !s.failed;
    s.video.hidden = !hasVideo || media.kind === "audio";
    s.audio.hidden = !(hasVideo && media.kind === "audio");
    s.empty.hidden = hasVideo;
    s.unlock.hidden = !(hasVideo && s.blocked);
    s.bar.hidden = !hasVideo;
    s.tcOverlay.hidden = !(hasVideo && s.mc.show_tc && s.mc.sync !== "free");
    if (!hasVideo) {
      s.emptyText.textContent = !s.mc.media_id ? t("MEDIA_EMPTY") : (s.failed ? t("MEDIA_PLAY_ERR") : (media && media.missing ? t("MEDIA_MISSING") : t("MEDIA_NOT_IN_SHOW")));
      s.pick.textContent = t("MEDIA_ADD");
    } else {
      s.audioName.textContent = media.name;
    }
    wrap.classList.toggle("mp--free", s.mc.sync === "free");
    wrap.style.setProperty("--mp-fit", s.mc.fit === "cover" ? "cover" : "contain");
    s.video.controls = s.mc.sync === "free";
    s.video.loop = s.mc.sync === "free" && !!s.mc.loop;
    s.video.muted = !!s.mc.muted;
    s.video.volume = clamp((Number(s.mc.volume) || 0) / 100, 0, 1);
    setBarButtonIcon(s.mute, s.mc.muted ? "volume-off" : "volume");
    s.mute.classList.toggle("mp__btn--on", !!s.mc.muted);
    s.mute.title = t(s.mc.muted ? "MEDIA_UNMUTE" : "MEDIA_MUTE");
    s.mute.setAttribute("aria-label", s.mute.title);
    s.mute.setAttribute("aria-pressed", s.mc.muted ? "true" : "false");
  }

  function applyMedia(wrap) {
    const s = wrap._mp;
    s.media = OCMedia.get(s.mc.media_id);
    const url = s.media && !s.media.missing ? OCMedia.url(s.media.id) : "";
    if (s.src !== url) {
      s.src = url;
      s.failed = false;
      s.blocked = false;
      if (url) { s.video.src = url; s.video.load(); } else { s.video.removeAttribute("src"); s.video.load(); }
    }
    renderState(wrap);
  }

  function syncOne(wrap) {
    const s = wrap._mp;
    const v = s.video;
    const pos = OC().position();
    s.tcLabel.textContent = "TC " + OC().fmt(pos);
    if (!s.tcOverlay.hidden) s.tcOverlay.textContent = "TC " + OC().fmt(pos);
    if (!s.media || s.media.missing || s.failed || !s.src) return;
    if (s.mc.sync === "free") { s.status.textContent = ""; return; }
    if (v.readyState < 1) { s.status.textContent = t("MEDIA_LOADING"); return; }
    const tc = OC().state;
    const start = Number(s.mc.tc_start_ms) || 0;
    let target = (pos - start) / 1000;
    const dur = Number.isFinite(v.duration) ? v.duration : 0;
    const now = performance.now();
    const seekTo = (value) => {
      if (v.seeking || now - (s.lastSeek || 0) < 250) return;     // nicht im Dauerfeuer springen
      s.lastSeek = now;
      v.currentTime = value;
    };
    if (target < 0) {
      s.status.textContent = t("MEDIA_STARTS_AT", { tc: OC().fmt(start) });
      if (!v.paused) v.pause();
      if (Math.abs(v.currentTime) > 0.05) seekTo(0);
      s.bar.style.setProperty("--mp-progress", "0");
      return;
    }
    if (dur && target >= dur) {
      if (s.mc.loop && tc.running && tc.direction > 0) target = target % dur;
      else {
        s.status.textContent = t("MEDIA_ENDED");
        if (!v.paused) v.pause();
        if (Math.abs(v.currentTime - dur) > 0.1) seekTo(dur);
        s.bar.style.setProperty("--mp-progress", "1");
        return;
      }
    }
    if (tc.running && tc.direction > 0) {
      const rate = clamp(tc.rate, 0.0625, 16);
      if (v.playbackRate !== rate) v.playbackRate = rate;
      if (Math.abs(v.currentTime - target) > 0.15) seekTo(target);
      if (v.paused && !v.seeking) requestPlay(wrap);
    } else {
      if (!v.paused) v.pause();
      if (Math.abs(v.currentTime - target) > 0.03) seekTo(target);
    }
    s.status.textContent = dur ? `${clock(target)} / ${clock(dur)}` : clock(target);
    s.bar.style.setProperty("--mp-progress", dur ? String(clamp(target / dur, 0, 1)) : "0");
  }

  /** Medium hinzufuegen und dem Panel zuweisen (fragt zuerst, wo es gespeichert wird). */
  async function importInto(wrap) {
    const s = wrap._mp;
    const meta = await importFlow((p) => { s.emptyText.textContent = t("MEDIA_UPLOADING", { p: Math.round(p * 100) }); });
    renderState(wrap);
    if (!meta) return;
    saveConfig(wrap, { media_id: meta.id });
    applyMedia(wrap);
  }

  function openPanelMenu(wrap, x, y) {
    const s = wrap._mp;
    const free = s.mc.sync === "free";
    const entries = [];
    if (!free) {
      entries.push({ label: t("MEDIA_CTX_START", { tc: OC().fmt(Number(s.mc.tc_start_ms) || 0) }), onClick: async () => {
        const ms = await askStart(Number(s.mc.tc_start_ms) || 0, s.media && s.media.kind);
        if (ms !== null) { saveConfig(wrap, { tc_start_ms: ms }); syncOne(wrap); }
      } });
      entries.push({ separator: true });
    }
    entries.push({ label: t(s.mc.muted ? "MEDIA_UNMUTE" : "MEDIA_MUTE"), onClick: () => saveConfig(wrap, { muted: !s.mc.muted }) });
    entries.push({ label: t(s.mc.loop ? "MEDIA_LOOP_OFF" : "MEDIA_LOOP_ON"), onClick: () => saveConfig(wrap, { loop: !s.mc.loop }) });
    entries.push({ label: t(s.mc.fit === "cover" ? "MEDIA_FIT_TO_CONTAIN" : "MEDIA_FIT_TO_COVER"), onClick: () => saveConfig(wrap, { fit: s.mc.fit === "cover" ? "contain" : "cover" }) });
    if (!free) entries.push({ label: t(s.mc.show_tc ? "MEDIA_TC_HIDE" : "MEDIA_TC_SHOW"), onClick: () => saveConfig(wrap, { show_tc: !s.mc.show_tc }) });
    entries.push({ separator: true });
    entries.push({ label: t(free ? "MEDIA_CTX_SYNC" : "MEDIA_CTX_FREE"), onClick: () => saveConfig(wrap, { sync: free ? "timecode" : "free" }) });
    entries.push({ label: t(OCFullscreen.isFull(wrap) ? "MEDIA_FULLSCREEN_EXIT" : "MEDIA_FULLSCREEN"), onClick: () => toggleFullscreen(wrap) });
    ContextMenu.show(x, y, entries);
  }

  function buildPanel(panel) {
    const wrap = el("div", "mp");
    const stage = el("div", "mp__stage");
    const video = document.createElement("video");
    video.className = "mp__video";
    video.playsInline = true;
    video.preload = "auto";
    video.disablePictureInPicture = true;
    const audio = el("div", "mp__audio");
    audio.appendChild(Icons.svg("music", "mp__audio-icon"));
    const audioName = el("div", "mp__audio-name");
    audio.appendChild(audioName);
    const empty = el("div", "mp__empty");
    empty.appendChild(Icons.svg("film", "mp__empty-icon"));
    const emptyText = el("div", "mp__empty-text");
    const pick = el("button", "mp__pick");
    pick.type = "button";
    empty.append(emptyText, pick);
    const unlock = el("button", "mp__unlock");
    unlock.type = "button";
    unlock.appendChild(Icons.svg("play"));
    unlock.appendChild(el("span", "", t("MEDIA_UNLOCK")));
    const tcOverlay = el("div", "mp__tc");
    tcOverlay.hidden = true;
    const bar = el("div", "mp__bar");
    const tcLabel = el("span", "mp__tc-label");
    const status = el("span", "mp__status");
    const mute = el("button", "mp__btn");
    mute.type = "button";
    const full = el("button", "mp__btn");
    full.type = "button";
    full.appendChild(Icons.svg("expand"));
    full.title = t("MEDIA_FULLSCREEN");
    full.setAttribute("aria-label", t("MEDIA_FULLSCREEN"));
    const spacer = el("span", "mp__spacer");
    bar.append(tcLabel, status, spacer, mute, full);
    stage.append(video, audio, empty, tcOverlay, unlock, bar);
    wrap.appendChild(stage);

    wrap._mp = { mc: { ...(panel && panel.module_config) }, video, audio, audioName, empty, emptyText, pick, unlock, bar, status, tcLabel, tcOverlay, mute, media: null, src: "", failed: false, blocked: false, lastSeek: 0 };
    wrap._relabel = () => { unlock.querySelector("span").textContent = t("MEDIA_UNLOCK"); full.title = t(OCFullscreen.isFull(wrap) ? "MEDIA_FULLSCREEN_EXIT" : "MEDIA_FULLSCREEN"); renderState(wrap); };
    const onTranslated = () => {
      if (wrap.isConnected) wrap._wasConnected = true;
      if (!wrap.isConnected && wrap._wasConnected && !OCFullscreen.isFull(wrap)) { document.removeEventListener("i18n-applied", onTranslated); return; }
      wrap._relabel();
    };
    document.addEventListener("i18n-applied", onTranslated);

    pick.addEventListener("click", () => importInto(wrap));
    full.addEventListener("click", () => toggleFullscreen(wrap));
    wrap.addEventListener("ocfullscreen", (event) => {                   // Symbol und Beschriftung folgen dem Zustand
      setBarButtonIcon(full, event.detail ? "collapse" : "expand");
      wrap._relabel();
    });
    mute.addEventListener("click", () => saveConfig(wrap, { muted: !wrap._mp.mc.muted }));
    stage.addEventListener("dblclick", (e) => {
      if (typeof isEditMode !== "undefined" && isEditMode) return;
      if (!e.target.closest("button, video[controls]")) toggleFullscreen(wrap);
    });
    unlock.addEventListener("click", () => { wrap._mp.blocked = false; renderState(wrap); requestPlay(wrap); syncOne(wrap); });
    video.addEventListener("error", () => { wrap._mp.failed = !!wrap._mp.src; renderState(wrap); });
    video.addEventListener("loadedmetadata", () => syncOne(wrap));
    wrap.addEventListener("contextmenu", (event) => {
      if (typeof isEditMode !== "undefined" && isEditMode) return;       // im Bearbeiten-Modus gilt das Panel-Menue
      event.preventDefault();
      openPanelMenu(wrap, event.clientX, event.clientY);
    });

    wraps.add(wrap);
    ensureTimer();
    const stopListening = OCMedia.subscribe(() => { if (!wrap.isConnected && wrap._wasConnected) { stopListening(); return; } wrap._wasConnected = wrap.isConnected || wrap._wasConnected; applyMedia(wrap); });
    const stopTc = OC().subscribe(() => { if (!wrap.isConnected && wrap._wasConnected) { stopTc(); return; } syncOne(wrap); });
    requestAnimationFrame(() => { wrap._wasConnected = true; applyMedia(wrap); });
    applyMedia(wrap);
    return wrap;
  }

  // Erste Bedienung irgendwo auf der Seite: blockierte Wiedergabe (Browser-Regel gegen Autoplay mit Ton) wieder freigeben
  document.addEventListener("pointerdown", () => {
    wraps.forEach((wrap) => { const s = wrap._mp; if (s && s.blocked) { s.blocked = false; renderState(wrap); syncOne(wrap); } });
  }, { capture: true });

  // ---- Feste Dialoge verdrahten (Startzeit, Pfad eingeben)
  function wireDialogs() {
    const startOk = document.getElementById("media-start-ok");
    if (startOk) {
      startOk.addEventListener("click", finishStart);
      document.getElementById("media-start-input").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); finishStart(); } });
      document.getElementById("media-start-now").addEventListener("click", () => {
        document.getElementById("media-start-input").value = OC().fmt(Math.floor(OC().position()));
      });
    }
    const removeOk = document.getElementById("media-remove-ok");
    if (removeOk) {
      removeOk.addEventListener("click", () => {
        const resolve = removeResolver;
        removeResolver = null;
        delete Modal._hooks["media-remove"];
        Modal.close("media-remove");
        if (resolve) resolve(true);
      });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wireDialogs);
  else wireDialogs();

  // ---------------------------------------------------------------------------------------- Eigenschaften-Dialog
  function buildProps(moduleConfig, api) {
    const mc = { media_id: "", sync: "timecode", tc_start_ms: 0, muted: false, volume: 100, loop: false, fit: "contain", show_tc: false, ...(moduleConfig || {}) };
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

    // Medium
    const select = el("select", "modal__input");
    select.id = "mp-prop-media";
    const fillSelect = (keep) => {
      select.textContent = "";
      const none = el("option", "", api.i18n("MEDIA_NONE"));
      none.value = "";
      select.appendChild(none);
      Object.values(OCMedia.items).forEach((m) => {
        const o = el("option", "", `${m.name} (${size(m.size)})${m.missing ? " - " + api.i18n("MEDIA_MISSING_SHORT") : ""}`);
        o.value = m.id;
        select.appendChild(o);
      });
      select.value = keep !== undefined ? keep : mc.media_id;
      if (select.value !== (keep !== undefined ? keep : mc.media_id)) select.value = "";
    };
    fillSelect();
    field("MEDIA_PROP_MEDIA", select, "mp-prop-media");

    // Medium hinzufuegen (fragt zuerst, wo es gespeichert wird)
    const importRow = el("div", "mp-prop__upload");
    const addBtn = el("button", "modal__button modal__button--icon");
    addBtn.type = "button";
    addBtn.id = "mp-prop-add";
    addBtn.append(Icons.svg("upload"), el("span", "", api.i18n("MEDIA_ADD")));
    const progress = el("span", "mp-prop__progress");
    importRow.append(addBtn, progress);
    frag.appendChild(importRow);
    const adopt = (meta) => { fillSelect(meta.id); mc.media_id = meta.id; };
    addBtn.addEventListener("click", async () => {
      addBtn.disabled = true;
      const meta = await importFlow((p) => { progress.textContent = api.i18n("MEDIA_UPLOADING").replace("{p}", String(Math.round(p * 100))); });
      progress.textContent = "";
      addBtn.disabled = false;
      if (meta) adopt(meta);
    });

    // Medien der Show (verwalten: entfernen)
    const manager = el("div", "mp-prop__list");
    manager.id = "mp-prop-list";
    const heading = el("div", "mp-prop__heading", api.i18n("MEDIA_LIST_TITLE"));
    const where = el("div", "mp-prop__where");
    where.id = "mp-prop-where";
    const list = el("div", "mp-prop__items");
    manager.append(heading, list, where);
    frag.appendChild(manager);
    const renderList = () => {
      list.textContent = "";
      where.textContent = OCMedia.dir ? api.i18n("MEDIA_STORE_AT").replace("{path}", OCMedia.dir) : "";
      const all = Object.values(OCMedia.items);
      if (!all.length) { list.appendChild(el("div", "mp-prop__none", api.i18n("MEDIA_LIST_EMPTY"))); return; }
      all.forEach((m) => {
        const row = el("div", "mp-prop__item");
        row.dataset.id = m.id;
        row.appendChild(Icons.svg(m.kind === "audio" ? "music" : "film"));
        const info = el("div", "mp-prop__info");
        info.appendChild(el("div", "mp-prop__name", m.name));
        const meta = el("div", "mp-prop__meta", [size(m.size), m.duration_ms ? OC().fmt(m.duration_ms, false) : "", m.missing ? api.i18n("MEDIA_MISSING_SHORT") : ""].filter(Boolean).join(" \u00B7 "));
        info.appendChild(meta);
        row.appendChild(info);
        const del = el("button", "mp-prop__del");
        del.type = "button";
        del.title = api.i18n("MEDIA_REMOVE_TITLE");
        del.setAttribute("aria-label", api.i18n("MEDIA_REMOVE_TITLE"));
        del.appendChild(Icons.svg("trash"));
        del.addEventListener("click", async () => {
          const removed = await OCMedia.confirmRemove(m.id);
          if (removed && select.value === m.id) { select.value = ""; mc.media_id = ""; }
        });
        row.appendChild(del);
        list.appendChild(row);
      });
    };
    renderList();
    const stop = OCMedia.subscribe(() => { if (!document.body.contains(manager)) { stop(); return; } const keep = select.value; fillSelect(keep); renderList(); });

    // Wiedergabe
    const sync = el("select", "modal__input");
    sync.id = "mp-prop-sync";
    [["timecode", "MEDIA_SYNC_TC"], ["free", "MEDIA_SYNC_FREE"]].forEach(([v, k]) => { const o = el("option", "", api.i18n(k)); o.value = v; sync.appendChild(o); });
    sync.value = mc.sync === "free" ? "free" : "timecode";
    field("MEDIA_PROP_SYNC", sync, "mp-prop-sync");

    const start = el("input", "modal__input");
    start.type = "text";
    start.id = "mp-prop-start";
    start.value = OC().fmt(mc.tc_start_ms || 0);
    start.placeholder = "00:00:00.000";
    start.maxLength = 14;
    const startField = field("MEDIA_PROP_START", start, "mp-prop-start");
    const startRow = el("div", "mp-prop__upload");
    const now = el("button", "modal__button");
    now.type = "button";
    now.id = "mp-prop-start-now";
    now.textContent = api.i18n("MEDIA_START_NOW_SHORT");
    now.addEventListener("click", () => { start.value = OC().fmt(Math.floor(OC().position())); });
    const startHint = el("div", "mp-prop__hint", api.i18n("MEDIA_START_HINT"));
    startRow.append(now);
    frag.append(startRow, startHint);

    toggle("mp-prop-muted", "MEDIA_PROP_MUTED", !!mc.muted);
    const volume = el("input", "mp-prop__range");
    volume.type = "range";
    volume.id = "mp-prop-volume";
    volume.min = "0"; volume.max = "100"; volume.step = "1";
    volume.value = String(Number.isFinite(Number(mc.volume)) ? mc.volume : 100);
    field("MEDIA_PROP_VOLUME", volume, "mp-prop-volume");
    toggle("mp-prop-loop", "MEDIA_PROP_LOOP", !!mc.loop);
    toggle("mp-prop-showtc", "MEDIA_PROP_SHOWTC", !!mc.show_tc);
    const fit = el("select", "modal__input");
    fit.id = "mp-prop-fit";
    [["contain", "MEDIA_FIT_CONTAIN"], ["cover", "MEDIA_FIT_COVER"]].forEach(([v, k]) => { const o = el("option", "", api.i18n(k)); o.value = v; fit.appendChild(o); });
    fit.value = mc.fit === "cover" ? "cover" : "contain";
    field("MEDIA_PROP_FIT", fit, "mp-prop-fit");
    const syncState = () => { startField.hidden = startRow.hidden = startHint.hidden = sync.value === "free"; };
    sync.addEventListener("change", syncState);
    syncState();
    return frag;
  }

  function readProps() {
    const val = (id) => { const node = document.getElementById(id); return node ? node.value : ""; };
    const chk = (id) => { const node = document.getElementById(id); return node ? node.checked : false; };
    let start = OC().parse(val("mp-prop-start"));
    if (start === null) { _showToast("TC_ERR_PARSE", "warn", 3500); start = 0; }
    return {
      media_id: val("mp-prop-media"), sync: val("mp-prop-sync") === "free" ? "free" : "timecode", tc_start_ms: start,
      muted: chk("mp-prop-muted"), volume: clamp(parseInt(val("mp-prop-volume"), 10) || 0, 0, 100), loop: chk("mp-prop-loop"),
      show_tc: chk("mp-prop-showtc"), fit: val("mp-prop-fit") === "cover" ? "cover" : "contain",
    };
  }

  window.__panelPlugins.register({
    type: "media_player",
    buildContent: buildPanel,
    onModuleConfigChanged(panelEl, mc) {
      const wrap = OCFullscreen.query(panelEl, ".mp");
      if (!wrap) return;
      wrap._mp.mc = { ...mc };
      applyMedia(wrap);
      syncOne(wrap);
    },
    onMessage(panelEl, messageType) {
      if (messageType === "language_changed") {
        const wrap = OCFullscreen.query(panelEl, ".mp");
        if (wrap && wrap._relabel) wrap._relabel();
      }
    },
    buildPropertiesPane: buildProps,
    readPropertiesPane: readProps,
  });

  if (typeof PANEL_TITLE_KEYS !== "undefined") PANEL_TITLE_KEYS.media_player = "PANEL_MEDIA_PLAYER";
})();

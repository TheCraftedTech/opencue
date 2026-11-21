// Copyright (C) 2026 Samuel Zenker
// SPDX-License-Identifier: GPL-3.0-or-later
/* 3D-Simulation: KAMERA SYNCHRONISIEREN (Praesentationsmodus). Knopf in der Leiste oben rechts neben "Raum & Licht"; oeffnet ein kleines Fenster, in dem man die Gruppe waehlt, mit
 * der die Kamera geteilt wird: "Global" (alle Geraete, Vorgabe), eine selbst angelegte Gruppe oder "Getrennt" (eigene Kamera). "Nur ansehen" sperrt die Kamera dieses Geraets.
 * Die eigentliche Verwaltung (Gruppe, Server-Nachrichten, Gleiten) liegt in window.OCSimCam (sim3d_boot.js) und laeuft auch, wenn kein 3D-Panel offen ist; dieses Panel meldet sich
 * dort mit seiner Kamera an. Es kann immer nur ein Fenster der Leiste offen sein (Ereignis "sim3d-popover"). */

function injectStyle() {
  if (document.getElementById("sim3d-cam-style")) return;
  const style = document.createElement("style");
  style.id = "sim3d-cam-style";
  style.textContent = `
    .sim3d__cam .sim3d__room-row .sim3d__select { flex: 1 1 auto; min-width: 0; }
    .sim3d__cam-new { display: flex; align-items: center; gap: 0.4rem; }
    .sim3d__cam-new .sim3d__text { flex: 1 1 auto; }
    .sim3d__cam-status { margin: 0; color: var(--secondary-text); font-size: 0.8rem; }
    .sim3d__cam .sim3d__btn.sim3d__btn--wide { flex: 0 0 auto; height: 2.5rem; }
  `;
  document.head.appendChild(style);
}

const fill = (text, n) => String(text).split("{n}").join(String(n));

/** host: .sim3d-Wurzel, tools: Knopfleiste oben rechts. Gibt { dispose } zurueck. */
export function createCamSync(sim, host, tools) {
  injectStyle();
  const cam = window.OCSimCam;
  const detach = cam ? cam.attach(sim) : () => {};

  const wrap = document.createElement("div");
  wrap.style.cssText = "display:inline-flex";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "sim3d__btn";
  button.dataset.act = "cam";
  button.title = i18n("SIM3D_CAM_TIP");
  button.setAttribute("aria-label", i18n("SIM3D_CAM"));
  button.setAttribute("aria-pressed", "false");
  button.appendChild(Icons.svg("present"));
  const panel = document.createElement("div");
  panel.className = "sim3d__room sim3d__cam";
  panel.hidden = true;
  wrap.append(button, panel);
  const room = tools.firstChild;
  tools.insertBefore(wrap, room ? room.nextSibling : null);                // direkt hinter "Raum & Licht"

  const title = document.createElement("h4");
  title.className = "sim3d__title";
  title.textContent = i18n("SIM3D_CAM_TITLE");

  const groupRow = document.createElement("div");
  groupRow.className = "sim3d__room-row";
  const groupLabel = document.createElement("label");
  groupLabel.textContent = i18n("SIM3D_CAM_GROUP");
  const select = document.createElement("select");
  select.className = "sim3d__select";
  select.dataset.field = "cam-group";
  groupLabel.htmlFor = "sim3d-cam-group-" + Math.random().toString(36).slice(2, 7);
  select.id = groupLabel.htmlFor;
  groupRow.append(groupLabel, select);

  const status = document.createElement("p");
  status.className = "sim3d__cam-status";

  const newRow = document.createElement("div");
  newRow.className = "sim3d__cam-new";
  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.className = "sim3d__text";
  nameInput.maxLength = 48;
  nameInput.placeholder = i18n("SIM3D_CAM_NEW_PH");
  nameInput.dataset.field = "cam-new";
  nameInput.setAttribute("aria-label", i18n("SIM3D_CAM_NEW"));
  const create = document.createElement("button");
  create.type = "button";
  create.className = "sim3d__btn sim3d__btn--wide";
  create.dataset.act = "cam-create";
  create.textContent = i18n("SIM3D_CAM_CREATE");
  newRow.append(nameInput, create);

  const lockRow = document.createElement("div");
  lockRow.className = "sim3d__room-row";
  const lockLabel = document.createElement("label");
  lockLabel.textContent = i18n("SIM3D_CAM_LOCK");
  const lock = document.createElement("input");
  lock.type = "checkbox";
  lock.dataset.field = "cam-lock";
  lock.id = "sim3d-cam-lock-" + Math.random().toString(36).slice(2, 7);
  lockLabel.htmlFor = lock.id;
  lockRow.append(lockLabel, lock);

  const hint = document.createElement("p");
  hint.className = "sim3d__room-hint";
  hint.textContent = i18n("SIM3D_CAM_HINT");
  panel.append(title, groupRow, status, newRow, lockRow, hint);

  const groupName = (key, count) => {
    const base = key === "global" ? i18n("SIM3D_CAM_GLOBAL") : key === "off" ? i18n("SIM3D_CAM_OFF") : key;
    return key === "off" ? base : base + " (" + count + ")";
  };
  function paint() {
    if (!cam) return;
    const list = cam.groups();
    const keys = ["global", "off", ...list.map((g) => g.key).filter((k) => k !== "global")];
    const countOf = (k) => (list.find((g) => g.key === k) || { count: 0 }).count;
    select.innerHTML = "";
    keys.forEach((key) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = groupName(key, countOf(key));
      select.appendChild(option);
    });
    select.value = cam.group;
    const here = cam.group === "off" ? 0 : countOf(cam.group);
    status.textContent = cam.group === "off" ? i18n("SIM3D_CAM_STATUS_OFF") : fill(i18n("SIM3D_CAM_STATUS"), Math.max(1, here));
    lock.checked = cam.lock;
    lock.disabled = cam.group === "off";
    const shared = cam.group !== "off" && here > 1;
    button.classList.toggle("sim3d__btn--on", shared || panel.hidden === false);
    button.dataset.state = cam.group === "off" ? "off" : (cam.lock ? "locked" : (shared ? "shared" : "alone"));
  }
  const unsubscribe = cam ? cam.subscribe(paint) : () => {};

  const toggle = (open) => {
    panel.hidden = !open;
    button.setAttribute("aria-pressed", String(open));
    if (open) {
      host.dispatchEvent(new CustomEvent("sim3d-popover", { detail: "cam" }));          // ein anderes Fenster der Leiste schliesst sich
      fit();
    }
    paint();
  };
  function fit() {
    if (panel.hidden) return;
    panel.style.maxHeight = "";
    const bottom = host.getBoundingClientRect().bottom;
    const top = panel.getBoundingClientRect().top;
    panel.style.maxHeight = Math.max(140, Math.floor(bottom - top - 8)) + "px";
  }
  const fitObserver = new ResizeObserver(fit);
  fitObserver.observe(host);
  const onOther = (e) => { if (e.detail !== "cam" && !panel.hidden) toggle(false); };
  host.addEventListener("sim3d-popover", onOther);
  button.addEventListener("click", () => toggle(panel.hidden));
  const onKey = (e) => { if (e.key === "Escape" && !panel.hidden) { toggle(false); e.stopPropagation(); } };
  host.addEventListener("keydown", onKey);
  [wrap, panel].forEach((n) => n.addEventListener("dblclick", (e) => e.stopPropagation()));

  select.addEventListener("change", () => { if (cam) cam.setGroup(select.value); });
  const createGroup = () => {
    const name = nameInput.value.trim();
    if (!name || !cam) return;
    cam.setGroup(name);
    nameInput.value = "";
  };
  create.addEventListener("click", createGroup);
  nameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); createGroup(); } e.stopPropagation(); });
  lock.addEventListener("change", () => { if (cam) cam.setLock(lock.checked); });
  paint();

  return {
    paint,
    dispose() {
      unsubscribe();
      detach();
      fitObserver.disconnect();
      host.removeEventListener("sim3d-popover", onOther);
      host.removeEventListener("keydown", onKey);
      wrap.remove();
    },
  };
}

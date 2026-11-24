# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
window_host.py
Das 3D-Panel in einem EIGENEN Fenster (eigener Browser-Prozess). Die 3D-Simulation rechnet viel (Lichtkegel, Schatten, Nebel, Strahlproben); laeuft sie im selben Fenster wie die
Konsole, teilen sich beides denselben Haupt-Thread der Seite - Fader und Listen ruckeln, wenn die 3D-Ansicht viel zu tun hat. Ein zweites Programmfenster bekommt einen eigenen
Renderer-Prozess (eigener Haupt-Thread), und sein Prozess laeuft mit niedrigerer Prioritaet (main.py): die Konsole hat Vorrang, die 3D-Ansicht bekommt, was uebrig bleibt.

Aufbau: main.py meldet hier vier Funktionen an (open / close / focus / is_open - nur wenn es ein Programmfenster gibt; im Server-Modus --no-ui fehlen sie, dann gibt es den Knopf nicht).
Das Fenster laedt dieselbe Oberflaeche mit ?solo=sim3d: app.js baut dann kein Layout, sondern nur das 3D-Panel in voller Groesse (panel_window.js solo()). Das Hauptfenster haelt seine
3D-Simulation an, solange das Fenster offen ist, und zeigt einen Platzhalter mit "Fenster nach vorn" / "Hier anzeigen".

HTTP (nur vom Konsolen-Rechner selbst, nie von Fernzugriffs-Geraeten):
  GET  /api/sim3d/window              -> {ok, available, open, paused, hidden: {main, sim3d}}
  POST /api/sim3d/window {action: "open" | "close" | "focus" | "pause" | "resume"} -> {ok, open, paused}
Ereignisse an die Konsolen-Fenster (remote.LOCAL_ONLY_EVENTS): {"type": "sim3d_window", "payload": {"open", "paused"}} und
{"type": "host_window_visible", "payload": {"window": "main" | "sim3d", "visible": bool}}: main.py beobachtet auf Windows-Ebene, ob ein Programmfenster minimiert, auf einem anderen Desktop oder
vollstaendig von anderen Fenstern verdeckt ist (WebView2 meldet das nicht von selbst: die Seite gilt weiter als sichtbar und zeichnet mit ~10 Bildern/s weiter). Die 3D-Ansicht zeichnet dann nichts.
"Pause" des 3D-Fensters gilt serverseitig, damit man es am Hauptfenster anhalten und starten kann.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import remote

logger = logging.getLogger(__name__)
router = APIRouter()

_handlers: Dict[str, Callable[..., Any]] = {}
_state: Dict[str, Any] = {"paused": False, "hidden": {}}


def register(open_fn: Callable[[], bool], close_fn: Callable[[], None], focus_fn: Callable[[], None], is_open_fn: Callable[[], bool], info_fn: Optional[Callable[[], Dict[str, Any]]] = None) -> None:
    """main.py: die Fenster-Funktionen anmelden (nur mit Programmfenster)."""
    _handlers.update(open=open_fn, close=close_fn, focus=focus_fn, is_open=is_open_fn)
    if info_fn is not None:
        _handlers["info"] = info_fn


def available() -> bool:
    return "open" in _handlers


def is_open() -> bool:
    fn = _handlers.get("is_open")
    try:
        return bool(fn()) if fn else False
    except Exception:                                                                    # noqa: BLE001
        return False


def _broadcast(message: Dict[str, Any]) -> None:
    try:
        from app import server
        loop = getattr(server, "_app_loop", None)
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(server.event_bus.broadcast(message), loop)
    except Exception as exc:                                                             # noqa: BLE001
        logger.debug("3D-Fenster: Meldung fehlgeschlagen: %s", exc)


def notify() -> None:
    """Aus jedem Thread: allen Konsolen-Fenstern melden, ob das 3D-Fenster offen und angehalten ist."""
    if not is_open():
        _state["paused"] = False                                                         # ein neu geoeffnetes Fenster laeuft immer
    _broadcast({"type": "sim3d_window", "payload": {"open": is_open(), "paused": bool(_state["paused"])}})


def set_paused(paused: bool) -> None:
    _state["paused"] = bool(paused)
    notify()


def set_hidden(name: str, hidden: bool) -> None:
    """main.py: das Programmfenster `name` ("main" | "sim3d") ist jetzt verdeckt / wieder sichtbar."""
    if _state["hidden"].get(name, False) == bool(hidden):
        return
    _state["hidden"][name] = bool(hidden)
    _broadcast({"type": "host_window_visible", "payload": {"window": name, "visible": not hidden}})


def close_all() -> None:
    """Beim Beenden: das 3D-Fenster zuerst schliessen (sonst bleibt der Prozess, bis es zu ist)."""
    fn = _handlers.get("close")
    if fn:
        try:
            fn()
        except Exception as exc:                                                         # noqa: BLE001
            logger.debug("3D-Fenster schliessen: %s", exc)


def _local(request: Request) -> bool:
    return remote.is_local(request.client.host if request.client else None)


@router.get("/api/sim3d/window")
async def window_info(request: Request) -> JSONResponse:
    local = _local(request)
    out: Dict[str, Any] = {"ok": True, "available": bool(local and available()), "open": bool(local and is_open()), "paused": bool(_state["paused"]), "hidden": dict(_state["hidden"])}
    info = _handlers.get("info")
    if local and info:
        try:
            out["info"] = info()
        except Exception:                                                                # noqa: BLE001
            pass
    return JSONResponse(out)


@router.post("/api/sim3d/window")
async def window_action(request: Request) -> JSONResponse:
    if not _local(request) or not available():
        return JSONResponse({"ok": False, "error": "unavailable", "message": "The 3D window is only available on the console computer."}, status_code=403)
    try:
        body = await request.json()
    except Exception:                                                                    # noqa: BLE001
        body = {}
    action = str((body or {}).get("action") or "")
    if action not in ("open", "close", "focus", "pause", "resume"):
        return JSONResponse({"ok": False, "error": "bad_action"}, status_code=400)
    if action in ("pause", "resume"):
        set_paused(action == "pause" and is_open())
        return JSONResponse({"ok": True, "open": is_open(), "paused": bool(_state["paused"])})
    handler = _handlers.get({"open": "open", "close": "close", "focus": "focus"}[action])
    try:
        await asyncio.to_thread(handler)
    except Exception as exc:                                                             # noqa: BLE001
        logger.exception("3D-Fenster: %s fehlgeschlagen", action)
        return JSONResponse({"ok": False, "error": "failed", "message": f"{type(exc).__name__}: {exc}"[:200]}, status_code=500)
    return JSONResponse({"ok": True, "open": is_open(), "paused": bool(_state["paused"])})


# ------------------------------------------------------------------------------------------------ Prozess-Prioritaet (Windows)
def process_ids(name: str = "msedgewebview2.exe") -> set:
    """IDs aller laufenden Prozesse mit diesem Programmnamen (Windows, ohne zusaetzliche Bibliothek)."""
    import sys
    if sys.platform != "win32":
        return set()
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    kernel = ctypes.windll.kernel32
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    found: set = set()
    snapshot = kernel.CreateToolhelp32Snapshot(0x2, 0)                                   # TH32CS_SNAPPROCESS
    if not snapshot or snapshot == wintypes.HANDLE(-1).value:
        return found
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(ProcessEntry)
        ok = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == name.lower():
                found.add(int(entry.th32ProcessID))
            ok = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return found


def lower_priority(pid: int) -> bool:
    """Einen Prozess auf "Niedriger als normal" setzen (Windows). Ohne Recht oder ohne Windows: False, ohne Folgen."""
    import sys
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x0200, False, pid)                                       # PROCESS_SET_INFORMATION
    if not handle:
        return False
    try:
        return bool(kernel.SetPriorityClass(handle, 0x4000))                              # BELOW_NORMAL_PRIORITY_CLASS
    finally:
        kernel.CloseHandle(handle)


def lower_new_processes(before: set, alive: Optional[Callable[[], bool]] = None, first_seconds: float = 12.0, sink: Optional[list] = None) -> list:
    """Solange das 3D-Fenster offen ist (`alive`): die neu entstandenen WebView2-Prozesse (sein Renderer) auf niedrigere Prioritaet setzen und dort halten. Der Renderer entsteht erst, wenn die Seite
    laedt - darum wird gleich mehrfach nachgesehen; Chromium setzt die Prioritaet bei Fokus-/Sichtbarkeitswechseln selbst wieder auf "Normal", deshalb wird sie alle ~1,5 s erneut gesetzt.
    Gibt die betroffenen Prozess-IDs zurueck (am Ende). Laeuft in einem eigenen Thread."""
    import time
    lowered: list = sink if sink is not None else []                                     # `sink`: Liste, die schon waehrend der Laufzeit gefuellt wird (fuer die Anzeige)
    started = time.monotonic()
    while (alive() if alive else time.monotonic() - started < first_seconds):
        for pid in sorted(process_ids() - before):
            if lower_priority(pid) and pid not in lowered:
                lowered.append(pid)
        time.sleep(1.5)
    logger.info("3D-Fenster: %d Prozess(e) auf niedrigere Prioritaet gesetzt", len(lowered))
    return lowered


# ------------------------------------------------------------------------------------------------ Verdeckt? (Windows)
def window_hidden(hwnd: int) -> bool:
    """True, wenn das Fenster nichts Sichtbares hat: minimiert, nicht sichtbar, auf einem anderen virtuellen Desktop (DWM "cloaked") oder an allen Probepunkten von anderen Fenstern bedeckt.
    Probe: ein Raster von Punkten im Fenster; gehoert an irgendeinem Punkt das oberste Fenster (Wurzel) uns, ist es sichtbar."""
    import sys
    if sys.platform != "win32" or not hwnd:
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    h = wintypes.HWND(hwnd)
    if user32.IsIconic(h) or not user32.IsWindowVisible(h):
        return True
    try:
        cloaked = wintypes.DWORD(0)
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(h, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0 and cloaked.value:     # DWMWA_CLOAKED
            return True
    except Exception:                                                                    # noqa: BLE001
        pass
    rect = wintypes.RECT()
    if not user32.GetWindowRect(h, ctypes.byref(rect)):
        return False
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width < 40 or height < 40:
        return False
    for fy in (0.12, 0.35, 0.6, 0.85):
        for fx in (0.1, 0.3, 0.5, 0.7, 0.9):
            point = wintypes.POINT(int(rect.left + width * fx), int(rect.top + height * fy))
            top = user32.WindowFromPoint(point)
            if top and user32.GetAncestor(top, 2) == hwnd:                               # GA_ROOT
                return False
    return True

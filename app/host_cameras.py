"""
host_cameras.py
Kameras am Hauptgeraet: der Computer, auf dem dieses Programm laeuft (Konsole/Laptop). Die Kameras (Webcam, angeschlossene Kamera) werden
HIER aufgenommen und als Bildstrom (MJPEG) an alle verbundenen Geraete weitergereicht - auch an ein iPad, das nur per http:// im Netz
haengt und selbst gar keinen Kamerazugriff bekaeme. Die Liste der Kameras kommt deshalb immer vom Hauptgeraet, egal auf welchem Geraet
man gerade eine Quelle waehlt.

- Aufnahme mit ffmpeg (externes Programm, KEINE Python-Abhaengigkeit): gesucht wird OPENCUE_FFMPEG, dann ffmpeg/ffmpeg.exe im Programmordner (so wird es
  mitgeliefert; im Build neben OpenCue.exe bzw. in _internal) / im Datenordner, dann der PATH. Windows: DirectShow-Geraete; Linux: /dev/video*.
- Die Aufnahme endet sofort beim Beenden des Programms (stop_all) - und selbst wenn das Programm hart beendet wird oder abstuerzt, denn unter
  Windows haengen die ffmpeg-Prozesse an einem Job-Objekt, das beim Ende des Programms alle Prozesse beendet.
- Pro Kamera laeuft hoechstens EIN ffmpeg (eine Kamera laesst sich nur einmal oeffnen); alle Betrachter teilen sich das neueste Bild
  (langsame Geraete ueberspringen Bilder, nichts staut sich). Der Prozess startet beim ersten Betrachter und endet kurz nach dem letzten.
- Die Kamera laeuft nur, solange mindestens ein Panel sie zeigt (die Kamera-LED am Laptop zeigt das).
"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app import paths as _paths
from app.stream_sources import StreamError

# Qualitaetsstufen: (hoechste Sendebreite, hoechste Bildrate, JPEG-Qualitaet ffmpeg -q:v (2 = beste, 31 = schlechteste), bevorzugte Kameragroesse).
# Webcams bieten feste Modi; geht der gewuenschte nicht, nimmt ffmpeg den Standardmodus der Kamera.
PROFILES: Dict[str, Tuple[int, int, int, str]] = {
    "low": (640, 10, 10, "640x480"),
    "medium": (960, 15, 8, "1280x720"),
    "high": (1280, 20, 5, "1280x720"),
    "max": (1920, 30, 3, "1920x1080"),
}
PROFILE_ORDER = ["low", "medium", "high", "max"]
DEFAULT_PROFILE = "medium"
MAX_VIEWERS = 6                     # gleichzeitige Betrachter je Kamera
IDLE_GRACE = 5.0                    # Sekunden Nachlauf nach dem letzten Betrachter (Panel-Wechsel/Neuladen ohne Kamera-Neustart)
START_TIMEOUT = 8.0                 # Sekunden bis zum ersten Bild
LIST_TTL = 20.0
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_job_handle: Any = None


def normalize_profile(name: Any) -> str:
    return name if isinstance(name, str) and name in PROFILES else DEFAULT_PROFILE


def _bind_to_job(proc: subprocess.Popen) -> None:
    """Windows: den Prozess an ein Job-Objekt 'beim Schliessen alles beenden' haengen - stirbt das Programm (auch hart), sterben die Kameras mit."""
    global _job_handle
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.windll.kernel32
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        if _job_handle is None:
            class _Basic(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

            class _Io(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

            class _Extended(ctypes.Structure):
                _fields_ = [("Basic", _Basic), ("Io", _Io), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

            job = kernel.CreateJobObjectW(None, None)
            info = _Extended()
            info.Basic.LimitFlags = 0x2000                       # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not job or not kernel.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)):
                return
            _job_handle = job
        kernel.AssignProcessToJobObject(wintypes.HANDLE(_job_handle), wintypes.HANDLE(int(proc._handle)))
    except Exception:
        pass                                                      # nur ein zusaetzliches Sicherheitsnetz


class Device:
    """Eine Kamera. fmt_args = Eingabeformat fuer ffmpeg (z. B. ['-f','dshow']), source = das -i-Argument; fixed: Groesse/Takt nicht vorschlagen."""

    def __init__(self, dev_id: str, name: str, fmt_args: List[str], source: str, fixed: bool = False) -> None:
        self.id, self.name, self.fmt_args, self.source, self.fixed = dev_id, name, fmt_args, source, fixed

    def public(self) -> Dict[str, str]:
        return {"id": self.id, "name": self.name}


# ------------------------------------------------------------------------------------------------ ffmpeg finden
def find_ffmpeg() -> Optional[str]:
    candidates: List[str] = []
    env = os.environ.get("OPENCUE_FFMPEG", "")
    if env:
        candidates.append(env)
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    base = _paths.project_root()                                      # Projektordner (ffmpeg/ffmpeg.exe); im PyInstaller-Build der Ordner _internal
    candidates += [str(base / exe), str(base / "ffmpeg" / exe)]
    if getattr(sys, "frozen", False):                                 # ... oder neben OpenCue.exe (so laesst sich ffmpeg im fertigen Ordner austauschen)
        beside = Path(sys.executable).resolve().parent
        candidates += [str(beside / exe), str(beside / "ffmpeg" / exe)]
    candidates += [str(_paths.get_data_root() / exe), str(_paths.get_data_root() / "ffmpeg" / exe)]
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return shutil.which("ffmpeg")


def _slug_id(name: str, index: int) -> str:
    return "c" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:10] + (f"-{index}" if index else "")


def parse_dshow_list(text: str) -> List[Device]:
    """Videogeraete aus der Ausgabe von 'ffmpeg -list_devices true -f dshow -i dummy' (Zeilen wie '"Integrated Camera" (video)')."""
    devices: List[Device] = []
    seen: Dict[str, int] = {}
    for line in text.splitlines():
        match = re.search(r'"([^"]+)"\s+\(([a-z, ]+)\)\s*$', line.strip())
        if not match or "video" not in match.group(2):
            continue
        name = match.group(1)
        index = seen.get(name, 0)
        seen[name] = index + 1
        source = f"video={name}"
        fmt = ["-f", "dshow"] + (["-video_device_number", str(index)] if index else [])
        devices.append(Device(_slug_id(name, index), name, fmt, source))
    return devices


def _enumerate(ffmpeg: str) -> List[Device]:
    if sys.platform == "win32":
        try:
            done = subprocess.run([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True, timeout=20, creationflags=_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired):
            return []
        return parse_dshow_list((done.stderr or b"").decode("utf-8", "replace"))
    if sys.platform.startswith("linux"):
        found = []
        for node in sorted(Path("/dev").glob("video*")):
            try:
                label = (Path("/sys/class/video4linux") / node.name / "name").read_text(encoding="utf-8").strip() or node.name
            except OSError:
                label = node.name
            found.append(Device(_slug_id(str(node), 0), f"{label} ({node.name})", ["-f", "v4l2"], str(node)))
        return found
    return []


def supported() -> bool:
    return sys.platform == "win32" or sys.platform.startswith("linux")


_list_lock = threading.Lock()
_list_cache: Tuple[float, List[Device]] = (0.0, [])


def list_devices(refresh: bool = False) -> List[Device]:
    """Kameras am Hauptgeraet (kurz zwischengespeichert: die Abfrage startet ein Programm)."""
    global _list_cache
    ffmpeg = find_ffmpeg()
    if not ffmpeg or not supported():
        return []
    with _list_lock:
        stamp, cached = _list_cache
        if refresh or time.monotonic() - stamp > LIST_TTL:
            cached = _enumerate(ffmpeg)
            _list_cache = (time.monotonic(), cached)
        return list(cached)


def overview(refresh: bool = False) -> Dict[str, Any]:
    ffmpeg = find_ffmpeg()
    devices = list_devices(refresh) if ffmpeg and supported() else []
    return {"supported": supported(), "ffmpeg": bool(ffmpeg), "devices": [d.public() for d in devices]}


def get_device(dev_id: str) -> Optional[Device]:
    return next((d for d in list_devices() if d.id == dev_id), None)


# ------------------------------------------------------------------------------------------------ Aufnahme
def _error_from(tail: str) -> Tuple[str, str]:
    """(Code, Meldung) aus der Fehlerausgabe von ffmpeg."""
    low = tail.lower()
    if any(x in low for x in ("access is denied", "permission denied", "zugriff")):
        return "permission", "Windows verweigert den Kamerazugriff (Einstellungen > Datenschutz > Kamera)"
    if any(x in low for x in ("could not run graph", "device or resource busy", "already in use")):
        return "in_use", "Die Kamera ist belegt (ein anderes Programm nutzt sie)"
    if any(x in low for x in ("could not find video device", "no such file", "cannot find")):
        return "no_camera", "Diese Kamera ist am Hauptgeraet nicht (mehr) angeschlossen"
    last = [line for line in tail.strip().splitlines() if line.strip()]
    return "camera_failed", (last[-1][:200] if last else "Die Kamera liefert kein Bild")


class Capture:
    """Ein laufender ffmpeg fuer eine Kamera; das neueste Bild wird an alle Betrachter verteilt."""

    def __init__(self, device: Device, ffmpeg: str, profile: str = DEFAULT_PROFILE) -> None:
        self.device, self.ffmpeg, self.profile = device, ffmpeg, profile
        self.state = "new"               # new | running | failed | stopped
        self.error: Tuple[str, str] = ("", "")
        self.viewers = 0
        self.seq = 0
        self.frame: Optional[bytes] = None
        self.started_at = 0.0
        self.frames_total = 0
        self._cond = threading.Condition()
        self._start_lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._tail = ""
        self._idle_timer: Optional[threading.Timer] = None

    # -- Start
    def _command(self, extra: List[str]) -> List[str]:
        width, fps, quality, _size = PROFILES[self.profile]
        pacing = ["-re"] if self.device.fixed else []                    # synthetische Quellen (Test) laufen sonst so schnell wie moeglich
        return [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", *pacing, *self.device.fmt_args, *extra, "-i", self.device.source,
                "-an", "-fpsmax", str(fps), "-vf", f"scale='min({width},iw)':-2", "-c:v", "mjpeg", "-q:v", str(quality), "-f", "image2pipe", "-"]

    def _spawn(self, extra: List[str]) -> None:
        self._tail = ""                                                  # Bildnummer (seq) zaehlt weiter: wartende Betrachter bleiben dran
        self._proc = subprocess.Popen(self._command(extra), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW)
        _bind_to_job(self._proc)
        threading.Thread(target=self._read_frames, args=(self._proc,), daemon=True).start()
        threading.Thread(target=self._read_errors, args=(self._proc,), daemon=True).start()

    def ensure_started(self, profile: str = DEFAULT_PROFILE) -> None:
        """Startet die Aufnahme; laeuft sie schon, aber mit niedrigerer Qualitaet als verlangt, wird sie auf die hoehere Stufe umgestellt
        (die anderen Betrachter bleiben verbunden und bekommen danach die bessere Qualitaet)."""
        with self._start_lock:
            if self.state == "running":
                if PROFILE_ORDER.index(profile) > PROFILE_ORDER.index(self.profile):
                    self.profile = profile
                    self._kill()
                    self._launch()
                return
            if self.state == "failed":
                raise StreamError(self.error[0] or "camera_failed", self.error[1] or "Die Kamera liefert kein Bild", 502)
            self.profile = profile
            self._launch()
            self.started_at = time.monotonic()

    def _launch(self) -> None:
        options = [[]] if self.device.fixed else [["-video_size", PROFILES[self.profile][3]], []]
        for extra in options:
            self._spawn(extra)
            if self._wait_first_frame():
                self.state = "running"
                return
            self._kill()
        time.sleep(0.2)                                          # Fehlerausgabe fertig einlesen
        self.state = "failed"
        self.error = _error_from(self._tail)
        raise StreamError(self.error[0], self.error[1], 502)

    def _wait_first_frame(self) -> bool:
        end = time.monotonic() + START_TIMEOUT
        with self._cond:
            base = self.seq
            while self.seq <= base and time.monotonic() < end:
                if self._proc is None or self._proc.poll() is not None:
                    break
                self._cond.wait(0.2)
            return self.seq > base

    # -- Lesen
    def _read_frames(self, proc: subprocess.Popen) -> None:
        buf = bytearray()
        try:
            while True:
                chunk = proc.stdout.read1(65536)
                if not chunk:
                    break
                buf += chunk
                while True:
                    start = buf.find(b"\xff\xd8")
                    if start < 0:
                        buf.clear()
                        break
                    end = buf.find(b"\xff\xd9", start + 2)
                    if end < 0:
                        if len(buf) > 8 * 1024 * 1024:
                            buf.clear()
                        elif start:
                            del buf[:start]
                        break
                    frame = bytes(buf[start:end + 2])
                    del buf[:end + 2]
                    with self._cond:
                        if proc is not self._proc:
                            return
                        self.frame, self.seq, self.frames_total = frame, self.seq + 1, self.frames_total + 1
                        self._cond.notify_all()
        except (OSError, ValueError):
            pass
        finally:
            with self._cond:
                unexpected = proc is self._proc and self.state == "running"        # unerwartet beendet (Kamera abgezogen, anderes Programm ...)
            if unexpected:
                time.sleep(0.2)                                                    # Fehlerausgabe fertig einlesen
            with self._cond:
                if unexpected and self.state == "running":
                    self.state = "failed"
                    self.error = _error_from(self._tail)
                self._cond.notify_all()

    def _read_errors(self, proc: subprocess.Popen) -> None:
        try:
            for raw in iter(proc.stderr.readline, b""):
                self._tail = (self._tail + raw.decode("utf-8", "replace"))[-4000:]
        except (OSError, ValueError):
            pass

    def wait_frame(self, after_seq: int, timeout: float) -> Tuple[int, Optional[bytes]]:
        """Wartet auf ein Bild neuer als after_seq (None bei Zeitablauf oder wenn die Kamera nicht mehr laeuft)."""
        end = time.monotonic() + timeout
        with self._cond:
            while self.seq <= after_seq and self.state == "running":
                left = end - time.monotonic()
                if left <= 0:
                    return after_seq, None
                self._cond.wait(left)
            if self.seq > after_seq and self.frame is not None:
                return self.seq, self.frame
            return after_seq, None

    # -- Ende
    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        if sys.platform == "win32":                                      # ganzen Prozessbaum beenden (z. B. ffmpeg-Startprogramm von Paketverwaltern)
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=10, creationflags=_NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        for pipe in (proc.stdout, proc.stderr):
            try:
                pipe.close()
            except Exception:
                pass

    def stop(self) -> None:
        with self._cond:
            if self.state != "failed":
                self.state = "stopped"
            self._cond.notify_all()
        self._kill()

    def status(self) -> Dict[str, Any]:
        return {"state": self.state, "profile": self.profile, "viewers": self.viewers, "seq": self.seq, "frames": self.frames_total,
                "error": self.error[0], "message": self.error[1]}


_lock = threading.Lock()
_captures: Dict[str, Capture] = {}


def acquire(dev_id: str, profile: str = DEFAULT_PROFILE) -> Capture:
    """Betrachter anmelden (startet die Kamera beim ersten). Blockiert bis zum ersten Bild; wirft StreamError."""
    profile = normalize_profile(profile)
    ffmpeg = find_ffmpeg()
    if not supported():
        raise StreamError("unsupported_os", "Kameras am Hauptgeraet gibt es unter Windows und Linux", 501)
    if not ffmpeg:
        raise StreamError("no_ffmpeg", "ffmpeg fehlt: ffmpeg.exe in den Ordner ffmpeg im Programmordner legen oder in den PATH aufnehmen", 503)
    device = get_device(dev_id)
    if device is None:
        raise StreamError("no_camera", "Diese Kamera ist am Hauptgeraet nicht (mehr) angeschlossen", 404)
    with _lock:
        cap = _captures.get(dev_id)
        if cap is not None and cap.state in ("failed", "stopped") and cap.viewers == 0:
            cap = None
        if cap is None:
            cap = _captures[dev_id] = Capture(device, ffmpeg, profile)
        if cap.viewers >= MAX_VIEWERS:
            raise StreamError("busy", "Zu viele gleichzeitige Betrachter dieser Kamera", 429)
        cap.viewers += 1
        if cap._idle_timer is not None:
            cap._idle_timer.cancel()
            cap._idle_timer = None
    try:
        cap.ensure_started(profile)
    except Exception:
        release(cap)
        raise
    return cap


def release(cap: Capture) -> None:
    with _lock:
        cap.viewers = max(0, cap.viewers - 1)
        if cap.viewers == 0 and cap._idle_timer is None:
            cap._idle_timer = threading.Timer(IDLE_GRACE, _stop_if_idle, args=(cap,))
            cap._idle_timer.daemon = True
            cap._idle_timer.start()


def _stop_if_idle(cap: Capture) -> None:
    with _lock:
        cap._idle_timer = None
        if cap.viewers > 0:
            return
        if _captures.get(cap.device.id) is cap:
            del _captures[cap.device.id]
    cap.stop()


def status(dev_id: str) -> Dict[str, Any]:
    cap = _captures.get(dev_id)
    return cap.status() if cap is not None else {"state": "idle", "profile": "", "viewers": 0, "seq": 0, "frames": 0, "error": "", "message": ""}


def running_count() -> int:
    return sum(1 for c in list(_captures.values()) if c.state == "running")


def stop_all() -> None:
    with _lock:
        caps = list(_captures.values())
        _captures.clear()
    for cap in caps:
        if cap._idle_timer is not None:
            cap._idle_timer.cancel()
        cap.stop()


atexit.register(stop_all)

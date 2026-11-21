# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Beschreibung von OpenCue: Ordner-Build (onedir) nach dist/OpenCue/ (OpenCue.exe + _internal/).
#
# Bauen (im Projektordner):   powershell -File packaging\build.ps1            (empfohlen; erzeugt vorher Versionsdateien und Lizenztexte)
#                       oder: venv\Scripts\python.exe -m PyInstaller packaging\OpenCue.spec --noconfirm --clean
# Test-Build mit Konsole:     powershell -File packaging\build.ps1 -Console   (zeigt Fehlermeldungen; Umgebungsvariable OPENCUE_CONSOLE=1)
#
# Hineingehoert: nur app/, defaults/, static/, templates/, main.py und ffmpeg/. Version/Firma/Beschreibung kommen aus app/version.py (-> packaging/version_info.txt).
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

SPEC_DIR = os.path.abspath(SPECPATH)           # SPECPATH setzt PyInstaller auf den Ordner dieser Datei
ROOT = os.path.dirname(SPEC_DIR)               # Projektordner
sys.path.insert(0, ROOT)
from app import version  # noqa: E402

CONSOLE = os.environ.get("OPENCUE_CONSOLE", "0") == "1"
ICON = os.path.join(SPEC_DIR, "OpenCue.ico")
VERSION_FILE = os.path.join(SPEC_DIR, "version_info.txt")
for required in (ICON, VERSION_FILE, os.path.join(ROOT, "ffmpeg", "ffmpeg.exe"), os.path.join(SPEC_DIR, "third_party", "components.json")):
    if not os.path.exists(required):
        raise SystemExit(f"Fehlt fuer den Build: {required}  (packaging\\build.ps1 erzeugt die Versions- und Lizenzdateien)")

# ---- mitgelieferte Dateien (Quelle, Ziel relativ zu _internal). _old/, READMEs, venv/ gehoeren NICHT dazu.
datas = [
    (os.path.join(ROOT, "static"), "static"),
    (os.path.join(ROOT, "templates"), "templates"),
    (os.path.join(ROOT, "defaults"), "defaults"),                               # (ohne defaults/voice: das Sprachmodell laedt das Programm bei Bedarf nach, siehe unten)
    (os.path.join(ROOT, "ffmpeg"), "ffmpeg"),                                    # ffmpeg.exe (GPL-3, eigenes Programm) + LICENSE.txt + README.md
    (os.path.join(ROOT, "LICENSE"), "."),
    (os.path.join(SPEC_DIR, "third_party"), "third_party"),                      # Lizenztexte der Bibliotheken + components.json (Ueber-Dialog)
    (ICON, "."),                                                                 # Fenster-Icon (main.py: _window_icon)
]
binaries = []
hiddenimports = [
    "webview.platforms.winforms",             # pywebview laedt die Plattform ueber den Namen
    "webview.platforms.edgechromium",
    "app.dmx_output",                         # DMX-Ausgabe als eigener Prozess (OpenCue.exe --dmx-output): wird nur innerhalb einer Funktion importiert
    "multiprocessing.shared_memory",          # gemeinsamer Speicher zwischen Programm und Ausgabe-Prozess
    "app.fx_runner", "app.dmx_in",                          # Rechenkern der Effekte und der Cue-Ueberblendungen: laeuft im Ausgabe-Prozess (wird nur innerhalb einer Funktion importiert)
    "app.cue_fade",
    "app.fx_script",
    "app.fxlang",
    "app.fx_categories",
    "app.audio_vars",
    "app.dmx_resolve",
]
for package in ("uvicorn", "websockets", "zeroconf"):     # laden Protokolle/Untermodule ueber Namen (zeroconf: kompilierte Teile)
    hiddenimports += collect_submodules(package)
for package in ("pythonnet", "clr_loader", "vosk", "faster_whisper", "ctranslate2", "onnxruntime", "tokenizers", "rtmidi"):   # .NET-Bruecke von pywebview (Python.Runtime.dll u. a.); vosk bringt libvosk.dll mit; Diktieren (faster-whisper): Modellcode, Silero-VAD (onnx) und die nativen Bibliotheken von ctranslate2 / onnxruntime / PyAV
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "watchfiles", "unittest", "pytest", "av", "hf_xet"],           # av = PyAV (nur zum Dekodieren von Dateien: OpenCue gibt faster-whisper fertige Audiodaten; ersetzt durch ein leeres Modul in app/dictation.py), hf_xet = optionaler Beschleuniger des Modell-Downloads
    noarchive=False,
)
# Das Sprachmodell (Vosk, 68 MB) wird NICHT mitgeliefert: app/voice.py laedt es bei Bedarf in den Datenordner (Einstellungen -> Triggerwort; der Installer kann es auf Wunsch gleich mitladen).
a.datas = [d for d in a.datas if not d[0].replace("\\", "/").startswith("defaults/voice")]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=version.APP_NAME,                    # OpenCue.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                                # UPX loest oefter Virenwarnungen aus
    console=CONSOLE,
    disable_windowed_traceback=False,
    icon=ICON,
    version=VERSION_FILE,
    manifest=os.path.join(SPEC_DIR, "OpenCue.manifest"),           # asInvoker, DPI, lange Pfade, Windows 10 / 11
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=version.APP_NAME,                    # dist/OpenCue/
)

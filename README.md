# OpenCue

**An open-source lighting control console for DMX and fixtures, inspired by dot2 onPC – with extended features.**

OpenCue turns a Windows PC into a complete lighting desk: patch fixtures, program cues and effects, see the result in a 3D stage, and control the show from a tablet or phone. It works offline, needs no account or licence key (output via Art-Net, sACN or a USB DMX interface).

## What it can do

- **Fixtures and programmer:** GDTF fixture library with patching, groups, presets and variables; every fixture channel (dimmer, colour, position, beam, focus, gobo, prism, shutter) gets its own control.
- **Cues and effects:** cue lists with fades, follow and timecode triggers, executors, an effect engine with its own script language and an effect studio, and a dot2-style command line with autocomplete.
- **3D simulation:** build a stage, see fixtures with their real GDTF models and live DMX light, and aim moving heads at a point on the stage.
- **Timecode and media:** global timecode, video/audio player and camera panels.
- **Remote control:** tablets and phones in the local network (password, QR code, installable web app) – off by default, switchable at any time.
- **Your layout:** free panel layouts, colour themes, German and English, show export/import as ZIP.

## Install (Windows 10 / 11, 64-bit)

Download `OpenCue-Setup-v<version>.exe` from the [Releases](https://github.com/TheCraftedTech/opencue/releases) page and run it. The setup lets you choose the language, program folder, data folder and shortcuts; later versions update through the same setup (OpenCue also tells you when a new version is available).

OpenCue shows its window with the Microsoft Edge WebView2 Runtime, which is part of current Windows; the setup installs it if it is missing (internet needed once).

## Run from source

You need Python 3.13 (64-bit) and an internet connection for the first start.

```
git clone https://github.com/TheCraftedTech/opencue.git
cd opencue
run.bat
```

`run.bat` creates the virtual environment, installs `requirements.txt` on the first start, and then starts OpenCue. `ffmpeg/` contains the ffmpeg build used for cameras on the main device.

## Project layout

```
main.py            entry point (web server thread + native window)
app/               backend: FastAPI server, DMX engine, cue and effect engines, command line
static/            web interface (JavaScript, CSS, in-app guides)
templates/         HTML template
defaults/          demo show, example layout and effect scripts, copied on the first start
packaging/         PyInstaller + Inno Setup build (build.ps1), icons, licence collection
ffmpeg/            ffmpeg.exe (GPL build) with its licence
```

The version number lives in `app/version.py`. To build the Windows program and installer yourself, install Inno Setup 6, run `venv\Scripts\pip install -r packaging\requirements-build.txt`, and then `powershell -File packaging\build.ps1 -Installer`; the result is in `dist\`.

## Licence

OpenCue is free software under the **GNU General Public License v3.0 or later** – see [LICENSE](LICENSE). Third-party components and their licences are listed in `packaging/third_party/THIRD_PARTY_NOTICES.md` and in *Help → About OpenCue*. The included `ffmpeg.exe` is a separate program under the GPL; its source is available from https://ffmpeg.org/download.html.

Changes per version: [CHANGELOG.md](CHANGELOG.md).

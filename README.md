<div align="center">

# OpenCue

### DMX Lighting Control Console

**A free, open-source lighting console for your PC** – DMX over Art-Net, sACN and USB, cues and effects, a 3D stage, and a remote control on any tablet or phone.

[![Version](https://img.shields.io/github/v/release/TheCraftedTech/opencue?include_prereleases&label=version&color=ffb000)](https://github.com/TheCraftedTech/opencue/releases)
[![Licence](https://img.shields.io/github/license/TheCraftedTech/opencue?label=licence&color=blue)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4?logo=windows&logoColor=white)
![Languages](https://img.shields.io/badge/UI-6%20languages-34d96b)

[What it is](#what-is-opencue) · [Features](#what-it-can-do) · [Install](#install-windows-10--11-64-bit) · [First steps](#first-steps) · [Run from source](#run-from-source) · [Help](#help-bugs-ideas)

</div>

---

## What is OpenCue?

**OpenCue – DMX Lighting Control Console** turns a Windows computer into a **complete lighting desk**. You patch your fixtures, program cues and effects, watch the result on a 3D stage, and run the show from the PC – or from an **iPad or phone in the same network**, which shows exactly the same console.

- **It controls real lights.** DMX goes out as Art-Net, sACN (E1.31) or through a USB-DMX adapter to moving heads, LED bars, dimmers, fog machines and more.
- **It is a full console, not a toy.** Fixture library, programmer, cue lists with fades and tracking, an effect engine, a command line, timecode and a timeline.
- **It is free, offline and open.** No account, no licence key, no cloud, no paid tiers. Every feature is included, the source code is here.

## Why OpenCue

- **Built for the stage.** The DMX output runs in its own process with its own clock, so a busy window, a hanging browser or a slow tablet can never make a fade stutter. Measured with 83 fixtures in 4 universes under heavy load: a steady 40 frames per second.
- **Everything in one program.** Fixture library, programmer, cue lists, effects, timeline, command line, 3D simulation, MIDI, OSC, remote control, backups – no add-ons.
- **A remote that is the real console.** The tablet has the same rights as the main computer. Run OpenCue without a window on a small PC under the stage and operate everything from the iPad.
- **Your data stays yours.** Shows are plain files, the program talks to no cloud, and the optional AI assistant runs on your own computer.
- **Careful with your show.** Background backups with crash recovery, undo, a lock screen, safe saving and a warning before anything can be lost.

## What it can do

| | |
|---|---|
| **Fixtures** | GDTF library with online search in GDTF Share, an editor for your own fixtures, CSV / Excel import of patch lists, patching with overlap warnings, groups. |
| **Programming** | A programmer with a control for every fixture channel (dimmer, colour, position, beam, focus, gobo, prism, shutter, wheels), presets and variables, a console-style command line with autocomplete. |
| **Cues** | Cue lists with fades, delays, follow and timecode triggers, tracking or absolute cues, executors with a mix fader, scheduler, undo for the whole show. |
| **Effects** | An effect engine with its own small script language, an effect studio with live preview, ready-made libraries – including effects that react to music. |
| **Output** | Art-Net, sACN (E1.31) and USB-DMX (Enttec DMX USB Pro and compatible); automatic discovery of Art-Net nodes; output in its own process. |
| **Input** | Receive Art-Net and sACN from another desk or software, forward and merge it (highest wins or replace), use channels as triggers; OpenCue announces itself as an Art-Net device. |
| **Control** | MIDI in and out, OSC, a token-based REST API, custom keyboard shortcuts, optional offline voice control. |
| **3D stage** | Build a stage, see the fixtures with their real GDTF models and live DMX light, aim moving heads at a point, import and export MVR scenes (Vectorworks, Capture, Depence), and run the 3D view in its own window. |
| **Time and media** | Global timecode (internal, MIDI timecode, LTC in and out), a timeline editor, video and audio player, camera and stream panels. |
| **Remote control** | Tablets and phones in the local network with password, QR code and an installable web app; off by default; server-only mode (`--no-ui`) with a tray icon. |
| **Safe shows** | Background backups, crash recovery, lock screen, safe saving, export and import of shows with their fixtures. |
| **For everyone** | Six languages, free panel layouts, colour themes where every colour can be changed, built-in guides (press `F1`). |

Protocols and standards: Art-Net · sACN (E1.31) · USB-DMX · GDTF · MIDI · OSC · REST API · LTC · WebXR.

## Install (Windows 10 / 11, 64-bit)

[![Downloads](https://img.shields.io/github/downloads/TheCraftedTech/opencue/total?label=downloads&color=34d96b)](https://github.com/TheCraftedTech/opencue/releases)

1. Download `OpenCue-Setup-v<version>.exe` from the [Releases](https://github.com/TheCraftedTech/opencue/releases) page and run it. The setup lets you choose the language, the program folder, the data folder and shortcuts.
2. Start OpenCue. A welcome dialog helps with the language and the first steps.

OpenCue shows its window with the Microsoft Edge WebView2 Runtime, which is part of current Windows; the setup installs it if it is missing.

## First steps

1. **Library → Fixture Library** – install the fixtures you use (GDTF files, or search GDTF Share).
2. **Add fixtures** in the fixture list: type, quantity, universe and start channel.
3. **Settings → DMX output** – switch on Art-Net, sACN or choose the USB adapter. The DMX monitor shows what leaves the program.
4. Set values in the programmer, then **Store** them as a cue. Play the cue list with **Go**.
5. Want a tablet as a second screen? **Settings → Remote access** – set a password, switch it on, scan the QR code.

The guides inside the program (`F1`) explain each area step by step.

## Run from source

You need Python 3.13 (64-bit) and an internet connection for the first start.

```
git clone https://github.com/TheCraftedTech/opencue.git
cd opencue
run.bat
```

`run.bat` creates the virtual environment, installs `requirements.txt` on the first start and starts OpenCue. `ffmpeg/` contains the ffmpeg build used for cameras on the main computer.

## Build the Windows program and installer

Install Inno Setup 6, then:

```
venv\Scripts\pip install -r packaging\requirements-build.txt
powershell -File packaging\build.ps1 -Installer
```

The result is `dist\OpenCue\` (the program) and the installer `OpenCue-Setup-v<version>.exe`. The version number lives only in `app/version.py`.

## Project layout

![Made with Python](https://img.shields.io/github/languages/top/TheCraftedTech/opencue?label=made%20with&logo=python&logoColor=white)
![Python 3.13](https://img.shields.io/badge/python-3.13-3776ab?logo=python&logoColor=white)
![Code size](https://img.shields.io/github/languages/code-size/TheCraftedTech/opencue?label=code)

```
main.py            entry point (web server thread + native window)
app/               backend: FastAPI server, DMX engine and output process, cue and effect engines, command line
static/            web interface (JavaScript, CSS, in-app guides, translations)
templates/         HTML template
defaults/          demo show, example layouts and effect scripts, copied on the first start
packaging/         PyInstaller + Inno Setup build (build.ps1), icons, licence collection
ffmpeg/            ffmpeg.exe (GPL build) with its licence
```

## Safety note

OpenCue controls real lighting equipment. Test a show before you rely on it, keep a backup of important shows, and do not use any software as the only safeguard for safety-critical effects such as strobes or pyrotechnics.

## Help, bugs, ideas

[![Issues](https://img.shields.io/github/issues/TheCraftedTech/opencue?color=e5484d)](https://github.com/TheCraftedTech/opencue/issues)
[![Last commit](https://img.shields.io/github/last-commit/TheCraftedTech/opencue?color=8b5cf6)](https://github.com/TheCraftedTech/opencue/commits/main)

- Questions and bug reports: [GitHub Issues](https://github.com/TheCraftedTech/opencue/issues). In the program, **Help → Report a problem** collects the technical details for you.
- What changed in each version: [CHANGELOG.md](CHANGELOG.md).

## Licence and credits

OpenCue is free software under the **GNU General Public License v3.0 or later** – see [LICENSE](LICENSE). Third-party components and their licences are listed in `packaging/third_party/THIRD_PARTY_NOTICES.md` and in *Help → About OpenCue*. The bundled ffmpeg build is licensed under the GPL; its licence and source information are in `ffmpeg/`.

Fixture descriptions use the **GDTF** standard; online fixture search is provided by **GDTF Share** (gdtf-share.com), and OpenCue shows who uploaded each file.

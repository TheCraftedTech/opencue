# Changelog

**Website:** https://thecraftedtech.github.io/opencue/

All notable changes to OpenCue, newest first. Each entry describes **what you get**, not how it was built. The date is the day the feature was finished. The version number lives in `app/version.py`; every release gets a `vMAJOR.MINOR.PATCH` tag. The format follows [Keep a Changelog](https://keepachangelog.com/).

## v2.2.0 – 2026-11-24

OpenCue 2.2.0 brings the **MVR import** (stage and fixtures from Vectorworks, Capture, Depence ...), a calmer file manager, a faster 3D simulation with new settings and a guide, and fixes the freezing with big shows.

### Added

- **MVR import (stage and fixtures).** *Library → Import MVR scene…* reads an `.mvr` file from Vectorworks, Capture, Depence and other design programs. You see what is inside and choose to replace, add to or leave alone the 3D stage, and whether to patch the fixtures. The fixtures are patched with type, mode, DMX address and number from the file and placed in the 3D simulation at their position and rotation; their GDTF files go into the fixture library (nothing is overwritten). The stage parts (floor, truss, set pieces, screens) become 3D models and stage objects that you can move, rotate and resize like any other; a part used many times shares one model, and a scene with more than 200 parts is combined per layer. The imported stage stays unsaved until you save the show; the stage file you had before is not touched. A progress bar shows the import, and the dialog also opens from a small button in the 3D panel.
- **MVR import: settings.** Choose which layers to import, keep the addresses of the file (optionally shifted by a number of universes, for example +4) or assign new ones from a start universe, patch only or also place the fixtures in the 3D stage, keep or neutralise the colours, and fix the up axis of the 3D files. Material colours are kept, mirrored parts stay mirrored, walls and curtains are shown from both sides.
- **File manager: groups.** The lists of 3D models, media, effects and fixtures have a **List | Groups** switch (your choice is remembered). *Groups* shows the groups first - effects by kind (dimmer, colour, position ...), media by type (audio, image, video), fixtures by brand, 3D models by the show they are used in (a model in two shows is in both groups) - a click opens one group, *All groups* goes back.
- **File manager: Delete unused** (list *3D models*) removes every 3D model that is on no stage - neither the loaded nor a saved one - so old imports do not pile up. Models on a saved stage are marked.
- **New layout in the Edit menu.** *Edit → New layout…* creates an empty layout, loads it and switches to edit mode - no detour through the file manager any more.
- **3D simulation on/off.** A pause / play button at the top of the 3D simulation stops it completely: the scene, the graphics context, the models and the live light are torn down, so nothing is calculated or drawn and the rest of the console runs undisturbed. The panel stays in the layout and shows a play button; starting builds everything again. The choice is remembered per device.
- **3D simulation: *Room & light* is now a dialog** instead of a small window at the edge of the panel, split into *For all devices* (lighting, bounce, image, haze) and *This device only* (quality and limits). The gear icon replaces the second light bulb (the bulb stays for Blackout). Haze 0 % switches the haze off completely.
- **3D simulation: options for very big stages** (per device, in *Room & light*): *Max. simple light cones* (0 = all, as before; with a limit every fixture keeps its first cone first), *Fixtures cast shadows* (on, as before) and *Max. frame rate* (0 = unlimited). By default nothing is limited and the picture looks as before.
- **New guide *3D Simulation*** (Help → Guides, all six languages): the buttons, the settings in *Room & light* and a troubleshooting list - not every fixture lights the stage, shadows or gobos only on some fixtures, missing cones, slow picture, fixtures that do not move. The AI assistant uses the guide, so it can point to the per-device limits when someone reports that not all fixtures are rendered.

### Changed

- **Saving no longer freezes the program.** The show is written in the background while OpenCue keeps answering all devices, a spinner next to the show name shows that it is saving, and closing the program shows 'Saving and closing ...'. The quit dialog now opens immediately, even when the server is busy.
- **Much faster fixture library.** Every GDTF file is read only once and remembered on disk (`cache/gdtf_types.json`), so adding a fixture file no longer re-reads the whole library and program starts with a big library are quicker. Large LED fixtures (many pixels) used to take up to 13 seconds each time.
- **3D simulation faster with many fixtures.** Measured with 100 fixtures blinking at 10 Hz on a 146-fixture stage: with *Haze* at 0 % the graphics card needs about 35 ms per picture instead of 437 ms (cones, haze calculation and depth image are skipped); all simple light cones are drawn in one call; fixtures that are off are no longer calculated; ray probes against the stage are limited per picture and re-used; shadow maps are refreshed at most about 9 times per second; the fixture tiles in the control panels redraw at most about 15 times per second and no longer force a new layout for every tile.
- **Updates no longer create a desktop shortcut.** The silent update installed from OpenCue used to add a desktop shortcut every time; now it leaves your desktop alone (an existing shortcut stays). A normal installation still asks.
- **3D panel:** the *Tools / JSON* switch stays at the top of the side bar while you scroll, and the extra *Edit as JSON* button at the end of the tools is gone.

### Fixed

- **Starting with a big show no longer makes the program unresponsive.** Wheels, shutter, gobo and channel data of every fixture type were read from the GDTF file again for each request - four times per type, up to 10 s each for LED bars, and all inside the server's main loop - so with 146 fixtures the server stood still for about a minute after the start and keys, layout changes and faders only took effect afterwards. Now each file is read only once, in a separate helper process, the results are kept on disk (`cache/gdtf_derived/`, so the next start reads nothing) and are prepared in the background right after the show is loaded. The first start after the update reads the files once (about 15 seconds in the background).
- **Big stages no longer freeze the 3D view.** With many fixtures the lighting shaders were compiled in one blocking step; they are now compiled in the background with a short *Preparing lighting …* note, so keys, layout changes and everything else keep working.
- **Light cones and movement of imported fixtures.** Some GDTF files point the beam into the housing while the lenses sit on the other side (for example the ROXX CLUSTER B4-FC: the cone went to the ceiling, the lenses faced down). OpenCue now checks every fixture type and turns only the direction of the beam when that happens. Fixtures whose pan and tilt channels move a *Geometry* instead of an *Axis* (for example the Martin MAC Viper AirFX) now move in the 3D simulation too.

## v2.1.2 – 2026-11-22

OpenCue 2.1.2 completes Chat & Notes (export, backup, REST API) and makes starting immediate again.

### Added

- **Chat & Notes: save as a Markdown file.** A new download button in the panel header saves the open note as its text and the open chat as a transcript sorted by day (`.md`).
- **Chat & Notes in backups and show packages.** *File manager → Back up everything* now includes all chats and notes. In *Export show...* they can be added to the package (off by default, each chat or note separately). Importing never overwrites: an entry that differs from the one you already have comes as a copy; open panels update at once.
- **REST API for chats and notes** (`/api/v1/notebook`) with two new permissions, *Read chats and notes* and *Write chats and notes*: list, read and download chats and notes, create, rename and delete them, send and delete messages, replace a note's text (with `base_rev` as protection against overwriting a change made in the meantime, answer `409`) or just add a line at its end. Everything appears at once in the open panels. The event stream has a new event `notebook`. The REST API guide and the Chat guide describe it in all six languages.

### Changed

- **Start is always immediate again.** OpenCue no longer waits up to 25 seconds for a previous OpenCue that is still closing (added in 2.1.1): the start screen must appear right away, so a second start while the old one is still shutting down shows the "already running" message at once. The message now also says that the old OpenCue may simply not have finished closing yet – wait a few seconds and start again.

## v2.1.1 – 2026-11-22

OpenCue 2.1.1 makes updating and restarting smoother.

### Changed

- **Update window:** the release notes are shown properly formatted (headings, lists, bold) instead of as plain text.
- **"What's new" is now its own window** instead of a guide. After an update it opens once and lists the new features of every version you skipped, in your language; you can open it again any time from *Help → What's new*. The old *What's new* guide was removed.
- **Settings search:** the search box is wider and its suggestions are no longer cut off.

### Fixed

- **Restarting right after closing:** if you start OpenCue again while the old one is still shutting down, it now waits for it and starts normally instead of reporting that it is already running. If the old one really does not finish, the message now says it may still be closing.

## v2.1.0 – 2026-11-22

OpenCue 2.1.0 adds a panel for chatting and taking notes with all the devices connected to your console.

### Added

- **New panel "Chat & Notes":** a messenger and a notebook in one, saved on the server so every device sees the same content.
  - **Chat** between the console, iPads and phones: every message shows who wrote it and when, new messages appear at once everywhere, you see "Name is typing" while someone writes, an unread dot and a short pop-up tell you about new messages in a chat that is not open, and every device chooses its own name. Several chats can exist side by side; chats can be renamed and deleted, single messages can be copied or deleted.
  - **Notes and checklists** in Markdown with a toolbar (bold, italic, underline, strikethrough, heading, bulleted and numbered lists, checkboxes, quote, code). In the finished view you tick checkboxes directly; Enter continues a list; notes save themselves, and you see who else is editing.
  - Chats and notes belong to the program, not to a show: they stay when you load another show. They are files in the data folder (`notebook`). New guide *Chat and notes*.

### Fixed

- Long sub-menus (*View → Open Panel as Window*, *Edit → Add Panel*) are no longer cut off at the bottom on large GUI scales or small screens; they scroll.
- Password fields show dots instead of dashes on some devices.

## v2.0.0 – 2026-11-21

OpenCue roughly tripled in features since v1.0.0. The big ones:

- **A new DMX core:** output (and now also effects and cue fades) runs in its **own process** with its own clock – a steady 40 frames per second even under heavy load.
- **DMX input:** receive Art-Net and sACN from another desk, forward and merge it, use channels as triggers.
- **Remote control that can do everything:** a tablet has the same rights as the console, including all settings, and gets its own file explorer. Server-only mode (`--no-ui`) with a tray icon.
- **Control from outside:** MIDI in and out, OSC, a REST API with a WebSocket stream, custom keyboard shortcuts, a scheduler, offline voice control.
- **Timeline and timecode:** a timeline editor with waveforms, LTC in and out, MIDI timecode.
- **Your own fixtures:** a fixture editor, GDTF Share preview, CSV / Excel patch import.
- **Safe shows:** background backups with crash recovery, global undo, show lock, safe saving.
- **Six languages** (German, English, French, Dutch, Italian, Spanish), in-program guides, error codes with explanations.

### Added

#### Fixtures and library
- **Own fixture editor** (*Library → Own fixture…*): create or copy a fixture type with modes, channels, ranges, wheels, tags, category, picture and 3D model – or start from any installed type. Warns when a change would affect the current show. *(2026-11-16)*
- **GDTF Share: preview before installing** – look at every channel and range of an online fixture before you install it; choose a specific revision, update installed fixtures, see who uploaded each file. *(2026-11-16)*
- **Search by long and short name** and by tag in the fixture library; manufacturer filter that merges different spellings. *(2026-11-16)*
- **Import a patch list from CSV or Excel** with guessed columns and a preview of every row. *(2026-11-10)*
- **DMX Direct channel details:** hover or long-press a fader to see the channel, the readable function name and the named ranges from the GDTF file, with the active range highlighted live. *(2026-11-16)*
- **Round beam preview** on the fixture tiles (colour, brightness, gobo, shutter), and a second, free **layout view** of the fixture list (unlimited area, saved views, pinch zoom on the iPad). *(2026-11-17)*
- **Overlap markers** in the fixture list and a warning when addresses collide; *Add fixtures* continues in the next universe like a console. *(2026-11-15)*

#### Programming, cues and command line
- **Global undo / redo** for the whole show (`Ctrl+Z`, `Ctrl+Y`), also through the menu. *(2026-11-15)*
- **Cue lists:** select and edit several cells and cues at once, copy cues into the same or another list, trigger symbols in the list and in the cue dialog. *(2026-11-15)*
- **Cue triggers:** Go, Follow, Timecode, Audio, MIDI and Time of day. *(2026-11-08 – 2026-11-10)*
- **Cues store the complete state** next to the changes, so a stored cue looks the same later; *Store* saves the difference to the cue before it. *(2026-11-05)*
- **Simple control panel** – big, plain controls for people who only need brightness, colour and zoom. *(2026-11-12)*
- **Operator mode (kiosk):** a device that can only operate – no menus, dialogs or settings – protected by the password. *(2026-11-12)*
- **Own buttons, faders and toggles** with rules (“when … then …”), signals (blackout, active cue, audio, timecode …) and an action mode that only types the command into the command line. *(2026-11-04)*
- **Command console window** (`Ctrl+F`) and **any panel as a free window**; command keys that fill the panel exactly; panels that can be made very small. *(2026-11-04)*
- **`At At`** switches everything on (dimmer 100 % and white). *(2026-11-05)*

#### Effects and audio
- **Audio analysis:** a panel that shows spectrum, level and the hits of bass, snare and hi-hat – with **33 audio effects** and an *Audio* cue trigger. *(2026-11-04)*
- **96 default effects**, sorted into *Basic* and *Advanced*, each with fitting controls, labels and hints; a large effect picker with categories and tags; search and tags in the effect list. *(2026-11-04)*

#### DMX output and input
- **Separate DMX output process** – Art-Net, sACN and USB-DMX are sent by their own process with a precise clock; effects and cue fades are calculated there too, so a hanging window cannot disturb a fade. Measured with 83 fixtures in 4 universes under heavy load: 40 frames per second in every phase. *(2026-11-15)*
- **DMX input** (*Controls → DMX input…*): receive Art-Net and sACN, forward or merge into the output (highest wins or replace, per channel range, several sources, sACN priority), use channels as triggers (button or fader, with *Learn*), live view of every source. *(2026-11-17)*
- **ArtPollReply:** OpenCue announces itself as an Art-Net device, so other desks and tools find it without typing the IP address. *(2026-11-17)*
- **Plug and play:** Art-Net devices are found automatically; an Enttec-compatible USB-DMX adapter is recognised by itself. *(2026-11-10)*
- **Nothing leaves the computer on the first start** – Art-Net is off until you switch it on, no network port is opened except on this computer. *(2026-11-04)*

#### Remote control and network
- **A remote device can do everything the console can** – all settings included – which is what server-only mode needs. The remote also gets the **OpenCue Explorer**: browse, download, upload, rename, duplicate and delete files in the data folder, and pick a storage folder. *(2026-11-17)*
- **Server-only mode** (`--no-ui`) with a tray menu, **start with Windows**, more start options (`OpenCue.exe --help`), administrator detection and a Windows firewall rule you can create from the settings. *(2026-11-10)*
- **Secure page (HTTPS)** with an own certificate authority (fixes the iPad home-screen app), an offline page with server choice, an installable web app with its own icon, and a revised guide page. *(2026-11-15)*
- **Network name `opencue.local`** (mDNS) and one master switch for remote access. *(2026-11-04)*
- **Lock screen** and **password-protected lock mode**; remote devices can log out. There is no default password – you choose your own. *(2026-11-11)*

#### Control from outside
- **MIDI in and out:** controllers, keyboards and pads trigger commands; LED and motor-fader feedback, templates, learn mode, MIDI timecode, show control. *(2026-11-05)*
- **OSC:** receive and send, built-in addresses, a feedback channel that reports the state back to the device. *(2026-11-10)*
- **REST API with tokens** (`/api/v1`): read and control nearly everything the window can, edit the whole show, a WebSocket stream for hardware such as an ESP32, status views for simple displays, per-token permissions. *(2026-11-04)*
- **Custom keyboard shortcuts:** several keys, keys of one specific keyboard, quick-start chips, and the program's own shortcuts are editable. *(2026-11-10)*
- **Schedule:** run commands at a time of day, on weekdays or once on a date. *(2026-11-10)*
- **Voice control:** say the wake word “OpenCue”, then a command – offline; **dictation** into the AI chat. *(2026-11-05)*
- **AI assistant** that runs on your own computer (Ollama): chat, and a work mode that can look at and change the show with permissions you set. *(2026-11-04)*

#### 3D stage
- **VR mode** for the 3D simulation (WebXR), **screens** (images and videos on the stage), **camera sync** between devices for presentations. *(2026-11-04)*
- **A Tinkercad-style editor:** move, scale, rotate and lift several objects together, edge handles, copy and paste poses, align and distribute, import several own STL / OBJ models at once, resizable side bar. *(2026-11-10)*
- **The stage as JSON** to copy, edit and re-apply; a **PDF plan** with real rotations. *(2026-11-10)*

#### Timecode and media
- **Timeline editor:** cues as markers on a time axis, one track per media player with its waveform, command tracks, winding and markers. *(2026-11-14)*
- **LTC in and out** and **MIDI timecode**; one place (*Settings → Timecode*) decides who leads the clock. *(2026-11-14)*
- **Media library** with images, videos and audio; one place for media in the file manager; smoother playback on the iPad. *(2026-11-04)*

#### Shows, files and safety
- **Background backups and crash recovery:** the current state – also unsaved changes – is saved every 15 minutes; after a crash OpenCue offers to restore it. *(2026-11-10)*
- **Lock a show** so it can never be overwritten; a careful quit dialog when a show cannot be saved. *(2026-11-10)*
- **Safe saving:** shows, settings, layouts and stages are written to a neighbouring file first and then swapped in – a crash cannot leave half a file. *(2026-11-17)*
- **`.ocshow` files** (double-click opens them), **recent shows**, **export and import of all settings**, **print / PDF documentation** of the show (patch list, DMX map, groups, plan, cue lists). *(2026-11-10)*
- **Question before anything is lost:** every delete, every unsaved change and every cancelled input asks first – one wording, one look, and switchable in *Settings → Defaults*. *(2026-11-16)*

#### Interface, settings and help
- **Settings, simpler:** grouped categories, search across all categories with a result list, explanations collapsed behind a small (i), changes counted on the *Save* button, per-category reset. *(2026-11-17)*
- **One size system for all dialogs** – five types relative to the window, so big dialogs also fit small screens. Colour themes where **every colour** (including the status colours) can be changed. *(2026-11-17)*
- **Toolbar settings, tooltips for everything, keyboard shortcut overview (`?`), `F5` reload, `Ctrl+F5` full reload.** *(2026-11-12)*
- **Six languages:** German, English, French, Dutch, Italian, Spanish – the interface in all six, all 19 guides (`F1`) in all six languages. The in-program AI guide answers from the translated texts in the language you use. *(2026-11-11 – 2026-11-17)*
- **The error window speaks your language:** titles, explanations and buttons of the start-up and crash window appear in the language of OpenCue (English if it cannot be read); the text copied by *Copy details* stays English for bug reports. *(2026-11-18)*
- **Guides inside the program** (`F1`, offline, with search), **error codes** with a page that explains each one, a log folder and *Report a problem*. *(2026-11-08)*
- **Safe start:** one OpenCue at a time, a clear error window instead of a silent failure, a small start screen that appears at once. *(2026-11-08)*
- **A welcome dialog** at the very first start. *(2026-11-10)*

#### Installer and program
- **The installer speaks six languages** (English, German, French, Dutch, Italian, Spanish): it offers the language at the start, picks Windows' language by default, and OpenCue starts in the language you chose. *(2026-11-17)*
- **A clear options page** – start menu and desktop shortcut up front, and a collapsible *Advanced* section: open `.ocshow` files with OpenCue, start with Windows (also without a window, for a computer that only outputs DMX), download the voice model, check for updates at start. A summary page lists everything before anything is installed. *(2026-11-17)*
- **Voice model on demand:** the 41 MB model is no longer part of the program; *Settings → Trigger word* has a *Load voice model* button with progress (verified download, never a half-finished model), and the installer can fetch it at the first start. *(2026-11-17)*
- **Version 2.0.0.** *(2026-11-17)*

### Changed
- **Every source file carries the same licence header** (copyright and SPDX line), and comments no longer point to files that are not part of the published source. *(2026-11-19)*
- **Plain English messages instead of German ones** in the file, fixture, media, camera and 3D-model checks of the server – the interface shows them translated by their code, the English text is the fallback. *(2026-11-18)*
- **Releases build themselves on GitHub:** a new version number triggers a workflow that builds the program and the installer, tests both (start, guides in six languages, API, install and uninstall in all six installer languages) and prepares the release with checksums as a draft. *(2026-11-19)*
- **More plain-English messages** for DMX ports, network name, https address, file restore and deleting – shown in English until translated, instead of German. *(2026-11-19)*
- **The installer is 89 MB instead of 146 MB:** the voice model loads later, the second copy of ffmpeg inside the video library and an unused download component are gone, and the installer compresses harder. *(2026-11-17)*
- **A sturdier program file:** `OpenCue.exe` carries an explicit manifest (never asks for administrator rights, sharp on high-resolution screens, long paths, Windows 10 / 11). *(2026-11-17)*
- **The build script** checks its own result (manifest, version, no unwanted packages, installer size limit), writes a checksum file and runs unchanged on GitHub Actions. *(2026-11-17)*
- **Remote access** is described as a *secure page*, the network name sits next to the ports, and the default Art-Net target is *automatic*. *(2026-11-04)*
- **The cue list marks the selection clearly**, the cue dialog is tidier (name and number side by side, triggers as symbol buttons). *(2026-11-15)*
- **Settings take effect only with *Save*** – nothing is sent to the server before. *(2026-11-04)*
- **Wake word and dictation** are two separate settings pages. *(2026-11-05)*
- **Position → Fine** is a swipe strip, and there is a digital joystick as a third view. *(2026-11-04)*
- **Unsaved-change marks in the programmer** are small and quiet and lead all the way to the changed fader. *(2026-11-04)*
- **The DMX output keeps priority over the API** and the interface (higher thread priority, steadier timing). *(2026-11-10)*

### Fixed
- **A stalled API WebSocket client can no longer hold a connection slot forever:** if a client stops reading for 5 seconds it is disconnected, so the other connections are unaffected. *(2026-11-18)*
- **Other web pages could talk to OpenCue:** a page open in a browser on the same computer could reach the console without a password (also over the WebSocket, which has no browser protection). The password-free local connection now accepts only requests that really come from the program or from `127.0.0.1` / `localhost`. *(2026-11-17)*
- **The last installer page** cut off the text of *Start OpenCue*; the dialog for an existing installation shows its heading properly. *(2026-11-17)*
- **Art-Net timing:** about 37 frames per second instead of 40 and gaps up to 185 ms are gone. *(2026-11-15)*
- **Deleted fixtures** no longer stay in every cue; **Backspace in an input field** no longer deletes the selected fixtures. *(2026-11-15)*
- **Deleting an effect or an effect group** showed the wrong dialog and could delete the wrong item. *(2026-11-15)*
- **Saving a show is atomic**; `app_config.json` can no longer be lost by a half-written file. *(2026-11-10)*
- **Access tokens** no longer appear in the log file or in *Copy details*. *(2026-11-10)*
- **Voice control:** the microphone opens reliably after the program start. *(2026-11-05)*
- **iPad:** a red rectangle instead of the struck-through microphone, a red icon in the top bar, overlapping icons on narrow screens, stuttering audio and video in the media player. *(2026-11-12)*
- **A cue stored once looked different later**, and `Update` kept effects that were no longer running. *(2026-11-05)*
- **Quitting** could end the process in the middle of the clean-up. *(2026-11-10)*

## v1.0.0 – 2026-10-19

The first complete version.

- **Control:** fixture list with patching (GDTF library including GDTF Share), programmer with a fixture control panel (dimmer, colour, position, beam, focus, DMX direct), groups, presets and variables, command line.
- **Cues and effects:** cue lists with fades, follow and timecode triggers, executors, an effect engine with its own script language and an effect studio.
- **DMX output:** Art-Net, sACN and USB-DMX (Enttec DMX USB Pro) with a dedicated output thread; blackout and grand master.
- **Interface:** free panel layouts with edit mode, colour themes, German and English, a file manager for shows, layouts, 3D stages, effects, themes and fixtures.
- **3D simulation:** stage builder, fixtures with their real GDTF models, live DMX light, aiming at a point from the fixture control panel.
- **Timecode, media and streams:** global timecode, video and audio player, camera panel (also cameras on the main computer through ffmpeg).
- **Remote control:** tablets and phones in the local network (password, QR code, installable web app), switchable at runtime.
- **Updates and installer:** an update check at startup (switchable), a Windows 10 / 11 installer.

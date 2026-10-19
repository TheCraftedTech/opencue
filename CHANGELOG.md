# Changelog

All notable changes to OpenCue. The version number lives in `app/version.py`; each release gets a `vMAJOR.MINOR.PATCH` tag.

## v1.0.0 — 2026-10-19

First release.

- **Control:** fixture list with patching (GDTF library incl. GDTF Share), programmer with fixture control panel (dimmer, colour, position, beam, focus/zoom, gobo/prism/shutter), groups, presets, variables.
- **Cues and effects:** cue lists with fades, follow and timecode triggers, executors, effect engine with its own effect script language and studio, command line in dot2 style with autocomplete.
- **DMX output:** Art-Net, sACN and USB DMX (Enttec DMX USB Pro) with a dedicated output thread; blackout and grand master.
- **Interface:** free panel layouts with edit mode, themes, German and English, file manager (shows, layouts, 3D stages, effects, themes, fixtures), show export/import as ZIP.
- **3D simulation:** stage builder, fixtures with their real GDTF models, live DMX light, point-at-target aiming from the fixture control panel.
- **Timecode, media and livestream:** global timecode, video/audio player panel, camera panel (also cameras on the main device via ffmpeg).
- **Remote control:** tablets and phones in the local network (password, QR code, installable web app), switchable at runtime.
- **First start:** the demo show `Default_1` opens by itself (fresh installation only), no stage is shown until one is created, new stages are named `Stage 1`, no Windows firewall question (sACN is off by default and opens its network port only when switched on; remote access is off by default), a demo show (`Default_1`) and an example layout are copied from `defaults/` once, the built-in Generic dimmer / RGBW par / moving head are always available. No GDTF Share files are bundled (their terms do not allow redistribution); fixtures are downloaded by the user from the library.
- **Updates and installer:** OpenCue checks GitHub for new releases at startup (switchable; offline it stays silent) and offers *Install now / Remind me later / Skip this version*; *Help -> Check for Updates...* checks on demand. The Inno Setup installer lets you choose the program folder and the data folder, creates shortcuts, updates and uninstalls cleanly.
- **Packaging:** Windows 10/11 build with PyInstaller (folder build), Inno Setup installer, *Help → About OpenCue* with version, licence and third-party notices; GNU GPL v3 or later.

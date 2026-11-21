# What's new

The most important changes of this version at a glance. The complete list is in `CHANGELOG.md`; each topic has its own guide (Help → Guides).

---

## A new DMX core

- **DMX output runs in its own process** – together with effects and cue fades. A busy window or a slow tablet can no longer disturb a fade: a steady 40 frames per second, even under heavy load.
- **DMX input:** receive Art-Net and sACN from another desk, forward and mix it, use channels as triggers (*Controls → DMX input…*). OpenCue also announces itself as an Art-Net device.

## Remote control that can do everything

- A tablet has the **same rights as the console, all settings included**, and its own **OpenCue Explorer** for files. **Server mode** without a window (`--no-ui`) with a tray icon and start with Windows.

## Control from outside

- **MIDI** in and out, **OSC**, a **REST API** with a WebSocket stream, **custom keyboard shortcuts**, a **schedule** and offline **voice control**.

## Timeline and timecode

- A **timeline editor** with waveforms and command tracks, **LTC** in and out, **MIDI timecode**.

## Fixtures

- An **own fixture editor**, a **preview of GDTF Share fixtures** before installing, and **import of a patch list from CSV or Excel**.

## Safe shows

- **Undo / redo**, **backups** in the background with crash recovery, a **lock** for finished shows, **safe saving**, and a question before anything can be lost.

## Look and help

- **Six languages**, dialogs in five consistent sizes, **settings** with a search across all categories and explanations behind a small **(i)**, colour themes where every colour can be changed, and **guides** with `F1`.

Everything stays off by default; you decide what is switched on.

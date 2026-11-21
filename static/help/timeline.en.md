# Timeline editor and LTC

With the **timeline editor** you place cues and commands graphically on a time axis - with the waveforms of your songs underneath. With **LTC** OpenCue runs in time with an outside source (a player, DJ or show software, a console) or sends a clock to other devices itself. Everything builds on the **global timecode**.

---

## 1. The idea in one minute

- OpenCue has **one** clock, the **timecode** (panel *Timecode*, display at the top of the toolbar). It runs, stops, jumps - on all devices at the same time.
- Things happen at certain times of this clock: a **cue** with the trigger *Timecode* starts, a **command** of a command track is executed, a **media player** starts its song (*start time*). This only happens when the clock runs **forward through** the time - jumping and running backwards trigger nothing.
- The clock can be led by **three sources**: this computer (you press Start), **MIDI timecode** (*Settings → MIDI*) or **LTC** (*Settings → Timecode*). Whoever is there first leads.
- The **timeline editor** shows all of this on a time axis and lets you set and move it comfortably - instead of typing every time in the cue dialog.

---

## 2. Opening the timeline editor

- As a panel in the layout: *Edit → Add panel → Media → **Timeline editor*** (best wide).
- Briefly as a window: *View → Panel as window → **Timeline editor*** (all panels are listed there, for example also **Simple control**).

---

## 3. What it looks like

- **Ruler** at the top: click or drag jumps to that time.
- **One track per cue list**: every cue with the trigger *Timecode* is a **marker** with number and name. The list name on the left selects it (for the tray and "Set cue here").
- **Command tracks** (red / pink): commands of the command line at times - see section 6.
- **Audio tracks** at the bottom: **by themselves** for every song that a media player plays along with the timecode, with a **waveform** and thin lines at every marker - you see whether something sits exactly on the beat (section 5).
- **Tray** at the very bottom: the **cues without a time** of the selected list.
- The yellow **playhead** is the global timecode.

---

## 4. Editing markers and winding

| Action | How |
|---|---|
| **Move** a marker | drag it sideways with mouse or finger; it snaps to the **grid** (hold **Shift** = no grid) |
| **Fine-move** a marker | click the marker, then `←` / `→` (one grid step; `Shift` = ten times as much) |
| Put a cue **without a time** on the timeline | drag it from the **tray** onto the track - or select the chip and press **Set cue here** |
| **Grid** | *off*, 10 ms, frame (25 fps), 0.1 s, 1 s |
| **Zoom** | keys `+` / `−`, Ctrl + mouse wheel, **two fingers** (iPad); *Show everything* (`F`) |
| **Follow** | the view scrolls along with the playhead |

**Winding** works in all ways:

| Key / button | Effect |
|---|---|
| **Drag** the ruler or the waveform | jumps there continuously (the sound follows) |
| Buttons **±5 s** | five seconds back / forward (clicking quickly adds up) |
| Buttons **previous / next marker** (`[` / `]`) | jumps to the next cue or command time |
| `←` / `→` (focus in the panel) | 1 s; with `Shift` 10 s; with `Alt` one frame (40 ms) |
| `Home` / `End` | to the start / to the end of the markers |
| `Space`, `L`, `K`, `J` | play / pause · forward · pause · play **backwards** |
| Button **Reverse** | plays the timecode backwards (triggers no cues and commands) |

---

## 5. Audio: by itself from the media players

You do not have to choose a song in the timeline. The timeline looks by itself at **what is played along with the timecode**:

- Every **media player** in mode **Timecode** with a chosen medium and its **start time** appears as an audio track: with name, **waveform** and a **start marker** (note symbol) at the start time. A player on **another device** (for example at the main computer while you work on the iPad) and the **screens of the 3D simulation** appear too.
- **Dragging the start marker** (or double-clicking it and typing the time) changes the **start time of the media player** - the song then begins at the new time.
- **Add audio ...** creates an **own audio** of this timeline (it runs in sync with the timecode) in case no media player is set up yet. The loudspeaker button only mutes these own audios. On the iPad the browser needs a touch of the panel before sound is allowed.
- OpenCue calculates the **waveform** once with the bundled *ffmpeg* (one value every 10 ms) and remembers it. If ffmpeg is missing, the track says so.
- With **LTC** the same applies: the media players follow the timecode no matter who leads it - so the audio tracks always show what runs at which time.

---

## 6. Command tracks

A **command track** executes **commands of the command line** at times of the timecode - independent of the cues, for example `Blackout Off` at 1:30, `Cuelist Show Go` at 2:00 or `Effect Off` at the chorus. It belongs to the **show** (saved and exported with it).

- **New command track**: button **+**. There may be several (for example "Light", "Fog", "Video"); a double-click on the name renames, the **×** deletes (click twice).
- **Adding a command**: button **Command here** (or `C`) puts a command at the current time on the selected track - or **double-click** the track at that place.
- A small window asks for **time** and **command**; `Enter` accepts. Every marker can be **dragged**, moved with the arrow keys, edited again with a **double-click** and deleted with `Del`.
- The **server** executes the command when the timecode runs **forward through** its time - exactly like cues (also with LTC / MIDI timecode). It appears in the command history. A jump skips it.
- In **operator mode** command tracks cannot be changed; they run as usual.

---

## 7. Setting cues with the music (recording)

Like on a console, only graphical:

1. Create your cues (cue list) - their time may still be empty. They appear in the **tray**.
2. Set up a **media player** with your song (mode Timecode, start time 0) - the waveform appears by itself.
3. Choose the cue list and the first cue in the tray.
4. Start playback (Space) and press **Set cue here** (or `Enter`) at every entrance: the selected cue gets the **current time**, then the **next** cue is selected.
5. Then touch up in peace: drag markers onto the waveform, let them snap.

Tip: with *grid 1 s* or *frame* the markers land on round times, with *off* on the exact millisecond.

---

## 8. LTC: timecode as an audio signal

**LTC** (Linear Timecode) is an audible signal - it sounds like noise - that carries the time of day. It sits on one channel (usually the left), the music on the other. *Settings → Timecode* shows at the top **who currently leads the clock** (this computer, MIDI timecode or LTC) and has two areas:

**Input: read timecode (Follow LTC)**

1. Switch on **Follow LTC**, choose the **audio input** (line-in, USB interface or the *system sound* of an output device). To try it out there is the **test signal** (25 frames/s, no device needed).
2. Choose the **channel** (left / right / mix), **Save**. Below you see live **"Signal found: 00:01:12:05 · 25 fps"** and a level bar.
3. As soon as a valid signal arrives, the **global timecode runs along**. All cues, commands and media players follow. **Pause or stop of the source** stops the timecode here too, a **jump** of the source is followed.
4. **24, 25, 29.97 (drop frame) and 30 frames per second** are recognised.
5. To play yourself, switch **Follow LTC** off again.

**Output: send timecode (Send LTC)**

OpenCue becomes the clock for other devices: when you start the timecode (for example Play in the *Timecode* panel), **LTC comes out of an audio output** - a player, console or recorder can run along.

1. Switch on **Send LTC**, choose the **audio output** and **channel** (*both*, *left only* or *right only* - use one channel if the other carries music).
2. Set the **frame rate** (24 / 25 / 29.97 drop frame / 30) and the **level** (strong but not clipping; many devices expect line level), **Save**.
3. It is sent **only while the timecode runs forward**; when it stands or runs backwards the output is silent. If you jump, the signal starts at once at the new time.
4. If OpenCue itself follows an LTC or MIDI source, the clock is passed on as well.

**If nothing arrives:** check the level bar (too quiet?), the channel (left / right), whether the input is used by another program.

---

## 9. Notes

- An **LTC or MIDI source leads** the clock: Start / Stop in the timecode panel are overruled by the source while it runs.
- The times belong to the **cues**, the **command tracks** and the **media players** of the show and are saved with it; the timeline editor is only the tool for it.
- *Settings → Inputs & outputs* shows in the group **Timecode** at a glance: who leads the clock, LTC read / send, MIDI timecode.
- More about the sources: guide **MIDI** (MIDI timecode), guide **Remote access** (iPad), panel **Timecode** (start, pause, jump, speed), **media player** (start time).

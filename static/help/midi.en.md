# MIDI

With **MIDI** you control OpenCue from a controller, keyboard, pads or music software – and OpenCue can send MIDI itself. A key, fader, knob or program change triggers a **command-line command**, just like a custom keyboard shortcut (see *Keyboard shortcuts*) – with faders on top.

The mapping belongs to the **program**, not the show: it applies to all shows and is stored in the app configuration. You reach it in four ways: the **MIDI icon** at the top right of the toolbar, **Settings → Controls → MIDI**, **Controls → MIDI mapping …** and – for keys and faders of a panel – **Assign MIDI …** in the panel's properties. The MIDI device is attached to the console computer; editing the list also works from a tablet, learning and the monitor only at the console computer.

---

## 1. What is MIDI? (briefly)

MIDI does not send sound, but small **messages**. You need three kinds:

| Message | What your device reports | In OpenCue |
|---|---|---|
| **Note** | A key (piano key, pad) is pressed or released. Each has a number, e.g. 60 = **C4** (middle C), and a **velocity** (0–127, how hard it was hit). | Types **Key**, **Switch**, **Hold** – or **Fader** (the velocity becomes the value) |
| **Controller (CC)** | A fader or knob. Each has a number (0–127) and a value 0–127. | Types **Fader** (faders, pots) or **Encoder** (endless knobs) |
| **Program change** | A "program" with a number is chosen. | Type **Key** (e.g. program 3 = `Go Cue 3`) |

Every message also has a **channel** (1–16) so that several devices can share one line. If you do not know: leave it on **All**.

---

## 2. First steps

1. Plug the MIDI device in via USB (Windows recognises it on its own – class-compliant devices need no driver).
2. Click the **MIDI icon** at the top right (or **Controls → MIDI mapping …**). The top shows which devices are recognised. The **monitor** at the bottom shows live everything your device sends – press a key and look: `Note On C4 (60) · 100`.
3. **New MIDI mapping** → click the signal field in the row → **press or move** something on the device → **Apply**. The signal is learned.
4. Enter the **command** on the right, e.g. `Go`. Done – the key now triggers `Go`. The row lights up briefly when it triggers.

The mapping is saved at once. The **MIDI on** switch at the top turns everything off (OpenCue then listens to no device).

**The toolbar icon** shows the state: **green** = a device is ready, **grey** = no device connected, **yellow** = a device cannot be opened (usually another program holds it), **red and crossed out** = MIDI is off. A click opens the mapping; the tooltip names the recognised devices.

**Settings → Controls → MIDI** (like all settings with *Save*): use MIDI, **which devices** are used (every connected device has a switch – a deselected one is never opened), the **output**, **timecode (MTC)** and **tempo from the MIDI clock** (section 5b) and buttons to the mapping.

Under **Settings → Inputs & outputs → MIDI** you see the recognised devices, whether they are being read right now, the output and how many mappings are active.

---

## 3. The types

| Type | Effect | Example |
|---|---|---|
| **Key** | The command runs when the key is pressed. | Pad 1 → `Go`; Pad 2 → `Back`; Pad 3 → `Clear` |
| **Switch** | Every press switches between the **command** and the **off command** (empty = the same command both times). | `Blackout` (toggles by itself); or `Effect Rainbow` / `Effect Off` |
| **Hold** | The **command** runs on press, the **release command** on release ("flash"). | `Group front At Full` / `Group front At 0` |
| **Fader** | The command gets the value as `{value}`, scaled to the range **From … To** (also **Invert**). | Fader → `Master {value}` (0–100); Fader → `Cuelist main Fader {value}` |
| **Encoder** | For **endless knobs**: every step runs as `{delta}` (with a sign, times **Step**). The encoder type (usual / sign bit / centre 64) is set in the row. | Knob → `Pan {delta}` (select fixtures first) |

**Placeholders in the command:** `{value}` (fader value in the range From–To), `{delta}` (encoder steps, e.g. `+1` / `-2`), `{velocity}` (velocity 0–127), `{note}` and `{number}` (note / controller / program number), `{channel}`, `{raw}` (raw value 0–127).

**Start / Stop / Continue (transport):** You can also choose *Start*, *Stop* and *Continue* of the music software as the signal (type in the learn dialog; they have neither channel nor number). Example: Start → `Timecode Play`, Stop → `Timecode Stop`.

**Pickup:** A **fader** without a motor often stands differently from the value in the program. With **Pickup** the fader only takes over once it has reached or crossed the current value – no jump when you first touch it. If the value was changed elsewhere in between, it has to catch it again. This works for `Master {value}`, `Fader {value}`, `Cuelist <name> Fader {value}` and the brightness or a beam attribute of a fixture, group or the selection (`Fixture 5 At {value}`, `Group front At {value}`, `At {value}`, `Zoom {value}`); other commands take over at once.

**More types:** *Double click* (the command runs on the second press within 0.4 s) and *Long press* (it runs when the key is held for the set time - e.g. 600 ms; releasing earlier cancels). For faders you choose a **curve**: *Linear*, *Slow start* (fine values at the bottom) or *Fast start*. **Aftertouch** (pressure on a held key) and **channel pressure** can be mapped as faders too. **One fader, several commands:** separate them with a semicolon, e.g. `Master {value}; Group front At {value}`.

**Feedback to the device (LEDs, motor faders):** In the row choose a state of the console under **Feedback**: *Blackout*, *Master*, *Selection present*, *Cue active*, *Timecode running* or *Cue list fader*. OpenCue sends it as note / controller / pitch bend **with the same number and channel** as the signal to the output that has the same name as the device - on a pad controller the LED lights up, a motor fader moves along. For on/off states you set **LED on / LED off** (the velocity; on pads with colours it is the colour). It is only sent when the value changes, and after a device is plugged in everything is sent again.

More examples:

| Device | Mapping |
|---|---|
| Program change (e.g. on a keyboard) | Key, command `Go Cue {number}` – program 5 jumps to cue 5 |
| Key with velocity | Fader (source Note), command `Group front At {value}`, From 0 To 100 – the harder, the brighter |
| Pitch bend wheel | Fader, command `Master {value}` |
| Fader bank | one row per fader (CC 1…8): `Fixture 1 At {value}`, `Fixture 2 At {value}` … |

Triggers: a key triggers on **press**. A CC used as a key (the pads of many controllers) triggers at a value **of 64 or more**. A fader sends at most **about 40 commands per second** (fast movements are merged, the last value always arrives).

---

## 3b. Copy rows, export, import, from a panel

- **Copy** (icon next to the bin): duplicates a row with type and command, the signal stays empty – handy for a series of similar faders (fader 1 … 8).
- **Export / Import** (bottom of the dialog): saves the mapping as a file (`opencue-midi-mapping.json`) or reads such a file. On import the rows are **added** – nothing is replaced.
- **Template …** (bottom of the dialog): creates a **series** of rows - *Fader bank* (fixtures 1...8), *Cue pads*, *Transport keys* (Go, Back, Pause, Blackout), *Master & blackout* - and then lets you **press or move the controls one after the other** ("Signal 2 of 8", *Skip* goes on, Cancel ends the series). This maps any controller without knowing numbers.
- A **search field** above the list (signal, command, device) and the **arrows** on every row (move up / down; disabled during a search).
- **Jump to this cue with a MIDI key …** in the dialog of a **cue** (*Edit cue*): creates a mapping `Cuelist "<list>" Go Cue <number>` and learns the signal - the cue then starts on a key press, **at any time** (a free "jump" key). For a cue that waits for its signal inside a sequence see the cue trigger **MIDI** (section 5c).
- **Assign MIDI …** in the properties of a **button, switch or fader**: creates a mapping with the panel's command (switch: on and off command, fader: with From/To) and learns the signal right away. The mapping stays even if you delete the panel.

---

## 4. Applies to, Run, History

- **Learn signal → Applies to:** *All devices* (any device sending this signal triggers) or *Only this device* (e.g. when two controllers send the same numbers).
- **Run** off: the command is only **written into the command line**, not run (for checking or completing it).
- **In history:** the command appears in the command line history (all windows see it).
- There is no check against duplicate signals: two rows with the same signal **both** trigger (the learn dialog warns you).

**Safety:** `Delete …` and commands containing `Overwrite` **never run by MIDI** (an accidentally hit key must not destroy data). `Clear Clear` is allowed.

---

## 5. OpenCue sends MIDI: the `Midi` command

The `Midi` command sends to the **output** (chosen at the top of the dialog; **Automatic** takes the first real device, otherwise the Windows synthesizer "Microsoft GS Wavetable Synth" – so you hear something right away):

| Command | Effect |
|---|---|
| `Midi Note 60` | Play note C4 (60), velocity 100, off again after 0.3 s |
| `Midi Note 60 90 Ch 2 Len 1` | Note 60, velocity 90, channel 2, for 1 second |
| `Midi On 60 100` / `Midi Off 60` | Note on / off individually (stays until you send `Off`) |
| `Midi CC 7 100` | Controller 7 to value 100 |
| `Midi PC 3` | Program change 3 |
| `Midi MSC Go 5 List 2` | Send **MIDI Show Control** (`Go`, `Stop`, `Resume`, `AllOff`, `Restore` ...; optional `List <n>`, `Device <0-127>`) |
| `Midi Panic` | All notes off (all channels) |

Can be combined with buttons, keyboard shortcuts, cue commands or **voice control** ("OpenCue, MIDI note sixty") - e.g. a cue that triggers a sound in your music software. Also through the **REST API**: `POST /api/v1/command` with `Midi Note 60`; `GET /api/v1/midi` returns devices and state.

---

## 5b. Time and tempo from the music software (MTC and MIDI clock)

Two switches under **Settings → Controls → MIDI** make OpenCue follow music software (DAW) or another device. Both react **only to the matching format and only when something valid really arrives** – otherwise nothing happens. While one is on, the devices in use stay open.

**Timecode from MIDI (MTC).** If the software sends *MIDI Timecode* (MTC, 24 / 25 / 29.97 / 30 frames per second), the **global timecode** runs in step with that time: cues with the "Timecode" trigger, the timecode player and the panels follow. Only a **gap-free, plausible stream** is taken (three matching groups, values in the valid range); noise, backwards running and foreign signals are ignored. If your own clock drifts by more than 0.1 s it is set to the right time. **If the stream stops** (software stopped, cable pulled), the timecode stops. If the software jumps to a position while stopped (*full frame*), the timecode jumps too. A timecode you started by hand is **not** stopped when MTC is absent; while MTC runs, MTC has priority. The settings show the received time and the frame rate.

**Sending: OpenCue as the time source.** *Send timecode (MTC)* sends the global timecode as MIDI Timecode (frame rate 24 / 25 / 29.97 / 30; precisely timed quarter frames, a full-frame message on jumps) to the chosen output. *Send MIDI clock* sends *Start* / *Stop* and the clock at the tempo of the Audio panel while the timecode runs.

**Receive show control (MSC).** With *Receive show control* and a **device ID** (0-127, 127 = all), GO, STOP, RESUME, ALL_OFF and RESTORE (also with cue and list number) control the cue lists - e.g. from a show program or desk. The command `Midi MSC ...` sends them.

**Tempo from MIDI clock.** A **steady MIDI clock** (24 pulses per quarter note, 30 to 300 BPM) sets the tempo as the fixed tempo of the Audio panel (like the command `BPM 128`) and follows tempo changes. Map *Start*, *Stop* and *Continue* as signals (see above).

To try it without software: a MIDI timecode generator (there are free programs and web pages) sends through a virtual MIDI port (under Windows e.g. *loopMIDI*) – both sides choose the same port.

---

## 5c. Cue trigger: MIDI

Besides *Go*, *Follow*, *Timecode* and *Audio* a cue can have the trigger **MIDI**: it then waits for **one MIDI signal** and fires when it arrives – a **sequence that you play with a keyboard, a pad or a foot controller**. In the cue dialog (*Edit cue*) choose the trigger *MIDI*, then pick the **signal** (or press **Learn signal** and hit the key – it is filled in for you; learning works at the console computer). In the cue list you can also type it into the trigger cell (`midi note c4`, `midi cc 20 64`, `midi pc 5 ch 2`) or use the command `Cue 3 Trigger Midi Note 60` (see *Command line*).

| Signal | The cue fires … |
|---|---|
| **Note** (key / pad), number 0–127 | … when the key is pressed (Note On; releasing does nothing). |
| **Controller (CC)**, number 0–127, threshold 1–127 (default 64) | … when the controller value **rises to** the threshold from below. A pad sent as CC (127) fires at once; a fader fires when it is pushed past the threshold, and again after it was pulled back below and pushed up again. |
| **Program change**, number 0–127 | … when this program is chosen on the device. |

Every signal can be limited to one **channel** (1–16); *Any* accepts all channels and all devices.

How it works:
- Like the audio trigger, the cue fires when it is the **next cue** of a running list: first start the list with *Go*, then the following MIDI cue waits for its signal. Afterwards the next cue (if it also has a MIDI trigger) waits in turn – you can chain a whole sequence to keys or pads.
- A short pause of 0.25 s after each trigger keeps one hit from starting two cues.
- **MIDI must be switched on** (*Settings → MIDI → Use MIDI*, or the switch at the top of the mapping dialog). OpenCue opens the MIDI devices by itself as soon as any cue has a MIDI trigger – you do not need a mapping row for it – and releases them again when no cue needs MIDI any more. Devices you have unticked under *Settings → MIDI* stay closed.
- The trigger works for every cue list on its own, and it also works from the remote devices' point of view: the signal comes from the **console computer**'s MIDI devices.
- **Difference to the mapping** (section 3): a mapping row runs a command **at any time** (e.g. `Go`, or `Cuelist "Main" Go Cue 5` = jump there). The cue trigger is part of the **cue itself** and only counts while the cue is next in line. Both can be used together; a signal used by both does both.

---

## 6. When it does not work

| Problem | Solution |
|---|---|
| Device not recognised | Another USB cable/port; **Settings → Inputs & outputs** refreshes the devices every few seconds; many devices need a moment after plugging in. |
| "in use?" at the device | **Another program** (music software, the manufacturer's editor) has opened the device – under Windows usually only **one** program can read it. Close the other program, then switch **MIDI on** off and on again. |
| Monitor shows nothing | The monitor only runs while the dialog is open. Is **MIDI on** switched on? |
| A cue with the trigger **MIDI** never fires | It fires only when it is the **next cue** of a **running** list (start the list with *Go* first). *MIDI on* must be set, the device must not be unticked in *Settings → MIDI*, and number, channel and type must match what the monitor shows when you press the key (use *Learn signal* in the cue dialog). |
| Key triggers nothing | Check channel / device under "Applies to"; test the command by hand in the command line; does the row light up in the dialog? (then the signal arrives and the command is the problem). |
| Fader jumps | Switch **Pickup** on in the row (master and fader): the fader only takes over once it has reached the current value. |
| Music software and OpenCue should connect | Windows needs a **virtual MIDI port** for that (free, e.g. *loopMIDI*). It then appears as input/output in both programs. |


---

## 7. Limits

- **Tablets:** The iPad (Safari) cannot do MIDI in the browser. MIDI devices belong to the console computer; you can edit the mapping from any device.
- **Several programs:** Under Windows usually only **one** program reads a MIDI device (see "in use?"). Newer Windows versions (*Windows MIDI Services*) may change that - OpenCue only opens devices when needed and releases them with **MIDI on** off.
- **Network MIDI and virtual ports** are set up by the operating system (e.g. *loopMIDI*, *rtpMIDI*); they then appear like any device.
- **Controller profiles:** Instead of fixed profiles for single models there are **templates with a learn series** - they work with every controller. LED colours (velocities) differ per device; they are set under feedback as *LED on / LED off*.
- **Several mappings to switch between** (e.g. "stage" and "rehearsal"): as files through **Export / Import** in the dialog; there is no separate switch.
- Pitch bend, aftertouch and channel pressure are evaluated as faders; there is no song position and no MIDI events in the API's WebSocket stream.
- Not yet tried with all devices: faders, encoders, pads and feedback are tested with artificial messages - the **monitor** in the dialog shows what your device really sends.

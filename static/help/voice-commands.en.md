# Voice commands

With **voice commands** you control OpenCue by voice: you say the **wake word** (default "OpenCue") and right after it a **command-line command** – OpenCue writes it down, turns it into the command-line notation and **runs it at once**, exactly like a typed command (it also appears in the command history, all windows follow). Everything runs **offline** on the console computer (after the one-time download of the models), no AI is needed.

You speak **English**: the commands of the command line (`Fixture`, `At`, `Color`, `Blackout`, `Go` …) are English, and the speech recognition is set to write English words.

---

## 1. Switching it on

1. The **microphone symbol** at the top right of the toolbar is an **on/off switch**:
   - **green** = voice control listens for the wake word,
   - **red and crossed out** = off,
   - **yellow** = error (microphone unreachable, model missing …; the hint is in the tooltip).
2. Once, two models are downloaded (each only a single time, then everything works without internet): the small **wake word model** (41 MB: *Settings → Wake word → Download voice model*, or already in the installer) and the **speech model** for the commands (*Settings → Dictation → Load now*; it is the same as for dictation). The speech model *Accurate* (small) understands much better than *Fast* (base).
3. Microphone, wake word and sensitivity are set under *Settings → Wake word*.

The symbol exists at the console computer and also at remote devices (iPad): the switch turns the server's voice control on or off; the microphone itself always hangs on the main computer.

---

## 2. How to speak

```
"OpenCue … Blackout on."
"OpenCue … Fixture five at seventy nine, color green."
"OpenCue … Fixtures one through five at full."
```

- First the **wake word**, then – in the same breath or after a short pause (up to about 2 seconds) – the **command**.
- When the command is finished, **wait about a second**: a short pause ends the recording (at most 10 seconds).
- At the bottom centre of the screen a bubble shows the progress: **Listening …** → **Understanding …** → **the command** with its result (green = done, red = error or nothing understood). If OpenCue corrected a word it is shown behind it ("corrected: add → At").
- Speak short, clear commands. Filler words ("uh", "please", "now", "set") and stuttering are removed.

---

## 3. What you can say

You say the commands as they are written in the command line (see the guide *Command line*). Numbers can be said as words ("seventy nine") or as digits. Several commands in one breath are separated by **"then"**.

### Selecting fixtures and brightness

| You say | What runs |
|---|---|
| Fixture five | `Fixture 5` |
| Fixtures one through ten | `Fixture 1 Thru 10` |
| Fixture three and seven | `Fixture 3 + 7` |
| Fixture five at seventy nine | `Fixture 5 At 79` |
| Fixture five brightness fifty percent | `Fixture 5 At 50%` (also *dimmer, intensity, level*) |
| Fixtures one through five at full / at half | `Fixture 1 Thru 5 At Full` / `… At Half` |
| Fixture five on / full | `Fixture 5 At Full` |
| Fixture five off / out | `Fixture 5 At 0` |
| Fixture five at seventy nine point five | `Fixture 5 At 79.5` |
| At at / Everything on / All lights on | `At At` – **everything on** (100 % + white): without a selection all fixtures, with a selection only that selection. Say "Clear" first to be sure it is all. |
| Fixtures one through ten minus five (also *except / without*) | `Fixture 1 Thru 10 - 5` (without no. 5) |
| Next fixture / Previous fixture | `Next` / `Previous` (select the next / previous fixture) |
| Group front at full | `Group front At Full` |
| Group front truss at forty | `Group "front truss" At 40` (several name words go together in quotes) |
| Light / lamp / spot five | `Fixture 5` |

### Colours

| You say | What runs |
|---|---|
| Fixture five color green | `Fixture 5 Color Green` |
| Fixture five green | `Fixture 5 Color Green` (the word "color" is added) |
| Fixture five warm white / cool white / light blue | `Fixture 5 Color Warm` / `Cool` / `Lightblue` |
| RGB two fifty five zero zero | `RGB 255 0 0` |
| Color two fifty five one twenty eight zero | `Color 255 128 0` ("one twenty eight" = 128 after *color / rgb / bpm*) |

Colours as in the command line: red, green, blue, white, black, yellow, cyan, magenta, orange, pink, purple, amber, lime, teal, violet, light blue, warm, cool.

### Position and beam

| You say | What runs |
|---|---|
| Pan ninety / Pan fifty percent | `Pan 90` / `Pan 50%` |
| Tilt minus forty five / Pan plus fifteen | `Tilt -45` / `Pan +15` (a sign = relative) |
| Fixture five home / center | `Fixture 5 Pan 50% Tilt 50%` |
| Zoom half / full / minimum / fifty | `Zoom Half` / `Zoom Full` / `Zoom Min` / `Zoom 50` |
| Focus twenty five | `Focus 25` |
| Gobo forty / gobo spin thirty | `Gobo 40` / `GoboSpin 30` |
| Prism one hundred | `Prism 100` |
| Strobe zero / shutter ten | `Strobe 0` / `Strobe 10` |
| Channel six one hundred twenty eight | `Channel 6 128` (channel 6 of the fixture to DMX 128) |

### Master and blackout

| You say | What runs |
|---|---|
| Blackout | `Blackout` (toggle) |
| Blackout on / Blackout off | `Blackout On` / `Blackout Off` |
| Master eighty / Master full / Master minus ten | `Master 80` / `Master Full` / `Master -10` |

### Cue lists

| You say | What runs |
|---|---|
| Go / Next cue | `Go` |
| Back / Go back / Previous cue | `Back` |
| Pause / Resume / Stop | `Pause` / `Resume` / `Stop` |
| Go to cue five | `Go Cue 5` (also *goto cue five*) |
| Cue list main go | `Cuelist main Go` |
| Cue list front of house back | `Cuelist "front of house" Back` |
| Cuelist two go | `Cuelist 2 Go` |
| Cuelist main fader eighty / Fader fifty | `Cuelist main Fader 80` / `Fader 50` |
| Cue five fade three / Cue five delay one point five | `Cue 5 Fade 3` / `Cue 5 Delay 1.5` |
| Store cue five (merge) | `Store Cue 5` (`Merge`) |
| Update / Clear | `Update` / `Clear` |

### Timecode and audio

| You say | What runs |
|---|---|
| Timecode play / pause / stop / reset / reverse | `Timecode Play` / `Pause` / `Stop` / `Reset` / `Reverse` |
| Timecode rate two | `Timecode Rate 2` |
| Tap | `Tap` (tap the tempo) |
| BPM one twenty eight / BPM auto / BPM half | `BPM 128` / `BPM Auto` / `BPM Half` (also *beats per minute*) |
| Audio start / stop / demo | `Audio Start` / `Stop` / `Demo` |

### Effects, variables, programmer

| You say | What runs |
|---|---|
| Effect rainbow / Effect off | `Effect rainbow` / `Effect Off` |
| Variable warm white | `Variable "warm white"` |
| Manual / Manual color | `Manual` / `Manual Color` |

### Several commands

"Fixture one at full **then** fixture two at zero" → `Fixture 1 At Full; Fixture 2 At 0`.

---

## 4. What is corrected automatically

Whisper sometimes writes words that sound the same but make no sense in the command ("add" instead of "at", "true" instead of "thru"). OpenCue checks **where in the command** the word stands and puts in the fitting command word – only where it fits:

| Heard / written | Becomes | When |
|---|---|---|
| add, ad, it, app | At | after a number, before a number ("fixture 5 **add** 70") |
| true, threw, till, through, until, to, too, drew, grew, crew, throw … | Thru | between two numbers ("fixtures 1 **true** 5") |
| **2** (Whisper hears "thru" as the number *two*) | Thru | in a selection exactly between two numbers ("fixtures one **two** five" = `Fixture 1 Thru 5`; also "fixture 1-5" and "1, 2, 5") |
| eight (8) | At | in a selection between two numbers ("fixture 5 **eight** 70") |
| halve, calf | Half | always; "fixture 3 half" = `Fixture 3 At Half` |
| chanel, clair, stroke, pawn, tell, fate, delight … | Channel, Clear, Strobe, Pan, Tilt, Fade, Delay | depending on position (before a number, or always) |
| oh | 0 | where a number must stand ("at oh", "master oh") |
| picture, pitcher, fix sure, fixer | Fixture | always ("**picture** one to four") |
| for, to, too, won, ate, tree | 4, 2, 2, 1, 8, 3 | only where a number must stand ("fixture **for** at fifty" → Fixture 4 At 50) |
| collar, caller | Color | always |
| pen, ban, pun | Pan | before a number |
| till, tilted | Tilt | before a number ("**till** minus ten") |
| queue, q, cute, cube, key | Cue | before a number ("go **key** five") |
| fool | Full | always |
| of, own | Off, On | after Blackout |
| prison, prisms | Prism | always |
| strove | Strobe | always |
| paws, pours | Pause | always |
| affect, effects | Effect | always |
| tab | Tap | always |
| read, grin, grain, blew, wait … | Red, Green, Blue, White | after "color" or as a colour name |
| black out, black art, blackouts | Blackout | always |
| time code, cue list, grand master, go bo, b p m | Timecode, Cuelist, Master, Gobo, BPM | multi-word expressions |

Also:

- **Number words** → digits ("twenty one", "one hundred and five", "two point five", "minus ten percent").
- **Sound comparison:** an unknown word that stands where a particular command word must stand and sounds the same becomes that word.
- **Small misspellings** of keywords → the closest command word ("blakout" → Blackout).
- **Wake word variants** ("open queue", "open Q", "OpenCue") are removed at the start, also anything said before the wake word.
- **Names** (after *group, cuelist, effect, variable*) stay as spoken.
- **Percent** after Master, Fader, BPM and cue numbers is dropped ("master eighty percent" → `Master 80`) because the command line knows no percent there.
- Introductory chatter before the command ("set", "please", anything not understood) is dropped; the command must start with a command word.

---

## 5. What does not work by voice

In **operator mode** at the console (*View → Operator mode ...*) voice control is **switched off**, so that at this PC only what the control surface offers is possible; after leaving it runs again if it was switched on.

For safety voice control **never runs anything that deletes or overwrites**: `Delete …`, `Clear Clear`, `Overwrite`. The bubble then says "Not by voice". Type these commands or use the interface.

---

## 6. When it does not work

| Display | What to do |
|---|---|
| Microphone yellow | Read the tooltip; *Settings → Wake word* (right microphone?) |
| "Speech model missing" | *Settings → Dictation → Load now* (and for the wake word: *Settings → Wake word → Download voice model*) |
| "Nothing understood" | Closer to the microphone, speak more clearly, say the command right after the wake word |
| "No command recognised" | The text does not start with a command word – the bubble shows what was understood; speak exactly as in the command line |
| Command red (✗) | The command line says what does not fit (for example the fixture does not exist, "this cue list has no cues") |
| The wake word is not recognised | Raise *Settings → Wake word → Sensitivity* |
| A word is always written wrong | Note what Whisper writes (the text is in the log) – the table of corrections is easy to extend |

The wake word is recognised by a small offline model, the command after it is written down by Whisper (about 1–3 seconds on a normal computer). Loud music or noise in the room makes recognition worse – a microphone close to the mouth helps more than anything else.

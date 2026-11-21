# Audio: Lights That React to Music

OpenCue can **listen** to music and let lights react to it: brighter with the bass, a flash on every kick, colours that change on the beat, a chase that runs in time. The analysis runs live on the console, needs no internet and takes only a few percent of one processor core.

---

## 1. The idea in one minute

- The **Audio panel** takes a sound source and analyses it: loudness, a spectrum, the hits of **bass drum, snare and hi-hat**, the **tempo (BPM)** and the position within the beat.
- The results are available to effects as **variables** (`a_level`, `a_bass`, `a_kick`, `a_beat_phase` ...). An **audio effect** is a normal effect script that reads them. It works like every other effect: assign it to fixtures in the programmer, store it in cues, fade it in and out.
- 33 ready-made audio effects ship with the program. They carry the **Audio** tag (set automatically as soon as an effect reads audio values) - pick the tag in the effect type dialog to list them.
- Without a running source all audio values are `0`: an audio effect simply stays dark or at its idle value.
- Cues can start **on the music**, too: the cue trigger *Audio* (section 8).
- The console's own buttons, faders and toggles can follow the music (section 9), and the REST API can read and control the audio (section 10).

---

## 2. Quick start

1. Add the panel: **Edit → Add Panel…** → category *Media & Time* → **Audio**.
2. Choose **Demo beat** in the source list and press **Start**. A drum loop with 120 BPM is analysed - you see the spectrum, the lamps *Kick / Snare / Hi-hat / Beat* flash and the tempo appears.
3. In the programmer select some fixtures, open the **Effects** tab and click **Add effect**, choose the effect type **Kick Flash** (or *Bass Dimmer*, *Beat Chase* ... - tip: filter by the *Audio* tag) and create it. The fixtures now flash with the demo beat.
4. Switch the source to your real music (next section).

Existing installations get the new effects through the **File manager** (list *Effects*) with **Restore default effects**. This only creates *missing* files and never overwrites: if you restored an older version before, delete the old `audio_*.fx` files in the file manager first, then restore again.

---

## 3. Choosing the source

The list shows everything Windows knows:

| Group | What it is | Typical use |
|---|---|---|
| **System sound** | What this computer plays on a speaker or headphones ("loopback"). One entry per output device. | Music from the same computer (DJ software, Spotify, browser). No cable, no microphone. |
| **Inputs** | Microphones, line-in sockets and USB audio interfaces. | Music from a mixing desk or a phone: plug the cable into the **line-in** or the interface. A laptop with a single combined headset socket treats it as a *microphone*: the signal is weaker, raise the **input gain**. A microphone in the room works too, but the music has to be loud and clear. |
| **Test** | The demo beat. | Trying out effects without music. |

Entries marked *(default)* are the ones Windows uses by default. **Search again** (the arrows button) looks for devices again after plugging something in.

Press **Start**. The source stays open until you press **Stop**; the next program start opens it again by itself. If a source cannot be opened, the panel says why (in use by another program, blocked in the Windows privacy settings *Microphone*, unplugged).

---

## 4. What the panel shows

- **Spectrum:** 32 bars from 30 Hz to 16 kHz (deep tones on the left). The frame glows on every beat.
- **Lamps:** *Kick*, *Snare*, *Hi-hat* light up at every hit; *Beat* at every beat of the tempo.
- **Level** with an *Overload* mark: lights up when the signal is clipped (too loud at the input; lower the volume or the gain).
- **Tempo:** the BPM in big digits, a beat LED, a bar showing the position in the beat and a thin bar for how sure the detection is.

---

## 5. Tempo: automatic, tapped or fixed

- **Auto** detects the tempo from the music (70 - 180 BPM). It needs a few seconds and a steady beat; it follows tempo changes.
- **Tap:** tap the button in time with the music (also the command `Tap`). From the second tap the tempo is set from your taps and the beat starts exactly on the tap. The tempo is then *Manual*.
- **÷2 / ×2:** when the detection found half or double the speed (typical for very slow or very fast music).
- **Manual:** the tempo is fixed; type it into the field. With *Manual tempo: the beat follows the music* the beat position still adjusts gently to the hits. Without any music a fixed tempo runs like a **metronome** - effects with `a_beat_phase` keep running in time.
- **Auto** switches back to detection.

Commands: `Tap`, `BPM 128`, `BPM Auto`, `BPM Half`, `BPM Double`, `Audio Start`, `Audio Stop`, `Audio Demo`, `Audio Status`.

---

## 6. Settings

| Setting | What it does |
|---|---|
| **Input gain** | Amplifies (×0.1 to ×10) a weak signal, e.g. a microphone. |
| **Auto gain** | The analysis measures against the loudest parts of the last seconds, so a quiet song works like a loud one. Switch it off for a fixed scale (then the gain acts directly). |
| **Beat sensitivity** | Higher: even soft hits count (risk: false hits). Lower: only clear hits count. |
| **Smoothing** | How slowly the levels and bands fall back. |
| **Timing offset** | −100 to +200 ms. Positive: the lights react **earlier** - use it when the lights or the speakers are late. |

The settings belong to the console (not to a show or a panel) and are saved automatically. Every device with an Audio panel shows and controls the same source.

---

## 7. The ready-made audio effects

| Effect | Category | What it does |
|---|---|---|
| Band Bars | Dimmer | Every fixture shows one frequency band: the first the lows, the last the highs (repeats with more than 8 fixtures). |
| Bass Dimmer | Dimmer | The brightness follows the bass of the music. |
| Beat Chase | Dimmer | A chase that steps on every beat (or every n-th one). |
| Beat Pulse | Dimmer | The brightness pulses in time with the music: bright on the beat, then fading softly. |
| Beat Strobe | Dimmer | Strobe in time with the music: mult flashes per beat, locked to the tempo. |
| Beat Toggle | Dimmer | Switches between two groups on every beat (or every n-th one), hard or cross-faded (soft). |
| Hi-Hat Sparkle | Dimmer | On every hi-hat hit randomly chosen fixtures sparkle. |
| Kick Chase | Dimmer | A chase that steps on every bass drum hit (instead of the beat). |
| Kick Flash | Dimmer | Every bass drum hit flashes the lights and fades out. |
| Level Dimmer | Dimmer | The brightness follows the overall loudness. |
| Snare Flash | Dimmer | Every snare hit (or clap) flashes the lights and fades out. |
| Beat Color | Color | The colour changes on every beat (or every n-th one) and is brightest on the beat. |
| Beat Color Chase | Color | A coloured light (A) runs across a background colour (B), one step per beat (or every n-th). |
| Beat Color Fade | Color | Fades between two colours in time with the music. |
| Beat Color Strobe | Color | A coloured strobe in time with the music: mult flashes per beat, alternating between colour A and B. |
| Color Blend | Color | Blends from colour A (quiet) to colour B (loud). |
| Color Hit | Color | The base colour flashes into the flash colour on every hit of the chosen drum. |
| Hi-Hat Color Sparkle | Color | On every hi-hat hit randomly chosen fixtures flash in a random colour (within the colour range). |
| Hue Drift | Color | The colours drift through the colour range, one full cycle takes `beats` beats. |
| Kick Color Flash | Color | The base colour flashes into the flash colour on every bass drum hit. |
| Spectrum Color | Color | The colour mixes from the music: bass = red, mids = green, highs = blue. |
| Spectrum Hue | Color | The colour follows the sound: bass-heavy music shows the start of the colour range, bright sounds its end. |
| Bass Tilt | Position | The tilt follows the bass: quiet = down, strong bass = up (around the base position). |
| Beat Circle | Position | The heads travel a circle in time with the music: one turn takes `beats` beats. |
| Beat Fan | Position | The fixtures fan out and close in time with the music. |
| Kick Tilt Punch | Position | On every bass drum hit the heads punch in tilt and settle back to the base position. |
| Level Spread | Position | The louder the music, the wider the fixtures fan out (symmetrically around the base position). |
| Pan/Tilt Sway | Position | The heads move in time with the music. |
| Snare Pan Snap | Position | On every snare hit each head snaps to the next of four pan positions. |
| Beat Zoom Pulse | Zoom | The zoom pulses on every beat: high on the beat, then falling back to low. |
| Kick Zoom Punch | Zoom | The zoom punches from low to high on every bass drum hit and falls back. |
| Bass Focus | Focus | The focus follows the bass of the music. |
| Beat Gobo Change | Gobo | The gobo changes on every beat (or every n-th one). |

Almost every effect has options to **toggle animations** and to add a **strobe**: *strobe* (flashes per second, 0 = off), *mode* (for example all together / even-odd alternating / random), *direction* (chase forward, backward, bounce, random), *every* (switch every n-th beat), *soft* (hard switch or cross-fade). They are normal effects: store them in cues, vary them, copy them.

---

## 8. Cue trigger: Audio

Besides *Go*, *Follow*, *Timecode* and *MIDI* (guide *MIDI*) a cue can have the trigger **Audio**: it then fires by itself **on the music**. In the cue dialog choose the trigger *Audio*, pick **one source** and, if needed, a value - in the cue list you can also type it (`audio kick`, `audio beat 4`, `audio bass 70`) or use the command `Cue 2 Trigger Audio Beat 4`.

| Source | Value | The cue fires … |
|---|---|---|
| **Beat (tempo)**, **Bass drum**, **Snare**, **Hi-hat** | every n-th (1 to 64, default 1) | … on every n-th beat / hit. |
| **Overall level**, **Bass**, **Mids**, **Highs** or one of the **eight bands** (with their Hz range in the list) | threshold in % (default 70) | … when this part of the sound rises **to** the threshold from below. |

How it works:
- The cue fires when it is the **next cue** of a running list: first start the list with *Go*, then the following audio cue waits for its event. After it has fired, the cue after it (if it also has the trigger *Audio*) waits in turn - so you can chain a whole sequence to the music.
- The counter (*every n-th*) starts at 0 whenever a new cue becomes active.
- With a threshold the cue fires once when the level reaches it; it is armed again only after the level has fallen clearly below (about 80 % of the threshold). If the level is already above when the cue becomes next, it waits for the next rise.
- After a trigger there is a short pause (0.25 s), so one hit never starts two cues.
- The **Audio panel must be running** (a source started); without sound nothing fires. The trigger works for every cue list on its own.

---

## 9. Buttons, faders and toggles that react to the music

The console's own **Button**, **Fader** and **Toggle** panels can use the music as a *signal* – in *Follows the state of* (a fader moves with the music, a toggle switches with the signal) and in the **conditions of rules** (colour, text or command when …). The signals are in the group **Audio**:

| Signal | Meaning |
|---|---|
| **Audio signal present** | on while a source is open and something is playing |
| **Overall level**, **bass**, **mids**, **highs** | 0–100 % |
| **Bass drum**, **snare**, **hi-hat**, **beat** (pulse) | jump to 100 % at every hit and fade out |
| **Tempo (BPM)** | the detected or set tempo |

Examples: a fader that follows the bass as a level meter; a button that lights up red when the tempo is between 120 and 130 BPM; a toggle that shows whether music is coming in. The audio source runs on the console; a panel only needs to be on the screen of any device – the measurements are sent to a device exactly as long as such a panel (or the *Audio* panel) is open there.

## 10. Audio through the API

The REST API can read the analysis (`GET /api/v1/audio`), open and close the source, change the settings and tap the tempo (`PUT /api/v1/audio`, `POST /api/v1/audio/tap`, permission *Audio*), and the **live event stream** (`GET /api/v1/events?events=audio,beat,hit`) reports the source, every beat and every drum hit as they happen. See the *REST API* guide.

## 11. Writing your own audio effect

Open the **Effect Studio**, create an effect and read the audio variables - see the guide *Effect Studio*, section *Audio variables*. A first example:

```
#NAME My Flash
#CATEGORY dimmer
#RATE 40
#VAR peak Slider 100 0 100 1

loop() {
  dimmer = peak * a_kick;
}
```

The studio preview plays a sample beat (120 BPM) so you see right away how the curve behaves.

---

## 12. When something does not work

| Problem | Check |
|---|---|
| The source cannot be opened | Another program uses it exclusively; the microphone is blocked in the Windows privacy settings (*Settings → Privacy → Microphone*); the device is unplugged. |
| The panel shows nothing / everything flat | Is the source *Start*ed? Does the Windows volume meter move? Raise the **input gain**. For *System sound* the program must actually play to that output device. |
| *Overload* is lit | The signal is too loud: lower the volume at the source or the input gain. |
| BPM jumps or is half / double | Press **÷2 / ×2**, tap the tempo, or fix it with *Manual*. Music without a steady beat (classical, speech) has no detectable tempo. |
| Lights react too late | Use the **Timing offset** (positive values). |
| An audio effect stays dark | No source running, or the sensitivity is too low for the music; raise the effect's *gain* slider. |

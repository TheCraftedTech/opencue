# Sprachbefehle

Mit **Sprachbefehlen** steuerst du OpenCue per Stimme: Du sagst das **Triggerwort** (Standard: „OpenCue“) und gleich danach einen **Befehl der Befehlszeile** – OpenCue schreibt ihn auf, setzt ihn in die Schreibweise der Befehlszeile um und **führt ihn sofort aus**, genau wie einen getippten Befehl (er steht auch im Befehlsverlauf, alle Fenster folgen). Alles läuft **offline** auf dem Konsolenrechner (nach dem einmaligen Laden der Modelle), es ist keine KI nötig.

Gesprochen wird **Englisch**: Die Befehle der Befehlszeile (`Fixture`, `At`, `Color`, `Blackout`, `Go` …) sind englisch, und die Spracherkennung ist darauf eingestellt, englische Wörter zu schreiben.

---

## 1. Einschalten

1. Das **Mikrofon-Symbol** oben rechts in der Werkzeugleiste ist ein **Ein-/Aus-Schalter**:
   - **grün** = die Sprachsteuerung hört auf das Triggerwort,
   - **rot und durchgestrichen** = aus,
   - **gelb** = Fehler (Mikrofon nicht erreichbar, Modell fehlt …; der Hinweis steht im Tooltip).
2. Einmalig werden zwei Modelle geladen (jedes nur ein einziges Mal, danach geht alles ohne Internet): das kleine **Triggerwort-Modell** (41 MB: *Einstellungen → Triggerwort → Sprachmodell laden*, oder schon im Installer) und das **Sprachmodell** für die Befehle (*Einstellungen → Diktieren → Jetzt laden*; es ist dasselbe wie beim Diktieren). Das Sprachmodell *Genau* (small) versteht deutlich besser als *Schnell* (base).
3. Mikrofon, Triggerwort und Empfindlichkeit stellst du unter *Einstellungen → Triggerwort* ein.

Das Symbol gibt es am Konsolenrechner und auch an Fernzugriffs-Geräten (iPad): Der Schalter stellt die Sprachsteuerung des Servers ein oder aus; das Mikrofon hängt aber immer am Hauptrechner.

---

## 2. So sprichst du

```
„OpenCue … Blackout on.“
„OpenCue … Fixture five at seventy nine, color green.“
„OpenCue … Fixtures one through five at full.“
```

- Erst das **Triggerwort**, dann – im selben Atemzug oder nach einer kurzen Pause (bis etwa 2 Sekunden) – der **Befehl**.
- Ist der Befehl zu Ende, **warte etwa eine Sekunde**: Eine kurze Pause beendet die Aufnahme (höchstens 10 Sekunden lang).
- Unten in der Bildschirmmitte zeigt eine Blase den Verlauf: **Ich höre …** → **Verstehe …** → **der Befehl** mit seinem Ergebnis (grün = ausgeführt, rot = Fehler oder nichts verstanden). Hat OpenCue ein Wort korrigiert, steht es dahinter („korrigiert: add → At“).
- Sprich in kurzen, klaren Befehlen. Füllwörter („uh“, „please“, „now“, „set“) und Stottern werden entfernt.

---

## 3. Was du sagen kannst

Du sagst die Befehle so, wie sie in der Befehlszeile stehen (siehe die Anleitung *Befehlszeile*). Zahlen sagst du als Wörter („seventy nine“) oder als Ziffern. Mehrere Befehle in einem Atemzug trennst du mit **„then“**.

### Scheinwerfer wählen und Helligkeit

| Du sagst | Es wird ausgeführt |
|---|---|
| Fixture five | `Fixture 5` |
| Fixtures one through ten | `Fixture 1 Thru 10` |
| Fixture three and seven | `Fixture 3 + 7` |
| Fixture five at seventy nine | `Fixture 5 At 79` |
| Fixture five brightness fifty percent | `Fixture 5 At 50%` (auch *dimmer, intensity, level*) |
| Fixtures one through five at full / at half | `Fixture 1 Thru 5 At Full` / `… At Half` |
| Fixture five on / full | `Fixture 5 At Full` |
| Fixture five off / out | `Fixture 5 At 0` |
| Fixture five at seventy nine point five | `Fixture 5 At 79.5` |
| At at / Everything on / All lights on | `At At` – **alles an** (100 % + Weiß): ohne Auswahl alle Scheinwerfer, mit Auswahl nur diese. Vorher „Clear“ sagen = ganz sicher alle. |
| Fixtures one through ten minus five (auch *except / without*) | `Fixture 1 Thru 10 - 5` (ohne Nr. 5) |
| Next fixture / Previous fixture | `Next` / `Previous` (nächsten / vorigen Scheinwerfer wählen) |
| Group front at full | `Group front At Full` |
| Group front truss at forty | `Group "front truss" At 40` (mehrere Namenswörter kommen zusammen in Anführungszeichen) |
| Light / lamp / spot five | `Fixture 5` |

### Farben

| Du sagst | Es wird ausgeführt |
|---|---|
| Fixture five color green | `Fixture 5 Color Green` |
| Fixture five green | `Fixture 5 Color Green` (das Wort „color“ wird ergänzt) |
| Fixture five warm white / cool white / light blue | `Fixture 5 Color Warm` / `Cool` / `Lightblue` |
| RGB two fifty five zero zero | `RGB 255 0 0` |
| Color two fifty five one twenty eight zero | `Color 255 128 0` („one twenty eight“ = 128 hinter *color / rgb / bpm*) |

Farben wie in der Befehlszeile: red, green, blue, white, black, yellow, cyan, magenta, orange, pink, purple, amber, lime, teal, violet, light blue, warm, cool.

### Position und Beam

| Du sagst | Es wird ausgeführt |
|---|---|
| Pan ninety / Pan fifty percent | `Pan 90` / `Pan 50%` |
| Tilt minus forty five / Pan plus fifteen | `Tilt -45` / `Pan +15` (Vorzeichen = relativ) |
| Fixture five home / center | `Fixture 5 Pan 50% Tilt 50%` |
| Zoom half / full / minimum / fifty | `Zoom Half` / `Zoom Full` / `Zoom Min` / `Zoom 50` |
| Focus twenty five | `Focus 25` |
| Gobo forty / gobo spin thirty | `Gobo 40` / `GoboSpin 30` |
| Prism one hundred | `Prism 100` |
| Strobe zero / shutter ten | `Strobe 0` / `Strobe 10` |
| Channel six one hundred twenty eight | `Channel 6 128` (Kanal 6 des Scheinwerfers auf DMX 128) |

### Master und Blackout

| Du sagst | Es wird ausgeführt |
|---|---|
| Blackout | `Blackout` (umschalten) |
| Blackout on / Blackout off | `Blackout On` / `Blackout Off` |
| Master eighty / Master full / Master minus ten | `Master 80` / `Master Full` / `Master -10` |

### Cue-Listen

| Du sagst | Es wird ausgeführt |
|---|---|
| Go / Next cue | `Go` |
| Back / Go back / Previous cue | `Back` |
| Pause / Resume / Stop | `Pause` / `Resume` / `Stop` |
| Go to cue five | `Go Cue 5` (auch *goto cue five*) |
| Cue list main go | `Cuelist main Go` |
| Cue list front of house back | `Cuelist "front of house" Back` |
| Cuelist two go | `Cuelist 2 Go` |
| Cuelist main fader eighty / Fader fifty | `Cuelist main Fader 80` / `Fader 50` |
| Cue five fade three / Cue five delay one point five | `Cue 5 Fade 3` / `Cue 5 Delay 1.5` |
| Store cue five (merge) | `Store Cue 5` (`Merge`) |
| Update / Clear | `Update` / `Clear` |

### Timecode und Audio

| Du sagst | Es wird ausgeführt |
|---|---|
| Timecode play / pause / stop / reset / reverse | `Timecode Play` / `Pause` / `Stop` / `Reset` / `Reverse` |
| Timecode rate two | `Timecode Rate 2` |
| Tap | `Tap` (Tempo antippen) |
| BPM one twenty eight / BPM auto / BPM half | `BPM 128` / `BPM Auto` / `BPM Half` (auch *beats per minute*) |
| Audio start / stop / demo | `Audio Start` / `Stop` / `Demo` |

### Effekte, Variablen, Programmer

| Du sagst | Es wird ausgeführt |
|---|---|
| Effect rainbow / Effect off | `Effect rainbow` / `Effect Off` |
| Variable warm white | `Variable "warm white"` |
| Manual / Manual color | `Manual` / `Manual Color` |

### Mehrere Befehle

„Fixture one at full **then** fixture two at zero“ → `Fixture 1 At Full; Fixture 2 At 0`.

---

## 4. Was automatisch korrigiert wird

Whisper schreibt manchmal Wörter, die genauso klingen, aber im Befehl keinen Sinn ergeben („add“ statt „at“, „true“ statt „thru“). OpenCue prüft, **an welcher Stelle im Befehl** das Wort steht, und setzt das passende Befehlswort ein – nur dort, wo es hinpasst:

| Gehört / geschrieben | Wird | Wann |
|---|---|---|
| add, ad, it, app | At | hinter einer Nummer, vor einer Zahl („fixture 5 **add** 70“) |
| true, threw, till, through, until, to, too, drew, grew, crew, throw … | Thru | zwischen zwei Nummern („fixtures 1 **true** 5“) |
| **2** (Whisper hört „thru“ als Zahl *two*) | Thru | in einer Auswahl genau zwischen zwei Nummern („fixtures one **two** five“ = `Fixture 1 Thru 5`; auch „fixture 1-5“ und „1, 2, 5“) |
| eight (8) | At | in einer Auswahl zwischen zwei Nummern („fixture 5 **eight** 70“) |
| halve, calf | Half | immer; „fixture 3 half“ = `Fixture 3 At Half` |
| chanel, clair, stroke, pawn, tell, fate, delight … | Channel, Clear, Strobe, Pan, Tilt, Fade, Delay | je nach Stelle (vor einer Zahl bzw. immer) |
| oh | 0 | dort, wo eine Zahl stehen muss („at oh“, „master oh“) |
| picture, pitcher, fix sure, fixer | Fixture | immer („**picture** one to four“) |
| for, to, too, won, ate, tree | 4, 2, 2, 1, 8, 3 | nur dort, wo eine Zahl stehen muss („fixture **for** at fifty“ → Fixture 4 At 50) |
| collar, caller | Color | immer |
| pen, ban, pun | Pan | vor einer Zahl |
| till, tilted | Tilt | vor einer Zahl („**till** minus ten“) |
| queue, q, cute, cube, key | Cue | vor einer Zahl („go **key** five“) |
| fool | Full | immer |
| of, own | Off, On | hinter Blackout |
| prison, prisms | Prism | immer |
| strove | Strobe | immer |
| paws, pours | Pause | immer |
| affect, effects | Effect | immer |
| tab | Tap | immer |
| read, grin, grain, blew, wait … | Red, Green, Blue, White | hinter „color“ oder als Farbname |
| black out, black art, blackouts | Blackout | immer |
| time code, cue list, grand master, go bo, b p m | Timecode, Cuelist, Master, Gobo, BPM | Mehrwort-Ausdrücke |

Außerdem:

- **Zahlwörter** → Ziffern („twenty one“, „one hundred and five“, „two point five“, „minus ten percent“).
- **Klang-Vergleich:** Ein unbekanntes Wort, das an einer Stelle steht, wo ein bestimmtes Befehlswort stehen muss, und genauso klingt, wird dieses Wort.
- **Kleine Schreibfehler** bei Schlüsselwörtern → das ähnlichste Befehlswort („blakout“ → Blackout).
- **Weckwort-Varianten** („open queue“, „open Q“, „OpenCue“) werden am Anfang entfernt, auch Gerede vor dem Weckwort.
- **Namen** (nach *group, cuelist, effect, variable*) bleiben, wie gesprochen.
- **Prozentangaben** bei Master, Fader, BPM und Cue-Nummern fallen weg („master eighty percent“ → `Master 80`), weil die Befehlszeile dort keine Prozent kennt.
- Vorgeplänkel vor dem Befehl („set“, „please“, Unverständliches) wird verworfen; der Befehl muss mit einem Befehlswort beginnen.

---

## 5. Was nicht per Sprache geht

Im **Bedienmodus** an der Konsole (*Ansicht → Bedienmodus …*) ist die Sprachsteuerung **ausgeschaltet**, damit an diesem PC nur das geht, was die Bedienfläche anbietet; nach dem Verlassen läuft sie wieder, wenn sie eingeschaltet war.

Aus Sicherheit führt die Sprachsteuerung **nichts aus, was etwas löscht oder überschreibt**: `Delete …`, `Clear Clear`, `Overwrite`. Die Blase sagt dann „Nicht per Sprache“. Tippe diese Befehle oder nutze die Oberfläche.

---

## 6. Wenn es nicht klappt

| Anzeige | Was tun |
|---|---|
| Mikrofon gelb | Tooltip lesen; *Einstellungen → Triggerwort* (richtiges Mikrofon?) |
| „Sprachmodell fehlt“ | *Einstellungen → Diktieren → Jetzt laden* (und für das Triggerwort: *Einstellungen → Triggerwort → Sprachmodell laden*) |
| „Nichts verstanden“ | Näher ans Mikrofon, deutlicher sprechen, den Befehl direkt nach dem Triggerwort sagen |
| „Kein Befehl erkannt“ | Der Text beginnt nicht mit einem Befehlswort – die Blase zeigt, was verstanden wurde; sprich genau wie in der Befehlszeile |
| Befehl rot (✗) | Die Befehlszeile meldet, was nicht passt (z. B. den Scheinwerfer gibt es nicht, „this cue list has no cues“) |
| Das Triggerwort wird nicht erkannt | *Einstellungen → Triggerwort → Empfindlichkeit* erhöhen |
| Ein Wort wird immer falsch geschrieben | Notiere, was Whisper schreibt (der Text steht im Protokoll) – die Tabelle der Korrekturen lässt sich einfach erweitern |

Das Triggerwort erkennt ein kleines Offline-Modell, den Befehl danach schreibt Whisper auf (etwa 1–3 Sekunden auf einem normalen Rechner). Bei lauter Musik oder Lärm im Raum wird die Erkennung schlechter – ein Mikrofon nah am Mund hilft mehr als alles andere.

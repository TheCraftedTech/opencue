# MIDI

Mit **MIDI** steuerst du OpenCue von einem Controller, einem Keyboard, Pads oder einem Musikprogramm aus – und OpenCue kann selbst MIDI senden. Eine Taste, ein Regler, ein Drehknopf oder ein Programmwechsel löst einen **Befehl der Befehlszeile** aus, genau wie eine eigene Tastenkombination (siehe *Tastaturkürzel*) – nur mit Reglern dazu.

Die Belegung gehört zum **Programm**, nicht zur Show: sie gilt für alle Shows und steht in der App-Konfiguration. Du erreichst sie auf vier Wegen: über das **MIDI-Symbol** oben rechts in der Werkzeugleiste, über **Einstellungen → Bedienung → MIDI**, über **Steuerung → MIDI-Belegung …** und – für Tasten und Regler eines Panels – über **MIDI zuweisen …** in den Eigenschaften des Panels. Das MIDI-Gerät hängt am Konsolenrechner; die Liste bearbeitest du auch von einem Tablet aus – ebenso Einlernen und Monitor (sie zeigen, was das Gerät am Konsolenrechner sendet).

---

## 1. Was ist MIDI? (kurz)

MIDI sendet keine Töne, sondern kleine **Nachrichten**. Drei Arten brauchst du:

| Nachricht | Was dein Gerät damit meldet | In OpenCue |
|---|---|---|
| **Note** | Eine Taste (Klaviertaste, Pad) wird gedrückt oder losgelassen. Jede hat eine Nummer, z. B. 60 = **C4** (mittleres C), und eine **Anschlagstärke** (0–127, wie hart gedrückt). | Art **Taste**, **Schalter**, **Halten** – oder **Regler** (die Anschlagstärke wird der Wert) |
| **Controller (CC)** | Ein Regler oder Drehknopf. Jeder hat eine Nummer (0–127) und einen Wert 0–127. | Art **Regler** (Fader, Potis) oder **Drehgeber** (Endlos-Knöpfe) |
| **Programmwechsel** | Ein „Programm“ mit einer Nummer wird gewählt. | Art **Taste** (z. B. Programm 3 = `Go Cue 3`) |

Außerdem hat jede Nachricht einen **Kanal** (1–16), damit mehrere Geräte auf einer Leitung sprechen können. Wenn du es nicht weißt: **Alle** Kanäle lassen.

---

## 2. Erste Schritte

1. MIDI-Gerät per USB anstecken (Windows erkennt es von allein – bei Geräten mit „Class compliant“ ist kein Treiber nötig).
2. Das **MIDI-Symbol** oben rechts anklicken (oder **Steuerung → MIDI-Belegung …**). Oben steht, welche Geräte erkannt sind. Der **Monitor** unten zeigt live alles, was dein Gerät sendet – drück einfach eine Taste und sieh nach: `Note On C4 (60) · 100`.
3. **Neue MIDI-Belegung** → in der Zeile auf das Signal-Feld klicken → am Gerät **drücken oder bewegen** → **Übernehmen**. Das Signal ist eingelernt.
4. Rechts den **Befehl** eintragen, z. B. `Go`. Fertig – die Taste löst jetzt `Go` aus. Die Zeile leuchtet kurz, wenn sie auslöst.

Die Belegung wird sofort gespeichert. Der Schalter **MIDI aktiv** oben schaltet alles aus (dann hört OpenCue auf keinem Gerät mit).

**Das Symbol in der Werkzeugleiste** zeigt den Zustand: **grün** = ein Gerät ist bereit, **grau** = kein Gerät angeschlossen, **gelb** = ein Gerät lässt sich nicht öffnen (meist belegt ein anderes Programm es), **rot und durchgestrichen** = MIDI ist aus. Ein Klick öffnet die Belegung; der Tooltip nennt die erkannten Geräte.

**Einstellungen → Bedienung → MIDI** (wie alle Einstellungen mit *Speichern*): MIDI verwenden, **welche Geräte** benutzt werden (jedes angeschlossene Gerät hat einen Schalter – ein abgewähltes wird nie geöffnet), der **Ausgang**, **Timecode (MTC)** und **Tempo aus dem MIDI-Takt** (Abschnitt 5b) und Knöpfe zur Belegung.

Unter **Einstellungen → Ein- & Ausgänge → MIDI** siehst du die erkannten Geräte, ob sie gerade gelesen werden, den Ausgang und wie viele Belegungen aktiv sind.

---

## 3. Die Arten

| Art | Wirkung | Beispiel |
|---|---|---|
| **Taste** | Beim Drücken läuft der Befehl. | Pad 1 → `Go`; Pad 2 → `Back`; Pad 3 → `Clear` |
| **Schalter** | Jeder Druck wechselt zwischen **Befehl** und **Aus-Befehl** (leer = beide Male derselbe Befehl). | `Blackout` (schaltet selbst um); oder `Effect Regenbogen` / `Effect Off` |
| **Halten** | Beim Drücken läuft der **Befehl**, beim Loslassen der **Loslass-Befehl** („Flash“). | `Group front At Full` / `Group front At 0` |
| **Regler** | Der Befehl bekommt den Wert als `{value}`, umgerechnet auf den Bereich **Von … Bis** (auch **Umkehren**). | Fader → `Master {value}` (0–100); Fader → `Cuelist main Fader {value}` |
| **Drehgeber** | Für **Endlos-Drehknöpfe**: jeder Schritt läuft als `{delta}` (mit Vorzeichen, mal **Schritt**). Die Drehgeber-Art (üblich / Vorzeichen-Bit / Mitte 64) steht in der Zeile. | Knopf → `Pan {delta}` (Auswahl vorher treffen) |

**Platzhalter im Befehl:** `{value}` (Reglerwert im Bereich Von–Bis), `{delta}` (Drehgeber-Schritte, z. B. `+1` / `-2`), `{velocity}` (Anschlagstärke 0–127), `{note}` und `{number}` (Noten-/Controller-/Programmnummer), `{channel}`, `{raw}` (Rohwert 0–127).

**Start / Stop / Weiter (Transport):** Als Signal kannst du auch *Start*, *Stop* und *Weiter* der Musiksoftware wählen (Art im Lern-Dialog; sie haben weder Kanal noch Nummer). Beispiel: Start → `Timecode Play`, Stop → `Timecode Stop`.

**Aufnehmen (Pickup):** Bei einem **Regler** ohne Motor steht der Fader oft anders als der Wert im Programm. Mit **Aufnehmen** greift der Regler erst, wenn er den aktuellen Wert erreicht oder durchquert hat – kein Sprung beim ersten Anfassen. Wurde der Wert zwischendurch anderswo verändert, muss er ihn neu einfangen. Das gilt für `Master {value}`, `Fader {value}`, `Cuelist <Name> Fader {value}` und die Helligkeit oder ein Beam-Attribut einer Fixture, Gruppe oder der Auswahl (`Fixture 5 At {value}`, `Group front At {value}`, `At {value}`, `Zoom {value}`); bei anderen Befehlen greift der Regler sofort.

**Weitere Arten:** *Doppelklick* (der Befehl läuft erst beim zweiten Druck innerhalb von 0,4 s) und *Lang halten* (er läuft, wenn die Taste die eingestellte Zeit gehalten wird – z. B. 600 ms; vorher loslassen bricht ab). Bei Reglern wählst du eine **Kennlinie**: *Linear*, *Langsam anfangen* (feine Werte unten) oder *Schnell anfangen*. Auch **Aftertouch** (Druck auf eine gehaltene Taste) und **Kanaldruck** sind als Regler belegbar. **Ein Regler auf mehrere Befehle:** durch Strichpunkt trennen, z. B. `Master {value}; Group front At {value}`.

**Rückmeldung an das Gerät (LEDs, Motorfader):** In der Zeile wählst du bei **Rückmeldung** einen Zustand der Konsole: *Blackout*, *Master*, *Auswahl vorhanden*, *Cue aktiv*, *Timecode läuft* oder *Fader der Cue-Liste*. OpenCue sendet ihn als Note / Controller / Pitch-Bend **mit derselben Nummer und demselben Kanal** wie das Signal an den Ausgang, der so heißt wie das Gerät – bei einem Pad-Controller leuchtet die LED, bei einem Motorfader fährt der Fader mit. Bei Ein/Aus-Zuständen stellst du **LED an / LED aus** ein (die Anschlagstärke; bei Pads mit Farben ist sie die Farbe). Gesendet wird nur bei einer Änderung, und nach dem Anstecken eines Geräts wird alles neu gesendet.

Mehr Beispiele:

| Gerät | Belegung |
|---|---|
| Programmwechsel (z. B. am Keyboard) | Taste, Befehl `Go Cue {number}` – Programm 5 springt zu Cue 5 |
| Taste mit Anschlagstärke | Regler (Quelle Note), Befehl `Group front At {value}`, Von 0 Bis 100 – je härter, desto heller |
| Pitch-Bend-Rad | Regler, Befehl `Master {value}` |
| Fader-Bank | je Fader eine Zeile (CC 1…8): `Fixture 1 At {value}`, `Fixture 2 At {value}` … |

Auslöser: eine Taste löst beim **Drücken** aus. Ein CC, der als Taste dient (Pads vieler Controller), löst bei einem Wert **ab 64** aus. Ein Regler schickt höchstens **etwa 40 Befehle pro Sekunde** (schnelle Bewegungen werden zusammengefasst, der letzte Wert kommt immer an).

---

## 3b. Zeilen kopieren, exportieren, importieren, vom Panel aus

- **Kopieren** (Symbol neben dem Papierkorb): dupliziert eine Zeile mit Art und Befehl, das Signal bleibt leer – praktisch für eine Reihe ähnlicher Regler (Fader 1 … 8).
- **Exportieren / Importieren** (unten im Dialog): sichert die Belegung als Datei (`opencue-midi-mapping.json`) bzw. liest eine solche Datei ein. Beim Import kommen die Zeilen **neu dazu** – nichts wird ersetzt.
- **Vorlage …** (unten im Dialog): legt eine **Reihe** von Zeilen an – *Fader-Bank* (Fixture 1…8), *Cue-Pads*, *Transport-Tasten* (Go, Back, Pause, Blackout), *Master & Blackout* – und lässt dich danach **die Bedienelemente nacheinander drücken oder bewegen** („Signal 2 von 8“, *Überspringen* geht weiter, Abbrechen beendet die Reihe). So belegst du jeden Controller, ohne Nummern zu kennen.
- **Suchfeld** über der Liste (Signal, Befehl, Gerät) und die **Pfeile** an jeder Zeile (nach oben / unten verschieben; während einer Suche gesperrt).
- **Mit einer MIDI-Taste zu diesem Cue springen …** im Dialog einer **Cue** (*Cue bearbeiten*): legt eine Belegung `Cuelist "<Liste>" Go Cue <Nummer>` an und lernt das Signal ein – die Cue startet dann auf Tastendruck, **jederzeit** (eine freie „Sprung“-Taste). Für einen Cue, der innerhalb einer Abfolge auf sein Signal wartet, siehe den Cue-Auslöser **MIDI** (Abschnitt 5c).
- **MIDI zuweisen …** in den Eigenschaften eines **Buttons, Schalters oder Faders**: legt eine Belegung mit dem Befehl des Panels an (Schalter: An- und Aus-Befehl, Fader: mit Von/Bis) und lernt das Signal gleich ein. Die Belegung bleibt auch bestehen, wenn du das Panel löschst.

---

## 4. Gilt für, Ausführen, Verlauf

- **Signal einlernen → Gilt für:** *Alle Geräte* (jedes Gerät mit diesem Signal löst aus) oder *Nur dieses Gerät* (z. B. wenn zwei Controller dieselben Nummern senden).
- **Ausführen** aus: der Befehl wird nur in die **Befehlszeile geschrieben**, nicht ausgeführt (zum Prüfen oder Ergänzen).
- **Im Verlauf:** der Befehl erscheint im Verlauf der Befehlszeile (alle Fenster sehen ihn).
- Es gibt keine Prüfung gegen doppelte Signale: zwei Zeilen mit demselben Signal lösen **beide** aus (der Lern-Dialog weist darauf hin).

**Sicherheit:** `Delete …` und Befehle mit `Overwrite` laufen **nie per MIDI** (eine versehentlich getroffene Taste soll keine Daten vernichten). `Clear Clear` ist erlaubt.

---

## 5. OpenCue sendet MIDI: der Befehl `Midi`

Der Befehl `Midi` sendet an den **Ausgang** (im Dialog oben wählbar; **Automatisch** nimmt das erste echte Gerät, sonst den Windows-Synthesizer „Microsoft GS Wavetable Synth“ – damit hörst du sofort etwas):

| Befehl | Wirkung |
|---|---|
| `Midi Note 60` | Note C4 (60) spielen, Anschlagstärke 100, nach 0,3 s wieder aus |
| `Midi Note 60 90 Ch 2 Len 1` | Note 60, Stärke 90, Kanal 2, 1 Sekunde lang |
| `Midi On 60 100` / `Midi Off 60` | Note einzeln ein / aus (bleibt, bis du `Off` sendest) |
| `Midi CC 7 100` | Controller 7 auf Wert 100 |
| `Midi PC 3` | Programmwechsel 3 |
| `Midi MSC Go 5 List 2` | **MIDI Show Control** senden (`Go`, `Stop`, `Resume`, `AllOff`, `Restore` …; optional `List <n>`, `Device <0–127>`) |
| `Midi Panic` | Alle Noten aus (alle Kanäle) |

Mit Button, Tastenkürzel, Cue-Befehl oder **Sprachsteuerung** kombinierbar („OpenCue, MIDI Note sixty“) – z. B. eine Cue, die in der Musiksoftware einen Ton auslöst. Auch über die **REST-API**: `POST /api/v1/command` mit `Midi Note 60`; `GET /api/v1/midi` liefert Geräte und Zustand.

---

## 5b. Zeit und Tempo von der Musiksoftware (MTC und MIDI-Takt)

Zwei Schalter unter **Einstellungen → Bedienung → MIDI** machen OpenCue zum Mitläufer einer Musiksoftware (DAW) oder eines anderen Geräts. Beide reagieren **nur auf das passende Format und nur, wenn wirklich etwas Gültiges eintrifft** – sonst passiert nichts. Solange einer an ist, bleiben die benutzten Geräte geöffnet.

**Timecode aus MIDI (MTC).** Sendet die Software *MIDI Timecode* (MTC, 24 / 25 / 29,97 / 30 Bilder pro Sekunde), läuft der **globale Timecode** im Takt dieser Zeit: Cues mit Auslöser „Timecode“, der Timecode-Player und die Panels folgen. Übernommen wird erst ein **lückenloser, plausibler Strom** (drei zusammenpassende Gruppen, Werte im gültigen Bereich); Rauschen, Rückwärtslauf und fremde Signale werden ignoriert. Weicht die eigene Uhr um mehr als 0,1 s ab, wird sie nachgestellt. **Bleibt der Strom aus** (Software gestoppt, Kabel ab), hält der Timecode an. Springt die Software bei stehender Zeit an eine Stelle (*Full Frame*), springt der Timecode mit. Ein von Hand gestarteter Timecode wird beim Ausbleiben **nicht** angehalten; solange MTC läuft, hat MTC Vorrang. Die Einstellungen zeigen die empfangene Zeit und die Bildrate.

**Senden: OpenCue als Zeitgeber.** *Timecode senden (MTC)* schickt den globalen Timecode als MIDI Timecode (Bildrate 24 / 25 / 29,97 / 30; Quarter Frames genau getaktet, bei Sprüngen eine Full-Frame-Nachricht) an den gewählten Ausgang. *MIDI-Takt senden* sendet *Start* / *Stop* und den Takt im Tempo des Audio-Panels, solange der Timecode läuft.

**Show Control empfangen (MSC).** Mit *Show Control empfangen* und einer **Geräte-Kennung** (0–127, 127 = alle) steuern GO, STOP, RESUME, ALL_OFF und RESTORE (auch mit Cue- und Listennummer) die Cue-Listen – z. B. aus einem Show-Programm oder Pult. Der Befehl `Midi MSC …` sendet sie.

**Tempo aus MIDI-Takt.** Ein **gleichmäßiger MIDI-Takt** (24 Impulse pro Viertelnote, 30 bis 300 BPM) setzt das Tempo als festes Tempo des Audio-Panels (wie der Befehl `BPM 128`) und folgt Tempowechseln. *Start*, *Stop* und *Weiter* belegst du als Signal (siehe oben).

Zum Ausprobieren ohne Software: ein MIDI-Timecode-Generator (es gibt kostenlose Programme und Webseiten) sendet über einen virtuellen MIDI-Anschluss (unter Windows z. B. *loopMIDI*) – beide Seiten wählen denselben Anschluss.

---

## 5c. Cue-Auslöser: MIDI

Neben *Go*, *Follow*, *Timecode* und *Audio* kann ein Cue den Auslöser **MIDI** haben: Er wartet dann auf **ein bestimmtes MIDI-Signal** und feuert, wenn es eintrifft – eine **Abfolge, die du mit Keyboard, Pad oder Fußschalter spielst**. Im Cue-Dialog (*Cue bearbeiten*) den Auslöser *MIDI* wählen, dann das **Signal** einstellen (oder **Signal einlernen** drücken und die Taste treffen – es wird eingetragen; Einlernen geht auch vom Tablet aus). In der Cue-Liste lässt es sich auch in die Auslöser-Zelle tippen (`midi note c4`, `midi cc 20 64`, `midi pc 5 ch 2`) oder per Befehl `Cue 3 Trigger Midi Note 60` setzen (siehe *Befehlszeile*).

| Signal | Der Cue feuert … |
|---|---|
| **Note** (Taste / Pad), Nummer 0–127 | … wenn die Taste gedrückt wird (Note On; Loslassen tut nichts). |
| **Regler (CC)**, Nummer 0–127, Schwelle 1–127 (Standard 64) | … wenn der Reglerwert die Schwelle **von unten erreicht**. Ein Pad, das als CC sendet (127), feuert sofort; ein Fader feuert, wenn er über die Schwelle geschoben wird – und wieder, nachdem er darunter zurückgezogen und erneut hochgeschoben wurde. |
| **Programmwechsel**, Nummer 0–127 | … wenn am Gerät dieses Programm gewählt wird. |

Jedes Signal lässt sich auf einen **Kanal** (1–16) begrenzen; *Beliebig* nimmt alle Kanäle und alle Geräte.

So funktioniert es:
- Wie beim Audio-Auslöser feuert der Cue, wenn er der **nächste Cue** einer laufenden Liste ist: erst die Liste mit *Go* starten, dann wartet der folgende MIDI-Cue auf sein Signal. Danach wartet der nächste Cue (wenn er ebenfalls einen MIDI-Auslöser hat) – so lässt sich eine ganze Abfolge an Tasten oder Pads hängen.
- Eine kurze Pause von 0,25 s nach jedem Auslösen verhindert, dass ein Schlag zwei Cues startet.
- **MIDI muss eingeschaltet sein** (*Einstellungen → MIDI → MIDI benutzen* oder der Schalter oben im Belegungs-Dialog). OpenCue öffnet die MIDI-Geräte von selbst, sobald irgendein Cue einen MIDI-Auslöser hat – dafür braucht es keine Zeile in der Belegung – und gibt sie wieder frei, wenn kein Cue MIDI mehr braucht. Unter *Einstellungen → MIDI* abgewählte Geräte bleiben zu.
- Der Auslöser gilt für jede Cue-Liste einzeln. Das Signal kommt von den MIDI-Geräten des **Konsolenrechners** (auch wenn du über ein Fernbedienungsgerät arbeitest).
- **Unterschied zur Belegung** (Abschnitt 3): Eine Belegungszeile führt **jederzeit** einen Befehl aus (z. B. `Go` oder `Cuelist "Main" Go Cue 5` = dorthin springen). Der Cue-Auslöser gehört zum **Cue selbst** und zählt nur, solange der Cue als Nächster dran ist. Beides lässt sich kombinieren; ein Signal, das beide benutzen, löst beides aus.

---

## 6. Wenn es nicht klappt

| Problem | Lösung |
|---|---|
| Gerät wird nicht erkannt | Anderes USB-Kabel/-Port; **Einstellungen → Ein- & Ausgänge** zeigt die Geräte alle paar Sekunden neu an; viele Geräte brauchen einen Moment nach dem Anstecken. |
| „belegt?“ am Gerät | Ein **anderes Programm** (Musiksoftware, Editor des Herstellers) hat das Gerät geöffnet – unter Windows kann es meist nur **ein** Programm lesen. Das andere Programm schließen, dann **MIDI aktiv** aus- und wieder einschalten. |
| Monitor zeigt nichts | Der Monitor läuft nur, solange der Dialog offen ist. Ist **MIDI aktiv** an? |
| Ein Cue mit dem Auslöser **MIDI** feuert nie | Er feuert nur, wenn er der **nächste Cue** einer **laufenden** Liste ist (die Liste vorher mit *Go* starten). *MIDI an* muss gesetzt sein, das Gerät darf unter *Einstellungen → MIDI* nicht abgewählt sein, und Nummer, Kanal und Art müssen zu dem passen, was der Monitor beim Drücken der Taste zeigt (im Cue-Dialog *Signal einlernen* benutzen). |
| Taste löst nichts aus | Kanal / Gerät in „Gilt für“ prüfen; Befehl in der Befehlszeile von Hand testen; Zeile leuchtet im Dialog? (dann kommt das Signal an, der Befehl ist das Problem). |
| Regler springt | Schalte in der Zeile **Aufnehmen** ein (Master und Fader): der Regler greift erst, wenn er den aktuellen Wert erreicht hat. |
| Musiksoftware und OpenCue sollen sich verbinden | Dafür braucht Windows einen **virtuellen MIDI-Anschluss** (kostenlos z. B. *loopMIDI*). Er erscheint dann als Eingang/Ausgang in beiden Programmen. |


---

## 7. Grenzen

- **Tablets:** Das iPad (Safari) kann kein MIDI im Browser. MIDI-Geräte gehören an den Konsolenrechner; die Belegung bearbeitest du von jedem Gerät.
- **Mehrere Programme:** Unter Windows liest meist nur **ein** Programm ein MIDI-Gerät (siehe „belegt?“). Neuere Windows-Versionen (*Windows MIDI Services*) können das ändern – OpenCue öffnet Geräte nur bei Bedarf und gibt sie mit **MIDI aktiv** aus wieder frei.
- **Netzwerk-MIDI und virtuelle Anschlüsse** richtet das Betriebssystem ein (z. B. *loopMIDI*, *rtpMIDI*); sie erscheinen dann wie jedes Gerät.
- **Controller-Profile:** Statt fester Profile für einzelne Modelle gibt es **Vorlagen mit Einlern-Reihe** – sie funktionieren mit jedem Controller. Die LED-Farben (Anschlagstärke) unterscheiden sich je Gerät; sie stehen bei der Rückmeldung unter *LED an / LED aus*.
- **Mehrere Belegungen zum Umschalten** (z. B. „Bühne“ und „Probe“): als Dateien über **Exportieren / Importieren** im Dialog; ein eigener Umschalter ist nicht eingebaut.
- Pitch-Bend, Aftertouch und Kanaldruck werden als Regler ausgewertet; es gibt keine Song-Position und keine MIDI-Ereignisse im WebSocket-Strom der API.
- Noch nicht mit allen Geräten ausprobiert: Regler, Drehgeber, Pads und Rückmeldung sind mit künstlichen Nachrichten getestet – der **Monitor** im Dialog zeigt, was dein Gerät wirklich sendet.

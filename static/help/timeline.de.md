# Timeline-Editor und LTC

Mit dem **Timeline-Editor** legst du Cues und Befehle grafisch auf eine Zeitachse – mit den Wellenformen deiner Lieder darunter. Mit **LTC** läuft OpenCue im Takt einer äußeren Quelle (Zuspieler, DJ- oder Show-Software, Pult) oder gibt selbst eine Uhr an andere Geräte aus. Alles baut auf dem **globalen Timecode** auf.

---

## 1. Die Idee in einer Minute

- OpenCue hat **eine** Uhr, den **Timecode** (Panel *Timecode*, Anzeige oben in der Werkzeugleiste). Er läuft, steht, springt – auf allen Geräten gleichzeitig.
- Zu bestimmten Zeiten dieser Uhr passiert etwas: ein **Cue** mit Auslöser *Timecode* startet, ein **Befehl** einer Befehlsspur wird ausgeführt, ein **Medien-Player** beginnt sein Lied (*Startzeit*). Das gilt immer nur, wenn die Uhr **vorwärts durch** die Zeit läuft – Springen und Rückwärtslauf lösen nichts aus.
- Die Uhr kann von **drei Quellen** geführt werden: dieser Computer (du drückst Start), **MIDI Timecode** (*Einstellungen → MIDI*) oder **LTC** (*Einstellungen → Timecode*). Wer zuerst da ist, führt.
- Der **Timeline-Editor** zeigt das alles auf einer Zeitachse und lässt dich es bequem setzen und verschieben – statt jede Zeit im Cue-Dialog zu tippen.

---

## 2. Den Timeline-Editor öffnen

- Als Panel im Layout: *Bearbeiten → Panel hinzufügen → Medien → **Timeline-Editor*** (am besten breit).
- Kurz als Fenster: *Ansicht → Panel als Fenster → **Timeline-Editor*** (dort stehen alle Panels, auch zum Beispiel **Einfache Steuerung**).

---

## 3. So sieht er aus

- **Lineal** oben: Klick oder Ziehen springt zu dieser Zeit.
- **Eine Spur je Cue-Liste**: jeder Cue mit Auslöser *Timecode* ist eine **Marke** mit Nummer und Name. Der Name der Liste links wählt sie aus (für das Tablett und „Cue hier setzen“).
- **Befehlsspuren** (rot / pink): Befehle der Befehlszeile zu Zeiten – siehe Abschnitt 6.
- **Tonspuren** unten: **von selbst** für jedes Lied, das ein Medien-Player zum Timecode abspielt, mit **Wellenform** und feinen Linien an jeder Marke – du siehst, ob etwas genau auf dem Einsatz liegt (Abschnitt 5).
- **Tablett** ganz unten: die **Cues ohne Zeit** der gewählten Liste.
- Der gelbe **Abspielkopf** ist der globale Timecode.

---

## 4. Marken bearbeiten und spulen

| Aktion | So geht es |
|---|---|
| Marke **verschieben** | mit Maus oder Finger waagerecht ziehen; sie rastet auf das **Raster** ein (**Umschalt** gedrückt halten = ohne Raster) |
| Marke **fein verschieben** | Marke anklicken, dann `←` / `→` (je Raster-Schritt; mit `Umschalt` zehnmal so viel) |
| Cue **ohne Zeit** auf die Zeitleiste legen | im **Tablett** auf die Spur ziehen – oder Chip wählen und **Cue hier setzen** |
| **Raster** | *aus*, 10 ms, Bild (25 fps), 0,1 s, 1 s |
| **Zoom** | Tasten `+` / `−`, Strg + Mausrad, **zwei Finger** (iPad); *Alles zeigen* (`F`) |
| **Folgen** | der Ausschnitt läuft mit dem Abspielkopf mit |

**Spulen** geht auf allen Wegen:

| Taste / Knopf | Wirkung |
|---|---|
| Lineal oder Wellenform **ziehen** | springt laufend dorthin (der Ton folgt) |
| Knöpfe **±5 s** | fünf Sekunden zurück / vor (schnell hintereinander klicken addiert sich) |
| Knöpfe **vorige / nächste Marke** (`[` / `]`) | springt zur nächsten Cue- oder Befehlszeit |
| `←` / `→` (Fokus im Panel) | 1 s; mit `Umschalt` 10 s; mit `Alt` ein Bild (40 ms) |
| `Pos1` / `Ende` | an den Anfang / an das Ende der Marken |
| `Leertaste`, `L`, `K`, `J` | abspielen / pausieren · vorwärts · Pause · **rückwärts** abspielen |
| Knopf **Rückwärts** | spielt den Timecode rückwärts (ändert nichts an Cues und Befehlen) |

---

## 5. Töne: von selbst aus den Medien-Playern

Du musst kein Lied in der Timeline wählen. Die Timeline sieht selbst nach, **was zum Timecode abgespielt wird**:

- Jeder **Medien-Player** im Modus **Timecode** mit einem gewählten Medium und seiner **Startzeit** erscheint als Tonspur: mit Namen, **Wellenform** und einer **Startmarke** (Notensymbol) an der Startzeit. Auch ein Player auf einem **anderen Gerät** (zum Beispiel am Hauptrechner, während du am iPad arbeitest) und die **Bildschirme der 3D-Simulation** erscheinen.
- Die **Startmarke ziehen** (oder doppelt anklicken und die Zeit tippen) ändert die **Startzeit des Medien-Players** – das Lied beginnt dann zur neuen Zeit.
- **Ton hinzufügen …** legt einen **eigenen Ton** dieser Timeline an (er läuft synchron zum Timecode), falls noch kein Medien-Player eingerichtet ist. Der Lautsprecher-Knopf schaltet nur diese eigenen Töne stumm. Auf dem iPad braucht der Browser eine Berührung des Panels, bevor Ton erlaubt ist.
- Die **Wellenform** berechnet OpenCue einmal mit dem mitgelieferten *ffmpeg* (alle 10 ms ein Wert) und merkt sie sich. Fehlt ffmpeg, steht das auf der Spur.
- Mit **LTC** gilt dasselbe: Die Medien-Player folgen dem Timecode, egal wer ihn führt – die Tonspuren zeigen also immer, was zu welcher Zeit läuft.

---

## 6. Befehlsspuren

Eine **Befehlsspur** führt **Befehle der Befehlszeile** zu Zeiten des Timecodes aus – unabhängig von den Cues, zum Beispiel `Blackout Off` bei 1:30, `Cuelist Show Go` bei 2:00 oder `Effect Off` beim Refrain. Sie gehört zur **Show** (wird mit ihr gespeichert und exportiert).

- **Neue Befehlsspur**: Knopf **+**. Es dürfen mehrere sein (zum Beispiel „Licht“, „Nebel“, „Video“); ein Doppelklick auf den Namen benennt um, das **×** löscht (zweimal klicken).
- **Befehl hinzufügen**: Knopf **Befehl hier** (oder `C`) setzt einen Befehl an die aktuelle Zeit der gewählten Spur – oder **Doppelklick** auf die Spur an die Stelle.
- Ein Eingabefenster fragt nach **Zeit** und **Befehl**; `Enter` übernimmt. Jede Marke lässt sich **ziehen**, mit den Pfeiltasten verschieben, per **Doppelklick** wieder bearbeiten und mit `Entf` löschen.
- Der **Server** führt den Befehl aus, wenn der Timecode **vorwärts durch** seine Zeit läuft – genau wie bei Cues (auch bei LTC / MIDI-Timecode). Er steht im Befehlsverlauf. Ein Sprung überspringt ihn.
- Im **Bedienmodus** lassen sich Befehlsspuren nicht ändern; sie laufen aber ganz normal.

---

## 7. Cues mit der Musik setzen (Aufnehmen)

So geht es wie an einem Pult, nur grafisch:

1. Lege deine Cues an (Cue-Liste) – ihre Zeit darf noch leer sein. Sie erscheinen im **Tablett**.
2. Richte einen **Medien-Player** mit deinem Lied ein (Modus Timecode, Startzeit 0) – die Wellenform erscheint von selbst.
3. Wähle die Cue-Liste und den ersten Cue im Tablett.
4. Starte die Wiedergabe (Leertaste) und tippe bei jedem Einsatz auf **Cue hier setzen** (oder `Enter`): der gewählte Cue bekommt die **aktuelle Zeit**, danach ist der **nächste** Cue gewählt.
5. Danach in Ruhe nachbessern: Marken an die Wellenform ziehen, einrasten lassen.

Tipp: Mit *Raster 1 s* oder *Bild* landen die Marken auf runden Zeiten, mit *aus* auf die Millisekunde genau.

---

## 8. LTC: der Timecode als Audiosignal

**LTC** (Linear Timecode) ist ein hörbares Signal – klingt wie Rauschen –, das die Uhrzeit trägt. Es liegt auf einem Kanal (meist links), die Musik auf dem anderen. *Einstellungen → Timecode* zeigt oben, **wer die Uhr gerade führt** (dieser Computer, MIDI-Timecode oder LTC), und hat zwei Bereiche:

**Eingang: Timecode lesen (LTC folgen)**

1. **LTC folgen** einschalten, **Audio-Eingang** wählen (Line-In, USB-Interface oder der *Systemton* eines Ausgabegeräts). Zum Ausprobieren gibt es das **Testsignal** (25 Bilder/s, ohne Gerät).
2. **Kanal** wählen (links / rechts / Mischung), **Speichern**. Darunter siehst du live **„Signal erkannt: 00:01:12:05 · 25 Bilder/s“** und einen Pegelbalken.
3. Sobald ein gültiges Signal ankommt, **läuft der globale Timecode mit**. Alle Cues, Befehle und Medien-Player folgen. **Pause oder Stopp der Quelle** hält auch hier den Timecode an, ein **Sprung** der Quelle wird mitgemacht.
4. Erkannt werden **24, 25, 29,97 (Drop Frame) und 30 Bilder pro Sekunde**.
5. Um selbst abzuspielen, schalte **LTC folgen** wieder aus.

**Ausgang: Timecode senden (LTC senden)**

OpenCue wird zur Uhr für andere Geräte: Startest du den Timecode (zum Beispiel im Panel *Timecode* auf Play), kommt **LTC aus einem Audio-Ausgang** – ein Zuspieler, ein Pult oder ein Rekorder kann mitlaufen.

1. **LTC senden** einschalten, **Audio-Ausgang** und **Kanal** wählen (*beide*, *nur links* oder *nur rechts* – nimm einen Kanal, wenn auf dem anderen Musik liegt).
2. **Bildrate** (24 / 25 / 29,97 Drop Frame / 30) und **Pegel** einstellen (kräftig, aber nicht übersteuert; viele Geräte erwarten Line-Pegel), **Speichern**.
3. Gesendet wird **nur, solange der Timecode vorwärts läuft**; steht er oder läuft er rückwärts, ist der Ausgang still. Springst du, beginnt das Signal sofort bei der neuen Zeit.
4. Folgt OpenCue selbst einer LTC- oder MIDI-Quelle, wird die Uhr ebenfalls weitergegeben.

**Wenn nichts ankommt:** Pegelbalken prüfen (zu leise?), Kanal (links / rechts), ob der Eingang von einem anderen Programm belegt ist.

---

## 9. Hinweise

- Eine **LTC- oder MIDI-Quelle führt** die Uhr: Start / Stopp im Timecode-Panel werden von der Quelle überstimmt, solange sie läuft.
- Die Zeiten gehören zu den **Cues**, den **Befehlsspuren** und den **Medien-Playern** der Show und werden mit ihr gespeichert; der Timeline-Editor ist nur das Werkzeug dafür.
- *Einstellungen → Ein-/Ausgänge* zeigt in der Gruppe **Timecode** auf einen Blick: wer die Uhr führt, LTC lesen / senden, MIDI-Timecode.
- Mehr zu den Quellen: Anleitung **MIDI** (MIDI Timecode), Anleitung **Fernzugriff** (iPad), Panel **Timecode** (Start, Pause, Springen, Tempo), **Medien-Player** (Startzeit).

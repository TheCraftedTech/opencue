# Audio: Lichter, die auf Musik reagieren

OpenCue kann Musik **mithören** und Lichter darauf reagieren lassen: heller mit dem Bass, ein Blitz bei jeder Bassdrum, Farben, die im Beat wechseln, ein Lauflicht im Takt. Die Analyse läuft live auf der Konsole, braucht kein Internet und belegt nur wenige Prozent eines Prozessorkerns.

---

## 1. Die Idee in einer Minute

- Das **Audio-Panel** nimmt eine Tonquelle und analysiert sie: Lautstärke, ein Spektrum, die Schläge von **Bassdrum, Snare und Hi-Hat**, das **Tempo (BPM)** und die Position im Beat.
- Die Ergebnisse stehen Effekten als **Variablen** zur Verfügung (`a_level`, `a_bass`, `a_kick`, `a_beat_phase` ...). Ein **Audio-Effekt** ist ein normales Effekt-Skript, das sie liest. Er funktioniert wie jeder andere Effekt: im Programmer Scheinwerfern zuweisen, in Cues speichern, ein- und ausblenden.
- 33 fertige Audio-Effekte gehören zum Programm. Sie tragen das Schlagwort **Audio** (wird automatisch gesetzt, sobald ein Effekt Audiowerte liest) – im Dialog zur Effekttyp-Wahl lässt sich danach filtern.
- Ohne laufende Quelle sind alle Audiowerte `0`: Ein Audio-Effekt bleibt dann einfach dunkel oder auf seinem Ruhewert.
- Auch Cues können **zur Musik** starten: der Cue-Auslöser *Audio* (Abschnitt 8).
- Die eigenen Buttons, Fader und Toggles der Konsole können der Musik folgen (Abschnitt 9), und die REST-API kann das Audio lesen und steuern (Abschnitt 10).

---

## 2. Schnellstart

1. Das Panel hinzufügen: **Bearbeiten → Panel hinzufügen…** → Kategorie *Medien & Zeit* → **Audio**.
2. In der Quellenliste **Demo-Beat** wählen und **Start** drücken. Ein Schlagzeug-Loop mit 120 BPM wird analysiert – du siehst das Spektrum, die Lampen *Kick / Snare / Hi-Hat / Beat* blitzen, und das Tempo erscheint.
3. Im Programmer einige Scheinwerfer wählen, den Reiter **Effekte** öffnen und auf **Effekt hinzufügen** klicken, den Effekttyp **Kick Flash** (oder *Bass Dimmer*, *Beat Chase* ... – Tipp: nach dem Schlagwort *Audio* filtern) wählen und erstellen. Die Scheinwerfer blitzen jetzt mit dem Demo-Beat.
4. Die Quelle auf die echte Musik umstellen (nächster Abschnitt).

Bestehende Installationen bekommen die neuen Effekte im **Dateimanager** (Liste *Effekte*) über **Standard-Effekte wiederherstellen**. Das legt nur *fehlende* Dateien an und überschreibt nie: Hast du früher schon eine ältere Fassung wiederhergestellt, lösche zuerst die alten `audio_*.fx` im Dateimanager und stelle dann erneut wieder her.

---

## 3. Die Quelle wählen

Die Liste zeigt alles, was Windows kennt:

| Gruppe | Was es ist | Typischer Einsatz |
|---|---|---|
| **Systemton** | Was dieser Computer über Lautsprecher oder Kopfhörer abspielt („Loopback“). Ein Eintrag je Ausgabegerät. | Musik vom selben Computer (DJ-Software, Spotify, Browser). Kein Kabel, kein Mikrofon. |
| **Eingänge** | Mikrofone, Line-In-Buchsen und USB-Audio-Interfaces. | Musik von einem Mischpult oder Handy: das Kabel in den **Line-In** oder das Interface stecken. Ein Laptop mit nur einer kombinierten Headset-Buchse behandelt sie als *Mikrofon*: Das Signal ist schwächer, dann die **Eingangsverstärkung** erhöhen. Ein Mikrofon im Raum geht ebenfalls, aber die Musik muss laut und klar sein. |
| **Test** | Der Demo-Beat. | Effekte ohne Musik ausprobieren. |

Einträge mit *(Standard)* sind die, die Windows standardmäßig verwendet. **Neu suchen** (der Pfeile-Knopf) sucht die Geräte erneut, nachdem etwas angesteckt wurde.

**Start** drücken. Die Quelle bleibt offen, bis du **Stopp** drückst; beim nächsten Programmstart öffnet sie sich von selbst wieder. Lässt sich eine Quelle nicht öffnen, sagt das Panel, warum (von einem anderen Programm belegt, in den Windows-Datenschutzeinstellungen *Mikrofon* gesperrt, abgezogen).

---

## 4. Was das Panel zeigt

- **Spektrum:** 32 Balken von 30 Hz bis 16 kHz (tiefe Töne links). Der Rahmen glimmt bei jedem Beat.
- **Lampen:** *Kick*, *Snare*, *Hi-Hat* leuchten bei jedem Schlag; *Beat* bei jedem Beat des Tempos.
- **Pegel** mit einer Marke *Übersteuert*: leuchtet, wenn das Signal abgeschnitten wird (am Eingang zu laut; Lautstärke oder Verstärkung senken).
- **Tempo:** die BPM in großen Ziffern, eine Beat-LED, ein Balken mit der Position im Beat und ein dünner Balken für die Sicherheit der Erkennung.

---

## 5. Tempo: automatisch, getippt oder fest

- **Auto** erkennt das Tempo aus der Musik (70 - 180 BPM). Es braucht einige Sekunden und einen gleichmäßigen Beat; es folgt Tempowechseln.
- **Tap:** den Knopf im Takt der Musik antippen (auch der Befehl `Tap`). Ab dem zweiten Tipp wird das Tempo aus deinen Tipps gesetzt, und der Beat beginnt genau auf dem Tipp. Das Tempo ist dann *Manuell*.
- **÷2 / ×2:** wenn die Erkennung das halbe oder doppelte Tempo gefunden hat (typisch bei sehr langsamer oder sehr schneller Musik).
- **Manuell:** das Tempo ist fest; ins Feld eintippen. Mit *Manuelles Tempo: der Beat folgt der Musik* passt sich die Beat-Position weiter sanft den Schlägen an. Ohne Musik läuft ein festes Tempo wie ein **Metronom** – Effekte mit `a_beat_phase` laufen weiter im Takt.
- **Auto** schaltet zurück auf die Erkennung.

Befehle: `Tap`, `BPM 128`, `BPM Auto`, `BPM Half`, `BPM Double`, `Audio Start`, `Audio Stop`, `Audio Demo`, `Audio Status`.

---

## 6. Einstellungen

| Einstellung | Was sie tut |
|---|---|
| **Eingangsverstärkung** | Verstärkt (×0,1 bis ×10) ein schwaches Signal, z. B. ein Mikrofon. |
| **Automatische Verstärkung** | Die Analyse misst gegen die lautesten Stellen der letzten Sekunden; ein leises Lied funktioniert dadurch wie ein lautes. Ausschalten für eine feste Skala (dann wirkt die Verstärkung direkt). |
| **Beat-Empfindlichkeit** | Höher: auch leise Schläge zählen (Risiko: falsche Schläge). Niedriger: nur deutliche Schläge zählen. |
| **Glättung** | Wie langsam die Pegel und Bänder zurückfallen. |
| **Zeitversatz** | −100 bis +200 ms. Positiv: die Lichter reagieren **früher** – hilfreich, wenn Lichter oder Lautsprecher zu spät kommen. |

Die Einstellungen gehören zur Konsole (nicht zu einer Show oder einem Panel) und werden automatisch gespeichert. Jedes Gerät mit einem Audio-Panel zeigt und bedient dieselbe Quelle.

---

## 7. Die fertigen Audio-Effekte

| Effekt | Kategorie | Was er tut |
|---|---|---|
| Band Bars | Dimmer | Jeder Scheinwerfer zeigt ein Frequenzband: der erste die Tiefen, der letzte die Höhen (wiederholt sich bei mehr als 8 Scheinwerfern). |
| Bass Dimmer | Dimmer | Die Helligkeit folgt dem Bass der Musik. |
| Beat Chase | Dimmer | Ein Lauflicht, das bei jedem Beat (oder jedem n-ten) weiterspringt. |
| Beat Pulse | Dimmer | Die Helligkeit pulsiert im Takt der Musik: hell auf dem Beat, dann weich abklingend. |
| Beat Strobe | Dimmer | Stroboskop im Takt der Musik: mult Blitze pro Beat, phasenstarr zum Tempo. |
| Beat Toggle | Dimmer | Schaltet bei jedem Beat (oder jedem n-ten) zwischen zwei Gruppen um, hart oder überblendet (soft). |
| Hi-Hat Sparkle | Dimmer | Bei jedem Hi-Hat-Schlag funkeln zufällig ausgewählte Scheinwerfer auf. |
| Kick Chase | Dimmer | Ein Lauflicht, das bei jedem Bassdrum-Schlag (statt im Beat) weiterspringt. |
| Kick Flash | Dimmer | Bei jedem Bassdrum-Schlag blitzen die Scheinwerfer auf und klingen ab. |
| Level Dimmer | Dimmer | Die Helligkeit folgt der Gesamtlautstärke. |
| Snare Flash | Dimmer | Bei jedem Snare-Schlag (oder Klatschen) blitzen die Scheinwerfer auf und klingen ab. |
| Beat Color | Farbe | Die Farbe wechselt bei jedem Beat (oder jedem n-ten) und leuchtet auf dem Beat am hellsten. |
| Beat Color Chase | Farbe | Ein farbiges Licht (A) läuft über eine Hintergrundfarbe (B), ein Schritt pro Beat (oder jedem n-ten). |
| Beat Color Fade | Farbe | Blendet im Takt der Musik zwischen zwei Farben. |
| Beat Color Strobe | Farbe | Ein farbiges Stroboskop im Takt der Musik: mult Blitze pro Beat, abwechselnd in Farbe A und B. |
| Color Blend | Farbe | Blendet von Farbe A (leise) zu Farbe B (laut). |
| Color Hit | Farbe | Die Grundfarbe blitzt bei jedem Schlag der gewählten Trommel in die Blitzfarbe. |
| Hi-Hat Color Sparkle | Farbe | Bei jedem Hi-Hat-Schlag blitzen zufällig ausgewählte Scheinwerfer in einer zufälligen Farbe (im Farbbereich). |
| Hue Drift | Farbe | Die Farben wandern durch den Farbbereich, ein voller Durchlauf dauert beats Beats. |
| Kick Color Flash | Farbe | Die Grundfarbe blitzt bei jedem Bassdrum-Schlag in die Blitzfarbe. |
| Spectrum Color | Farbe | Die Farbe mischt sich aus der Musik: Bass = Rot, Mitten = Grün, Höhen = Blau. |
| Spectrum Hue | Farbe | Die Farbe folgt dem Klang: bassige Musik zeigt den Anfang des Farbbereichs, helle Klänge sein Ende. |
| Bass Tilt | Position | Der Tilt folgt dem Bass: leise = nach unten, kräftiger Bass = nach oben (um die Grundposition). |
| Beat Circle | Position | Die Köpfe fahren im Takt der Musik einen Kreis: eine Umdrehung dauert beats Beats. |
| Beat Fan | Position | Die Scheinwerfer fächern im Takt der Musik auf und zu. |
| Kick Tilt Punch | Position | Bei jedem Bassdrum-Schlag schlagen die Köpfe im Tilt aus und setzen sich auf die Grundposition zurück. |
| Level Spread | Position | Je lauter die Musik, desto weiter fächern die Scheinwerfer auf (symmetrisch um die Grundposition). |
| Pan/Tilt Sway | Position | Die Köpfe bewegen sich im Takt der Musik. |
| Snare Pan Snap | Position | Bei jedem Snare-Schlag springt jeder Kopf zur nächsten von vier Pan-Positionen. |
| Beat Zoom Pulse | Zoom | Der Zoom pulsiert bei jedem Beat: high auf dem Beat, dann zurück auf low. |
| Kick Zoom Punch | Zoom | Der Zoom schlägt bei jedem Bassdrum-Schlag von low nach high aus und fällt zurück. |
| Bass Focus | Fokus | Der Fokus folgt dem Bass der Musik. |
| Beat Gobo Change | Gobo | Das Gobo wechselt bei jedem Beat (oder jedem n-ten). |

Fast jeder Effekt hat Optionen, um **Animationen umzuschalten** und ein **Stroboskop** zuzufügen: *strobe* (Blitze pro Sekunde, 0 = aus), *mode* (zum Beispiel alle gemeinsam / gerade-ungerade im Wechsel / zufällig), *direction* (Lauflicht vorwärts, rückwärts, hin und her, zufällig), *every* (nur jeden n-ten Beat wechseln), *soft* (hart umschalten oder überblenden). Es sind normale Effekte: in Cues speichern, variieren, kopieren.

---

## 8. Cue-Auslöser: Audio

Neben *Go*, *Follow*, *Timecode* und *MIDI* (Anleitung *MIDI*) kann ein Cue den Auslöser **Audio** haben: Er feuert dann von selbst **zur Musik**. Im Cue-Dialog den Auslöser *Audio* wählen, **eine Quelle** wählen und bei Bedarf einen Wert – in der Cue-Liste lässt es sich auch tippen (`audio kick`, `audio beat 4`, `audio bass 70`) oder per Befehl setzen: `Cue 2 Trigger Audio Beat 4`.

| Quelle | Wert | Der Cue feuert … |
|---|---|---|
| **Beat (Tempo)**, **Bassdrum**, **Snare**, **Hi-Hat** | jeder n-te (1 bis 64, Standard 1) | … bei jedem n-ten Beat bzw. Schlag. |
| **Gesamtpegel**, **Bass**, **Mitten**, **Höhen** oder eines der **acht Bänder** (in der Liste mit ihrem Hz-Bereich) | Schwelle in % (Standard 70) | … wenn dieser Teil des Klangs die Schwelle **von unten erreicht**. |

So funktioniert es:
- Der Cue feuert, wenn er der **nächste Cue** einer laufenden Liste ist: Die Liste zuerst mit *Go* starten, dann wartet der folgende Audio-Cue auf sein Ereignis. Nach dem Feuern wartet der Cue dahinter (wenn er ebenfalls den Auslöser *Audio* hat) – so lässt sich eine ganze Folge an die Musik hängen.
- Der Zähler (*jeder n-te*) beginnt bei 0, sobald ein neuer Cue aktiv wird.
- Bei einer Schwelle feuert der Cue einmal, wenn der Pegel sie erreicht; erst nachdem der Pegel deutlich darunter gefallen ist (etwa 80 % der Schwelle), ist er wieder scharf. Liegt der Pegel schon darüber, wenn der Cue der nächste wird, wartet er auf den nächsten Anstieg.
- Nach einem Auslösen gibt es eine kurze Pause (0,25 s), damit ein Schlag nie zwei Cues startet.
- Das **Audio-Panel muss laufen** (eine Quelle gestartet); ohne Ton feuert nichts. Der Auslöser arbeitet für jede Cue-Liste für sich.

---

## 9. Buttons, Fader und Toggles, die auf die Musik reagieren

Die eigenen **Button-**, **Fader-** und **Toggle-Panels** der Konsole können die Musik als *Signal* benutzen – bei *Folgt dem Zustand von* (ein Fader bewegt sich mit der Musik, ein Toggle schaltet mit dem Signal) und in den **Bedingungen der Regeln** (Farbe, Text oder Befehl, wenn …). Die Signale stehen in der Gruppe **Audio**:

| Signal | Bedeutung |
|---|---|
| **Audiosignal vorhanden** | an, solange eine Quelle offen ist und etwas spielt |
| **Gesamtpegel**, **Bässe**, **Mitten**, **Höhen** | 0–100 % |
| **Bassdrum**, **Snare**, **Hi-Hat**, **Beat** (Impuls) | springen bei jedem Schlag auf 100 % und klingen ab |
| **Tempo (BPM)** | das erkannte oder eingestellte Tempo |

Beispiele: ein Fader, der den Bässen folgt, als Pegelanzeige; ein Button, der rot leuchtet, wenn das Tempo zwischen 120 und 130 BPM liegt; ein Toggle, der zeigt, ob Musik ankommt. Die Audioquelle läuft an der Konsole; ein Panel muss nur auf dem Bildschirm irgendeines Geräts stehen – die Messwerte gehen genau so lange an ein Gerät, wie dort so ein Panel (oder das *Audio*-Panel) offen ist.

## 10. Audio über die API

Die REST-API kann die Analyse lesen (`GET /api/v1/audio`), die Quelle öffnen und schließen, die Einstellungen ändern und das Tempo antippen (`PUT /api/v1/audio`, `POST /api/v1/audio/tap`, Berechtigung *Audio*), und der **Live-Ereignisstrom** (`GET /api/v1/events?events=audio,beat,hit`) meldet die Quelle, jeden Beat und jeden Schlag, sobald er passiert. Siehe die Anleitung *REST-API*.

## 11. Einen eigenen Audio-Effekt schreiben

Im **Effekt-Studio** einen Effekt anlegen und die Audio-Variablen lesen – siehe die Anleitung *Effekt-Studio*, Abschnitt *Audio-Variablen*. Ein erstes Beispiel:

```
#NAME Mein Blitz
#CATEGORY dimmer
#RATE 40
#VAR peak Slider 100 0 100 1

loop() {
  dimmer = peak * a_kick;
}
```

Die Vorschau im Studio spielt einen Beispiel-Takt (120 BPM), du siehst also sofort, wie sich die Kurve verhält.

---

## 12. Wenn etwas nicht klappt

| Problem | Prüfen |
|---|---|
| Die Quelle lässt sich nicht öffnen | Ein anderes Programm belegt sie exklusiv; das Mikrofon ist in den Windows-Datenschutzeinstellungen gesperrt (*Einstellungen → Datenschutz → Mikrofon*); das Gerät ist abgezogen. |
| Das Panel zeigt nichts / alles flach | Ist die Quelle *gestartet*? Bewegt sich der Windows-Lautstärkemesser? **Eingangsverstärkung** erhöhen. Beim *Systemton* muss das Programm wirklich auf diesem Ausgabegerät abspielen. |
| *Übersteuert* leuchtet | Das Signal ist zu laut: Lautstärke an der Quelle oder die Eingangsverstärkung senken. |
| Die BPM springen oder sind halb / doppelt | **÷2 / ×2** drücken, das Tempo tippen oder mit *Manuell* festlegen. Musik ohne gleichmäßigen Beat (Klassik, Sprache) hat kein erkennbares Tempo. |
| Lichter reagieren zu spät | Den **Zeitversatz** nutzen (positive Werte). |
| Ein Audio-Effekt bleibt dunkel | Keine Quelle läuft, oder die Empfindlichkeit ist für die Musik zu niedrig; den *gain*-Regler des Effekts erhöhen. |

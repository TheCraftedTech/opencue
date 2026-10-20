# Befehlszeile – Befehlsreferenz

Die **Befehlszeile** steuert OpenCue per Tippen, im Stil professioneller Lichtstellpulte (dot2 / MA Lighting). Sie ergänzt die Bedienung mit Maus und Touch um kurze Befehle, die sich tippen, verketten und in Cues ablegen lassen. Sie steht als Panel **Befehlszeile** zur Verfügung (*Bearbeiten → Panel hinzufügen…*); die Panels **Befehls-Ziffernblock** und **Befehls-Tasten** schreiben für die Touch-Bedienung in dieselbe Eingabezeile.

Jeder Befehl wird auf dem Server ausgeführt, und das Ergebnis geht an **alle** verbundenen Geräte: Scheinwerferliste, Cue-Liste und Programmer aktualisieren sich überall sofort, nicht nur dort, wo getippt wurde.

> Die Befehlswörter sind – wie bei dot2 und MA Lighting üblich – **Englisch**. Groß- und Kleinschreibung spielt bei Befehlen, Attributen und Namen **keine** Rolle.

---

## 1. Die Idee in einer Minute

Jeder Befehl folgt demselben Muster: **was** – **welche** – **Wert**.

| Aktion / Objekt | ID / Bereich | Eigenschaft / Ziel |
|---|---|---|
| `Fixture` | `1` | – |
| `At` | – | `80` |
| `Store` | `Cue 1.5` | – |
| `Cue` | `1` | `Fade 3` |
| `Cuelist` | `Show` | `Go` |

- **Aktion oder Objekt** steht immer an erster Stelle (`Fixture`, `Group`, `At`, `Color`, `Pan`, `Zoom`, `Store`, `Cue`, `Go`, `Cuelist` …).
- **ID oder Bereich** sagt, WAS betroffen ist: eine Fixture-Nummer (FID), ein Name, eine Cue-Nummer, ein Cue-Listen-Name oder ein Bereich (`1 Thru 10`).
- **Eigenschaft oder Ziel** ist der eigentliche Wert: Prozent, Grad, Zeit, Name, Farbe.
- Befehle **bauen aufeinander auf**, wie am echten Pult: Zuerst wählt man aus (`Fixture 1 Thru 4`), danach wirkt ein Wertbefehl (`At 80`) auf genau diese Auswahl. Die Auswahl wird von **allen Geräten geteilt**: ein Klick in der Scheinwerferliste auf einem Bildschirm und ein `Fixture`-Befehl auf einem anderen arbeiten auf derselben Auswahl.
- Texte mit Leerzeichen (Cue-Name, Listenname) kommen in doppelte Anführungszeichen: `Label Cue 1 "Intro Szene"`. Ein Wort in Anführungszeichen ist immer ein **Name** und nie ein Befehlswort – so lässt sich auch eine Gruppe „Color“ ansprechen.
- Eingaben werden geprüft: ungültige Zahlen (`Zoom abc`), unbekannte Attribute oder Namen und fehlende Werte ergeben eine Fehlermeldung, **ohne** dass etwas verändert wird.

```
Fixture 1 Thru 4 At 80
Fixture 1 Thru 4 Color Red
Store Cue 1 "Auftakt"
Go
```

---

## 2. Scheinwerfer und Gruppen auswählen

| Befehl | Wirkung |
|---|---|
| `Fixture 1` | Wählt die Fixture mit FID 1 (ersetzt die bisherige Auswahl). |
| `Fixture 1 Thru 10` | Wählt FID 1 bis 10. |
| `Fixture 1 + 3` | Wählt FID 1 **und** 3 (beliebig oft mit `+` kombinierbar). |
| `Fixture 1 Thru 5 + 10` | Wählt FID 1–5 und zusätzlich 10. |
| `Fixture "Kopf 2"` | Wählt die Fixture(s) mit diesem **Namen** (auch mit `+` kombinierbar). |
| `Group 1` | Wählt die 1. Gruppe der Gruppenliste. |
| `Group 1 Thru 4` | Wählt die Fixtures der Gruppen 1 bis 4. |
| `Group Front` | Wählt die Gruppe mit diesem **Namen** (`Group "Front Truss"` bei Leerzeichen). |

`Group N` meint die **N-te angelegte Gruppe**. Einfacher und stabiler ist der Name: `Group Front` funktioniert unabhängig von der Reihenfolge.

Ein einzelnes Wort darf ohne Anführungszeichen stehen, wenn es keinem Befehlswort gleicht und den Namen wirklich gibt. Sonst gilt: Namen mit Leerzeichen, Komma, Semikolon oder `+` und Namen, die wie ein Befehl oder eine Zahl aussehen, immer in `"…"` setzen.

### Gruppen anlegen, umbenennen, löschen

Die **aktuelle Auswahl** lässt sich als Gruppe speichern:

| Befehl | Wirkung |
|---|---|
| `Store Group "Front"` | Legt die Gruppe aus der aktuellen Auswahl an. |
| `Store Group "Front" Merge` | Gibt es sie schon: die Auswahl kommt **dazu**. |
| `Store Group "Front" Overwrite` | Gibt es sie schon: die Mitglieder werden **ersetzt**. |
| `Label Group Front "Bühne vorn"` | Benennt um (`Set Group 2 Name "Bühne vorn"` geht auch, auch per Nummer). |
| `Delete Group Front` | Löscht die Gruppe (`Delete Group 2` per Nummer) – die Geräte bleiben. |

Ohne Auswahl meldet `Store Group` einen Fehler; ein vorhandener Name (Groß-/Kleinschreibung egal) wird nie stillschweigend überschrieben. Ein Gerät gehört höchstens einer Gruppe an.

---

## 3. Werte setzen: At / Full

Wirkt auf die **aktuell ausgewählten** Fixtures (Dimmer-Kanal).

| Befehl | Wirkung |
|---|---|
| `At 80` | Dimmer auf 80 % (`At 80%` geht auch). |
| `At Full` | Dimmer auf 100 %. |
| `At At` | Wie `At Full` (dot2-Kurzform – zweimal „At“). |
| `Full` | Kurzform ohne führendes „At“ – ebenfalls 100 %. |
| `At 0` | Dimmer auf 0 % (aus). |
| `At +10` / `At -10` | Erhöht / verringert den aktuellen Dimmerwert um 10 Prozentpunkte. |

Werte werden auf 0–100 % begrenzt. `At +` / `At -` bezieht sich auf den zuletzt im Programmer gesetzten Wert jeder Fixture (oder auf den aktuell ausgegebenen DMX-Wert, falls noch nichts programmiert wurde).

Betroffene Fixtures erhalten in der Scheinwerferliste eine rote Markierung – sie sind jetzt „im Programmer“ und lassen sich mit `Store Cue` sichern.

### Master (Gesamthelligkeit)

`Master` (Kurzform `GrandMaster`) skaliert die Ausgabe **aller** Dimmer-Kanäle in Prozent. Standard ist 100 %. Der Wert bleibt bis zur nächsten Änderung bestehen und wird mit dem Showfile gespeichert.

| Befehl | Wirkung |
|---|---|
| `Master 80` / `Master At 80` | Gesamthelligkeit 80 % (das Wort `At` ist optional). |
| `Master Full` | 100 %. |
| `Master -10` / `Master +10` | Um 10 Prozentpunkte verringern / erhöhen. |

Der Master skaliert nur Dimmer-Kanäle; Farben und Pan/Tilt bleiben unverändert. (Der **Fader einer Cue-Liste** ist etwas anderes – siehe Kapitel 10.)

### Blackout

`Blackout` dreht die **Helligkeit aller Geräte auf 0** und stellt sie beim nächsten `Blackout` wieder her. Ein Umschalter, unabhängig vom Master.

| Befehl | Wirkung |
|---|---|
| `Blackout` | Umschalten. |
| `Blackout On` / `Blackout Off` | Ein- / ausschalten (`1`/`0`, `True`/`False` gehen auch). |

**Der Blackout hat Vorrang vor allem anderen** – Fader, Befehle, Cues, Überblendungen und laufende Effekte: Solange er aktiv ist, bleibt die Helligkeit jedes Geräts auf 0, in der DMX-Ausgabe **und** in der 3D-Simulation. Die Werte bleiben erhalten: Während des Blackouts lassen sich Helligkeiten normal ändern, und nach `Blackout Off` erscheint der **zuletzt eingestellte** Stand. Geräte **ohne** Dimmer-Kanal (reine RGB-Geräte) werden über ihre Farbe abgedunkelt. Ein pulsierender Glühbirnen-Knopf in der Werkzeugleiste zeigt den aktiven Blackout; ein Klick schaltet um. Der Zustand gilt für alle Geräte, wird aber **nicht** in der Show gespeichert.

### Timecode: `Timecode` / `TC`

Der globale Timecode (die interne Uhr) lässt sich auch per Befehl steuern – zum Beispiel im **CMD**-Feld eines Cues (`Timecode Play` startet die Uhr, sobald der Cue feuert).

| Befehl | Wirkung |
|---|---|
| `Timecode` | Zeigt den Stand (Zeit, läuft/steht, Geschwindigkeit). |
| `Timecode At 4.3` | Springt auf 4,3 s (auch `00:00:04.300`, `1:04.300`; höchstens 100 h). |
| `Timecode At 4.3 Play` | Springt und startet gleich (`Reverse` startet rückwärts). |
| `Timecode +5` / `Timecode -2` | Relativ: 5 s vor / 2 s zurück. |
| `Timecode Play` / `Reverse` | Vorwärts / rückwärts laufen lassen. |
| `Timecode Pause` | Anhalten. |
| `Timecode Stop` (`Reset`) | Anhalten und auf 00:00:00.000 setzen. |
| `Timecode Rate 2` | Geschwindigkeit (0,1 … 8; auch `0.5x`). |

Springen löst keine Timecode-Cues aus; nur der laufende Vorwärtslauf tut das.

---

## 4. Farbe und Position: Color / RGB / Pan / Tilt

Wirken ebenfalls auf die **aktuell ausgewählten** Fixtures.

| Befehl | Wirkung |
|---|---|
| `Color Red` | Setzt die Farbe auf Rot (benannte Farbe, Liste unten). |
| `Color #FF8000` | Farbe als Hex-Wert (`#F80` als Kurzform geht auch). |
| `Color 255 128 0` | Farbe als drei Werte 0–255 (Rot / Grün / Blau). |
| `RGB 255 0 0` | Dasselbe (dot2-Schreibweise). |
| `Pan 180` | Fährt Pan auf 180°. |
| `Tilt -45` | Fährt Tilt auf -45°. |
| `Pan 50%` | Pan in Prozent des Bereichs (0–100 %; 50 % = Mitte). |
| `Pan +10%` / `Tilt -5%` | Relativ zum aktuellen Wert, in Prozent des Bereichs. |
| `Pan +15` / `Tilt -15` | Relativ in Grad (mit Vorzeichen). |

**Benannte Farben:** `Red`, `Green`, `Blue`, `White`, `Black`, `Yellow`, `Cyan`, `Magenta`, `Orange`, `Pink`, `Purple`, `Amber`, `Lime`, `Teal`, `Violet`, `LightBlue`, `Warm`, `Cool`.

**Gradbereich bei Pan/Tilt:** OpenCue liest den tatsächlichen Bewegungsbereich (physical range) aus dem GDTF-Profil der Fixture aus; verschiedene Geräte stehen bei demselben Gradwert deshalb leicht unterschiedlich. Ist im Profil kein Bereich hinterlegt, gilt der Standard: **Pan -270° bis +270°, Tilt -135° bis +135°**.

---

## 5. Beam-Attribute und Kanäle: Zoom, Gobo, CH …

Neben Helligkeit, Farbe und Position lässt sich **jeder Kanal** eines Geräts setzen – auf zwei Wegen: über **Attributnamen** (Prozent, gleiche Logik wie die Fader im Programmer) oder direkt über **Kanalnummern** bzw. **-namen** (wie im „DMX direkt“).

### Attribute in Prozent

| Befehl | Wirkung |
|---|---|
| `Zoom 50` | Zoom auf 50 % (auch `Zoom Full`, `Zoom Half`, `Zoom Min`, `Zoom 50%`). |
| `Focus 25` | Fokus. |
| `Gobo 40` / `Gobo2 40` | Gobo-Rad 1 / 2 (Auswahl; Zahl = Prozent des Kanals). |
| `GoboSpin 30` / `Gobo2Spin 30` | Drehung / Position des Gobo-Rads. |
| `Prism 100` | Prisma. |
| `Strobe 0` (`Shutter 0`) | Shutter / Strobe. |
| `Zoom +10` / `Zoom -20` | Relativ zum aktuellen Wert (Prozentpunkte). |

Alle Werte laufen 0–100 und werden wie bei den Fadern gespeichert: ein `Store Cue` übernimmt sie. Hat ein Gerät den Kanal nicht (ein reiner Dimmer hat keinen Zoom), wird es übersprungen, und die Rückmeldung nennt es: `OK: Zoom 50 applied to 3 fixtures (Zoom not available on 1 of 3 fixtures)`. Hat **keines** der gewählten Geräte den Kanal, ist das ein Fehler, und es wird nichts verändert.

### Kanäle nach Nummer: `CH` / `Channel`

| Befehl | Wirkung |
|---|---|
| `CH6 128` | Kanal 6 **des Geräts** (1 = erster Kanal der Fixture) auf DMX-Wert 128. |
| `Channel 6 128` | Dasselbe, mit Leerzeichen (auch `CH 6 128`). |
| `CH6 50%` | Mit `%`: Prozent statt DMX-Wert (50 % = 128). |
| `CH6 +20` | Relativ: 20 DMX-Stufen mehr (`-20` weniger). |
| `CH6 Full` | 255 (auch `Half` = 50 %, `Min` = 0). |

Die Kanalnummer bezieht sich auf die **Reihenfolge im Modus des Geräts** (im Tab „DMX direkt“ des Programmers sichtbar), nicht auf die DMX-Adresse: `Fixture 5 Thru 8 CH6 255` setzt den 6. Kanal jeder gewählten Fixture, egal wo sie gepatcht ist. Der Wert ist wie im DMX direkt **0–255**.

### Kanäle nach Name

Jeder GDTF-Kanalname des Geräts lässt sich direkt als Klausel verwenden (Wert in **Prozent**):

```
Fixture 1 Frost 50        Iris 30        Cyan 100
Channel Frost1 50         CH Frost 50
```

Der Name darf verkürzt sein, solange er eindeutig bleibt (`Frost` für `Frost1`); gängige Kurznamen sind eingebaut (`Cyan`, `Magenta`, `Yellow` für CMY-Kanäle, `Red`/`Green`/`Blue` für RGB-Kanäle, `Intensity` für den Dimmer). Welche Namen ein Gerät hat, zeigt der Autocomplete (Kapitel 14).

Kanäle mit eigenem Attribut (Dimmer, Pan, Tilt, Zoom, Fokus, Gobo-Rad, Prisma, Shutter) werden als dieses Attribut gespeichert; alle anderen (Frost, Iris, Farbrad, Fein-Kanäle …) als roher Kanalwert. Beides übernimmt `Store Cue`.

---

## 6. Variablen, Effekte, Manuell

Variablen (Presets) und Effekte lassen sich auf die **aktuelle Auswahl** anwenden – allein oder als Klausel hinter einer Auswahl wie jedes andere Attribut.

| Befehl | Wirkung |
|---|---|
| `Variable "Warm White"` | Wendet die Variable an **und verknüpft** sie: die Geräte folgen ihr, bis ein Wert, ein Effekt oder ein Cue das Attribut übernimmt (ändert man die Variable, ändern sich die Geräte mit). Kurzformen: `Var`, `Preset`. |
| `Effect Regenbogen` | Weist den Effekt zu (die Kategorie ergibt sich aus dem Effekt). Mehrere Geräte laufen mit Phasenversatz wie im Dropdown. |
| `Effect Off` | Beendet **alle** Effekte der Auswahl; `Effect Off color position` nur die genannten Kategorien. |
| `Manual` | Zurück auf **Manuell**: löst die Variablen-Verknüpfung **und** den Effekt aller Kategorien; die zuletzt ausgegebenen Werte bleiben stehen. |
| `Manual color` | Nur diese Kategorie (`dimmer`, `color`, `position`, `zoom`, `focus`, `gobo`, mehrere nacheinander oder `all`). |

Variablen- und Effektnamen sind in OpenCue eindeutig; Groß-/Kleinschreibung spielt keine Rolle. Mit Leerzeichen entweder in `"…"` oder einfach hintereinander (`Variable warm white`). Ein unbekannter Name ergibt eine Fehlermeldung mit der Liste der vorhandenen. Der Autocomplete schlägt Variablen (mit ihrem Typ) und Effekte (mit ihrer Kategorie) vor.

```
Fixture 1 Thru 4 Variable "Warm White" Variable Weit Effect Welle
Group Front Manual color
Effect Off
```

---

## 7. Direkte Kombi-Befehle

Auswahl und Wert-/Attributbefehl lassen sich in **einer Zeile** kombinieren – gleichwertig mit zwei Befehlen hintereinander, aber schneller getippt:

```
Fixture 1 At 80
Fixture 1 Thru 5 At Full
Fixture 1 + 3 At 50
Fixture 1 Thru 10 Color Blue
Fixture 1 Pan 90 Tilt 45
Fixture 1 Thru 4 At 80 Zoom 30 Gobo 40 Frost 0
Group Front At 100 Color Warm
Fixture "Kopf 2" CH6 128
```

Mehrere Attribut-Klauseln dürfen direkt aneinandergereiht werden (`Fixture 1 At 80 Color Red` setzt Dimmer UND Farbe in einem Rutsch). Enthält eine Klausel einen Fehler (Tippfehler im Attribut, ungültige Zahl, ein Kanal, den kein Gerät hat), ändert sich **weder** die Auswahl **noch** ein Wert.

---

## 8. Verkettete Befehle (Komma oder Semikolon)

Mehrere vollständige Befehle lassen sich, durch Komma oder Semikolon getrennt, in **einer** Zeile verketten. Sie laufen nacheinander:

```
Fixture 1 At 100, Fixture 2 At 50
Fixture 1 Color Red; Fixture 2 Color Blue; Fixture 3 At 0
```

Schlägt ein Teil fehl, werden die übrigen trotzdem ausgeführt; das Log zeigt alle Teilergebnisse durch `|` getrennt in einer Zeile. Kommas und Semikolons **innerhalb von Anführungszeichen** (zum Beispiel in einem Cue-Namen) werden korrekt ignoriert: `Label Cue 1 "Akt 1, Szene 2"` wird nicht aufgeteilt.

---

## 9. Clear: `Clear` und `Clear Clear`

| Eingabe | Wirkung |
|---|---|
| `Clear` | Hebt nur die aktuelle Auswahl auf. Programmierte Werte bleiben. |
| `Clear Clear` | **Vollständiger Reset:** setzt **alle** Fixtures komplett zurück – Dimmer, Farbe (schwarz), Pan/Tilt (0°), Zoom, Fokus, Gobo-Räder 1 und 2 samt Drehung, Prisma, Strobe **und jeden weiteren Kanal des Geräts** (Frost, Iris, Farbrad, Geschwindigkeit, Fein-Kanäle …) auf 0. Beendet alle Effekte, leert den Programmer und hebt die Auswahl auf. |
| `Clear` zweimal **innerhalb von 1,0 Sekunde** | Wie `Clear Clear` – schnelles Doppel-Tippen löst denselben Reset aus. |
| `Clear` … (mehr als 1,0 s Pause) … `Clear` | Zwei unabhängige „Auswahl aufheben“-Vorgänge – **kein** Reset. |

---

## 10. Cue-Listen: Auswahl per Name, Go, Fader, Verwalten

Cue-Befehle wirken auf die **aktive Cue-Liste** (Dropdown im Cue-Listen-Panel). Mit `Cuelist` (gleichbedeutend `QList`, `Q-List`, `CL`, `List`, `Exec`) lässt sich jede Liste **beim Namen** ansprechen – Groß-/Kleinschreibung egal; Namen sind in OpenCue eindeutig, deshalb ist das immer klar. Wie überall gilt: **erst die Kategorie, dann der Name** – ein Listenname allein (`Show Go`) ist kein Befehl.

| Befehl | Wirkung |
|---|---|
| `Cuelist Show` | Macht „Show“ zur **aktiven** Liste. |
| `Cuelist "Cue List 1"` | Name mit Leerzeichen (auch ohne Anführungszeichen, wenn eindeutig: `Cuelist Cue List 1`). |
| `Cuelist 2` | Die 2. Liste in der Reihenfolge des Dropdowns (wie `Exec 2`). |
| `Cuelist Show Go` | Liste „Show“ eine Stufe weiter – **ohne** die aktive Liste zu wechseln. |
| `QList Show Go` | Dasselbe mit der Kategorie `QList`. |

### Cue-Listen anlegen, umbenennen, duplizieren, löschen

| Befehl | Wirkung |
|---|---|
| `Cuelist New "Akt 1"` | Legt eine neue Liste an (Namen sind eindeutig; ohne Namen: `Cue List 1`, `Cue List 2` …). Gab es noch keine, wird sie aktiv. |
| `Cuelist Show Rename "Akt 1"` | Benennt um (ein vergebener Name wird abgelehnt). |
| `Cuelist Show Duplicate` | Kopiert mit allen Cues, neue IDs, Name `Show (Kopie)`; mit eigenem Namen: `Duplicate "Sicherung"`. |
| `Cuelist Show Delete` | Löscht die Liste (auch `Delete Cuelist Show`) – **ohne** Rückfrage; eine laufende Überblendung endet. |

Eine Liste mit dem Namen „New“ erreichst du in Anführungszeichen: `Cuelist "New" Go`. Nach dem Listennamen darf jeder Cue-Befehl stehen; er gilt dann genau für diese Liste, und die Rückmeldung nennt sie in eckigen Klammern (`OK: Go Cue 1 [Show]`).

### Abspielen

| Befehl | Wirkung |
|---|---|
| `Go` | Nächster Cue (am Ende der Liste springt Go zum ersten Cue, wie die Taste). |
| `Go Cue 3` / `Go 3` | Springt direkt zu Cue 3 (weiche Überblendung mit dessen Fade-Zeit). |
| `Goto Cue 3` | Wie `Go Cue 3`. |
| `Back` / `Go Back` | Vorheriger Cue. |
| `Pause` / `Resume` | Laufende Überblendung anhalten / weiterlaufen lassen. |
| `Stop` | Überblendung abbrechen (Werte bleiben stehen); beendet auch alle laufenden Effekte. |
| `Fader 50` | Der **Fader** der Liste (Mix zwischen manuellem Wert und Cue, wie der Executor-Fader) auf 50 %. Auch `Fader Full`, `Fader +10`, `Fader At 30`. |
| `Off` / `Off Exec 1` / `Off Cuelist Show` | Setzt den aktiven-Cue-Status der aktiven / der 1. / der genannten Liste zurück. (Executoren sind noch keine eigenständigen Objekte; `Exec N` meint die N-te Liste. `Off` blendet die zuletzt ausgegebenen DMX-Werte nicht aus.) |

```
Cuelist Show Go                Go Cue 3
Cuelist "Zugabe" Goto Cue 1    QList "Zugabe" Fader 40
Cuelist Show Fader +10         Cuelist 2 Back
```

---

## 11. Cue-Verwaltung

Alle Cue-Befehle wirken auf die **aktive Cue-Liste** – oder, mit vorangestelltem `Cuelist <Name>`, auf die genannte Liste.

| Befehl | Wirkung |
|---|---|
| `Store Cue 1` | Übernimmt die im Programmer gesetzten (roten, „berührten“) Werte als neuen Cue. |
| `Store Cue 1.5` | Dezimalnummern erlauben nachträgliches Einschieben zwischen bestehenden Cues. |
| `Store Cue 4 "Intro"` | Mit Namen (sonst heißt der Cue „Cue 4“). |
| `Store Cue 3 Merge` | Gibt es Cue 3 schon: nur die geänderten Kanäle kommen hinein, der Rest bleibt. Ohne `Merge`/`Overwrite` meldet `Store Cue 3` einen Fehler statt eine doppelte Nummer anzulegen. |
| `Store Cue 3 Overwrite` | Gibt es Cue 3 schon: ihr Inhalt wird komplett durch den Programmer ersetzt (Name, Zeiten, Trigger bleiben). |
| `Update` | Übernimmt die Programmer-Werte in den **aktiven** Cue (nur die geänderten Kanäle). Folge-Cues, die diese Werte nicht selbst setzen, übernehmen sie beim Abspielen (Tracking). |
| `Update CueOnly` | Wie `Update`, der Folge-Cue behält aber seinen bisherigen Stand. |
| `Delete Cue 3` | Löscht Cue 3. Mit Bereich: `Delete Cue 3 Thru 5`. |
| `Move Cue 1 At 5` | Nummeriert Cue 1 auf 5 um (die Liste sortiert sich neu). Gibt es die Zielnummer schon, meldet der Befehl einen Fehler. |
| `Label Cue 1 "Intro"` / `Set Cue 1 Name "Intro"` | Benennt Cue 1 um. |

Nach erfolgreichem `Store Cue` wird der Programmer für die gespeicherten Fixtures geleert (die rote Markierung verschwindet). Neue Cues erhalten standardmäßig `Fade = 0,0 s` (hartes Umschalten).

### Cue-Eigenschaften: `Cue <Nummer> <Eigenschaft> <Wert>`

Alles, was im Bearbeiten-Dialog (und in den Spalten der Cue-Liste) steht, lässt sich auch per Befehl setzen. Statt einer Nummer geht auch ein Bereich: `Cue 1 Thru 5 Fade 2` ändert die Cues 1 bis 5.

| Befehl | Wirkung |
|---|---|
| `Cue 1 Fade 3` / `Cue 1 Delay 1.5` | Allgemeine (Dimmer-)Zeiten in Sekunden. |
| `Cue 1 Color Fade 2` / `Color Delay` | Eigene Zeit für Farbe (`Colour` geht auch). |
| `Cue 1 Pos Fade 4` / `Pos Delay` | Eigene Zeit für Position (`Position Fade` geht auch). |
| `Cue 1 Beam Fade 0` / `Beam Delay` | Eigene Zeit für Beam (Gobo, Prisma, Strobe, Fokus …). |
| `Cue 1 Zoom Fade 2` / `Zoom Delay 1` | Eigene Zeit für Zoom. |
| `Cue 1 Color Fade -` | Ein `-` (oder `default`) setzt die Gruppe zurück auf die allgemeine Zeit. |
| `Cue 1 FX In 2` / `FX Out 1` | Effekte ein-/ausblenden in Sekunden (`Effect In` / `Effect Out` gehen auch). |
| `Cue 1 Trigger Go` / `Follow` | Auslöser des Cues. |
| `Cue 1 Trigger Timecode 00:01:30` | Auslöser per globalem Timecode (Zeit wie bei `Timecode At`). |
| `Cue 1 MIB Auto` (`Off` / `On`) | Move In Black. |
| `Cue 1 Cmd "Fixture 1 At 0; Go"` | Befehl(e), die der Cue beim Auslösen ausführt (Kapitel 12). |
| `Cue 1 Name "Intro"` | Name. |

---

## 12. CMD: Befehle an einen Cue koppeln

Jeder Cue hat ein optionales Textfeld **CMD** (Rechtsklick → Bearbeiten → Abschnitt „MIB & CMD“, Doppelklick in der Spalte der Cue-Liste oder per Befehl `Cue 3 Cmd "…"`). Enthält es einen Befehl, führt OpenCue ihn **automatisch** aus, sobald der Cue getriggert wird (über `Go`, einen automatischen `Follow`-Start oder das Kontextmenü „Hierhin faden“) – noch bevor die eigentliche Überblendung beginnt.

Mehrere Befehle werden mit **Komma oder Semikolon** getrennt:

```
Fixture 1 At 0
Fixture 3 Thru 6 Color Blue
Fixture 1 At 0; Fixture 2 Zoom 30; Cuelist Zugabe Go
```

Das Ergebnis erscheint in derselben gemeinsamen Befehlshistorie wie ein getippter Befehl – so bleibt nachvollziehbar, dass ein Cue selbst eine Aktion ausgelöst hat. Das Feld nimmt bis zu 200 Zeichen. CMD darf **jeden** Befehl dieser Referenz enthalten, auch verkettete und kombinierte – ein Cue kann so mit `Cuelist Zugabe Go` eine andere Liste starten. Rekursive `Go Cue`-Aufrufe sind möglich, aber OpenCue erkennt keine Endlosschleifen zwischen verketteten CMD-Cues.

---

## 13. Rückmeldungen im Log

Jeder ausgeführte Befehl erzeugt eine Zeile im Log-Bereich des Panels, mit Zeitstempel:

```
[20:45:01] OpenCue> Fixture 1 Thru 10
           OK: 10 fixtures selected
[20:45:07] OpenCue> At 80
           OK: At 80 applied to 10 fixtures
[20:45:12] OpenCue> Store Cue 1
           OK: Cue 1 stored
```

Fehlerhafte Befehle werden **rot** markiert:

```
[20:46:40] OpenCue> At 80
           At: no fixtures selected
[20:46:55] OpenCue> Go Cue 99
           Cue 99 not found
[20:47:02] OpenCue> Fixture 1 Colr Red
           Unknown attribute: Colr
```

Verkettete Befehle ergeben **eine** Zeile mit allen Teilergebnissen, durch `|` getrennt. Das Log ist auf **allen** verbundenen Geräten identisch – jeder Befehl, egal wo getippt (oder durch das CMD eines Cues ausgelöst), erscheint in jedem geöffneten Befehlszeilen-Panel. Log-Text lässt sich markieren und kopieren. (Die Rückmeldungen sind Englisch, wie die Befehle.)

---

## 14. Tastatur und Autocomplete

| Taste | Wirkung |
|---|---|
| `Enter` | Führt den Befehl aus und leert das Eingabefeld. |
| `Pfeil hoch` | Vorheriger (älterer) Befehl. |
| `Pfeil runter` | Nächster (neuerer) Befehl bzw. zurück zum begonnenen Entwurf. |
| `Tab` | Übernimmt den ersten Vorschlag; jeder weitere `Tab` wechselt zum nächsten. |
| `Umschalt` + `Tab` | Wie `Tab`, rückwärts. |
| `Esc` | Schließt die Vorschlagsliste. |

**Autocomplete:** Beim Tippen (und beim Klick ins Feld) erscheint über dem Eingabefeld eine Liste passender Fortsetzungen. Am Zeilenanfang stehen **nur die Kategorien** (`Fixture`, `Group`, `Cuelist`, `Cue`, `Go` …) – Namen und Werte kommen erst danach. Die Liste kennt den **aktuellen Zustand**, nicht nur die Befehlswörter:

- nach `Fixture ` die Nummern (mit dem Gerätenamen) und die Namen,
- nach `Group ` die Gruppen, nach `Cuelist ` die Cue-Listen (Namen mit Leerzeichen kommen automatisch in `"…"`),
- nach einer Fixture-Auswahl die Attribute und genau die **Kanäle, die diese Geräte haben** (`Frost1`, `Iris`, `ColorSub_C` … mit der Kanalnummer als Hinweis),
- nach `Go `, `Cue `, `Delete Cue ` die Cues der (genannten) Liste mit Namen, danach die Eigenschaften (`Fade`, `Color Fade`, `FX In`, `Trigger` …),
- nach `Color ` die Farbnamen, nach `Zoom ` Werte (`Full`, `Half`, `Min`),
- nach `Variable ` / `Effect ` die Variablen (mit Typ) und Effekte (mit Kategorie); nach `Manual ` die Kategorien; nach `Store ` / `Delete ` / `Label ` `Cue` und `Group`; nach `Cuelist ` zuerst `New`; nach `Blackout ` `On` / `Off`.

Kursive Zeilen sind **Hinweise** auf den erwarteten Wert (`<0-100> | +<n> | -<n> (%)`, `<0-255> (DMX) | <0-100>%`) und lassen sich nicht einfügen. Die Liste bezieht sich immer auf den **letzten Teilbefehl** (nach dem letzten Komma/Semikolon). Ein Klick auf einen Eintrag fügt ihn ebenfalls ein. Die gesamte Grammatik steckt im Server; die Oberfläche zeigt nur an, was der Server vorschlägt – Vorschläge weichen deshalb nie vom echten Parser ab.

Ein kleiner **Schalter** ganz rechts neben der Eingabezeile schaltet die Vorschläge ein und aus (wird in der App-Konfiguration gespeichert und gilt auf allen Geräten).

Unter *Panel-Eigenschaften → Modul-Einstellungen* lassen sich außerdem Text-, Erfolgs- und Fehlerfarbe des Logs anpassen.

---

## 15. Schnellreferenz

```
Fixture 1                       Fixture 1 Thru 10          Fixture 1 + 3
Fixture "Kopf 2"                Group 1                    Group Front

At 80          At Full          At At          Full        At 0     At +10     At -10
Master 80      Master Full      Master -10

Color Red      Color #FF8000    Color 255 128 0            RGB 255 0 0
Pan 180   Tilt -45   Pan 50%    Pan +10%                   Pan +15

Zoom 50   Focus 25   Gobo 40   Gobo2 40   GoboSpin 30   Prism 100   Strobe 0
CH6 128   CH6 50%    Channel 6 +20   Frost 50   Channel Frost1 50   Cyan 100

Fixture 1 At 80 Color Red Zoom 30          Group Front At 100, Fixture 5 At 0

Blackout       Blackout On       Blackout Off

Variable "Warm White"   Effect Welle   Effect Off   Effect Off color   Manual   Manual color

Store Group "Front"   Store Group "Front" Merge   Delete Group Front   Label Group Front "Neu"

Clear          Clear Clear

Go    Back    Go Cue 3    Goto Cue 3    Pause    Resume    Stop    Fader 50
Cuelist New "Akt 1"    Cuelist Show Rename "Akt 2"    Cuelist Show Duplicate    Cuelist Show Delete
Cuelist Show    Cuelist Show Go    QList "Zugabe" Fader 40    Cuelist 2 Back    Off    Off Cuelist Show

Store Cue 1    Store Cue 1.5    Store Cue 4 "Intro"    Store Cue 3 Merge    Update    Update CueOnly
Delete Cue 3   Delete Cue 3 Thru 5    Move Cue 1 At 5    Label Cue 1 "Intro"
Cue 1 Fade 3   Cue 1 Delay 1.5   Cue 1 Thru 5 Fade 2   Cue 1 Color Fade 2   Cue 1 Pos Delay 1
Cue 1 FX In 2  Cue 1 Trigger Follow   Cue 1 Trigger Timecode 00:01:30   Cue 1 MIB Auto   Cue 1 Cmd "Fixture 1 At 0; Go"

Timecode Play    Timecode At 4.3    Timecode Stop
```

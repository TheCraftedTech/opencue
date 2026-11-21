# Scheinwerfer und Patchen

Ein **Scheinwerfer** (Fixture) ist ein Licht, das du steuerst: ein Dimmer, ein LED-Par, ein Moving Head. Damit OpenCue ihn steuern kann, muss es wissen, **was für ein Gerät es ist** (seine Kanäle) und **wo es zuhört** (seine DMX-Adresse). Beides festzulegen heißt **Patchen**. Diese Anleitung führt durch die Scheinwerfer-Bibliothek, das Patchen, Gruppen und den Programmer.

---

## 1. Die Idee in einer Minute

- Ein **Scheinwerfer-Typ** beschreibt ein Gerätemodell: wie viele DMX-Kanäle es in welchem Modus belegt und was jeder Kanal tut (Dimmer, Pan, Tilt, Farbe, Gobo …). OpenCue nutzt dafür das Standardformat **GDTF** – eine kleine Datei pro Gerät, die der Hersteller veröffentlicht.
- Ein **Scheinwerfer** in deiner Show ist ein echtes Gerät dieses Typs mit einer **Nummer** (FID), einem **Namen**, einem **Universum** und einem **Startkanal** (die DMX-Adresse, die du am Gerät einstellst).
- Die Show speichert die Scheinwerfer (Typ, Modus, Adresse, Name, Gruppe). Die GDTF-Dateien selbst liegen in der **Scheinwerfer-Bibliothek** auf deinem Computer.
- Drei **eingebaute** Typen gibt es immer, auch ohne GDTF-Datei: **Generic Dimmer** (1 Kanal), **Generic RGBW LED Par** (4 Kanäle) und **Generic Moving Head Spot 16ch** (16 Kanäle, mit Fein-Pan/Tilt). Ideal zum Ausprobieren.

---

## 2. Scheinwerfer-Typen beschaffen: die Bibliothek

Öffne **Bibliothek → Scheinwerfer-Bibliothek…**. Der große Dialog hat diese Tabs:

| Tab | Was er zeigt |
|---|---|
| **Installiert** | Jede GDTF-Datei auf diesem Computer als Karte: Vorschaubild, Name, Hersteller, Typ, Modi, Kanalzahl, Revision und *In Benutzung (N)*, wenn die Show sie verwendet. |
| **In dieser Show** | Die Typen der geladenen Show mit Anzahl („4× in der Show“) und Revision. Fehlt die Datei eines Typs in der Bibliothek, zeigt der Tab *Eingebauter Ersatz* oder *Datei fehlt*. Nur Ansicht. |
| **Online (GDTF Share)** | Suche in der offiziellen GDTF-Datenbank (siehe unten). |

Im Tab *Installiert* kannst du nach Name oder Hersteller **suchen** und nach **Typ** (Moving Head, LED-Bar, PAR / Wash, Dimmer, Strobe / Blinder, Effekt / Nebel, Sonstige – aus den echten Kanälen abgeleitet) und nach **Hersteller** filtern. Jeder Tab behält seine eigenen Filter.

### Eine vorhandene GDTF-Datei importieren

Klicke auf **GDTF-Datei importieren…** oder **ziehe die Datei** einfach in den Dialog. Sie muss eine gültige GDTF-Datei sein (höchstens 30 MB). Die Dateien werden in den Ordner `fixtures` im Datenordner von OpenCue kopiert (*Einstellungen → Speicherort* zeigt, wo der liegt).

### Aus GDTF Share herunterladen

GDTF Share (gdtf-share.com) ist die offizielle, kostenlose Sammlung von GDTF-Dateien von Herstellern und Nutzern.

1. Öffne den Tab **Online (GDTF Share)**.
2. **Melde dich an** mit deinem GDTF-Share-Konto. Zum Herunterladen ist ein kostenloses Konto nötig; im Dialog gibt es den Link *Kostenloses Konto anlegen*. Dein Passwort bleibt nur für diese Sitzung im Speicher – außer du setzt den Haken *Angemeldet bleiben*; dann wird es **verschlüsselt auf diesem Computer** gespeichert.
3. Suche, sortiere (Name, Neueste zuerst, Beste Bewertung), filtere nach **Herstellerdateien** / Bewertung. Jede Karte zeigt, ob die Datei **vom Hersteller** oder **von einem Nutzer** hochgeladen wurde, wie viele Modi sie hat (mit Kanalzahl) und wie groß sie ist.
4. Klicke auf **Details**, um den Scheinwerfer **vor dem Installieren anzusehen**: die Datei wird nur vorübergehend geladen (nicht installiert) und in derselben Detailansicht wie bei installierten Typen geöffnet – mit allen Kanälen, Rädern und dem 3D-Modell. Oben stehen **Installieren** und **Zurück zur Suche**. Oder klicke direkt auf **Installieren**.
5. Die Karte zeigt danach *Installiert*. Erscheint später eine neuere Revision, wird ein Knopf **Aktualisieren** angeboten.

Das ist die einzige Stelle, an der OpenCue für Scheinwerfer das Internet nutzt; alles andere funktioniert offline. OpenCue liefert keine GDTF-Dateien von GDTF Share mit, weil deren Bedingungen die Weitergabe nicht erlauben – du lädst sie selbst herunter.

### Details eines Scheinwerfers

Klicke auf eine Karte, um die **Details** zu öffnen:

- **Übersicht** – Stammdaten, Optik je Strahl (Strahlart, Lampe, Leistung, Lichtstrom, Farbtemperatur, Strahl- und Ausleuchtwinkel), Anschlüsse, Leuchtmittel.
- **3D-Vorschau** – das Gerät als 3D-Modell. Ziehen dreht, Mausrad oder zwei Finger zoomen, Rechtsklick-Ziehen verschiebt, Doppelklick setzt zurück. Knöpfe *Schräg / Vorne / Seite / Oben*, Schalter für *Lichtstrahl* und *Raster* und **Pan-/Tilt-Regler**, um einen Moving Head zu bewegen. Enthält die GDTF-Datei kein 3D-Modell, zeichnet OpenCue die Grundformen (Zylinder, Bügel, Kopf …) in den angegebenen Maßen.
- **DMX-Kanäle** – die Modusauswahl und eine Tabelle aller Kanäle mit Funktionen und Wertebereichen.
- **Gobos & Farben** – jedes Rad mit seinen Slots: Gobo-Muster als Bilder, Farb-Slots als Farbfelder.

### Entfernen und aktualisieren

- **Deinstallieren** (fragt ein zweites Mal) entfernt einen Typ aus der Bibliothek – wird aber **abgelehnt, solange die Show ihn noch verwendet**.
- **Aktualisieren** installiert eine neuere Revision. Verwendet die Show die alte, bleibt sie installiert.

---

## 3. Scheinwerfer zur Show hinzufügen (Patchen)

Scheinwerfer legst du im Panel **Scheinwerfer-Liste** an.

1. Klicke im Panel **Scheinwerfer-Liste** auf **Scheinwerfer hinzufügen**.
2. **Scheinwerfer-Typ** – wähle mit *Scheinwerfer-Typ auswählen…* (Hersteller → Gerät → Modus, mit Suche) oder einen der eingebauten Generics.
3. **Modus** – der DMX-Modus des Geräts (er bestimmt die Kanalzahl).
4. **Name** (optional) – zum Beispiel „Kopf“; leer heißt Typname. Bei mehreren Scheinwerfern nummeriert OpenCue die Namen.
5. **Anzahl** – wie viele gleiche Scheinwerfer angelegt werden. Sie werden **hintereinander** auf aufeinanderfolgende Adressen gelegt.
6. **Universum** und **Startkanal** – die Adresse des ersten. Sie muss mit der am Gerät eingestellten Adresse übereinstimmen (Display oder DIP-Schalter).
7. Klicke auf **Scheinwerfer hinzufügen**.

Der Dialog warnt, wenn der letzte Scheinwerfer über Kanal **512** eines Universums hinausreichen würde („end address exceeds 512 … Reduce quantity or start address“). Ein Universum hat 512 Kanäle; für mehr nimmst du das nächste Universum.

Jeder Scheinwerfer bekommt eine stabile **FID** (Scheinwerfernummer), die die Befehlszeile benutzt (`Fixture 1 Thru 5`).

### Viele Scheinwerfer auf einmal: Liste aus CSV oder Excel

Im Dialog *Scheinwerfer hinzufügen* gibt es unten **Erweiterte Importfunktionen …** (auch im Menü **Bibliothek → Scheinwerfer-Liste importieren**). Damit legst du eine ganze Anlage aus einer Tabelle an:

1. **Datei wählen …** – eine `.csv`- oder Excel-Datei (`.xlsx`). Die **erste Zeile** enthält die Spaltentitel. Nur der **Typ** ist nötig; *Name*, *Modus*, *Universum*, *Adresse*, *Nummer* (FID) und *Anzahl* sind optional. **Aktuelle Patch-Liste als CSV laden** gibt dir eine Vorlage.
2. OpenCue **errät die Spalten** (Namen wie *Name*, *Typ*, *Gerät*, *Universum*, *Adresse*, *Anzahl* …); du kannst jede Zuordnung ändern. Eine Adresse darf auch `2.045` oder `2/45` heißen (Universum 2, Adresse 45). Fehlt die Adresse, läuft sie hinter dem vorigen Gerät desselben Universums weiter.
3. Die **Vorschau** zeigt jede Zeile – rot mit dem Grund, wenn etwas nicht stimmt (Typ unbekannt oder mehrdeutig, Modus unbekannt, passt nicht ins Universum, Nummer schon vergeben). **Typ, wenn die Zelle leer ist** und **Universum, wenn es fehlt** füllen Lücken.
4. **Importieren** legt die Scheinwerfer an. Bei Problemen erst **Zeilen mit Problemen auslassen** ankreuzen. Vorher wird nichts angelegt.

### Die Scheinwerfer-Liste und der Tab „Scheinwerfer“

Zwei Stellen zeigen deine Scheinwerfer:

- Das Panel **Scheinwerfer-Liste** ist die Patch-Tabelle: eine Zeile pro Scheinwerfer mit FID, Name, Typ, Universum, Adresse und Kanalzahl, dazu der Knopf **Scheinwerfer hinzufügen**.
- Der Tab **Scheinwerfer** im Panel **Scheinwerfer-Steuerung** zeigt dieselben Scheinwerfer als Kachelraster (wie auf einem Lichtpult) zum schnellen Auswählen.

| Aktion | So geht's |
|---|---|
| Auswählen | Klick / Tippen auf eine Zeile oder Kachel |
| Mehrere auswählen | Im Kachelraster ein **Lasso** über die Kacheln ziehen (Maus und Touch) |
| Einen Scheinwerfer bearbeiten | Rechtsklick / langes Drücken → **Scheinwerfer bearbeiten…** |
| Löschen | Auswählen, `Entf` drücken oder das Kontextmenü nutzen (fragt nach) |

### Scheinwerfer bearbeiten

Ein Dialog ändert alles: **Name**, **Universum**, **Startkanal**, **Gruppe** und einen freien **Sortier-Index**.

- Der Sortier-Index bestimmt, wo die Kachel erscheint. Leer heißt FID; eine Zahl (auch mit Dezimalstellen, zum Beispiel 2,5) ordnet sie entsprechend ein.
- Ein Scheinwerfer gehört höchstens **einer Gruppe** an.
- Sind **mehrere Scheinwerfer gewählt**, bietet das Menü außerdem *N Scheinwerfer in Gruppe verschieben…*.

Eine geänderte Adresse ändert, wohin OpenCue die Daten sendet – ändere sie also, wenn du ein Gerät auf eine andere Adresse stellst.

---

## 4. Gruppen

Gruppen dienen nur der Ordnung: Sortieren und mehrere Scheinwerfer mit einem Klick oder Befehl auswählen. Sie werden mit der Show gespeichert.

- **Anlegen:** im Tab **Scheinwerfer** der Scheinwerfer-Steuerung Rechtsklick / langes Drücken auf die leere Fläche → *Neue Gruppe hinzufügen…* und einen Namen eingeben (Namen sind eindeutig, Groß-/Kleinschreibung egal).
- **Füllen:** das Dropdown *Gruppe* in *Scheinwerfer bearbeiten…* oder *N Scheinwerfer in Gruppe verschieben…* für eine Auswahl.
- **Auswählen:** die Gruppe anklicken oder per Befehlszeile: `Group Front`, `Group 1 Thru 4`.
- **Aus einer Auswahl:** `Store Group "Front"` speichert die aktuelle Auswahl als Gruppe (siehe *Befehlsreferenz*).

---

## 5. Scheinwerfer steuern: das Panel Scheinwerfer-Steuerung

Wähle Scheinwerfer aus und nutze dann das Panel **Scheinwerfer-Steuerung** (auf Pulten oft „Programmer“). Ein Panel kann alles zeigen (Seitenleiste mit allen Kategorien) oder nur eine Kategorie (*Panel-Eigenschaften → Ansicht*).

| Kategorie | Bedienelemente |
|---|---|
| **Scheinwerfer** | Das Kachelraster zum Auswählen; Schalter **Liste / Layout** (siehe unten) |
| **Helligkeit** | Fader und Schnelltasten |
| **Position** | Schalter **Grob / Fein**. *Grob*: Pan-/Tilt-Fader, **Center / Home / Flip**, Zahlenfelder in Grad. *Fein*: die Fein-Kanäle (16 Bit) als Zahlenfelder; auf einem Zahlenfeld nach oben oder unten wischen ändert den Wert fein. Geräte ohne Fein-Kanäle arbeiten mit 8 Bit. |
| **Farbe** | **Fader** (HSV, CMY oder RGB) oder **Color Picker** (Farbrad) |
| **Beam** | Unterseiten **Shutter/Strobe** (offen, zu, langsam, schnell, Strobe, Puls …), **Gobo** (mit Vorschaubildern des Rades), **Prisma** |
| **Fokus** | Fokus und Zoom |
| **DMX Direkt** | Jeder Kanal des Modus als eigener Fader (nach Kanalnummer, 0–255) |

Jeder Kanal, den die GDTF-Datei beschreibt, bekommt ein Bedienelement, sodass du auch ungewöhnliche Funktionen erreichst (Frost, Iris, Farbräder, Geschwindigkeiten).

**Auf einen Punkt zielen (3D):** Sind die Scheinwerfer in der **3D-Simulation** platziert, bietet die Positionsseite *Punkt in 3D-Simulation setzen*: Tippe in der 3D-Ansicht auf ein Ziel, und die gewählten Moving Heads richten sich darauf aus. Auf der Fokusseite stellen *Auto-Fokus (3D)* und *Auto-Zoom (3D) …* Fokus und Zoom aus der Entfernung zu diesem Punkt ein.

### Was die Markierung an den Bedienelementen sagt

Die Bedienelemente zeigen immer, was gerade ausgegeben wird (dieselben Werte wie im DMX-Monitor) – auch während ein Cue oder Effekt läuft. Eine dünne farbige Linie an einem Scheinwerfer oder einem Kategorie-Tab zeigt, was sich **gegenüber dem aktiven Cue geändert hat** – von Hand bedient oder durch ein *Clear*, das alles dunkel gemacht hat. Gespeichert wird beim *Cue speichern* immer die Änderung gegenüber dem Cue, der davor abgespielt würde (auch beim Einfügen mit `2.5`). Nach dem Speichern ist der neue Cue der aktive und die Linien verschwinden. Bei mehreren Cue-Listen gilt der aktive Cue der zuletzt benutzten Liste.

---

### Scheinwerfer: Liste oder Layout

Oben im Tab **Scheinwerfer** schaltest du zwischen zwei Ansichten um (wie bei *Farbe* zwischen Fader / Picker / Rad):

- **Liste:** die Kacheln nach Gruppen und Nummern geordnet.
- **Layout:** jeder Scheinwerfer ist eine **quadratische Kachel** auf einem Raster. So kannst du die Scheinwerfer so anordnen, wie sie auf der Bühne hängen, und sie schneller treffen. Die Kacheln zeigen dasselbe wie in der Liste (Nummer, Helligkeit, Farb- und Strahl-Vorschau).

Im Layout gilt:

- **Auswählen** wie in der Liste: Klick oder **Wischgeste** (Lasso) über die leere Fläche.
- **Unbegrenzte Fläche:** sie reicht in **alle Richtungen** weiter (auch nach links und oben, die Positionen dürfen negativ sein). Verschieben der Ansicht: Mausrad / Scrollleisten / Wischen, **Mitteltaste ziehen**, oder beim Ziehen einer Kachel an den Rand gehen. **Strg + Mausrad** zoomt.
- **Alle zeigen:** der Knopf oben rechts zoomt und zentriert so, dass **alle Scheinwerfer** in der Mitte stehen.
- **Ansichten (Bereiche):** *Ansicht speichern…* (Rechtsklick) merkt die aktuelle Mitte und den Zoom unter einem Namen, zum Beispiel „Bühne links“. Oben erscheint ein Knopf; ein Klick springt dorthin, Rechtsklick auf den Knopf: überschreiben, umbenennen, löschen. So musst du bei vielen Scheinwerfern nicht alles auf einmal im Blick haben.
- **Rechtsklick** (Touch: langes Drücken) auf die freie Fläche oder auf eine Kachel öffnet das Menü: *Baumodus*, *Alle zeigen*, *Ansicht speichern…*, *Raster* (ganze, halbe oder Viertel-Kachel), *Kacheln dürfen sich überlappen*, *Zoom zurücksetzen*, *Alle Scheinwerfer neu anordnen…*.
- **Baumodus:** Ziehen verschiebt eine Kachel; sind mehrere gewählt, werden alle gemeinsam verschoben. Die Kacheln rasten im Raster ein; ohne *Überlappen* überdecken sie sich nie, mit *Überlappen* darf man sie ineinander legen (die zuletzt bewegte liegt oben) und mit dem feinen Raster (1/4) dicht staffeln. Eine leere Fläche wählt weiter per Wischgeste aus. **Fertig** oder **Esc** beendet den Baumodus.
- **Gespeichert in der Show:** die Positionen, die Rasterfeinheit, *Überlappen* und die gespeicherten Ansichten. **Auf deinem Gerät** (nicht in der Show): der Zoom, die zuletzt gezeigte Mitte und die zuletzt benutzte Unteransicht.

**Gemerkte Ansichten:** Überall, wo ein Panel zwischen Ansichten umschaltet, merkt sich dein Gerät die zuletzt benutzte und stellt sie beim nächsten Öffnen wieder her: in der Scheinwerfer-Steuerung (Liste / Layout, Fader / Picker / Rad, Strobe / Gobo / Prism, Grob / Fein), bei *Variablen und Effekte* (Variablen oder Effekte, Typ-Filter, Sortierung), im *Effekt-Studio* (Vorschau an / aus), in der *3D-Simulation* (Ansicht / Bauen / Scheinwerfer) und in der Effekt-Auswahl (Kategorie und Schlagworte wie *Basis*).

## 6. Variablen und Effekte (Presets)

Das Panel **Variablen / Effekte** enthält wiederverwendbare Werte: eine Farbe „Warm White“, eine Position „Front“, einen Beam „Weit“. Eine Variable ist eine **lebende Referenz**: Wende sie auf Scheinwerfer an, und sie folgen ihr; ändert man die Variable später, ändern sich alle Scheinwerfer mit, die sie benutzen – auch Cues, die sie verwenden. Effekte sind kleine Programme, die Werte über die Zeit verändern; siehe die Anleitung *Effekt-Studio*.

---

## 7. Scheinwerfer und die Show-Datei

- Ein Showfile speichert die Scheinwerfer **mit** Typ, Modus, Adresse und Gruppe, dazu Cues, Effekte, Variablen und Presets.
- Die GDTF-Dateien liegen **nicht** in der Show – beim **Export einer Show** (Dateimanager → Export) werden aber die GDTF-Dateien und Effekt-Skripte, die die Show benutzt, in die ZIP gepackt. So öffnest du die Show auf einem anderen Computer, ohne etwas zu installieren. Beim Import wird eine lokale Datei gleichen Namens nie ersetzt.
- **Drucken / PDF** (Datei-Menü): Dokumentation der Show für Techniker – **Patch-Liste**, **DMX-Kanalbelegung** (welcher Scheinwerfer welche Kanäle jedes Universums belegt, Überschneidungen rot), **Gruppen**, **Plan (Draufsicht)** der Scheinwerfer (aus der 3D-Bühne, sonst aus der Layout-Ansicht) und **Cue-Listen**. Der Dialog zeigt neben der Auswahl eine **Vorschau** des PDFs (sie folgt jeder Änderung der Auswahl und der Papiergröße; auf kleinen Bildschirmen entfällt die Vorschau). Lange Namen werden in den Tabellen und im Plan **umgebrochen** (ein sehr langer Name ohne Leerzeichen wird geteilt). Im Plan trägt jeder Scheinwerfer seine Nummer, eine Liste unter dem Plan sagt, welche Nummer welcher Scheinwerfer ist; Namen von Bühnenobjekten stehen in ihrer Fläche. *Als PDF speichern* lädt die Datei, *Zum Drucken öffnen* zeigt sie im PDF-Betrachter (dort mit Strg+P drucken).
- **Show-Datei `.ocshow`:** *Datei → Show exportieren* schreibt eine `.ocshow`-Datei (ein ZIP mit der Show und ihren Dateien). Ein **Doppelklick** darauf öffnet sie in OpenCue (der Installer richtet das ein; bei der entpackten Version *Einstellungen → Allgemein → Dateien .ocshow mit OpenCue öffnen*). Läuft OpenCue schon, übernimmt es die Datei und fragt bei ungespeicherten Änderungen vorher. **Datei → Zuletzt benutzt** listet die letzten Shows.
- **3D-Bühne als JSON:** im 3D-Panel (Modus *Bauen* oder *Scheinwerfer*) die Seitenleiste von **Werkzeuge** auf **JSON** umschalten (Umschalter unter dem Speichern-Knopf; der Knopf *Als JSON bearbeiten* ganz am Ende der Werkzeuge tut dasselbe). Die Werkzeuge (Körper hinzufügen, Liste, Eigenschaften) werden durch den Text der Bühne ersetzt (Raum, Objekte, Scheinwerfer-Positionen; Meter, Grad, Z nach oben; Scheinwerfer unter ihrer Nummer); Bühnenname, Rückgängig und **Speichern** bleiben gleich, **Werkzeuge** bringt die normale Ansicht zurück. **Die Breite der Seitenleiste lässt sich ändern:** den linken Rand ziehen (Doppelklick = Standardbreite); die Breite wird als Anteil des Panels gemerkt (höchstens drei Viertel) und bleibt so auch im Vollbild proportional. Änderungen werden geprüft und **live übernommen** (ein Syntaxfehler nennt die Zeile und ändert nichts); was du in der 3D-Ansicht verschiebst, erscheint im Text. *Speichern* speichert die Bühne, *JSON schließen* bringt die Seitenleiste zurück. Derselbe Text steht als Dialog unter *Bibliothek → 3D-Bühne als JSON bearbeiten* bereit (mit *Prüfen* und *Übernehmen*).
- Verwendet eine Show einen Typ, dessen Datei fehlt, nimmt OpenCue einen eingebauten Ersatz, damit die Show trotzdem funktioniert; der Tab *In dieser Show* zeigt das als *Eingebauter Ersatz* oder *Datei fehlt*.

---

## 8. Kurze Tipps

- **Fang mit einem Generic an:** Lege ein paar *Generic Dimmer* an und lerne damit Programmer, Cues und Befehlszeile, bevor du echte GDTF-Dateien suchst.
- **Adressen abgleichen:** Der Startkanal in OpenCue muss der Adresse am Gerät entsprechen. Moving Heads brauchen meist einen Kanalblock (zum Beispiel 16 Kanäle), der nächste Scheinwerfer beginnt dann 16 Kanäle später – OpenCue rechnet das, wenn du eine Anzahl anlegst.
- **Mehrere Modi:** Viele Geräte haben mehrere Modi (zum Beispiel 8 Bit und 16 Bit). Wähle den Modus, auf den das Gerät wirklich eingestellt ist.
- **Gerät fehlt?** Suche in GDTF Share nach dem Hersteller; ist das Modell nicht dabei, nimm das ähnlichste oder *Generic* und baue deine eigenen Cues.

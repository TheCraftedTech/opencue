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
3. Suche, sortiere (Name, Neueste zuerst, Beste Bewertung), filtere nach verifiziert / Bewertung und klicke auf **Installieren**.
4. Die Karte zeigt danach *Installiert*. Erscheint später eine neuere Revision, wird ein Knopf **Aktualisieren** angeboten.

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

### Die Scheinwerfer-Liste und der Tab „Scheinwerfer“

Zwei Stellen zeigen deine Scheinwerfer:

- Das Panel **Scheinwerfer-Liste** ist die Patch-Tabelle: eine Zeile pro Scheinwerfer mit FID, Name, Typ, Universum, Adresse und Kanalzahl, dazu der Knopf **Scheinwerfer hinzufügen**.
- Der Tab **Scheinwerfer** im Panel **Scheinwerfer-Steuerung** zeigt dieselben Scheinwerfer als Kachelraster (wie bei dot2) zum schnellen Auswählen.

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

Wähle Scheinwerfer aus und nutze dann das Panel **Scheinwerfer-Steuerung** (bei dot2 „Programmer“). Ein Panel kann alles zeigen (Seitenleiste mit allen Kategorien) oder nur eine Kategorie (*Panel-Eigenschaften → Ansicht*).

| Kategorie | Bedienelemente |
|---|---|
| **Scheinwerfer** | Das Kachelraster zum Auswählen |
| **Helligkeit** | Fader und Schnelltasten |
| **Position** | Schalter **Grob / Fein**. *Grob*: Pan-/Tilt-Fader, **Center / Home / Flip**, Zahlenfelder in Grad. *Fein*: die Fein-Kanäle (16 Bit) als Zahlenfelder; auf einem Zahlenfeld nach oben oder unten wischen ändert den Wert fein. Geräte ohne Fein-Kanäle arbeiten mit 8 Bit. |
| **Farbe** | **Fader** (HSV, CMY oder RGB) oder **Color Picker** (Farbrad) |
| **Beam** | Unterseiten **Shutter/Strobe** (offen, zu, langsam, schnell, Strobe, Puls …), **Gobo** (mit Vorschaubildern des Rades), **Prisma** |
| **Fokus** | Fokus und Zoom |
| **DMX Direkt** | Jeder Kanal des Modus als eigener Fader (nach Kanalnummer, 0–255) |

Jeder Kanal, den die GDTF-Datei beschreibt, bekommt ein Bedienelement, sodass du auch ungewöhnliche Funktionen erreichst (Frost, Iris, Farbräder, Geschwindigkeiten).

**Auf einen Punkt zielen (3D):** Sind die Scheinwerfer in der **3D-Simulation** platziert, bietet die Positionsseite *Punkt in 3D-Simulation setzen*: Tippe in der 3D-Ansicht auf ein Ziel, und die gewählten Moving Heads richten sich darauf aus. Auf der Fokusseite stellen *Auto-Fokus (3D)* und *Auto-Zoom (3D) …* Fokus und Zoom aus der Entfernung zu diesem Punkt ein.

### Was die Markierung an den Bedienelementen sagt

Die Bedienelemente zeigen immer, was gerade ausgegeben wird (dieselben Werte wie im DMX-Monitor) – auch während ein Cue oder Effekt läuft. Eine dünne farbige Linie an einem Scheinwerfer oder einem Kategorie-Tab erscheint **nur, nachdem du diese Kategorie von Hand bedient hast**: Das sind deine *Programmer-Werte*, die noch nicht gespeichert sind. Sie verschwinden nach *Cue speichern* oder *Clear*.

---

## 6. Variablen und Effekte (Presets)

Das Panel **Variablen / Effekte** enthält wiederverwendbare Werte: eine Farbe „Warm White“, eine Position „Front“, einen Beam „Weit“. Eine Variable ist eine **lebende Referenz**: Wende sie auf Scheinwerfer an, und sie folgen ihr; ändert man die Variable später, ändern sich alle Scheinwerfer mit, die sie benutzen – auch Cues, die sie verwenden. Effekte sind kleine Programme, die Werte über die Zeit verändern; siehe die Anleitung *Effekt-Studio*.

---

## 7. Scheinwerfer und die Show-Datei

- Ein Showfile speichert die Scheinwerfer **mit** Typ, Modus, Adresse und Gruppe, dazu Cues, Effekte, Variablen und Presets.
- Die GDTF-Dateien liegen **nicht** in der Show – beim **Export einer Show** (Dateimanager → Export) werden aber die GDTF-Dateien und Effekt-Skripte, die die Show benutzt, in die ZIP gepackt. So öffnest du die Show auf einem anderen Computer, ohne etwas zu installieren. Beim Import wird eine lokale Datei gleichen Namens nie ersetzt.
- Verwendet eine Show einen Typ, dessen Datei fehlt, nimmt OpenCue einen eingebauten Ersatz, damit die Show trotzdem funktioniert; der Tab *In dieser Show* zeigt das als *Eingebauter Ersatz* oder *Datei fehlt*.

---

## 8. Kurze Tipps

- **Fang mit einem Generic an:** Lege ein paar *Generic Dimmer* an und lerne damit Programmer, Cues und Befehlszeile, bevor du echte GDTF-Dateien suchst.
- **Adressen abgleichen:** Der Startkanal in OpenCue muss der Adresse am Gerät entsprechen. Moving Heads brauchen meist einen Kanalblock (zum Beispiel 16 Kanäle), der nächste Scheinwerfer beginnt dann 16 Kanäle später – OpenCue rechnet das, wenn du eine Anzahl anlegst.
- **Mehrere Modi:** Viele Geräte haben mehrere Modi (zum Beispiel 8 Bit und 16 Bit). Wähle den Modus, auf den das Gerät wirklich eingestellt ist.
- **Gerät fehlt?** Suche in GDTF Share nach dem Hersteller; ist das Modell nicht dabei, nimm das ähnlichste oder *Generic* und baue deine eigenen Cues.

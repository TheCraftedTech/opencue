# Erste Schritte mit OpenCue

OpenCue ist ein Lichtsteuerpult für deinen PC. Diese Anleitung führt dich in etwa zehn Minuten vom Installer zum ersten Licht-Cue – ganz ohne angeschlossene Lampen, denn die ersten Schritte funktionieren mit der eingebauten Demo-Show.

Alle Anleitungen gibt es auch im Programm, selbst ohne Internet: **Hilfe → Anleitungen** (oder **F1**) öffnet sie mit einer Suche (darin `Strg+F`).

---

## 1. Was du brauchst

- Einen PC mit **Windows 10 oder 11** (64 Bit). Die **Microsoft Edge WebView2-Laufzeit** zeigt das OpenCue-Fenster; sie gehört zu aktuellem Windows, und der Installer richtet sie ein, falls sie fehlt (dafür ist einmalig Internet nötig).
- Für echte Lampen: eine DMX-Verbindung – über das Netzwerk (**Art-Net** oder **sACN**) oder eine **USB-DMX-Schnittstelle** (Enttec DMX USB Pro und kompatible). Ohne Hardware kannst du trotzdem alles programmieren und in der **3D-Simulation** ansehen.
- Kein Konto, kein Lizenzschlüssel, keine Internetverbindung während der Arbeit.

---

## 2. Installieren

1. Lade `OpenCue-Setup-v<Version>.exe` von der Releases-Seite des Projekts herunter und starte sie.
2. Das Setup beginnt mit einer Willkommensseite, auf der du die **Sprache** wählst (Englisch oder Deutsch; es ist auch die Sprache von OpenCue selbst).
3. Klicke dich durch: **Lizenz** (die GNU GPL, zum Lesen), **Programmordner**, **Datenordner**, **Verknüpfungen** (Startmenü, Desktop), die Übersicht, **Installieren**.
4. Beenden und OpenCue starten.

Der **Datenordner** ist der Ort, an dem deine Shows, Layouts, Scheinwerfer und Einstellungen liegen. Der Vorschlag (`%LOCALAPPDATA%\OpenCue`) passt für die meisten; du kannst im Setup einen anderen Ort wählen und ihn später in OpenCue unter *Einstellungen → Speicherort* ändern.

Ist OpenCue schon installiert, erkennt das Setup das und bietet *Aktualisieren*, *Neu installieren* oder *Deinstallieren* an – deine Daten bleiben immer erhalten. OpenCue prüft auch beim Start auf neue Versionen (abschaltbar unter *Einstellungen → Allgemein*) und bietet die Installation an; *Hilfe → Nach Updates suchen…* tut das auf Wunsch. Das Update-Fenster zeigt die Versionshinweise; nach einem Update öffnet sich einmal ein Fenster **Was ist neu** mit den neuen Funktionen jeder übersprungenen Version (auch unter *Hilfe → Was ist neu*).

OpenCue lässt sich über die Windows-Suche finden (Windows-Taste drücken und „OpenCue“ tippen).

---

## 3. Der erste Start

Bei einer frischen Installation öffnet OpenCue eine fertige **Demo-Show** namens **Default_1**:

- fünf **Generic Dimmer** („Dimmer 1“ … „Dimmer 5“) im Universum 1 auf den Kanälen 1 bis 5,
- eine Cue-Liste „Default“ mit zwei Cues („Cue 1“ und „Cue 2“, je eine Sekunde Überblendung),
- ein **Layout** mit den Panels, die du zuerst brauchst: Cue-Liste, Scheinwerfer-Liste, Scheinwerfer-Steuerung, Executor, Befehlszeile, Befehls-Tasten und Ziffernblock.

Beim allerersten Start öffnet sich ein kurzer **Willkommens-Dialog**: Sprache, dann – nur wenn du möchtest – das Netzwerk (Art-Net, Fernzugriff mit eigenem Passwort, OSC). Er lässt sich nicht schließen, man klickt sich durch (oder drückt auf der ersten Seite *Überspringen*). Nichts wird ohne dein Zutun eingeschaltet; schaltest du etwas ein, das das Netzwerk nutzt, fragt Windows eventuell einmal, ob OpenCue es benutzen darf. Nach einem Update zeigt **Hilfe → Was ist neu?** die Änderungen (öffnet sich einmal von selbst).

In der 3D-Simulation gibt es noch keine Bühne – die legst du an, wenn du sie brauchst. Die Demo-Dateien sind normale Dateien: ändere oder lösche sie nach Belieben.

---

## 4. Die Oberfläche in einer Minute

### Menüs (oben links)

| Menü | Inhalt |
|---|---|
| **Datei** | Neu / Öffnen / Speichern / Speichern unter (Showfiles), Abmelden (nur Fernsteuer-Geräte), Beenden |
| **Bearbeiten** | **Panels bearbeiten** (Bearbeitungsmodus), Rückgängig / Wiederholen, **Panel hinzufügen…**, Button / Fader hinzufügen, **Layouts verwalten…** |
| **Bibliothek** | **Scheinwerfer-Bibliothek…**, 3D-Bühnen und die Dateimanager-Listen *Shows*, *Layouts*, *3D-Bühnen*, *Effekte* |
| **Ansicht** | Vollbild, GUI-Skalierung, Layouts |
| **Sprache** | English / Deutsch |
| **Hilfe** | Tastenkürzel, GitHub-Repository, Was ist neu, Nach Updates suchen…, Über OpenCue |

### Werkzeugleiste (oben)

Die Werkzeugleiste zeigt das aktuelle **Layout** und die **Bühne**, den **Showfile-Namen** (ein Klick öffnet den Dateimanager), einen pulsierenden **Blackout**-Knopf (Glühbirne), den **Timecode**, eine DMX-Anzeige, die Zahl der verbundenen **Fernsteuer-Geräte** und den Knopf **Einstellungen**. Fährst du mit der Maus über einen Eintrag, hebt er sich ab und ein **Tooltip** nennt, was er ist. Was in der Leiste erscheint, bestimmst du unter *Einstellungen → Toolbar & Internet* (jeder Eintrag einzeln; nur für dieses Gerät; das Zahnrad bleibt immer sichtbar).

**Bedienmodus in einfachen Worten** (*Ansicht → Bedienmodus …*): Du gibst die Konsole jemandem, der nur **bedienen** soll – Fader schieben, Tasten drücken, Cues starten –, aber nichts verstellen darf. Im Bedienmodus sind Menüs, Einstellungen und Umbauen gesperrt, und die **Sprachsteuerung ist aus** (das Mikrofon bleibt zu). Raus kommst du nur mit dem **Passwort** (Schloss unten rechts oder `Strg+L`). Er braucht das Passwort aus *Einstellungen → Sicherheit*. Etwas anderes ist **Bildschirm sperren** (*Steuerung → Bildschirm sperren*, `Strg+L`): Das verdunkelt alles, bis das Passwort eingegeben ist – nichts ist mehr bedienbar.

### Panels

Alles andere sind **Panels**, die du frei anordnest. Die wichtigsten:

| Panel | Zweck |
|---|---|
| **Scheinwerfer-Liste** | Das Patch: Scheinwerfer hinzufügen, bearbeiten und löschen |
| **Scheinwerfer-Steuerung** | Helligkeit, Position, Farbe, Beam, Fokus und DMX direkt für die gewählten Scheinwerfer; auch das Kachelraster zum Auswählen |
| **Cue-Liste** | Die Cues einer Liste: speichern, aktualisieren, bearbeiten, löschen, abspielen |
| **Executor** | Wiedergabe mit Go / Pause / Zurück / Stopp und einem Mix-Fader |
| **Befehlszeile**, **Befehls-Ziffernblock**, **Befehls-Tasten** | Tipp- und Touch-Eingabe für Befehle |
| **Variablen / Effekte** | Wiederverwendbare Farben, Positionen, Beams und Effekte |
| **Effekt-Studio** | Eigene Effekte schreiben |
| **DMX-Monitor** | Die gesendeten Werte ansehen |
| **3D-Simulation** | Bühne und Lichter live sehen |
| **Timecode**, **Timeline-Editor**, **Video/Audio-Player**, **Livestream / Kamera** | Zeit und Medien (Anleitung *Timeline-Editor und LTC*) |
| **Audio** | Live-Musikanalyse (Spektrum, Beat, Tempo): Lichter und Cues können auf Musik reagieren |
| **Einfache Steuerung** | Eine schlichte Bedienfläche zum Weitergeben: Lichter per Kachel wählen, **Joystick**, Helligkeit, Farbfeld, Zoom, Gobos – siehe *Fernzugriff → Bedienmodus* |
| **Button**, **Fader**, **Schalter** | Eigene Knöpfe, Fader und Ein/Aus-Schalter, die Befehle ausführen (oder in die Befehlszeile schreiben) |

Panels fügst du mit **Bearbeiten → Panel hinzufügen…** hinzu.

---

## 5. Dein erster Cue

Das kannst du mit der Demo-Show nachmachen.

### Schritt 1 – Auswählen

Klicke im Tab **Scheinwerfer** der Scheinwerfer-Steuerung (oder in der Scheinwerfer-Liste) auf Scheinwerfer – oder tippe in der Befehlszeile:

```
Fixture 1 Thru 3
```

### Schritt 2 – Einen Look einstellen

Nimm den **Helligkeit**-Fader – oder tippe:

```
At 80
```

Wähle eine Farbe, wenn deine Scheinwerfer eine haben (`Color Red`). Geänderte Scheinwerfer bekommen eine rote Markierung: Sie sind jetzt im **Programmer**.

Bei Moving Heads findest du unter **Position** drei Ansichten: **Grob** (Fader für Pan und Tilt), **Fein** (ein Wisch-Streifen je Achse: nach oben oder unten wischen, die Striche folgen dem Finger – ein Schritt im Fein-Kanal je 4 Pixel) und **Joystick**. Der Joystick ist ein runder Knauf mit zwei Achsen, **relativ**: je weiter du ihn auslenkst, desto schneller fährt der Scheinwerfer; im inneren Kreis ist es sehr genau, ganz außen schnell. Beim Loslassen springt der Knauf in die Mitte und der Scheinwerfer bleibt stehen. Er verstellt Grob- und Fein-Wert, und mehrere gewählte Scheinwerfer bewegen sich um dasselbe Stück (die Abstände bleiben). Maus und Touch funktionieren.

### Schritt 3 – Einen Cue speichern

Klicke im Panel Cue-Liste auf **Cue speichern**. Ein Dialog fragt nach der **Position** (am Ende, nach einem Cue oder frei), der **Cue-Nummer** und einem optionalen **Namen**. Klicke auf **Speichern**. Oder tippe:

```
Store Cue 3 "Warmer Look"
```

Gibt es die Nummer schon, wählst du **Zusammenführen** (nur die geänderten Kanäle kommen hinein) oder **Überschreiben**.

### Schritt 4 – Abspielen

Drücke **Go** (Wiedergabe) im Panel Cue-Liste oder Executor – oder tippe `Go`. Der Look wird über die Fade-Zeit des Cues eingeblendet. `Go Cue 3` springt direkt zu einem Cue; **Zurück** geht einen Cue zurück; **Pause** und **Stopp** steuern eine laufende Überblendung.

Mit dem **Executor-Fader** mischst du zwischen deinen manuellen Werten (0 %) und dem Cue (100 %). Für eine große Show legst du **mehrere Executor-Panels** an, jedes an eine eigene Cue-Liste gebunden (Panel-Einstellungen → Liste): jedes hat seinen eigenen Fader und Go / Pause / Back / Stop – zusammen mit dem Hauptregler (*Master*) arbeiten sie als Submaster.

### Schritt 5 – Speichern

Drücke `Strg+S`. Das speichert das **Showfile** und dein **Layout**. Ohne Speichern leben Änderungen nur im Arbeitsspeicher; OpenCue fragt vor dem Schließen nach.

---

## 6. Echte Lampen anschließen

1. Öffne **Einstellungen → DMX-Ausgabe**.
2. **Art-Net**: ist beim ersten Start **aus** (es sendet ins Netzwerk) – schalte es ein. **Geräte automatisch finden** ist standardmäßig an: OpenCue sucht alle paar Sekunden Art-Net-Geräte im Netzwerk und sendet an jedes direkt, ein angesteckter Node funktioniert also einfach. **Netzwerk absuchen** zeigt, was gefunden wurde (Name, Adresse, Universen); **Verwenden** macht ein Gerät zum festen Ziel. Schalte den Automatik-Betrieb aus, um selbst eine feste **Ziel-IP** einzutragen (zum Beispiel die Art-Net-Broadcast-Adresse) und bei Bedarf die **Bind-IP** (welche Netzwerkkarte benutzt wird).
3. **sACN (E1.31)**: schalte es ein. Auch das ist standardmäßig aus, damit Windows beim ersten Start keine Firewall-Frage zeigt.
4. **USB DMX** (Enttec DMX USB Pro oder kompatibel): einschalten. Der **COM-Port** bleibt auf **Automatisch (empfohlen)**: OpenCue erkennt den Adapter beim Anstecken selbst, verbindet sich und verbindet sich nach Abziehen und Wiederanstecken erneut (auch an einem anderen USB-Anschluss). Das **Universum** wählen; einen COM-Port nur von Hand wählen, wenn mehrere Adapter angesteckt sind.
5. Startet eine Schnittstelle nicht, nutze **DMX-Schnittstellen neu initialisieren** – ohne Neustart.

Danach **patchst** du deine Scheinwerfer (Anleitung *Scheinwerfer und Patchen*): Universum und Startkanal müssen mit der am jeweiligen Gerät eingestellten Adresse übereinstimmen.

Das Panel **DMX-Monitor** zeigt genau, was gesendet wird. Der **Blackout**-Knopf setzt alle Helligkeiten sofort auf 0; ein erneuter Klick bringt den Look zurück.

---

## 7. Die Oberfläche zu deiner machen

- **Bearbeitungsmodus** (**Bearbeiten → Panels bearbeiten**, `Strg+E`): Panels verschieben und in der Größe ändern (sehr klein möglich, der Inhalt rollt dann), ihre Eigenschaften und Farben anpassen, sie kopieren und einfügen. **Rechtsklick auf die leere Fläche** legt ein Panel, einen Button, Schalter oder Fader an der Klickstelle an. Der Haken **Bearbeiten → Hilfslinien** schaltet die Ausrichtungslinien beim Verschieben ein oder aus (`Alt` gedrückt halten: kurz aus).
- **Layouts** sind Dateien. Baue mehrere (zum Beispiel ein kleines zum Programmieren und ein großes zur Wiedergabe) und wechsle mit `Strg+1` … `Strg+9` oder **Ansicht → Layouts**. Gespeichert wird mit `Strg+S` oder im Dateimanager. Ein neues, leeres Layout legst du über **Bearbeiten → Neues Layout…** an.
- **Themes** (Farbprofile): *Einstellungen → Darstellung* – dunkel, hell oder eigene.
- **GUI-Skalierung** (`Strg +` / `Strg -`): macht alles größer, etwa für Touchscreens; sie wird pro Gerät gespeichert.
- **Sprache:** Menü *Sprache* (Englisch, Deutsch, Français, Nederlands, Italiano, Español) oder `Strg+Umschalt+L`. Die Anleitungen gibt es in allen sechs Sprachen.

### Die Einstellungen im Überblick

Das Zahnrad (**Einstellungen**) öffnet einen Dialog mit Kategorien links, gruppiert nach Aufgabe. Wichtige Kategorien beginnen mit einem **großen An/Aus-Schalter**: ist er aus, ist alles darunter abgeblendet und gesperrt. Nichts gilt, bevor du **Speichern** klickst (der Dialog bleibt dabei offen); **Schließen** fragt nach, wenn noch ungespeicherte Änderungen da sind. Das Feld **Einstellungen suchen …** findet auch Einstellungen in Kategorien, die du noch nie geöffnet hast, und listet die Treffer über **alle Kategorien** (*Einstellung – Kategorie / Abschnitt*); ein Klick springt zur Zeile. Das kleine **(i)** hinter einer Einstellung zeigt ihre Erklärung; der **(i)-Knopf neben dem Suchfeld** blendet alle Erklärungen ein oder aus (wird pro Gerät gemerkt).

**Einstellungen sichern:** Unter *Allgemein* ganz unten speichert **Einstellungen exportieren** alle Einstellungen als Datei (`opencue-settings.json`), **Einstellungen importieren …** liest sie wieder ein. Importierte Werte erscheinen als **Änderungen** (markiert und gezählt) – erst **Speichern** übernimmt sie, **Schließen** verwirft sie. Nicht enthalten sind Passwörter und Zugangsschlüssel, geräte- oder rechnerbezogene Werte (Skalierung, Datenordner, Mikrofone, MIDI-Geräte) sowie die Tastenbelegung und die MIDI-Belegung – die haben ihren eigenen Export.

| Gruppe | Kategorie | Wofür |
|---|---|---|
| Programm | **Allgemein** | Die Grundlagen: Sprache, GUI-Skalierung, Layout per Wischgeste wechseln, OpenCue mit Windows starten, Updates, Sicherungen der Show, Datenordner, Einstellungen sichern |
| Programm | **Darstellung** | Farben, Themes, Voreinstellungen für neue Panels |
| Ausgabe | **DMX-Ausgabe** | Art-Net, sACN, USB-DMX – jeweils mit eigenem Schalter, **alles ist beim ersten Start aus** |
| Netzwerk | **Fernzugriff** | Tablet / Handy als Fernsteuerung: Hauptschalter, HTTP / HTTPS, Passwort, Adressen und QR-Codes, Netzwerk-Name `opencue.local` |
| Netzwerk | **REST-API** | Andere Programme steuern OpenCue: Schalter, *Erreichbar von* (nur dieser PC / im Netzwerk), Tokens |
| Bedienung | **Tastatur** | Tastaturkürzel ansehen, **eigene Tastenbelegung** (Anleitung *Tastaturkürzel*) |
| Bedienung | **MIDI** | MIDI verwenden, Geräte wählen, Ausgang, Timecode / Tempo aus MIDI, **MIDI-Belegung** (Anleitung *MIDI*) |
| Sprache & Audio | **Triggerwort** | Sprachsteuerung mit eigenem Mikrofon: Triggerwort + englischer Befehl, z. B. „OpenCue, blackout on“ (Anleitung *Sprachbefehle*); Ein/Aus mit dem Mikrofon-Symbol oben rechts |
| Sprache & Audio | **Diktieren** | Mikrofon und Sprachmodell für das Diktieren im KI-Chat |
| Assistent | **KI-Assistent** | Hauptschalter, Verbindung zu Ollama, Verhalten, Berechtigungen |
| Erweitert | **Weitere Optionen** | **Schnellschalter** (Sprachsteuerung, MIDI, Blackout, Rückgängig mit Go – wirken sofort, auch wenn ihr Knopf in der Toolbar ausgeblendet ist), **Bildschirm wach halten** (Rechner und Tablets; am iPad nur auf einer sicheren Seite, https), was oben rechts in der Leiste erscheint (jeder Eintrag einzeln, pro Gerät) und die **Internet-Verbindung** (Knopf *Verbindung testen*) |
| Erweitert | **Standardwerte** | Vorgaben für neue Cues, Grundzustand nach *Clear Clear*, Startwerte und **Löschen**: je Kategorie (Cues, Scheinwerfer, Bibliothek, Dateien, Sonstiges) eine Sicherheitsfrage vor dem Löschen – standardmäßig an |
| Erweitert | **Ein- & Ausgänge** | Nur Anzeige: jede Verbindung, wofür sie dient und **wie weit sie reicht** (*nur dieser PC*, *lokales Netzwerk*, *Internet*), mit Link zur passenden Einstellung |

**Beim ersten Start verlässt nichts den Computer:** Fernzugriff, Art-Net, sACN und die REST-API nach außen sind aus. Nur die Suche nach Updates ist an (abschaltbar); sie braucht das Internet. Klappt das Internet im Browser, aber nicht in OpenCue (Firewall, Virenscanner, Firmennetz), zeigt *Allgemein → Internet-Verbindung → Verbindung testen*, **woran** es hakt.

---

## 8. Was du als Nächstes erkunden kannst

| Thema | Wo |
|---|---|
| Scheinwerfer, GDTF-Bibliothek, Patchen, Gruppen | *Scheinwerfer und Patchen* |
| Alle getippten Befehle | *Befehlsreferenz* |
| Eigene Effekte mit einer kleinen Skriptsprache | *Effekt-Studio* |
| Tablet und Handy als Fernsteuerung | *Fernsteuerung* |
| Jedes Kürzel und jede Geste | *Tastenkürzel* (auch **Hilfe → Tastenkürzel**) |
| Bühne in 3D, Moving Heads auf einen Punkt ausrichten | Panel **3D-Simulation** (über *Panel hinzufügen*; Modi Ansicht / Bauen / Scheinwerfer) |
| Eigene 3D-Modelle (STL oder OBJ) auf der Bühne | 3D-Simulation → **Bauen** → **3D-Modell …** (Importieren oder aus der Bibliothek; die Datei-Einheit mm/cm/m/Zoll setzt die Originalgröße). **Mehrere Dateien auf einmal importieren** (im Dateidialog markieren oder im Modus *Bauen* aus dem Explorer auf die Bühne ziehen): Sie werden nebeneinander um die Bildmitte gestellt und gemeinsam ausgewählt. Verwaltet im Dateimanager unter **3D-Modelle** |
| Ein Panel kurz benutzen, ohne es ins Layout zu legen | **Ansicht → Panel als Fenster öffnen**; Befehlszeile mit Ziffernblock und Tasten: **Strg+F** (Befehls-Konsole) |
| Cues, die zu einer Zeit starten | Panel **Timecode** und der Cue-Trigger *Timecode* |
| Lichter und Cues, die auf Musik reagieren | Panel **Audio**, Effekte mit dem Schlagwort *Audio*, Cue-Trigger *Audio* (Anleitung *Audio*) |
| Cues, die auf eine Taste, ein Pad oder einen Regler eines MIDI-Geräts warten | Cue-Trigger *MIDI* (Anleitung *MIDI*, Abschnitt 5c) |
| OpenCue von anderen Programmen aus steuern | **REST-API** (Einstellungen → REST-API; Anleitung *REST-API*) |
| Dateien: Shows, Layouts, Bühnen, 3D-Modelle, Effekte | **Bibliothek → Shows… / Layouts… / 3D-Bühnen… / Effekte…** (der Dateimanager, mit Import und Export als ZIP; im Export-Paket einer Show sind auch die 3D-Modelle ihrer Bühne wählbar) |

---

## 9. Wo deine Daten liegen und wie du sie sicherst

Deine Daten sind einfache Dateien im Datenordner (standardmäßig `%LOCALAPPDATA%\OpenCue`):

| Ordner | Inhalt |
|---|---|
| `showfiles` | Shows (Scheinwerfer, Gruppen, Cues, Presets, Effekte) |
| `layouts` | Panel-Layouts |
| `themes` | Farbprofile |
| `fixtures` | GDTF-Scheinwerferdateien |
| `effects` | Effekt-Skripte (`.fx`) |
| `stages` | 3D-Bühnen |
| `media` | Videos und Audio deiner Shows |
| `config` | Einstellungen (`app_config.json`, auch die gewählte Audioquelle) und die API-Tokens (`api_tokens.json`, nur Hashes) |

Zum Sichern kopierst du den Ordner – oder nutzt den **Export** des Dateimanagers (eine Show als ZIP samt der Scheinwerfer und Effekte, die sie braucht), womit du eine Show auch auf einen anderen Computer bringst.

Im **Dateimanager** haben die Listen *3D-Modelle*, *Medien*, *Effekte* und *Scheinwerfer* einen Umschalter **Liste | Gruppen** (OpenCue merkt sich deine Wahl). *Gruppen* zeigt zuerst die Gruppen: Effekte nach Art (Dimmer, Farbe, Position, Gobo, Zoom, Fokus), Medien nach Typ (Audio, Bild, Video), Scheinwerfer nach Marke und 3D-Modelle nach der **Show**, in der sie benutzt werden (ein Modell, das in zwei Shows vorkommt, steht in beiden Gruppen; die Liste zeigt es einmal). Ein Klick öffnet eine Gruppe, *Alle Gruppen* führt zurück. **Nicht benutzte löschen** (Liste *3D-Modelle*) entfernt jedes 3D-Modell, das auf keiner Bühne steht – weder auf der geladenen noch auf einer gespeicherten –, damit sich alte Importe nicht anhäufen.

Beim Deinstallieren von OpenCue wird gefragt, ob diese Daten auch gelöscht werden sollen; die Vorgabe ist **Nein**.

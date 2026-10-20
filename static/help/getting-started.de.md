# Erste Schritte mit OpenCue

OpenCue ist ein Lichtsteuerpult für deinen PC. Diese Anleitung führt dich in etwa zehn Minuten vom Installer zum ersten Licht-Cue – ganz ohne angeschlossene Lampen, denn die ersten Schritte funktionieren mit der eingebauten Demo-Show.

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

Ist OpenCue schon installiert, erkennt das Setup das und bietet *Aktualisieren*, *Neu installieren* oder *Deinstallieren* an – deine Daten bleiben immer erhalten. OpenCue prüft auch beim Start auf neue Versionen (abschaltbar unter *Einstellungen → Allgemein*) und bietet die Installation an; *Hilfe → Nach Updates suchen…* tut das auf Wunsch.

OpenCue lässt sich über die Windows-Suche finden (Windows-Taste drücken und „OpenCue“ tippen).

---

## 3. Der erste Start

Bei einer frischen Installation öffnet OpenCue eine fertige **Demo-Show** namens **Default_1**:

- fünf **Generic Dimmer** („Dimmer 1“ … „Dimmer 5“) im Universum 1 auf den Kanälen 1 bis 5,
- eine Cue-Liste „Default“ mit zwei Cues („Cue 1“ und „Cue 2“, je eine Sekunde Überblendung),
- ein **Layout** mit den Panels, die du zuerst brauchst: Cue-Liste, Scheinwerfer-Liste, Scheinwerfer-Steuerung, Executor, Befehlszeile, Befehls-Tasten und Ziffernblock.

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
| **Hilfe** | Tastenkürzel, GitHub-Repository, Nach Updates suchen…, Über OpenCue |

### Werkzeugleiste (oben)

Die Werkzeugleiste zeigt das aktuelle **Layout** und die **Bühne**, den **Showfile-Namen** (ein Klick öffnet den Dateimanager), einen pulsierenden **Blackout**-Knopf (Glühbirne), den **Timecode**, eine DMX-Anzeige, die Zahl der verbundenen **Fernsteuer-Geräte** und den Knopf **Einstellungen**.

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
| **Timecode**, **Video/Audio-Player**, **Livestream / Kamera** | Zeit und Medien |
| **Button**, **Fader** | Eigene Knöpfe und Fader, die Befehle ausführen |

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

### Schritt 3 – Einen Cue speichern

Klicke im Panel Cue-Liste auf **Cue speichern**. Ein Dialog fragt nach der **Position** (am Ende, nach einem Cue oder frei), der **Cue-Nummer** und einem optionalen **Namen**. Klicke auf **Speichern**. Oder tippe:

```
Store Cue 3 "Warmer Look"
```

Gibt es die Nummer schon, wählst du **Zusammenführen** (nur die geänderten Kanäle kommen hinein) oder **Überschreiben**.

### Schritt 4 – Abspielen

Drücke **Go** (Wiedergabe) im Panel Cue-Liste oder Executor – oder tippe `Go`. Der Look wird über die Fade-Zeit des Cues eingeblendet. `Go Cue 3` springt direkt zu einem Cue; **Zurück** geht einen Cue zurück; **Pause** und **Stopp** steuern eine laufende Überblendung.

Mit dem **Executor-Fader** mischst du zwischen deinen manuellen Werten (0 %) und dem Cue (100 %).

### Schritt 5 – Speichern

Drücke `Strg+S`. Das speichert das **Showfile** und dein **Layout**. Ohne Speichern leben Änderungen nur im Arbeitsspeicher; OpenCue fragt vor dem Schließen nach.

---

## 6. Echte Lampen anschließen

1. Öffne **Einstellungen → DMX / Netzwerk**.
2. **Art-Net**: ist standardmäßig an; stelle die **Ziel-IP** ein (Standard ist die Art-Net-Broadcast-Adresse) und bei Bedarf die **Bind-IP** (welche Netzwerkkarte benutzt wird).
3. **sACN (E1.31)**: schalte es ein. Standardmäßig ist es aus, damit Windows beim ersten Start keine Firewall-Frage zeigt.
4. **USB DMX** (Enttec DMX USB Pro oder kompatibel): einschalten, den **COM-Port** und das **Universum** wählen. Nach dem Abziehen wird die Verbindung wiederhergestellt.
5. Startet eine Schnittstelle nicht, nutze **DMX-Schnittstellen neu initialisieren** – ohne Neustart.

Danach **patchst** du deine Scheinwerfer (Anleitung *Scheinwerfer und Patchen*): Universum und Startkanal müssen mit der am jeweiligen Gerät eingestellten Adresse übereinstimmen.

Das Panel **DMX-Monitor** zeigt genau, was gesendet wird. Der **Blackout**-Knopf setzt alle Helligkeiten sofort auf 0; ein erneuter Klick bringt den Look zurück.

---

## 7. Die Oberfläche zu deiner machen

- **Bearbeitungsmodus** (**Bearbeiten → Panels bearbeiten**, `Strg+E`): Panels verschieben und in der Größe ändern, ihre Eigenschaften und Farben anpassen, sie kopieren und einfügen.
- **Layouts** sind Dateien. Baue mehrere (zum Beispiel ein kleines zum Programmieren und ein großes zur Wiedergabe) und wechsle mit `Strg+1` … `Strg+9` oder **Ansicht → Layouts**. Gespeichert wird mit `Strg+S` oder im Dateimanager.
- **Themes** (Farbprofile): *Einstellungen → Farben* – dunkel, hell oder eigene.
- **GUI-Skalierung** (`Strg +` / `Strg -`): macht alles größer, etwa für Touchscreens; sie wird pro Gerät gespeichert.
- **Sprache:** Menü *Sprache* oder `Strg+Umschalt+L`.

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
| Cues, die zu einer Zeit starten | Panel **Timecode** und der Cue-Trigger *Timecode* |
| Dateien: Shows, Layouts, Bühnen, Effekte | **Bibliothek → Shows… / Layouts… / 3D-Bühnen… / Effekte…** (der Dateimanager, mit Import und Export als ZIP) |

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
| `config` | Einstellungen (`app_config.json`) |

Zum Sichern kopierst du den Ordner – oder nutzt den **Export** des Dateimanagers (eine Show als ZIP samt der Scheinwerfer und Effekte, die sie braucht), womit du eine Show auch auf einen anderen Computer bringst.

Beim Deinstallieren von OpenCue wird gefragt, ob diese Daten auch gelöscht werden sollen; die Vorgabe ist **Nein**.

# Startparameter und Server-Betrieb

OpenCue lässt sich mit Parametern starten – in einer Verknüpfung, einer Batch-Datei, der Aufgabenplanung oder im Terminal. Diese Anleitung listet sie auf, erklärt den **Server-Betrieb ohne Fenster** (`--no-ui`), **Start mit Windows**, was **Administratorrechte** ändern (und was nicht) und die **Windows-Firewall-Regel**.

---

## 1. Die Parameter

Sie stehen hinter dem Programm: `OpenCue.exe --no-ui --open-browser` (aus dem Quelltext: `python main.py ...`). In einer Verknüpfung: *Eigenschaften → Ziel*, hinter dem schließenden Anführungszeichen des Pfads.

| Parameter | Wirkung |
|---|---|
| `--no-ui` oder `--server-only` | Start **ohne Programmfenster** (Abschnitt 2). Schließt `--no-splash` ein. |
| `--open-browser` | Mit `--no-ui`: beim Start den Standard-Browser auf die Konsole öffnen. |
| `SHOWDATEI` oder `--show DATEI` | Diese Show laden statt der zuletzt benutzten. Eine Show-Datei als erster Parameter wirkt wie ein Doppelklick-Start; das gilt auch für eine `.ocshow`-Datei (Export-Paket). Läuft OpenCue schon, übernimmt das laufende Programm die Datei (und fragt bei ungespeicherten Änderungen vorher). |
| `--new-show` | Mit einer **leeren Show** starten statt mit der zuletzt benutzten. Nichts wird gelöscht; „zuletzt benutzt“ bleibt, wie es war. |
| `--port N` | Server-Port **nur für diesen Lauf** (1–65535). Die gespeicherte Einstellung ändert sich nicht. |
| `--remote` | **Netzwerk-Zugriff** einschalten (wie *Einstellungen → Fernzugriff*) – das wird **gespeichert**. |
| `--data-dir ORDNER` | Anderen **Datenordner** für diesen Lauf benutzen (tragbar, Tests). Wie die Variable `OPENCUE_DATA_DIR`. |
| `--fullscreen` | Programmfenster im Vollbild starten. |
| `--priority normal`, `above` oder `high` | Prozess-Priorität; Standard `above` (über normal), siehe Abschnitt 5. |
| `--no-splash` | Kein Startbild (auch: `OPENCUE_NO_SPLASH=1`). |
| `--version`, `--help` | Version bzw. Liste der Parameter ausgeben. |

Das gebaute Programm hat keine eigene Konsole: `--help` und `--version` schreiben in die Konsole, aus der es gestartet wurde (cmd, PowerShell).

---

## 2. Server-Betrieb ohne Fenster (`--no-ui`)

OpenCue startet wie gewohnt – DMX-Ausgabe, Cues, Effekte, MIDI, Fernzugriff, REST-API –, aber es öffnet sich **kein Programmfenster**. Bedient wird

- **im Browser auf diesem Rechner:** `http://127.0.0.1:8000` (der Port aus *Einstellungen → Fernzugriff*, oder `--port`) – genau dieselbe Konsole wie im Fenster, oder
- **mit Tablet oder Handy** über das Netzwerk (in den Einstellungen den **Fernzugriff** einschalten oder einmal mit `--remote` starten).

Ein **Symbol im Infobereich** der Taskleiste zeigt, dass OpenCue läuft: **Klick** öffnet die Konsole im Browser; **Rechtsklick** zeigt das Menü *OpenCue im Browser öffnen*, *Log-Ordner öffnen* und *OpenCue beenden*. Hat die Show ungespeicherte Änderungen, fragt das Beenden einmal nach (eine Sicherungskopie wird in jedem Fall geschrieben).

Das Menü zeigt oben den **Namen der Show**, bei ungespeicherten Änderungen die Warnung **⚠ Ungespeicherte Änderungen** (der Hinweistext am Symbol ebenso) und die **Adressen**, unter denen die Konsole erreichbar ist (bei eingeschaltetem Fernzugriff auch die im Netzwerk) – ein Klick darauf öffnet sie im Browser.

Weitere Wege zum Beenden: **Datei → Beenden** im Browser, **Strg+C**, wenn es aus einem Terminal gestartet wurde, sowie Abmelden oder Herunterfahren von Windows (OpenCue versucht dann, sich sauber zu beenden, mit der üblichen Sicherung).

**Ein zweiter Start** von OpenCue, während der Server läuft, zeigt keinen Fehler: er öffnet einfach den Browser auf der laufenden Konsole.

Was **ohne Fenster eventuell nicht geht**: alles, was das Programmfenster selbst braucht – zum Beispiel der Datei-Dialog zum *Verknüpfen* einer Video- oder Audiodatei oder der Vollbild-Schalter des Fensters. Alles andere gibt es im Browser.

Tipp: Für einen Bühnen-PC, der nur DMX ausgibt, *Start mit Windows* + *Ohne Fenster starten* einschalten (Abschnitt 3).

---

## 3. Start mit Windows

**Einstellungen → Allgemein → Verhalten:**

- **OpenCue beim Anmelden an Windows starten** – ein Eintrag für **deinen Windows-Benutzer** (keine Administratorrechte nötig; Ausschalten entfernt ihn).
- **Ohne Fenster starten (nur Server)** – startet mit `--no-ui`.

Das gibt es im **installierten Programm**, nicht beim Start aus dem Quelltext. (Eine exportierte Show mit der Endung `.ocshow` öffnet sich dort immer per Doppelklick in OpenCue – dafür gibt es keinen Schalter.) Der Eintrag zeigt auf die Programmdatei: Wird OpenCue verschoben oder anderswo neu installiert, aus- und wieder einschalten.

---

## 4. Administratorrechte und die Firewall

**Läuft OpenCue als Administrator?** Das Protokoll (`opencue.log`, erste Zeilen) und die Angaben eines Fehlerberichts nennen *„Administrator: yes“* oder *„no“*. Läuft es so, schreibt OpenCue auch einen Hinweis ins Protokoll.

**Du brauchst es nicht – und solltest es nicht benutzen:** Windows blockiert das **Ziehen von Dateien aus dem Explorer** in ein Programm, das als Administrator läuft, und ein Webserver mit Administratorrechten ist ein größeres Ziel. Administratorrechte helfen bei **einer** Sache: beim Anlegen der **Windows-Firewall-Regel**.

**Firewall-Regel:** Ohne sie fragt Windows beim ersten Netzwerk-Zugriff von OpenCue nach; eine unbeantwortete oder abgelehnte Frage blockiert Tablets, sACN und den Netzwerk-Namen `opencue.local`. **Einstellungen → Fernzugriff → Windows-Firewall → OpenCue in der Firewall erlauben** legt eine Regel für genau dieses Programm an, **eingehend, nur in privaten und Domänen-Netzwerken** (nie in öffentlichen). Windows fragt **einmal** um Erlaubnis (Administrator-Rückfrage) – nur dieser eine kleine Befehl läuft mit erhöhten Rechten, OpenCue selbst läuft normal weiter. *Firewall-Regel entfernen* löscht sie wieder. Die Statuszeile zeigt, ob die Regel existiert.

---

## 5. Priorität und genaue Zeitgeber

Beim Start setzt OpenCue die **Prozess-Priorität** auf *über normal* und die **Zeitgeber-Auflösung auf 1 ms** (Windows tickt sonst alle 15,6 ms). Beides hält die 40-Hz-Schleifen von Cues, Effekten und DMX gleichmäßig, wenn der Rechner ausgelastet ist – ohne Administratorrechte. `--priority high` erhöht weiter (für einen PC, der sonst nichts tut), `--priority normal` schaltet es ab.

---

## 6. Beispiele

- Server auf einem Bühnen-PC, Browser öffnet sich: `OpenCue.exe --no-ui --open-browser`
- Eine Show aus dem Explorer („Öffnen mit“): `OpenCue.exe "D:\Shows\Konzert.json"`
- Leer starten, ohne die letzte Show anzufassen: `OpenCue.exe --new-show`
- Test auf anderem Port mit eigenen Daten: `OpenCue.exe --port 8080 --data-dir D:\OpenCueTest`

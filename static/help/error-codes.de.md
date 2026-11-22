# Fehlercodes und Fehlerbehebung

Wenn etwas schiefgeht, verschwindet OpenCue nicht einfach: Es zeigt ein kleines **Fehlerfenster** mit einer kurzen Erklärung und einem **Fehlercode** wie `OC-1002`. Derselbe Code steht in der **Log-Datei**. Diese Seite erklärt jeden Code: was er bedeutet und wie man ihn behebt.

Wenn du ein Problem nicht lösen kannst, kopiere die Details (siehe Abschnitt 1) und schicke sie mit deiner Frage mit – der Code zeigt sofort, wo man suchen muss.

---

## 1. Das Fehlerfenster

Das Fenster hat eine Überschrift, eine kurze Erklärung, den **FEHLERCODE**, manchmal eine Box mit technischen Angaben und diese Knöpfe (das Fenster selbst ist immer englisch):

| Knopf | Was er tut |
|---|---|
| **Details kopieren** | Legt alles, was für einen Fehlerbericht nötig ist, in die Zwischenablage: Fehlercode, OpenCue-Version, Windows- und Python-Version, den Fehlertext und die **letzten 40 Zeilen des Logs**. Einfügen in eine E-Mail, ein GitHub-Issue oder einen Chat mit einem Assistenten. (Tastenkürzel: **Strg+C**) |
| **Log-Ordner öffnen** | Öffnet den Ordner mit den Log-Dateien im Explorer. |
| **Log-Datei öffnen** | Öffnet das aktuelle Log (`opencue.log`) im Texteditor. |
| **Schließen** | Schließt das Fenster (auch **Esc** oder das **×**). Hat der Fehler OpenCue beendet, endet das Programm nach dem Schließen. |

Das Fenster lässt sich an der Titelleiste verschieben. Das Fehlerfenster erscheint in der Sprache von OpenCue (englisch, wenn sie nicht ermittelt werden kann); der Text, den *Details kopieren* in die Zwischenablage legt, ist immer englisch, damit ein Bericht von jedem gelesen werden kann.

---

## 2. Wo die Log-Dateien liegen

Jeder Start von OpenCue schreibt ein Log:

| Datei | Inhalt |
|---|---|
| `opencue.log` | Der **aktuelle** Start: alles, was OpenCue meldet – Hinweise, Warnungen, Fehler mit ihren Codes und Absturzspuren. |
| `opencue.previous.log` | Das Log des **Starts davor**. Nach einem Absturz und Neustart steht die Ursache hier noch drin. |

Sie liegen im Ordner `logs` im OpenCue-Datenordner – normalerweise `%LOCALAPPDATA%\OpenCue\logs` (in die Adresszeile des Explorers eintippen). Das Fehlerfenster öffnet ihn für dich.

**Im Log suchen:** Codes stehen als `OC-1234` im Text. Suche nach `OC-`, um alle zu finden, oder nach `OC-3` für die kleinen Probleme einzelner Funktionen (Abschnitt 5).

---

## 3. Startprobleme (OC-1xxx)

OpenCue prüft diese Dinge **bevor** etwas anderes startet. Das Fenster sagt, was nicht stimmt; danach schließt sich OpenCue.

### OC-1001 – OpenCue läuft bereits

**Bedeutung:** Pro Datenordner kann nur ein OpenCue gleichzeitig laufen. Ein zweites würde um dieselben Einstellungen, denselben Port und denselben DMX-Ausgang kämpfen.

**Was passiert:** Das Fenster des laufenden OpenCue wird nach vorn geholt, und dieses Fenster erscheint. (Läuft ein **Server ohne Fenster**, siehe die Anleitung *Startparameter und Server-Betrieb*, erscheint keine Fehlermeldung: stattdessen öffnet sich dein Browser auf der laufenden Konsole.)

**Was tun:**
- Das nach vorn geholte Fenster benutzen. Siehst du es nicht, schau auf deinen **anderen Bildschirmen** und in der **Taskleiste** nach.
- OpenCue gerade geschlossen und trotzdem diese Meldung? Es braucht ein paar Sekunden zum Beenden. Kurz warten und neu starten.
- Gar nichts zu sehen? Im **Task-Manager** nach `OpenCue` suchen (beim Start aus dem Quelltext `python`/`pythonw`) und den übrig gebliebenen Prozess beenden.
- Für Fortgeschrittene: Für ein zweites, getrenntes OpenCue (z. B. zum Testen) die Umgebungsvariable `OPENCUE_DATA_DIR` auf einen anderen Ordner setzen **und** in dessen `app_config.json` einen anderen Port eintragen (siehe OC-1002).
- **Neustart gleich nach dem Schließen:** OpenCue wartet jetzt (bis zu etwa 25 Sekunden), bis das alte fertig beendet ist, und startet dann von selbst. Die Meldung erscheint nur, wenn das alte nicht fertig wird.

### OC-1002 – Netzwerk-Port ist schon belegt

**Bedeutung:** OpenCue hat einen kleinen eingebauten Server, mit dem sein Fenster spricht. Dafür braucht es einen freien Netzwerk-Port (Standard **8000**). Ein anderes Programm benutzt ihn. Ohne diese Prüfung würde das OpenCue-Fenster die Seite des *anderen* Programms zeigen.

**Was tun:**
1. Das andere Programm schließen. Häufige Ursachen: ein anderer Webserver oder ein Entwicklerwerkzeug, oder ein übrig gebliebener OpenCue-Prozess (siehe OC-1001, Task-Manager).
2. Wer den Port benutzt, findest du in der Eingabeaufforderung mit `netstat -ano | findstr :8000` (deine Portnummer einsetzen). Die letzte Spalte ist die Prozess-ID; im Task-Manager (Reiter *Details*) nachschlagen.
3. Oder OpenCue einen anderen Port geben: OpenCue schließen, die im Fenster genannte Einstellungsdatei (normalerweise `%LOCALAPPDATA%\OpenCue\config\app_config.json`) im Texteditor öffnen und `"server_port": 8000` auf eine freie Zahl zwischen **1024 und 65535** ändern, z. B. `8010`. Fehlt die Zeile, füge sie hinzu. Speichern und OpenCue neu starten. (Läuft OpenCue, geht es auch in **Einstellungen → Fernzugriff → HTTP-Port**.)

### OC-1003 – Microsoft Edge WebView2 Runtime nicht gefunden

**Bedeutung:** OpenCue zeigt sein Fenster mit der kostenlosen **Microsoft Edge WebView2 Runtime**. Windows 11 hat sie; Windows 10 meist über Edge oder Office, aber nicht immer.

**Was tun:** **Download-Seite öffnen** anklicken, die *Evergreen*-Runtime von Microsoft installieren und OpenCue neu starten. Bist du sicher, dass sie installiert ist, wähle **Trotzdem starten**. Der OpenCue-Installer lädt die Runtime selbst nach, wenn sie fehlt und Internet da ist.

### OC-1004 – Der Datenordner ist nicht benutzbar

**Bedeutung:** OpenCue speichert Einstellungen, Shows, Layouts und Logs in seinem **Datenordner** (normalerweise `%LOCALAPPDATA%\OpenCue`) und kann ihn nicht anlegen oder beschreiben. Die Zeile unter der Erklärung nennt den technischen Grund.

**Was tun:** Prüfen, dass der Ordner existiert und dein Windows-Konto dort schreiben darf; dass das Laufwerk nicht voll und nicht schreibgeschützt ist und (bei Netzwerk- oder USB-Laufwerk) verbunden ist; dass kein Virenscanner oder „Überwachter Ordnerzugriff“ OpenCue blockiert. Wurde bei der Installation ein eigener Datenordner gewählt, muss dieses Laufwerk verfügbar sein. Auch ein Ordnername, der in Wahrheit eine vorhandene **Datei** ist, verursacht das.

---

## 4. Unerwartete Fehler (OC-2xxx)

Das sind Fehler, die OpenCue nicht erwartet hat – meist ein Programmfehler. **Bitte die Details kopieren und melden.** Fehlertext und Log zeigen, wo es passiert ist.

### OC-2001 – OpenCue konnte nicht starten

Ein unerwarteter Fehler hat OpenCue beim Starten gestoppt. Einmal neu starten. Kommt er wieder: Details kopieren und melden. Als Umweg kann eine beschädigte Einstellungsdatei die Ursache sein: OpenCue schließen, im Datenordner `config\app_config.json` in `app_config.old.json` umbenennen und neu starten (OpenCue startet dann mit Standardeinstellungen; Shows und Layouts sind eigene Dateien und bleiben erhalten).

### OC-2002 – Eine Hintergrundaufgabe ist fehlgeschlagen

In einer Hintergrundaufgabe ging etwas schief, z. B. Audioanalyse, MIDI oder Netzwerk. **OpenCue läuft weiter.** Das Fenster erscheint nur beim *ersten* solchen Fehler pro Start (alle stehen im Log). Verhält sich etwas seltsam, speichere deine Show und starte OpenCue neu. Bitte mit den kopierten Details melden.

### OC-2003 – Der OpenCue-Server wurde gestoppt

Der eingebaute Server hat unerwartet aufgehört oder ließ sich nicht starten, sodass das Fenster nicht arbeiten kann. OpenCue schließt sich nach dem Fenster und gibt vorher DMX-Ausgabe und Kameras frei. OpenCue neu starten. Passiert es wieder, melden; prüfe auch OC-1002 (ein Port-Problem kann ebenfalls hier enden).

### OC-2004 – OpenCue wurde unerwartet beendet

Während des Betriebs ist ein unerwarteter Fehler aufgetreten, und das Programm muss schließen. **Nicht gespeicherte Änderungen können verloren gehen.** OpenCue neu starten und den Fehler mit den kopierten Details melden. Tipp: Bei langen Einsätzen die Show regelmäßig speichern (**Strg+S**).

---

## 5. Probleme einzelner Funktionen (OC-3xxx, nur im Log)

Diese öffnen **kein** Fenster, und OpenCue läuft weiter. Sie stehen als erstes in einer **Log-Zeile** (z. B. `... [DMX] OC-3103 USB DMX: COM3 ...`) und oft als Hinweis auf der passenden Einstellungsseite. Im Log nach `OC-3` suchen.

| Code | Bedeutung | Was tun |
|---|---|---|
| **OC-3001** | Die Einstellungsdatei `app_config.json` ließ sich nicht lesen. OpenCue hat die automatische Sicherung (`.bak`) benutzt oder, wenn auch sie beschädigt war, die Standardeinstellungen. Die beschädigte Datei liegt daneben als `.corrupt`. | Einstellungen prüfen. Um ältere Einstellungen zu behalten, Werte aus der `.corrupt`-Datei in die neue `app_config.json` übernehmen (vorher OpenCue schließen). |
| **OC-3101** | Im DMX-Ausgabe-Thread ist ein Fehler aufgetreten. | DMX-Einstellungen (Einstellungen → DMX-Ausgabe) und Netzwerk- bzw. USB-Verbindung prüfen. Bei Wiederholung melden. |
| **OC-3102** | Die Art-Net-Ausgabe ließ sich mit den aktuellen Einstellungen nicht (neu) aufbauen. | Ziel- und Bind-IP-Adresse in den DMX-Einstellungen prüfen. Der Netzwerkadapter muss vorhanden und verbunden sein. |
| **OC-3103** | Das USB-DMX-Gerät wurde abgezogen oder meldete einen Sendefehler. | Wieder einstecken und in den DMX-Einstellungen *Ports neu laden* drücken. Anderen USB-Anschluss oder anderes Kabel probieren; prüfen, dass kein anderes Programm den Port benutzt. |
| **OC-3104** | Im Takt der DMX-Ausgabe (der die Bilder an Art-Net, sACN und USB sendet) ist ein Fehler aufgetreten. | OpenCue läuft weiter und der Takt macht beim nächsten Bild weiter. Bei Wiederholung melden (Hilfe → Problem melden). |
| **OC-3105** | Der **eigene Prozess der DMX-Ausgabe** (im Taskmanager ein zweiter OpenCue-Prozess) ist beendet worden oder ließ sich nicht starten. | OpenCue startet ihn automatisch neu (die Ausgabe ist dann in unter einer Sekunde wieder da). Stirbt er fünfmal in einer Minute oder startet er gar nicht, läuft die Ausgabe im Hauptprogramm weiter – ohne die Trennung, aber ohne Ausfall. Antivirenprogramm prüfen (es darf `OpenCue.exe` als zweiten Prozess starten); bei Wiederholung melden. |
| **OC-3201** | Die Audioanalyse konnte ihren Eingang oder ihre Quelle nicht öffnen (Gerät belegt, entfernt oder durch die Windows-Datenschutzeinstellung blockiert). | Im Audio-Panel eine andere Quelle wählen. Programme schließen, die das Gerät exklusiv nutzen. Für ein Mikrofon in Windows *Einstellungen → Datenschutz → Mikrofon* den Zugriff erlauben. |
| **OC-3202** | Die Sprachsteuerung konnte das gewählte Mikrofon nicht öffnen (OpenCue versucht es mehrmals). | In den Einstellungen unter „Triggerwort“ das Mikrofon neu wählen; andere Programme schließen, die es festhalten; die Windows-Mikrofon-Datenschutzeinstellung prüfen. |
| **OC-3301** | Ein MIDI-Gerät ließ sich nicht öffnen. Unter Windows kann die meisten Geräte nur **ein Programm** gleichzeitig benutzen. | Das andere Programm (Musiksoftware, DAW) schließen oder das Gerät dort abschalten. Gerät aus- und wieder einstecken. |
| **OC-3401** | Der Name `opencue.local` ließ sich im Netzwerk nicht bekannt machen (mDNS). Fernbediente Geräte können weiter die IP-Adresse benutzen. | Die Adresse mit der IP-Nummer aus den Einstellungen unter Fernzugriff verwenden. Prüfen, dass das Netzwerk Multicast erlaubt und die Windows-Firewall OpenCue in privaten Netzwerken zulässt. |
| **OC-3402** | OpenCue konnte auf einer Netzwerkadresse nicht für Fernbedienungsgeräte lauschen. | Evtl. benutzt ein anderes Programm den Port, oder die Adresse ist weg (WLAN gewechselt). In Einstellungen → Fernzugriff den Fernzugriff aus- und wieder einschalten oder einen anderen Port wählen. |
| **OC-3501** | Das Update ließ sich nicht herunterladen, oder die Prüfsumme stimmte nicht. | Internetverbindung prüfen und später erneut versuchen, oder den Installer von der Release-Seite laden. |
| **OC-3502** | Das heruntergeladene Update-Setup ließ sich nicht starten. | Den Installer von der Release-Seite laden und selbst ausführen. |
| **OC-3601** | Die Oberfläche hat einen JavaScript-Fehler gemeldet. Die Protokollzeile nennt die Meldung, Datei und Zeile und auf welchem Gerät es passiert ist (Konsole oder ein entferntes Gerät). Oft ist nichts zu sehen, manchmal bleibt ein Panel leer. | Das Fenster (bzw. die Seite am entfernten Gerät) neu laden. Tritt es wieder auf, mit *Hilfe → Problem melden* berichten – die Zeile gehört zur Diagnose. |
| **OC-3701** | Eine Sicherung der Show im Hintergrund ließ sich nicht schreiben (Platte voll, Ordner nicht beschreibbar oder vom Virenscanner geschützt). Die Show selbst ist davon nicht betroffen. | Speicherplatz schaffen oder einen anderen Datenordner wählen (*Einstellungen → Allgemein → Datenordner & Dateiverwaltung*). *Datei → Sicherung wiederherstellen* zeigt, welche Sicherungen es gibt; der Ordner heißt `backups` im Datenordner. |
| **OC-3801** | OSC konnte seinen UDP-Port nicht öffnen (ein anderes Programm benutzt ihn). | Unter **Steuerung → OSC …** einen anderen Port wählen oder das andere Programm schließen. |

---

## 6. Ein Problem melden

1. Am einfachsten: **Hilfe → Problem melden …** legt die Diagnose in die Zwischenablage und öffnet die Meldeseite. (Im Fehlerfenster: **Details kopieren**.) **Hilfe → Log-Ordner öffnen** öffnet den Ordner mit `opencue.log`.
2. Auf der **Issues**-Seite des OpenCue-Projekts auf GitHub beschreiben, was du vor dem Fehler getan hast.
3. Den kopierten Text einfügen. Er enthält keine Show-Daten, nur die technischen Angaben aus Abschnitt 1.

Bitte keine Passwörter oder Zugangsschlüssel schicken; falls du Log-Zeilen aus einer Einstellungsseite eingefügt hast, entferne sie vorher.

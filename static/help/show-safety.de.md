# Sicherungen, Sperre und sicheres Beenden

Du hast die Show vor der Veranstaltung programmiert und speicherst jetzt **mit Absicht nicht mehr** – nichts soll aus Versehen überschrieben werden. OpenCue schützt dich auf vier Wegen: **Sicherungen im Hintergrund**, **Wiederherstellung** nach einem Absturz, eine **Sperre** für fertige Shows und einen **vorsichtigen Beenden-Dialog**. Diese Anleitung erklärt alle vier und wie man ein Problem meldet.

---

## 1. Sicherungen im Hintergrund

OpenCue schreibt regelmäßig den **aktuellen Stand deiner Show** – auch Änderungen, die du *nicht* gespeichert hast – in einen versteckten Ordner. Du siehst ihn nie, bis du ihn brauchst. Eine Sicherung **ersetzt niemals deine Show-Datei**.

- **Wann:** standardmäßig alle **15 Minuten**, aber **nur**, wenn die Show ungespeicherte Änderungen hat und sich seit der letzten Sicherung etwas geändert hat. Nichts geändert = nichts geschrieben.
- **Außerdem:** beim Beenden ohne Speichern, wenn das Speichern gescheitert ist (zum Beispiel weil die Show gesperrt ist) und kurz bevor du eine andere Show öffnest oder neu beginnst, obwohl die jetzige noch ungespeicherte Änderungen hat.
- **Wie viele:** die neuesten **10** je Show bleiben erhalten, insgesamt höchstens 100; ältere werden automatisch gelöscht.
- **Wo:** der Ordner `backups` im Datenordner (`%LOCALAPPDATA%\OpenCue\backups`). Eine Sicherung ist eine ganz normale Show-Datei.

### Einstellungen

**Einstellungen → Allgemein → Sicherungen der Show**:

| Einstellung | Bedeutung |
|---|---|
| **Show im Hintergrund sichern** | Die ganze Funktion ein- oder ausschalten (Standard: an). |
| **Alle (Minuten)** | Das Intervall, 1 bis 240 (Standard 15). |
| **Behalten je Show** | Wie viele Sicherungen einer Show bleiben, 1 bis 50 (Standard 10). |
| **Sicherung wiederherstellen …** / **Ordner öffnen** | Öffnet den Wiederherstellen-Dialog (Abschnitt 2) oder den Ordner im Explorer. |

Die Einstellungen gelten für das ganze Programm und lassen sich von jedem Gerät aus ändern, auch von einem Fernsteuer-Gerät.

---

## 2. Eine Sicherung wiederherstellen

**Datei → Sicherung wiederherstellen …** (oder der Knopf in den Einstellungen) listet alle Sicherungen, die neueste zuerst: Show-Name, Zeitpunkt, Anlass (automatisch, beim Beenden, von Hand, vor einer Wiederherstellung, Speichern gescheitert) und Größe.

- **Wiederherstellen** lädt die Sicherung als **ungespeicherte Show**. Die Show-Datei auf der Platte bleibt genau wie sie ist, auch wenn sie gesperrt ist. Danach **Speichern** (oder **Showfile speichern unter...**), wenn du zufrieden bist.
- Der Stand von vorher wird zuerst gesichert – auch eine Wiederherstellung kann nichts verlieren.
- **Jetzt sichern** macht sofort eine Sicherung; **Löschen** entfernt eine. Das geht alles auch von einem Fernsteuer-Gerät (*Ordner öffnen* zeigt dort den OpenCue-Explorer).
- Shows, Layouts, Bühnen und Einstellungen werden **sicher** geschrieben: erst in eine Nachbardatei, dann ausgetauscht – ein Absturz oder Stromausfall mitten im Speichern kann die vorhandene Datei nicht zerstören.

### Nach einem Absturz

Wurde OpenCue nicht sauber beendet (Absturz, Stromausfall, Prozess beendet), bietet es beim nächsten Start **die letzte Sicherung dieser Sitzung an**: *„OpenCue wurde nicht sauber beendet … Wiederherstellen?“* – **Wiederherstellen**, **Alle Sicherungen zeigen** oder **Jetzt nicht** (die Sicherungen bleiben unter *Datei → Sicherung wiederherstellen …* erhalten).

---

## 3. Eine Show sperren

Eine fertige Show lässt sich **sperren**, damit niemand sie aus Versehen ändert. Im **Dateimanager** (*Datei → Dateimanager...*, Art *Shows*) auf das **Schloss-Symbol** in der Zeile der Show klicken; noch einmal klicken hebt die Sperre auf.

Eine gesperrte Show:

- ist in der Liste mit **Gesperrt** markiert und zeigt neben dem Show-Namen in der oberen Leiste ein kleines **Schloss**, solange sie geladen ist,
- lässt sich **nicht überschreiben, umbenennen oder löschen** – beim Speichern kommt *„Nicht gespeichert: … ist gesperrt“*,
- lässt sich weiter **laden**, **duplizieren** (die Kopie ist nicht gesperrt) und unter **anderem Namen** mit *Showfile speichern unter...* speichern.

Die Sperre schützt vor Versehen, nicht vor Kopieren: die Datei selbst lässt sich mit jedem anderen Programm ändern.

---

## 4. Sicher beenden

**Datei → Beenden** (oder der Schließen-Knopf) fragt: **Schließen mit Speichern**, **Schließen ohne Speichern** oder **Abbrechen**.

Lässt sich die Show **nicht speichern**, hat aber Änderungen – sie ist gesperrt, die Datei schreibgeschützt, der Ordner nicht beschreibbar oder das letzte Speichern ist gescheitert –, sieht der Dialog anders aus:

- Eine **orange Box** oben sagt *„Diese Show kann nicht gespeichert werden“* und nennt die Gründe. Sie sagt auch, ob eine Sicherungskopie deiner Änderungen erhalten bleibt.
- **Als Kopie speichern und beenden …** ersetzt *Schließen mit Speichern*: du wählst einen neuen Namen, die Show wird dort gespeichert, dann beendet sich OpenCue.
- **Schließen ohne Speichern** braucht **zwei Klicks**: der erste färbt den Knopf rot (*„Noch einmal klicken: beenden, Änderungen gehen verloren“*), erst der zweite beendet.

Auch dann wird beim Beenden noch eine Sicherung deiner Änderungen geschrieben (wenn die Sicherungen an sind); *Datei → Sicherung wiederherstellen …* holt sie zurück.

---

## 5. Ein Problem melden

- **Hilfe → Log-Ordner öffnen** öffnet den Ordner mit `opencue.log`.
- **Hilfe → Problem melden …** legt die **Diagnose** (Version, System, die letzten Protokollzeilen – ohne Zugangsschlüssel oder Passwörter) in die Zwischenablage und öffnet die Meldeseite des Projekts im Browser. Beschreibe, was du getan hast, und füge die Diagnose ein.
- Fehler der Oberfläche stehen im Protokoll als **OC-3601**, eine Sicherung, die sich nicht schreiben ließ, als **OC-3701** (siehe die Anleitung *Fehlercodes*).

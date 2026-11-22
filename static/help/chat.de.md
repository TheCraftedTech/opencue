# Chat und Notizen

Das Panel **Chat & Notizen** ist ein kleiner Messenger und ein Notizbuch in einem. Du kannst mit den **anderen Geräten chatten**, die mit OpenCue verbunden sind – Konsole, iPad, Handy – und **Notizen und Checklisten** für die Show führen: eine To-do-Liste vor dem Einlass, ein Merkzettel zum Patch, der Ablauf der Zugabe.

Alles wird **auf dem Server** gespeichert (dem Computer, auf dem OpenCue läuft). Jedes Gerät sieht dieselben Chats und Notizen, und sie sind morgen noch da.

---

## 1. Panel öffnen

*Bearbeiten → **Panel hinzufügen** → Bühne und Assistent → **Chat & Notizen*** (am Tablet genauso). Du kannst das Panel mehrfach hinzufügen und frei anordnen; alle zeigen dieselben Chats und Notizen.

Links steht die **Liste** der Chats und Notizen. Der erste Knopf im Kopf blendet sie aus; in einem schmalen Panel schiebt sie sich über den Inhalt. Der Knopf **+** legt einen **neuen Chat** oder eine **neue Notiz** an. Unter der Liste siehst du **deinen Namen**.

---

## 2. Mit anderen Geräten chatten

- Chat anklicken, tippen, mit **Enter** senden – **Umschalt + Enter** beginnt eine neue Zeile.
- Jede Nachricht zeigt, wer sie wann geschrieben hat. Deine eigenen Nachrichten stehen rechts.
- **Dein Name** (unten links, zum Ändern anklicken) wird je Gerät gewählt, zum Beispiel „Mischpult“ oder „iPad Bühne“. Er wird auf diesem Gerät gemerkt. Solange du keinen gewählt hast, heißt die Konsole „Konsole“ und ein Tablet „Fernsteuerung“ mit einer Nummer.
- Neue Nachrichten erscheinen **sofort** auf jedem Gerät. Ist der Chat auf einem Gerät nicht geöffnet, erscheint in der Liste ein kleiner **Punkt** und eine kurze Meldung.
- Solange jemand schreibt, siehst du unter den Nachrichten **„Name schreibt gerade“**. In einer Notiz steht **„Name bearbeitet die Notiz“**, solange jemand anderes darin arbeitet.
- Fahre mit der Maus über eine Nachricht (am Touchscreen sind die Knöpfe immer sichtbar) für **Kopieren** und **Löschen**. Löschen entfernt die Nachricht auf allen Geräten.
- Doppelklick auf den Titel (oder der Stift) **benennt** einen Chat um; der Mülleimer löscht den ganzen Chat nach Rückfrage.
- **Fett**, *kursiv*, `Code`, ++unterstrichen++ und Links funktionieren in Nachrichten wie in Notizen (Abschnitt 4).

---

## 3. Notizen und Checklisten

Eine Notiz ist ein Text in **Markdown** – du musst Markdown aber nicht kennen: die **Werkzeugleiste** erledigt das.

| Knopf | Was er macht |
|---|---|
| **B**, *I*, U, S | fett, kursiv, unterstrichen, durchgestrichen (auch **Strg+B / I / U**) |
| H | Überschrift – nochmal klicken für eine kleinere |
| Listen-Knöpfe | Liste mit Punkten, nummerierte Liste, **Checkliste**, Zitat, Code |

- **Bearbeiten / Ansicht** (oben rechts): *Ansicht* zeigt die fertige Notiz. In der Ansicht kannst du **Checkboxen direkt abhaken** – ideal für eine Checkliste, die du während der Show abarbeitest. Ein Doppelklick in der Ansicht startet das Bearbeiten.
- **Enter** in einer Liste setzt sie mit dem nächsten Punkt fort; **Enter** in einem leeren Punkt beendet die Liste. **Tab / Umschalt + Tab** rücken Punkte ein bzw. aus.
- In der Liste zeigt eine Notiz, wie viele Aufgaben erledigt sind, zum Beispiel „3/5“.
- Notizen werden **automatisch gespeichert**, kurz nachdem du aufgehört hast zu tippen („Gespeichert“ neben den Knöpfen).

---

## 4. Markdown auf einen Blick

| Du tippst | Du bekommst |
|---|---|
| `**fett**` | **fett** |
| `*kursiv*` | *kursiv* |
| `++unterstrichen++` | unterstrichen |
| `~~durchgestrichen~~` | durchgestrichen |
| `# Überschrift`, `## Kleiner` | Überschriften |
| `- Punkt` | Liste mit Punkten (zwei Leerzeichen einrücken für eine Unterliste) |
| `1. Punkt` | nummerierte Liste |
| `- [ ] Aufgabe` / `- [x] erledigt` | Checkbox |
| `> Zitat` | Zitat |
| `` `Code` `` | Code |
| `---` | waagerechte Linie |
| `[Text](https://...)` | Link |

---

## 5. Gut zu wissen

- Chats und Notizen gehören zum **Programm, nicht zu einer Show**: sie bleiben, wenn du eine andere Show lädst.
- Sie liegen als Dateien im Datenordner (`notebook`); kopiere den Ordner, um sie auf einen anderen Computer mitzunehmen.
- **Als Datei speichern:** Der Download-Knopf im Kopf speichert den geöffneten Chat oder die Notiz als **Markdown-Datei** (`.md`): eine Notiz als ihren Text, einen Chat als Verlauf nach Tagen gegliedert.
- **Sichern und mitnehmen:** *Dateimanager → Alles sichern* nimmt alle Chats und Notizen mit. Bei *Show exportieren...* lassen sie sich dem Paket hinzufügen (standardmäßig aus, jeder Eintrag einzeln). Beim Einlesen wird nichts überschrieben – ein abweichender Eintrag kommt als Kopie dazu.
- **Aus Programmen und Geräten:** Skripte und Hardware (zum Beispiel ein ESP32) können Chats und Notizen über die REST-API lesen und schreiben – Rechte *Chats und Notizen lesen* und *Chats und Notizen schreiben* (siehe Anleitung REST-API, Abschnitt 6).
- **Mehrere Personen in derselben Notiz:** der zuletzt gespeicherte Stand gilt. Tippen zwei Personen im selben Moment, erscheint ein Hinweis. Nutzt getrennte Notizen oder wechselt euch ab.
- Grenzen: 300 Chats und Notizen, 4000 Zeichen je Nachricht, 100 000 je Notiz; von einem Chat bleiben die letzten 5000 Nachrichten.
- Jeder, der mit OpenCue verbunden ist, kann alles lesen und schreiben – der Chat ist **nicht privat**. Schreibe keine Passwörter hinein.
- Nichts verlässt dein Netzwerk.

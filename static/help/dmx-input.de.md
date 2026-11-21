# DMX-Eingang (Art-Net und sACN empfangen)

OpenCue kann DMX nicht nur senden, sondern auch **über das Netzwerk empfangen** – von einem Lichtpult, einer Software (z. B. einem Visualisierer oder einer Show-Steuerung) oder einem Gerät. Die empfangenen Werte lassen sich **weiterleiten und mischen** oder als **Auslöser** nutzen.

Öffnen: **Steuerung → DMX-Eingang…** (auch von einem Tablet aus änderbar).

---

## 1. Einschalten

- Schalter **DMX empfangen** einschalten (aus ist der Standard – DMX hat kein Passwort, jeder im Netzwerk kann senden).
- **Protokolle:** Art-Net (UDP 6454) und/oder sACN / E1.31 (UDP 5568, Multicast). Art-Net-Universum = *Port-Address* (genau wie OpenCue es sendet: Universum 1 = Port-Address 1).
- **Erlaubte Absender:** leer = jeder; sonst IP-Adressen oder deren Anfänge (z. B. `192.168.1.`).
- **Netzwerkkarte:** nur nötig, wenn der Rechner mehrere hat und der Eingang an einer bestimmten lauschen soll.
- **Quelle verschwunden nach:** so lange ohne Paket, danach gibt OpenCue die Werte der Quelle frei (sACN: sofort bei „Stream beendet“).

Unter **Gesehene Quellen** erscheint live alles, was gerade gesendet wird: Protokoll, Universum, Absender, Pakete pro Sekunde und wie viele Kanäle nicht null sind. **Ansehen** zeigt die 512 Kanäle als Raster; **Weiterleiten** legt gleich eine Zuordnung an.

---

## 2. Weiterleiten / Mischen (Quelle → Ausgabe)

Eine **Zuordnung** mischt ein *Eingangs-Universum* in ein *Ausgabe-Universum* von OpenCue:

| Modus | Bedeutung |
|---|---|
| **Höchster gewinnt** (HTP) | Je Kanal gilt der größere Wert aus OpenCue und Eingang. Standard, sicher zum Zumischen. |
| **Ersetzen** | Der Eingang gilt, solange die Quelle da ist (auch Nullen). Optional nur für einen Kanalbereich. |

- Mehrere Quellen für dasselbe Universum: **Höchster gewinnt**. Bei sACN zählen nur die Quellen mit der höchsten **Priorität**.
- Hat das Ausgabe-Universum **keine Scheinwerfer**, wird es trotzdem ausgegeben – so geht eine **reine Weiterleitung** (z. B. Art-Net → sACN oder → USB-Adapter).
- Der Eingang liegt **über allem** (Programmer, Cues, Effekte). Die Werte in OpenCue selbst bleiben unverändert; gemischt wird nur in der **Ausgabe**.
- Eigene Pakete werden erkannt und ignoriert – eine Weiterleitung erzeugt keine Rückkopplung.
- Läuft im **Prozess der DMX-Ausgabe**: Die Weiterleitung geht unverändert weiter, auch wenn das Hauptprogramm hängt. Fällt dieser Prozess aus und die Ausgabe läuft ersatzweise im Hauptprogramm, funktionieren Auslöser und Anzeige weiter, das Mischen nicht (der Dialog sagt es).

---

## 3. Auslöser (Kanal → Befehl)

Ein **Auslöser** führt einen Befehl der Befehlszeile aus, wenn sich ein Kanal ändert:

- **Taste:** Steigt der Wert über die **Schwelle**, läuft der erste Befehl (z. B. `Go`); fällt er wieder darunter, der zweite (optional, z. B. `Blackout Off`).
- **Fader:** Jeder neue Wert läuft als Befehl; `{value}` steht für den Wert, umgerechnet auf den **Bereich** (Standard 0–100), z. B. `Master {value}`.
- **Einlernen:** Auf **Einlernen** klicken und am Pult einen Kanal bewegen – Protokoll, Universum und Kanal werden eingetragen.
- Der erste gesehene Wert wird nur gemerkt, nichts wird ausgelöst (kein Sprung beim Verbinden). Fader-Befehle laufen höchstens 20-mal pro Sekunde; der letzte Wert kommt immer an.

Beispiele: Kanal 1 = `Go` (Taste), Kanal 2 = `Blackout` (Taste), Kanal 3 = `Master {value}` (Fader), Kanal 10 = `Goto Cue 5`.

Unter **Letzte Auslöser** siehst du, was ausgelöst wurde.

---

## 4. Gut zu wissen

- Der Eingang gehört zur **App-Konfiguration** (nicht zur Show) und gilt für diesen Rechner.
- Damit ein Pult OpenCue erreicht, muss es an die IP-Adresse des Rechners oder per Broadcast senden; die Windows-Firewall muss UDP 6454 / 5568 für OpenCue erlauben – der Dialog zeigt, ob es die Regel gibt, und legt sie auf Knopfdruck an (Windows fragt am Hauptrechner um Erlaubnis).
- **Als Art-Net-Gerät melden:** OpenCue antwortet auf die Suche (ArtPoll) anderer Geräte und erscheint in deren Liste der Art-Net-Geräte – ein Pult kann es als Ziel auswählen, ohne die IP-Adresse einzutippen.
- Eine Übersicht aller Ein- und Ausgänge steht in **Einstellungen → Übersicht**.

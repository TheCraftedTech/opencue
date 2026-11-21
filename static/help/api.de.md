# REST-API

Mit der **REST-API** können andere Programme den Zustand von OpenCue **lesen** und OpenCue **steuern und bearbeiten** – Skripte, ein Show-Controller, Hausautomation, eine Webseite für die Inspizienz, eine Tablet-App oder ein eigenes Werkzeug. Sie spricht einfaches **HTTP** und antwortet in **JSON**. Es ist keine zusätzliche Software nötig, und sie funktioniert komplett offline innerhalb deines Netzwerks.

Der Zugriff ist durch **Tokens** geschützt, die du in OpenCue anlegst. Jedes Token hat eigene **Berechtigungen**: Eine Tablet-App darf zum Beispiel nur lesen, ein anderes Werkzeug darf zusätzlich Cues auslösen, ein drittes darf ganze Shows aufbauen.

---

## 1. Die Idee in einer Minute

- Die API liegt unter **`/api/v1/`** – auf derselben Adresse und demselben Port wie OpenCue selbst (zum Beispiel `http://127.0.0.1:8000/api/v1/`).
- Du **legst ein Token an** (*Einstellungen → API*) und schickst es bei jeder Anfrage mit.
- **Lesen** (`GET`) liefert den Zustand: Scheinwerfer, Cue-Listen, Cues, Variablen, Effekte, das DMX-Signal, den Timecode, den Programmer.
- **Bedienen** (`POST` / `PUT`) fährt die Show: Befehle, Cues, Timecode, Blackout, Audio, der Programmer.
- **Bearbeiten** ändert die Show selbst: Cue-Listen und Cues anlegen und ändern, Variablen, Effekte und Effekt-Skripte, Scheinwerfer patchen, Showfiles speichern und laden, Medien hochladen.
- Die eigenen **Buttons, Fader und Toggles** der Konsole lassen sich von außen drücken, bewegen und schalten.
- Alles, was jemand am Pult macht, erscheint **sofort in allen offenen Fenstern** – auch das, was die API ändert.
- Ein **Live-Strom** (`GET /events`) meldet Änderungen, sobald sie passieren: ein Dashboard muss nicht ständig nachfragen.
- Für **Hardware** (ESP32 mit Joystick, Reglern, Tasten, Mikrofon) gibt es einen **WebSocket** (`/api/v1/ws`): Joystick relativ oder absolut, Werte absolut oder relativ setzen, DMX- und Live-Werte, Timecode senden und empfangen, Audio-Werte und -Daten in beide Richtungen (Abschnitt 10). Für einfache Geräte ohne eigene Oberfläche gibt es **Status-Ansichten** als Bild oder Web-Seite (Abschnitt 11).
- Jede Funktion braucht **eine Berechtigung**. Ein Token ohne sie bekommt `403`. Die Bearbeiten-Rechte sind **standardmäßig aus**.
- Die API ist eine eigene, stabile Schnittstelle. Die internen Routen, die das Programmfenster benutzt, gehören *nicht* dazu.

---

## 2. Schnellstart

1. Öffne **Einstellungen → REST-API** (auch von einem angemeldeten Fernzugriffs-Gerät aus möglich). Standardmäßig gibt es **kein Token**, und die API antwortet nur auf **diesem Computer**.
2. Klicke auf **Neues Token**, gib einen Namen ein, wähle die Berechtigungen (oder eine Voreinstellung) und klicke auf **Token anlegen**. Ein **neues Token wird sofort angelegt** (ohne *Speichern*) und gleich danach angezeigt.
3. **Kopiere das Token jetzt.** Es wird nur dieses eine Mal angezeigt; danach sind nur noch die ersten Zeichen sichtbar. Geht es verloren, lege ein neues an oder nimm *Neues Token erzeugen*.
4. Probiere es aus:

```
curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status
```

Die Antwort ist ein JSON-Objekt mit Showname, Blackout, Grand Master, Timecode und mehr (siehe Abschnitt 6).

Die Adresse in den Beispielen (`127.0.0.1:8000`) ist die Konsole selbst. Für die Adresse anderer Geräte siehe Abschnitt 8. Eine Seite mit allen Routen – durchsuchbar und offline lesbar – gibt es unter `/api/v1/docs`.

---

## 3. Tokens und Berechtigungen

### Tokens verwalten

In **Einstellungen → REST-API** kannst du:

| Aktion | Bedeutung |
|---|---|
| **REST-API an/aus** | Der Hauptschalter. Ist er aus, antwortet jede Anfrage mit `403 api_disabled`. |
| **Erreichbar von** | *Nur dieser PC* (Standard) oder *Im Netzwerk*. Für andere Geräte muss zusätzlich der **Fernzugriff** an sein; sonst weist die Seite darauf hin (mit Link). Von außen antwortet die API bei *Nur dieser PC* mit `403 api_local_only`. |
| **Webseiten auf anderen Adressen erlauben** | Browser-Seiten, die von einer anderen Adresse geöffnet wurden, dürfen die API aufrufen (CORS, Abschnitt 8). Standardmäßig an. |
| **Status-Ansichten (Bild / Web)** | Schalter für die Ansichten aus Abschnitt 11. Standardmäßig an (jede braucht ein Token). |
| **Jetzt verbunden (WebSocket)** | Liste der Geräte, die gerade über den WebSocket verbunden sind (Token, Adresse, was sie empfangen, Joystick aktiv, Nachrichten je Sekunde) – live, mit **Trennen**. |
| **Neues Token** | Legt ein Token an. Ein breiter Dialog zeigt die Berechtigungen in drei Spalten: *Lesen*, *Bedienen*, *Show bearbeiten*. |
| **Bearbeiten** | Name und Berechtigungen ändern. |
| **Aktiv-Schalter** | Schaltet ein Token aus und wieder ein, ohne es zu löschen (`403 token_disabled`, solange es aus ist). |
| **Neues Token erzeugen** (in *Bearbeiten*) | Ersetzt das Geheimnis. Das alte Token funktioniert nicht mehr, sobald du speicherst. |
| **Löschen** | Fragt in einem eigenen Dialog nach (abschaltbar, siehe *Standardwerte → Löschen*) und löscht das Token dann **sofort**. |
| **Zuletzt benutzt** | Zeigt, wann ein Token zuletzt verwendet wurde. |

Ein **neues Token** wird sofort angelegt und angezeigt, ein **Löschen** gilt nach der Rückfrage sofort. Alles andere ist wie in allen Einstellungen ein **Entwurf** (Schalter, Ändern, Neu erzeugen): geänderte Zeilen sind markiert und gezählt, erst **Speichern** übernimmt alles (der Dialog bleibt offen), *Schließen* verwirft nach Rückfrage. Tokens lassen sich nur am Konsolenrechner selbst verwalten, nicht von Remote-Geräten.

Auf der Festplatte steht nur ein **Hash** des Tokens, nie das Token selbst.

### Die Berechtigungen

**Lesen**

| Berechtigung | Erlaubt | Standard |
|---|---|---|
| **Status** | Zustand: Showname, Blackout, Grand Master, Timecode, Auswahl, Programmer, Audio-Analyse, Ausgänge, der Live-Ereignisstrom | an |
| **Show-Daten** | Scheinwerfer, Fixture-Typen, Gruppen, Variablen, Effekte, Effekt-Skripte, Showfiles, Cue-Listen und Cues, Medien, Layouts | an |
| **DMX-Ausgabe** | Aktuelle DMX-Werte und der Live-Zustand jedes Scheinwerfers | an |

**Bedienen**

| Berechtigung | Erlaubt | Standard |
|---|---|---|
| **Konsolenbefehle** | Beliebige Befehle der Befehlszeile ausführen (können auch Show-Daten ändern und löschen) – *kritisch* | an |
| **Cue-Listen** | Go, Back, zu einem Cue springen, Pause, Weiter, Stopp, Fader | an |
| **Timecode** | Starten, anhalten, stoppen, springen, Geschwindigkeit | an |
| **Blackout und Master** | Blackout schalten, Grand Master setzen | an |
| **Audio** | Audio-Quelle öffnen / schließen, Einstellungen ändern, Tempo antippen | an |
| **Programmer und Auswahl** | Scheinwerfer auswählen, Werte und Variablen live setzen, den Programmer leeren | an |
| **Buttons, Fader, Toggles der Konsole** | Die eigenen Button-, Fader- und Toggle-Panels der Konsole drücken, bewegen und schalten (sie führen die in ihnen eingestellten Befehle aus) | an |
| **DMX direkt setzen** | DMX-Kanäle schreiben – überschreibt die laufende Show – *kritisch* | **aus** |

**Show bearbeiten**

| Berechtigung | Erlaubt | Standard |
|---|---|---|
| **Cue-Listen und Cues** | Cue-Listen und Cues anlegen, ändern, kopieren, umnummerieren und löschen; den Programmer als Cue speichern | **aus** |
| **Variablen** | Variablen und Variablengruppen anlegen, ändern und löschen | **aus** |
| **Effekte** | Effekte und Effektgruppen anlegen, ändern und löschen; Effekte auf Scheinwerfern starten und beenden | **aus** |
| **Effekt-Skripte** | Effekt-Typen (Skript-Dateien) prüfen, speichern und löschen | **aus** |
| **Patch und Scheinwerfer-Gruppen** | Scheinwerfer patchen, ändern und löschen; Scheinwerfer-Gruppen verwalten; GDTF-Fixture-Typen installieren und entfernen – *kritisch* | **aus** |
| **Showfiles** | Showfiles neu anlegen, laden, speichern, umbenennen, kopieren und löschen – *kritisch* | **aus** |
| **Medien** | Video- und Audio-Dateien hochladen, umbenennen und löschen | **aus** |
| **Layouts** | Ein gespeichertes Panel-Layout im Konsolenfenster anzeigen | **aus** |
| **DMX-Ausgänge und Sprache** | Art-Net, sACN und USB-DMX schalten, Adressen, Standard-Universum und Sprache ändern – *kritisch* | **aus** |

**Voreinstellungen** im Dialog: *Nur lesen* (die drei Lese-Rechte), *Bedienen* (Lesen plus Cue-Listen, Timecode, Blackout/Master, Audio, Programmer und die Buttons / Fader / Toggles der Konsole – ohne Befehle, ohne direktes DMX), *Show bearbeiten* (Bedienen plus Cue-Listen und Cues, Variablen, Effekte), *Voller Zugriff* und *Standard*.

---

## 4. Regeln für alle Anfragen

- **Anmeldung:** Schicke das Token als `Authorization: Bearer oc_…`. Der Kopf `X-API-Key: oc_…` funktioniert ebenfalls.
- **Format:** Anfragen mit Inhalt benutzen JSON und `Content-Type: application/json`. Antworten sind immer JSON (außer dem Ereignisstrom und Datei-Downloads).
- **Dinge auswählen:**
  - ein *Scheinwerfer* über seine **Nummer (FID)**, seine ID oder einen eindeutigen Namen; eine *Gruppe* von Scheinwerfern über ihren Namen;
  - eine *Cue-Liste* über ihren **Namen** oder ihre ID; ein *Cue* über seine **Nummer** (zum Beispiel `1.5`) oder ID;
  - eine *Variable*, ein *Effekt* oder ein *Showfile* über den **Namen** (Groß-/Kleinschreibung egal) oder die ID.
  - Namen mit Leerzeichen müssen im Pfad URL-kodiert werden (`Par%20links`).
- **Mehrere Scheinwerfer** in einem Body: `"fixtures": [1, 2, "Front"]`, `"fixture": 3` und / oder `"group": "Wash"`. Bei den Programmer-Aufrufen bedeutet `"selection": true` die an der Konsole ausgewählten Scheinwerfer; ein Aufruf ohne jede Angabe nimmt die Auswahl.
- **Prozent und Bytes:** Dimmer, Position und Ähnliches in **Prozent (0–100)**, rohe DMX-Kanäle in **0–255**, Farben als `"#rrggbb"`, `[r, g, b]` oder `{"r": …, "g": …, "b": …}` (0–255).
- **Zeiten** in Sekunden; der Timecode als Sekunden oder Text (`00:01:04.300`).
- **Genaue Eingabeprüfung:** Ein Feld, das es nicht gibt, wird abgelehnt (`422`), ein falscher Wert oder Name ist `400`, ein schon vergebener Name `409 duplicate`. Nichts wird geraten oder stillschweigend ignoriert.
- **Erst prüfen, dann ändern:** Ein Aufruf mit einem falschen Wert, Namen oder Scheinwerfer wird als Ganzes abgelehnt – ein Cue mit einem falschen Scheinwerfer wird nicht halb gespeichert.

### Fehler

Fehler sehen immer gleich aus:

```json
{ "error": { "code": "not_found", "message": "No fixture '99' (use the fixture number, id or an unambiguous name)." } }
```

| HTTP | `code` | Bedeutung |
|---|---|---|
| 400 | `bad_request` | Die Anfrage ist falsch (Wert außerhalb, unbekanntes Attribut, leerer Befehl …) |
| 401 | `unauthorized` | Token fehlt oder ist ungültig |
| 403 | `forbidden` | Das Token hat die Berechtigung für diese Funktion nicht |
| 403 | `token_disabled` / `api_disabled` | Das Token oder die ganze API ist ausgeschaltet |
| 404 | `not_found` | Scheinwerfer, Cue-Liste, Cue, Variable, Effekt, Showfile … gibt es nicht |
| 409 | `duplicate` | Der Name ist vergeben (Cue-Liste, Variable, Effekt, Gruppe …) |
| 409 | `cue_exists` | Ein Cue mit dieser Nummer gibt es schon – `on_conflict` (`merge` / `overwrite`) mitschicken |
| 409 | `address_conflict` | Die DMX-Adressen überlappen einen anderen Scheinwerfer – `allow_overlap: true` patcht trotzdem |
| 409 | `unsaved_changes` | Die Show hat ungespeicherte Änderungen – erst speichern oder `force: true` mitschicken |
| 409 | `exists` / `in_use` / `never_saved` | Ein Showfile oder Skript dieses Namens gibt es schon / das Showfile ist das geladene / die Show hat noch keine Datei |
| 409 | `no_active_cue` / `programmer_empty` | *Update* ohne aktiven Cue oder bei leerem Programmer |
| 409 | `audio_failed` | Die Audio-Quelle ließ sich nicht öffnen (der Grund steht in der Meldung) |
| 415 | `invalid_type` | Ein Medien-Upload, der keine unterstützte Video- oder Audiodatei ist |
| 422 | `invalid` | Ein Feld fehlt, ist unbekannt oder hat einen falschen Typ |
| 422 | `invalid_script` | Ein Skript lässt sich nicht übersetzen oder scheitert am Probelauf (mit Zeile) |
| 429 | `rate_limited` | Zu viele falsche Tokens von dieser Adresse – warte die Zeit aus `Retry-After` ab |

Ein **abgelehnter Konsolenbefehl** (zum Beispiel ein Tippfehler) ist *kein* HTTP-Fehler: Die Antwort ist `200` mit `"success": false` und der Meldung der Befehlszeile.

---

## 5. Übersicht der Routen

Alle Pfade beginnen mit `/api/v1`. In der rechten Spalte steht die Berechtigung, die das Token braucht. In den Pfaden ist `{list}` eine Cue-Liste, `{cue}` ein Cue, `{fixture}` ein Scheinwerfer, `{ref}` eine Variable / ein Effekt / ein Name.

### Lesen

| Methode | Pfad | Liefert | Berechtigung |
|---|---|---|---|
| GET | `/` | Index: Version, Links, was dieses Token darf | Status |
| GET | `/status` | Gesamtzustand: Show, Blackout, Master, Timecode, Auswahl, aktive Cue-Liste, DMX-Ausgänge, Anzahlen | Status |
| GET | `/blackout` · `/master` · `/timecode` · `/selection` | Ein Teil des Zustands | Status |
| GET | `/system` | Version, Sprache, DMX-Ausgänge (Art-Net, sACN, USB), Universen, Remote-Zugriff, Datenordner | Status |
| GET | `/showfile` | Name der geladenen Show, ob sie ungespeicherte Änderungen und eine Datei hat | Status |
| GET | `/programmer` | Auswahl, die von Hand gesetzten Werte (Prozent, Farbe + hex, rohe Kanäle), die Variablen, denen sie folgen, laufende Effekte | Status |
| GET | `/audio` · `/audio/devices` | Die laufende Audio-Analyse und die Einstellungen / alle Audio-Eingänge | Status |
| GET | `/system/usb-ports` · `/command/suggest?text=` | Serielle Ports für USB-DMX / Vorschläge für einen Befehl (wie Tab in der Befehlszeile) | Status |
| GET | `/events` | **Live-Strom** der Änderungen (Server-Sent Events, Abschnitt 6) | Status |
| GET | `/fixtures` | Alle Scheinwerfer. Optional `?universe=`, `?group=`, `?include_state=true` | Show-Daten |
| GET | `/fixtures/{fixture}` | Ein Scheinwerfer mit jedem Kanal (Adresse, aktueller DMX-Wert) und seinem Zustand | Show-Daten |
| GET | `/fixture-types` | Die Fixture-Bibliothek: ID, Name, Hersteller, Modi mit Kanalzahl (`?q=` filtert) | Show-Daten |
| GET | `/groups` · `/variable-groups` · `/effect-groups` | Scheinwerfer-Gruppen, Variablengruppen, Effektgruppen | Show-Daten |
| GET | `/variables` · `/variables/{ref}` | Alle Variablen / eine (mit der Zahl der Cue-Einträge, die sie benutzen) | Show-Daten |
| GET | `/effects` · `/effects/{ref}` · `/effects/assignments` | Effekte / ein Effekt mit Infos zu seinem Typ / welcher Effekt auf welchem Scheinwerfer läuft | Show-Daten |
| GET | `/effect-scripts` · `/effect-scripts/{name}` | Alle Effekt-Typen (Kategorie, Tags, Einstellungen) / der Quelltext eines Typs | Show-Daten |
| GET | `/cuelists` · `/cuelists/{list}` | Alle Cue-Listen mit aktivem Cue, Fader und Wiedergabezustand / eine Liste mit allen Cues | Show-Daten |
| GET | `/cuelists/{list}/cues` | Die Cues einer Liste; `?detail=true` ergänzt, **was jeder Cue ändert** | Show-Daten |
| GET | `/cuelists/{list}/cues/{cue}` | Ein Cue im Detail | Show-Daten |
| GET | `/showfiles` | Namen der gespeicherten Showfiles (und des geladenen) | Show-Daten |
| GET | `/media` · `/media/{id}/file` | Die Medien der Show / eines herunterladen | Show-Daten |
| GET | `/layouts` | Gespeicherte Layouts der Konsole | Show-Daten |
| GET | `/widgets` | Die Button- / Fader- / Toggle-Panels der Konsole: Befehle, Fadergrenzen und -wert, Zustand der Toggles | Show-Daten |
| GET | `/dmx` · `/dmx/{universe}` | Die Universen und ihre Werte (`?first=&last=`, `?nonzero=true`) | DMX-Ausgabe |
| GET | `/fixtures/state` | Der Live-Zustand **jedes** Scheinwerfers (was die Konsole gerade ausgibt) | DMX-Ausgabe |

### Bedienen

| Methode | Pfad | Body | Berechtigung |
|---|---|---|---|
| POST | `/command` | `{"command": "Fixture 1 At 80"}` | Konsolenbefehle |
| POST | `/commands` | `{"commands": ["…", "…"], "stop_on_error": false}` – bis zu 100 | Konsolenbefehle |
| POST | `/cuelists/{list}/go` | optional `{"cue": "2"}` (ohne: der nächste Cue) | Cue-Listen |
| POST | `/cuelists/{list}/back` · `/pause` · `/resume` · `/stop` | – | Cue-Listen |
| PUT | `/cuelists/{list}/fader` | `{"value": 70}` (Prozent) | Cue-Listen |
| PUT | `/timecode` | `{"action": "play" \| "pause" \| "stop" \| "seek" \| "rate", "position": …, "direction": 1, "rate": 1}` | Timecode |
| PUT | `/blackout` | `{"enabled": true}` (ohne Wert: umschalten) | Blackout und Master |
| PUT | `/master` | `{"value": 80}` (Prozent) | Blackout und Master |
| PUT | `/audio` | `{"running": true, "device": "demo", "settings": {"mode": "manual", "bpm": 128}}` – jedes Feld optional | Audio |
| POST | `/audio/tap` | – (ein Tippen auf die Tempo-Taste) | Audio |
| PUT | `/selection` | `{"fixtures": [1, 2], "mode": "set" \| "add" \| "remove" \| "clear"}` (auch `group`) | Programmer und Auswahl |
| PUT | `/programmer/values` | `{"fixtures": [1, 2], "values": {"dimmer": 80, "color": "#ff0000"}}` | Programmer und Auswahl |
| POST | `/programmer/variables` | `{"variable": "Warmweiß", "fixtures": [1, 2]}` – wendet eine Variable an und verknüpft sie | Programmer und Auswahl |
| POST | `/widgets/{id}/press` | – (führt den Befehl eines Buttons aus) | Buttons, Fader, Toggles der Konsole |
| PUT | `/widgets/{id}/value` | `{"value": 70}` (Fader; auf Minimum / Maximum begrenzt, gerundet) | Buttons, Fader, Toggles der Konsole |
| PUT | `/widgets/{id}/state` | `{"on": true}` (Toggle; ohne Wert wird umgeschaltet) | Buttons, Fader, Toggles der Konsole |
| POST | `/programmer/clear` | `{"fixtures": [1]}` vergisst ihre Werte; `{"all": true}` = *Clear Clear*: alles dunkel | Programmer und Auswahl |
| PUT | `/dmx/{universe}/{channel}` | `{"value": 255}` oder `{"percent": 100}` | DMX direkt setzen |
| PUT | `/dmx/{universe}` | `{"channels": {"1": 255, "2": 0}}` | DMX direkt setzen |
| PUT | `/fixtures/{fixture}/channels/{channel}` | `{"value": 128}` oder `{"percent": 50}`; `{channel}` ist die Kanalnummer des Scheinwerfers (1 = erster) oder sein Name (`Dimmer`) | DMX direkt setzen |

### Bearbeiten: Cue-Listen und Cues – Berechtigung *Cue-Listen und Cues*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/cuelists` | `{"name": "Akt 1"}` | Eine Cue-Liste anlegen (201) |
| PUT | `/cuelists/{list}` | `{"name": "…", "active": true}` | Umbenennen; `active` macht sie zur Liste, die die Cue-Listen-Panels zeigen |
| PUT | `/cuelists/order` | `{"order": ["Akt 2", "Akt 1"]}` | Reihenfolge der Listen |
| POST | `/cuelists/{list}/duplicate` | `{"name": "Kopie"}` | Kopie mit allen Cues |
| DELETE | `/cuelists/{list}` | – | Die Liste löschen |
| POST | `/cuelists/{list}/cues` | siehe unten | Einen Cue anlegen (201) |
| PUT | `/cuelists/{list}/cues/{cue}` | siehe unten | Eigenschaften und / oder Inhalt ändern, umnummerieren |
| DELETE | `/cuelists/{list}/cues/{cue}` | – | Einen Cue löschen |
| POST | `/cuelists/{list}/cues/delete` | `{"cues": ["1", "2.5"]}` | Mehrere löschen (alle oder keiner) |
| POST | `/cuelists/{list}/cues/{cue}/duplicate` | `{"number": 9, "name": "…"}` | Einen Cue kopieren |
| POST | `/cuelists/{list}/update-active` | `{"mode": "normal" \| "only"}` | Den Programmer in den aktiven Cue übernehmen (wie *Update*) |

**Cue-Body** (Anlegen und Ändern; beim Ändern ist jedes Feld optional):

| Feld | Bedeutung |
|---|---|
| `number` | Cue-Nummer, Dezimalzahlen erlaubt. Beim Anlegen weggelassen: die nächste freie Nummer. |
| `name`, `fade`, `delay` | Name und die allgemeinen Zeiten in Sekunden |
| `trigger` | `go` · `follow` · `timecode` · `audio` · `midi` |
| `timecode` | Für `timecode`: Sekunden oder `1:04.300` |
| `audio` | Für `audio`: `{"source": "beat" \| "kick" \| "snare" \| "hat" \| "level" \| "bass" \| "mid" \| "high" \| "b1" … "b8", "value": 4}` (jeder n-te Schlag oder eine Schwelle in %) |
| `midi` | Für `midi`: `{"type": "note" \| "cc" \| "pc", "number": 60, "channel": 0, "value": 64}` – der Cue feuert, wenn dieses Signal eintrifft, während er der nächste Cue einer laufenden Liste ist; `channel` 0 = beliebig (1–16 = ein Kanal), `value` = Schwelle eines `cc` (1–127) |
| `mib`, `command` | Move in Black (`Off` / `Auto` / `On`); Konsolenbefehle, die mit dem Cue laufen |
| `times` | Eigene Zeiten je Gruppe: `{"color": {"fade": 2, "delay": 0}, "position": {…}, "beam": {…}, "zoom": {…}}`; `null` = wieder die allgemeine Zeit |
| `effect_fade` | `{"in": 1, "out": 2}` |
| `changes` | Was der Cue ändert (unten) |
| `effects` | Die Effekte, die der Cue startet: `[{"fixtures": [2, 3], "effects": {"dimmer": "Strobe"}}]` (Kategorie → Effektname) |
| `from_programmer` | *(Anlegen)* speichert zusätzlich, was im Programmer steht, **und jede Änderung des Bildes gegenüber dem Cue davor** (wie *Store Cue*; hat sich nichts geändert: `409 nothing_changed`); `clear_programmer` leert ihn danach |
| `on_conflict` | *(Anlegen / Umnummerieren)* die Nummer gibt es schon: `merge` (nur die gesendeten Attribute kommen in den bestehenden Cue) oder `overwrite` |
| `content` | *(Ändern)* `merge` (Standard) oder `replace`: Der Inhalt des Cues ist genau das Gesendete |

`changes` ist eine Liste; jeder Eintrag nennt Scheinwerfer und was sie bekommen:

```json
{ "fixtures": [2, 3], "values": { "dimmer": 80, "color": "#00ff00", "pan": 40 }, "variables": { "color": "Warmweiß" } }
```

`values`: `dimmer`, `pan`, `tilt`, `strobe`, `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin`, `prism`, `focus`, `zoom` in Prozent, `color`, rohe Kanäle `ch<N>` (0–255). `variables` ordnet einem Typ (`dimmer`, `position`, `color`, `focus`, `zoom`, `gobo`) eine Variable zu: Der Cue **verweist dann auf die Variable** (ein Platzhalter, der beim Abspielen live aufgelöst wird), statt den Wert zu speichern.

### Bearbeiten: Variablen – Berechtigung *Variablen*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/variables` | `{"name": "Warmweiß", "type": "color", "group": "Farben", "values": {"hex": "#ffb060"}}` | Anlegen |
| PUT | `/variables/{ref}` | `{"name": "…", "group": "…", "values": {…}}` | Ändern; der Typ bleibt. Ein neuer Wert erreicht den Programmer, laufende Cues und **jeden Cue, der die Variable benutzt** |
| DELETE | `/variables/{ref}` | – | Löschen (Verknüpfungen im Programmer werden gelöst) |
| POST · DELETE | `/variable-groups` · `/variable-groups/{name}` | `{"name": "Farben"}` | Gruppe anlegen / löschen (ihre Variablen bleiben) |

`values` je Typ: `dimmer`, `focus`, `zoom`: `{"level": 0-100}` · `position`: `{"pan": 0-100, "tilt": 0-100}` · `color`: `{"r","g","b"}` oder `{"hex": "#ff8000"}` · `gobo`: `{"level", "spin", "gobo2", "gobo2_spin"}`.

### Bearbeiten: Effekte – Berechtigung *Effekte*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/effects` | `{"script": "strobe", "name": "Blitz", "group": "…", "params": {"rate_hz": 8}}` | Einen Effekt aus einem Effekt-Typ anlegen (`GET /effect-scripts`); `params` werden gegen die Grenzen des Typs geprüft |
| PUT | `/effects/{ref}` | `{"name", "group", "params"}` | Ändern (der Typ bleibt) |
| DELETE | `/effects/{ref}` | – | Löschen; er endet überall |
| POST | `/effects/{ref}/assign` | `{"fixtures": [2, 3]}` (auch `group`) | Den Effekt auf Scheinwerfern **starten** (die Reihenfolge verteilt Wellen) |
| POST | `/effects/release` | `{"fixtures": [2], "categories": ["dimmer"]}` | Effekte auf Scheinwerfern **beenden** (die Werte bleiben) |
| POST · DELETE | `/effect-groups` · `/effect-groups/{name}` | `{"name": "…"}` | Gruppe anlegen / löschen |

### Bearbeiten: Effekt-Skripte – Berechtigung *Effekt-Skripte*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/effect-scripts/check` | `{"text": "…"}` | Ein Skript übersetzen und probeweise ausführen, ohne zu speichern: `{ok, line, message}` |
| POST | `/effect-scripts/preview` | `{"text": "…", "count": 3, "duration": 4, "bpm": 120, "params": {…}}` | Die Verläufe ohne Scheinwerfer simulieren |
| PUT | `/effect-scripts/{name}` | `{"text": "…", "overwrite": false}` | Als Datei im Effekt-Ordner des Benutzers speichern – **nur wenn es übersetzt und läuft** (`422 invalid_script` mit Zeile). Ein vorhandener Name braucht `overwrite` |
| DELETE | `/effect-scripts/{name}` | – | Ein Skript aus dem Benutzerordner löschen; Effekte dieses Typs enden |

Die Skriptsprache steht in der Anleitung *Effekt-Studio*.

### Bearbeiten: Patch und Scheinwerfer-Gruppen – Berechtigung *Patch und Scheinwerfer-Gruppen*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/fixtures` | `{"type": "Generic RGBW LED Par", "mode": "…", "name": "Par", "quantity": 4, "universe": 1, "address": 11, "group": "Wash"}` | Einen oder mehrere Scheinwerfer nacheinander patchen. Die Adressen werden geprüft (sie müssen in 512 passen und dürfen nicht überlappen – `allow_overlap: true` hebt das auf) |
| PUT | `/fixtures/{fixture}` | `{"name", "universe", "address", "sort_index", "group", "allow_overlap"}` | Ändern; `"group": ""` nimmt ihn aus seiner Gruppe |
| DELETE | `/fixtures/{fixture}` · POST `/fixtures/delete` | `{"fixtures": [1, 2]}` | Löschen (Cues behalten ihre Einträge für den fehlenden Scheinwerfer, wie im Fenster) |
| POST | `/groups` | `{"name": "Wash", "fixtures": [2, 3]}` | Eine Scheinwerfer-Gruppe anlegen |
| POST | `/fixture-types` | die rohe `.gdtf`-Datei; Kopfzeile `X-Filename` (URL-kodiert) | Einen Fixture-Typ installieren (bis 30 MB; wird vor der Installation geprüft) |
| DELETE | `/fixture-types/{id}` | – | Einen installierten Typ entfernen (`409 in_use`, solange die Show ihn benutzt) |
| PUT · DELETE | `/groups/{name}` | `{"name": "…", "fixtures": […]}` | Umbenennen / Mitglieder setzen (ersetzt die Liste) / löschen (die Scheinwerfer bleiben) |

### Bearbeiten: Showfiles – Berechtigung *Showfiles*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/showfile/new` | `{"force": false}` | Eine neue, leere Show beginnen |
| POST | `/showfile/save` | – | Unter dem aktuellen Namen speichern (`409 never_saved`, wenn sie noch keine Datei hat) |
| POST | `/showfile/save-as` | `{"name": "Konzert", "overwrite": false}` | Unter einem Namen speichern (Zeichen, die in Dateinamen nicht erlaubt sind, werden entfernt) |
| POST | `/showfile/load` | `{"name": "Konzert", "force": false}` | Eine gespeicherte Show laden – ersetzt die laufende |
| POST | `/showfiles/{name}/rename` | `{"new_name": "…", "overwrite": false}` | Eine gespeicherte Datei umbenennen |
| POST | `/showfiles/{name}/duplicate` | – | Eine gespeicherte Datei kopieren |
| DELETE | `/showfiles/{name}` | `?force=true` für das geladene | Eine gespeicherte Datei löschen |

**Neu** und **Laden** ersetzen die laufende Show. Bei ungespeicherten Änderungen werden sie mit `409 unsaved_changes` abgelehnt, bis du erst speicherst oder `"force": true` mitschickst.

### Bearbeiten: Medien – Berechtigung *Medien*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/media` | die rohe Datei; Kopfzeile `X-Filename` (URL-kodiert) | Eine Video- / Audiodatei hochladen (bis 1 GB; dieselbe Datei zweimal ist ein Eintrag) |
| PUT | `/media/{id}` | `{"name": "…"}` | Umbenennen |
| DELETE | `/media/{id}` | – | Aus der Show nehmen und die Kopie löschen |

### Bearbeiten: Layouts und Einstellungen – Berechtigungen *Layouts* und *DMX-Ausgänge und Sprache*

| Methode | Pfad | Body | Was es tut |
|---|---|---|---|
| POST | `/layouts/{filename}/load` | – | Ein gespeichertes Layout (`Name.json` wie in `GET /layouts`) im Konsolenfenster anzeigen; ungespeicherte Layout-Änderungen dort gehen verloren |
| PUT | `/system` | `{"artnet": {"enabled": true, "ip": "2.255.255.255", "bind_ip": ""}, "sacn": {"enabled": true}, "enttec": {"enabled": false, "port": "COM3", "universe": 1}, "default_universe": 1, "language": "de"}` – jedes Feld optional | Die DMX-Ausgänge schalten, Sprache / Standard-Universum ändern; die Antwort ist `GET /system` |
| POST | `/system/dmx/reinitialize` | – | Die DMX-Ausgänge neu starten, ohne das Programm neu zu starten |

### Dokumentation (ohne Token)

| Methode | Pfad | Liefert |
|---|---|---|
| GET | `/docs` | Eine lesbare, durchsuchbare Übersicht aller Routen (funktioniert offline) |
| GET | `/openapi.json` | Die maschinenlesbare Beschreibung (OpenAPI 3.1); jede Route nennt ihre Berechtigung als `x-capability` |

---

## 6. Beispiele mit echten Antworten

### Zustand

```
GET /api/v1/status
```

```json
{
  "app": { "name": "OpenCue", "version": "1.0.0" },
  "show": { "name": "Konzert", "unsaved_changes": true },
  "blackout": false,
  "grand_master": 100.0,
  "timecode": { "running": false, "direction": 1, "rate": 1.0, "position_ms": 0.0, "position": "00:00:00.000" },
  "selection": { "fixture_ids": ["228a68e5-…"], "fids": [2] },
  "active_cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "dmx": { "universes": [1], "artnet": true, "sacn": false, "usb": false },
  "counts": { "fixtures": 2, "groups": 1, "variables": 0, "effects": 0, "cuelists": 1, "cues": 2 }
}
```

### Welche Scheinwerfer hat die Show, und welche Farbe haben sie?

```
GET /api/v1/fixtures?include_state=true
GET /api/v1/fixtures/state
```

```json
{
  "fixtures": [
    { "id": "9ea4feaa-…", "fid": 1, "name": "Front", "state": { "dimmer": 80.0 } },
    { "id": "228a68e5-…", "fid": 2, "name": "Par links",
      "state": { "dimmer": 100.0, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } } }
  ]
}
```

`state` enthält genau das, was die Konsole gerade ausgibt, aus dem DMX-Puffer gelesen: `dimmer`, `pan`, `tilt`, `zoom`, `focus` … in Prozent und `color` als r/g/b. Attribute, die ein Scheinwerfer nicht hat, fehlen. (Bei Grand Master 0 oder Blackout lässt sich der Dimmer nicht zurückrechnen und fehlt.)

### Ein Scheinwerfer mit allen Kanälen

```
GET /api/v1/fixtures/2
```

```json
{
  "id": "228a68e5-…", "fid": 2, "name": "Par links", "type": "Generic RGBW LED Par", "manufacturer": "Generic",
  "universe": 1, "start_channel": 11, "end_channel": 14, "channel_count": 4, "mode": "default", "group": "Wash",
  "channels": [
    { "channel": 1, "name": "ColorAdd_R", "address": 11, "value": 255 },
    { "channel": 2, "name": "ColorAdd_G", "address": 12, "value": 0 },
    { "channel": 3, "name": "ColorAdd_B", "address": 13, "value": 0 },
    { "channel": 4, "name": "ColorAdd_W", "address": 14, "value": 0 }
  ],
  "state": { "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }
}
```

### Was ändert ein Cue?

```
GET /api/v1/cuelists/Show/cues/1
```

```json
{
  "id": "700571ee-…", "number": 1, "name": "Auf", "active": false,
  "trigger": "go", "timecode_ms": null, "timecode": null,
  "fade": 2.0, "delay": 0.0,
  "times": { "color": { "fade": null, "delay": null }, "position": { "fade": null, "delay": null },
             "beam": { "fade": null, "delay": null }, "zoom": { "fade": null, "delay": null } },
  "effect_fade": { "in": 0.0, "out": 0.0 }, "mib": "Off", "command": "", "fixture_count": 2,
  "changes": [
    { "fixture_id": "9ea4feaa-…", "fid": 1, "name": "Front", "values": { "dimmer": 50 }, "variables": {} },
    { "fixture_id": "228a68e5-…", "fid": 2, "name": "Par links",
      "values": { "dimmer": 100, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }, "variables": {} }
  ],
  "effects": [],
  "cuelist": { "id": "7e5d274f-…", "name": "Show" }
}
```

- `fade` / `delay` sind die allgemeinen Zeiten; `times` enthält die optionalen Zeiten je Attributgruppe (`null` = nimmt die allgemeine Zeit).
- `changes[].values` sind die festen Werte, die im Cue stehen. `variables` nennt die Variablen (Platzhalter), auf die der Cue verweist, nach Typ und Name – eine Variable wird beim Abspielen live aufgelöst.
- `effects` nennt die Effekte, die der Cue startet, je Scheinwerfer.
- Alle Cues einer Liste auf einmal mit Details: `GET /api/v1/cuelists/Show/cues?detail=true`.

### Das DMX-Signal

```
GET /api/v1/dmx/1?first=1&last=14
GET /api/v1/dmx/1?nonzero=true
```

```json
{ "universe": 1, "first": 1, "last": 14, "values": [0,0,0,0,0,0,0,0,0,0,255,0,0,0] }
{ "universe": 1, "first": 1, "last": 512, "channels": { "11": 255 } }
```

### Einen Konsolenbefehl ausführen

```
POST /api/v1/command
{ "command": "Fixture 1 Thru 4 At 80" }
```

```json
{ "command": "Fixture 1 Thru 4 At 80", "success": true, "message": "OK: 4 fixtures selected; At 80 applied" }
```

Alle Befehle der Befehlszeile funktionieren, auch mit `;` verkettet (siehe die Anleitung *Befehlsreferenz*).

### Einen Cue auslösen

```
POST /api/v1/cuelists/Show/go            { "cue": "2" }
```

```json
{ "cuelist": { "id": "7e5d274f-…", "name": "Show" }, "command": "Cuelist \"Show\" Go Cue 2", "success": true, "message": "OK: Go Cue 2 [Show]" }
```

Ohne Body startet `go` den nächsten Cue. Achtung: Eine Cue-Liste, deren **Name ein Anführungszeichen enthält**, lässt sich so nicht ansprechen; benenne sie um.

### Timecode

```
PUT /api/v1/timecode   { "action": "seek", "position": "1:04.300" }
PUT /api/v1/timecode   { "action": "play", "position": 10 }
GET /api/v1/timecode
```

```json
{ "running": false, "direction": 1, "rate": 1.0, "position_ms": 64300.0, "position": "00:01:04.300" }
```

`position` ist eine Zahl in **Sekunden** oder Text wie `1:04.300` oder `00:00:04.300`. `play` kann ab einer `position` starten und mit `"direction": -1` rückwärts laufen; `rate` ist die Geschwindigkeit zwischen 0,1 und 8. Ein Sprung mit `seek` löst keine Timecode-Cues aus.

### DMX-Kanäle setzen

```
PUT /api/v1/dmx/1/200                      { "value": 255 }
PUT /api/v1/dmx/1                          { "channels": { "201": 10, "202": 20 } }
PUT /api/v1/fixtures/Front/channels/Dimmer { "percent": 50 }
```

```json
{ "universe": 1, "channel": 1, "value": 128, "fixture": { "fid": 1, "name": "Front" }, "channel_of_fixture": 1 }
```

Ein Kanal, der zu einem **Scheinwerfer** gehört, wird wie der Fader *DMX direkt* des Programmers gesetzt: Er wird ein manueller Wert, den laufende Cues nicht mehr mischen. Andere Kanäle gehen direkt an die Ausgabe. Diese Berechtigung ist **standardmäßig aus**.

### Audio: lesen und steuern

```
GET  /api/v1/audio/devices                    -> { "devices": [ { "id": "demo", "kind": "demo", "name": "Demo-Beat" }, ... ] }
PUT  /api/v1/audio    { "device": "demo" }    diese Quelle öffnen (`running` false schließt sie)
PUT  /api/v1/audio    { "settings": { "mode": "manual", "bpm": 128, "sensitivity": 0.7 } }
POST /api/v1/audio/tap                        Tempo antippen (etwa 4 Tipper hintereinander setzen es, das Tempo steht dann auf manuell)
GET  /api/v1/audio                            Pegel, Bänder, Kick / Snare / Hat, bpm, beat_phase ... und die Einstellungen
```

`PUT /audio` wendet zuerst die `settings` an und öffnet dann die Quelle (`running: true` oder ein `device`) bzw. schließt sie (`running: false`); die Antwort entspricht `GET /audio`. Lässt sich die Quelle nicht öffnen, antwortet die API mit `409 audio_failed` und dem Grund. Einstellungen: `gain`, `auto_gain`, `sensitivity`, `smoothing`, `latency_ms`, `mode` (`auto` | `manual`), `bpm` (manuelles Tempo), `phase_follow`, `demo_bpm`, `autostart`; unbekannte Schlüssel werden ignoriert, Zahlen auf ihren Bereich begrenzt.

### Einen Cue bauen

```
POST /api/v1/cuelists/Show/cues
{
  "number": 3, "name": "Blaues Wash", "fade": 3,
  "changes": [
    { "group": "Wash", "values": { "dimmer": 80, "color": "#0000ff" } },
    { "fixtures": [1], "values": { "dimmer": 20 } }
  ],
  "effects": [ { "fixtures": [2, 3], "effects": { "dimmer": "Blitz" } } ]
}
```

```json
{ "status": "created", "cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "cue": { "id": "5c0b…", "number": 3, "name": "Blaues Wash", "fade": 3.0, "changes": [ … ], "effects": [ … ], … } }
```

Die Antwort ist der ganze Cue, so wie ihn `GET …/cues/3` zeigt. Gibt es Cue 3 schon, kommt `409 cue_exists`; mit `"on_conflict": "merge"` kommen die gesendeten Attribute dazu, mit `"overwrite"` wird sein Inhalt ersetzt (Status `merged` / `overwritten`).

Dasselbe aus dem Programmer, wie *Store Cue*:

```
PUT  /api/v1/programmer/values   { "fixtures": [2, 3], "values": { "color": "#ff8000", "dimmer": 100 } }
POST /api/v1/cuelists/Show/cues  { "number": 4, "name": "Orange", "from_programmer": true, "clear_programmer": true }
```

### Cues ändern und löschen

```
PUT    /api/v1/cuelists/Show/cues/3   { "name": "Tiefblau", "fade": 5, "times": { "color": { "fade": 8 } } }
PUT    /api/v1/cuelists/Show/cues/3   { "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] }                       (ergänzt den Inhalt)
PUT    /api/v1/cuelists/Show/cues/3   { "content": "replace", "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] } (Inhalt = genau das)
PUT    /api/v1/cuelists/Show/cues/3   { "number": 2.5 }                                                                          (umnummerieren)
DELETE /api/v1/cuelists/Show/cues/3
```

Nur, was du sendest, ändert sich. Eine Änderung an einem laufenden Cue wirkt beim nächsten *Go*.

### Variablen und Effekte

```
POST /api/v1/variables  { "name": "Warmweiß", "type": "color", "values": { "hex": "#ffb060" } }
PUT  /api/v1/variables/Warmweiß   { "values": { "hex": "#ffa040" } }        -> jeder Cue, der sie benutzt, ist jetzt wärmer
POST /api/v1/effects    { "script": "strobe", "name": "Blitz", "params": { "rate_hz": 8 } }
POST /api/v1/effects/Blitz/assign   { "fixtures": [2, 3] }                  -> er läuft jetzt
POST /api/v1/effects/release        { "fixtures": [2, 3] }                  -> beenden
```

`GET /api/v1/effect-scripts` listet die Effekt-Typen mit ihren Einstellungen (`variables`: Name, Art, Grenzen, Standard, Beschriftungen in beiden Sprachen).

### Einen eigenen Effekt-Typ schreiben

```
POST /api/v1/effect-scripts/check   { "text": "…" }                  -> { "ok": false, "line": 3, "message": "…" }
PUT  /api/v1/effect-scripts/meine_welle { "text": "…", "overwrite": true }
POST /api/v1/effects                { "script": "meine_welle" }
```

Ein Skript wird nur gespeichert, wenn es übersetzt und läuft. Die Sprache steht in der Anleitung *Effekt-Studio*.

### Scheinwerfer patchen

```
GET  /api/v1/fixture-types?q=par
POST /api/v1/fixtures  { "type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "universe": 1, "address": 11, "group": "Wash" }
```

```json
{ "created": [ { "fid": 4, "name": "Par 1", "universe": 1, "start_channel": 11, "end_channel": 14, … },
               { "fid": 5, "name": "Par 2", "universe": 1, "start_channel": 15, … }, … ] }
```

Adressen, die andere Scheinwerfer überlappen, werden abgelehnt (`409 address_conflict`); `"allow_overlap": true` patcht trotzdem.

### Der Programmer

```
GET  /api/v1/programmer
PUT  /api/v1/selection            { "group": "Wash" }
PUT  /api/v1/programmer/values    { "values": { "dimmer": 100, "color": [255, 0, 0] } }       (ohne fixtures: die Auswahl)
POST /api/v1/programmer/variables { "variable": "Warmweiß" }
POST /api/v1/programmer/clear     { "fixtures": [2] }          ihre Werte vergessen (die Ausgabe bleibt)
POST /api/v1/programmer/clear     { "all": true }              Clear Clear: jeder Scheinwerfer dunkel, Effekte enden
```

So gesetzte Werte verhalten sich wie die Fader im Programmer-Fenster: Die Ausgabe ändert sich sofort, sie gelten als angefasst, und das nächste *Store Cue* übernimmt sie.

### Relative Werte (anstupsen statt setzen)

```
curl -X PUT -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/json" \
  -d '{"group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}' \
  http://127.0.0.1:8000/api/v1/programmer/values
```

Mit `"mode": "relative"` sind die Zahlen **Änderungen in Prozentpunkten** (−100 bis 100); jeder Scheinwerfer geht von seinem eigenen Wert aus und wird bei 0 / 100 % begrenzt. Farben und rohe Kanäle gibt es nur absolut. Für schnelle Folgen von Änderungen (Drehregler, Joystick) ist der WebSocket (Abschnitt 10) besser.

### Showfiles

```
POST /api/v1/showfile/save-as  { "name": "Konzert" }
POST /api/v1/showfile/load     { "name": "Konzert", "force": false }
POST /api/v1/showfile/new      { "force": true }
```

Ohne `force` bleiben *Laden* und *Neu* mit `409 unsaved_changes` stehen, wenn die laufende Show ungespeicherte Änderungen hat. Ob sie welche hat, sagt `GET /api/v1/showfile`.

### Buttons, Fader und Toggles der Konsole

```
GET /api/v1/widgets
POST /api/v1/widgets/b1/press
PUT  /api/v1/widgets/f1/value   { "value": 70 }
PUT  /api/v1/widgets/t1/state   { "on": true }
```

`GET /widgets` listet die Panels mit `id`, `label`, Befehl und dem aktuellen Wert (Fader) bzw. Zustand (Toggles). Drücken, Bewegen oder Schalten führt den Befehl aus, der im Panel eingestellt ist – denselben, den ein Bediener auslöst – und die Panels auf jedem Gerät folgen (ein gedrückter Button pulsiert, Fader und Toggles mit demselben Befehl ziehen mit). Ein Faderwert wird auf Minimum / Maximum begrenzt. Ein Panel ohne Befehl antwortet mit `409 no_command` (ein Toggle ohne Befehle schaltet nur um). Es sind die Panels des Layouts der **Konsole**; Remote-Geräte haben eigene Layouts.

### Ausgänge und Layouts

```
PUT  /api/v1/system   { "artnet": { "ip": "192.168.1.255" }, "sacn": { "enabled": false } }
POST /api/v1/layouts/Konzert.json/load
POST /api/v1/fixture-types   (rohe .gdtf-Datei, Kopfzeile X-Filename: mein_geraet.gdtf)
```

### Ein Medium hochladen

```
curl -X POST -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/octet-stream" \
     -H "X-Filename: intro.mp4" --data-binary @intro.mp4 http://127.0.0.1:8000/api/v1/media
```

### Live-Ereignisse (Strom)

```
curl -N -H "Authorization: Bearer oc_xxxxxxxx" "http://127.0.0.1:8000/api/v1/events?events=cue,blackout,command"
```

```
event: hello
data: {"app": "OpenCue", "events": ["blackout", "cue", "command"]}

event: cue
data: {"cuelists": [{"id": "7e5d…", "name": "Show", "active_cue": {"id": "700…", "number": 2, "name": "Blau", …}}]}

event: command
data: {"command": "Fixture 1 At 10", "success": true, "message": "OK: …", "time": "21:14:03"}
```

Die Verbindung bleibt offen. Zuerst kommen `hello` und je Art eine Meldung mit dem **aktuellen Stand**, danach jede Änderung. Arten: `cue` (der aktive Cue einer Liste hat gewechselt), `cuelists` (Listen / Cues kamen dazu, fielen weg, wurden umbenannt), `blackout`, `master`, `timecode` (gestartet, gestoppt, Tempo), `selection`, `effects`, `fixtures`, `variables`, `show` (Name / ungespeicherte Änderungen), `command` (ein Konsolenbefehl lief, von irgendwoher), `audio` (Quelle geöffnet / geschlossen, Tempo, Signal vorhanden). Nur auf Anfrage (`?events=beat,hit`): `beat` (jeder Beat, mit Tempo) und `hit` (jeder Schlag von Bassdrum / Snare / Hi-Hat: `{"drum": "kick", "strength": 0.9}`). `?events=` beschränkt den Strom. Änderungen werden binnen etwa 0,1 s bemerkt. Alle 15 s kommt eine Kommentarzeile (`: keep-alive`); es laufen höchstens 20 Ströme gleichzeitig. Braucht die Berechtigung *Status*.

Im Browser kann `EventSource` keine Kopfzeilen senden: nimm `?access_token=<Token>` oder `fetch()` mit Kopfzeile und lies den Strom. Das Token steht dann in der Adresse – gib so einer Seite ein eigenes Token nur mit *Status*.

---

## 7. Kleine Programme

Python, mit der Bibliothek `requests` (jede HTTP-Bibliothek geht):

```python
import requests

BASE = "http://127.0.0.1:8000/api/v1"
HEAD = {"Authorization": "Bearer oc_xxxxxxxx"}

# Welche Farbe hat jeder Scheinwerfer?
for fx in requests.get(f"{BASE}/fixtures/state", headers=HEAD).json()["fixtures"]:
    color = fx["state"].get("color")
    print(fx["fid"], fx["name"], color["hex"] if color else "-")

# Front dimmen, dann den nächsten Cue starten
requests.post(f"{BASE}/command", headers=HEAD, json={"command": "Fixture 1 At 30"})
requests.post(f"{BASE}/cuelists/Show/go", headers=HEAD)
```

Eine kleine Show aufbauen (braucht die Bearbeiten-Rechte):

```python
requests.post(f"{BASE}/fixtures", headers=HEAD, json={"type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "address": 1, "group": "Wash"})
requests.post(f"{BASE}/variables", headers=HEAD, json={"name": "Warm", "type": "color", "values": {"hex": "#ffb060"}})
requests.post(f"{BASE}/cuelists", headers=HEAD, json={"name": "Show"})
requests.post(f"{BASE}/cuelists/Show/cues", headers=HEAD, json={
    "number": 1, "name": "Warm", "fade": 3,
    "changes": [{"group": "Wash", "values": {"dimmer": 80}, "variables": {"color": "Warm"}}]})
requests.post(f"{BASE}/showfile/save-as", headers=HEAD, json={"name": "Aus der API"})
```

Eine Webseite, die den aktiven Cue live zeigt (JavaScript im Browser; die Seite darf von jeder Adresse kommen, siehe Abschnitt 8):

```javascript
const res = await fetch("http://192.168.1.20:8000/api/v1/events?events=cue", { headers: { Authorization: "Bearer oc_xxxxxxxx" } });
const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log(value);          // "event: cue\ndata: {...}\n\n"
}
```

---

## 8. Andere Geräte und Sicherheit

- **Von einem anderen Rechner oder Tablet** ist die API erreichbar, sobald **HTTP-Zugriff aus dem Netzwerk erlauben** (Einstellungen → Remote) eingeschaltet ist. Nimm die Adresse der Konsole (steht auf dieser Seite) statt `127.0.0.1`, zum Beispiel `http://192.168.1.20:8000/api/v1/status`. Bei ausgeschaltetem Remote-Zugriff ist der Port für das Netzwerk geschlossen. Das **Token ersetzt dort das Passwort** – eine Anmeldung ist nicht nötig.
- Tokens geben echte Kontrolle über die Lichter. Gib jedem Programm sein **eigenes Token mit nur den nötigen Berechtigungen** und lösche Tokens, die du nicht mehr brauchst.
- Die **Bearbeiten-Rechte sind standardmäßig aus** und können Show-Daten ändern oder zerstören: *Patch*, *Showfiles* und *Konsolenbefehle* sind als **kritisch** markiert. *Laden* und *Neu* werfen ungespeicherte Änderungen nicht ohne `force` weg.
- Der Datenverkehr ist einfaches HTTP innerhalb deines Netzwerks. Setze den Port nicht ins Internet.
- **Webseiten auf anderen Adressen** (ein eigenes Dashboard, ein Web-Werkzeug im Browser) dürfen die API direkt aufrufen: Die Antworten tragen die Kopfzeilen für den Zugriff von anderen Adressen (CORS), und die Vorab-Anfrage des Browsers (`OPTIONS`, die kein Token tragen kann) wird beantwortet. Die Seite braucht trotzdem ein Token im Kopf `Authorization` und muss es für sich behalten (lege kein mächtiges Token in eine öffentliche Webseite). Schalte es unter *Einstellungen → API → Webseiten auf anderen Adressen erlauben* aus, wenn du es nicht brauchst; dann blockieren Browser solche Seiten wieder (Programme und Skripte sind nicht betroffen).
- Die API ändert die Show **im Arbeitsspeicher**, wie das Fenster. Auf der Festplatte steht erst etwas, wenn die Show gespeichert wird (`POST /showfile/save` oder *Speichern* im Fenster).

---

## 9. Wenn etwas nicht funktioniert

| Problem | Prüfen |
|---|---|
| `401 unauthorized` | Kopf als `Authorization: Bearer oc_…` mit dem vollständigen Token geschrieben? Token gelöscht oder neu erzeugt? |
| `403 forbidden` | Dem Token fehlt diese Berechtigung – öffne es unter *Einstellungen → API* und schalte sie ein (die Meldung nennt sie). |
| `403 api_disabled` | Der Hauptschalter unter *Einstellungen → API* ist aus. |
| `403 remote access disabled` | Du rufst von einem anderen Gerät auf, während *HTTP-Zugriff aus dem Netzwerk erlauben* aus ist. |
| `404 not_found` | Scheinwerfernummer, Name der Cue-Liste (genau) und Cue-Nummer prüfen. |
| `409 duplicate` | Der Name ist vergeben (Groß-/Kleinschreibung egal). Wähle einen anderen oder ändere den vorhandenen mit `PUT`. |
| `409 cue_exists` | Ein Cue mit dieser Nummer ist in der Liste: `on_conflict` oder `PUT`. |
| `409 unsaved_changes` | Erst speichern (`POST /showfile/save`) oder `force: true` mitschicken. |
| `409 no_command` / `409 wrong_type` | Ein Panel hat keinen Befehl / du hast einen Fader gedrückt, einen Button bewegt … (den Typ zeigt `GET /widgets`). |
| `422` | Ein Feld, das es nicht gibt (Tippfehler?), oder ein falscher Typ – die Meldung nennt das Feld. |
| `422 invalid_script` | Das Skript hat einen Fehler – die Meldung nennt die Zeile. `POST /effect-scripts/check` testet ohne zu speichern. |
| `200`, aber `"success": false` | Der Befehl wurde abgelehnt – lies `message`. |
| `429` | Zu viele falsche Tokens von dieser Adresse. Warte `Retry-After` Sekunden. |
| Browser-Seite: „blocked by CORS“ | *Einstellungen → API → Webseiten auf anderen Adressen erlauben* ist aus, oder die Anfrage hat kein Token (die Fehlerantwort der API trägt die Kopfzeilen, der wahre Grund ist also sichtbar). |
| Gar keine Antwort | Läuft OpenCue, und stimmt der Port (Einstellungen → Remote zeigt ihn)? |

---

## 10. Hardware und schnelle Steuerung: der WebSocket-Strom

Für **Hardware** (ESP32, Arduino, Raspberry Pi, ein Pult-Selbstbau) und alle Anwendungen, die **viele kleine Werte schnell** schicken oder empfangen, gibt es neben den HTTP-Routen einen **WebSocket**: `ws://<Konsole>:8000/api/v1/ws`. Eine Verbindung bleibt offen, beide Seiten schicken kleine **JSON-Nachrichten** (Textrahmen) – ohne den Aufwand einer neuen HTTP-Anfrage je Wert. Er braucht keine zusätzliche Berechtigung: Jede Nachricht verlangt **dieselbe Berechtigung wie die passende HTTP-Route** (Tabelle unten). Mit der Voreinstellung *Bedienen* geht alles außer rohem DMX.

### Verbinden und anmelden

Das Token geht auf eine von drei Arten mit (Mikrocontroller nehmen am einfachsten die Adresse):

1. in der Adresse: `ws://opencue.local:8000/api/v1/ws?access_token=oc_xxxxxxxx`
2. im Kopf: `Authorization: Bearer oc_xxxxxxxx` (oder `X-API-Key`)
3. als **erste Nachricht** binnen 5 s: `{"op": "auth", "token": "oc_xxxxxxxx"}`

Danach schickt OpenCue `{"op": "hello", ...}` mit den erlaubten Berechtigungen, den Operationen, Themen und Grenzen. Fehler schließen die Verbindung mit einem Code: `4401` (Token fehlt / falsch), `4403` (API aus, nur dieser PC, Fernzugriff aus, Token ausgeschaltet), `4429` (zu viele Fehlversuche / zu viele Verbindungen). Gelten dieselben Regeln wie bei HTTP: *REST-API an*, *Erreichbar von*, Sperre nach Fehlversuchen. Es sind höchstens 10 Verbindungen gleichzeitig offen.

Jede Nachricht ist ein JSON-Objekt mit `"op"`. Ein optionales **`"id"`** (beliebige Zahl oder Text) kommt in der Antwort zurück: `{"op": "ack", "id": 7, ...}` bei Erfolg, `{"op": "error", "id": 7, "code": "...", "message": "..."}` bei einem Fehler. Ohne `id` gibt es nur Fehlermeldungen. Eine fehlerhafte Nachricht beendet die Verbindung nie.

### Nachrichten von der Hardware

| `op` | Berechtigung | Was es tut |
|---|---|---|
| `joystick` | Programmer | Ein Joystick-Knüppel – siehe unten |
| `set` | Programmer | Werte setzen, **absolut** oder **relativ** – siehe unten |
| `select` | Programmer | Auswahl ändern: `{"op":"select","mode":"set","fixtures":[1,2]}` (`mode`: `set`, `add`, `remove`, `clear`) |
| `cmd` | Befehle | Konsolenbefehl: `{"op":"cmd","line":"Cuelist Main Go"}` (Antwort: `success`, `message`) |
| `cue` | Cues | `{"op":"cue","list":"Main","action":"go"}`; `action`: `go` (mit `"cue": 5` springt es), `back`, `pause`, `resume`, `stop`, `fader` (mit `"value"`) |
| `master`, `blackout` | Blackout / Master | `{"op":"master","value":70}`, `{"op":"blackout","on":true}` |
| `dmx` | DMX-Kanäle | `{"op":"dmx","universe":1,"channels":{"1":255,"2":0}}` – roher Kanalwert wie `PUT /dmx/{universe}` |
| `tap` | Audio | Tempo antippen (ein Taster am ESP32) |
| `timecode` | Timecode | Timecode steuern: `{"op":"timecode","action":"play"}` (auch `pause`, `stop`, `seek`, `rate`) – oder `{"op":"timecode","action":"sync","position":12345,"running":true}`: OpenCue läuft als **Folger** einer äußeren Uhr (Position in ms oder `"0:12.345"`; Abweichungen unter 60 ms werden nicht nachgestellt, damit die Uhr nicht ruckelt; ein Sprung versetzt sie ohne Cues auszulösen) |
| `audio_in` | Audio | Audio **hinein** – siehe unten |
| `subscribe`, `unsubscribe` | je Thema | Live-Werte **abonnieren** – siehe unten |
| `ping` | – | Antwort `{"op":"pong","t":<dein t>,"server_ms":...}`: Antwortzeit messen, Uhren abgleichen |

Ziele (`set`, `joystick`, `select`) benennt man wie bei den HTTP-Routen: `"fixtures": [1, 2, "Front 3"]`, `"fixture": 5`, `"group": "Front"` und / oder `"selection": true` (die Auswahl der Konsole). Fehlt jede Angabe, gilt die Auswahl.

### Werte setzen: absolut und relativ

```json
{"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80, "pan": 25, "color": "#ff8800"}}
{"op": "set", "group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}
```

- **absolut** (Standard): die Werte sind die neuen Werte – Prozent 0–100, Farbe als `#rrggbb` / `[r,g,b]`, rohe Kanäle als `ch<N>` (0–255).
- **relativ** (`"mode": "relative"`): die Zahlen sind **Änderungen in Prozentpunkten** (−100 bis 100), jeder Scheinwerfer geht von **seinem eigenen** Wert aus und wird bei 0 / 100 % begrenzt. Das ist das Richtige für Drehregler und Tasten „ein Stück weiter“. Farben und rohe Kanäle können nicht relativ sein.

Dasselbe gibt es bei HTTP: `PUT /programmer/values` mit `"mode": "relative"`. Pan und Tilt werden mit voller **16-Bit-Auflösung** gesetzt (Grob und Fein).

### Joystick

```json
{"op": "joystick", "selection": true, "x": 0.35, "y": -0.8}
```

`x` und `y` gehen von −1 bis 1 (rechts / oben positiv). Standardmäßig steuert er Pan (`x`) und Tilt (`y`) der gewählten Scheinwerfer; mit `"axes": {"x": "pan", "y": "zoom"}` lässt sich jedes Attribut zuordnen (`dimmer`, `zoom`, `focus`, `strobe`, `gobo`, `prism` ...). Zwei Betriebsarten (`"mode"`):

- **`rate`** (Standard, **relativ**): die Auslenkung bestimmt die **Geschwindigkeit**, nicht die Stellung – wie der Joystick im Programmer. Kleine Ausschläge sind sehr genau (knapp aus der Mitte etwa 1° pro Sekunde), große schnell (ganz außen läuft der Bereich in wenigen Sekunden durch); die Kennlinie ist exponentiell. OpenCue rechnet die Bewegung **selbst im 40-Hz-Takt** aus der zuletzt gemeldeten Auslenkung – das Gerät muss also nur Änderungen und etwa alle 20–50 ms den Stand schicken; Schwankungen im WLAN machen die Bewegung nicht ruckelig. Mehrere gewählte Scheinwerfer bewegen sich von **ihrem** Startwert aus um dasselbe Stück; am Ende des Bereichs bleiben sie stehen. Mit `x = y = 0` (oder innerhalb der Totzone) ist der Knüppel losgelassen: **die Scheinwerfer bleiben stehen**.
- **`position`** (**absolut**): die Stellung ist die Position – `x = −1` ist Pan 0 %, `x = 1` Pan 100 %. Für Geräte mit Federrückstellung nicht sinnvoll, wohl aber für einen Drehgeber oder Schiebepoti.

Weitere Felder: `stick` (Name, wenn ein Gerät mehrere Knüppel hat; Standard `main`, bis zu 4), `speed` (Faktor 0,05–4 für die Geschwindigkeit, Standard 1), `deadzone` (0–0,5, Standard 0,04), `timeout_ms` (100–5000, Standard 500), `invert_y`, `release: true` (Knüppel sofort loslassen). Die Ziele werden beim Anfassen festgelegt und bis zum Loslassen beibehalten.

**Totmann:** kommt länger als `timeout_ms` keine Nachricht mehr (Kabel ab, WLAN weg, Gerät hängt), bleibt der Knüppel stehen, und OpenCue meldet `{"op":"joystick","stick":"main","state":"timeout"}`. Bricht die Verbindung ab, bleiben alle Scheinwerfer stehen.

### Live-Werte abonnieren

`{"op":"subscribe","topic":"<Thema>","hz":30}` – `hz` ist die höchste Rate (1–60, Standard 30). OpenCue schickt nur, was sich **geändert** hat. `unsubscribe` mit `"topic"` beendet das Abo.

| `topic` | Berechtigung | Nachrichten |
|---|---|---|
| `audio` | Status | `{"op":"audio","t":ms,"running":true,"v":{"a_level":0.62,"a_bass":0.9,"a_bpm":124,...}}` – die Audio-Variablen aus der Audio-Analyse; `"keys": ["a_level","a_bass"]` begrenzt sie |
| `dmx` | DMX | `"universes": [1]` (bis 8): zuerst `{"op":"dmx","universe":1,"full":true,"values":[512 Zahlen]}`, danach nur `{"op":"dmx","universe":1,"changes":{"17":255}}` (Kanal → Wert) |
| `fixtures` | DMX | `{"op":"fixtures","values":{"3":{"pan":12.5,"tilt":50,"dimmer":100,"color":{...}}}}` – Live-Werte je Scheinwerfer-**Nummer**, nur geänderte |
| `timecode` | Status | `{"op":"timecode","ms":83400,"text":"00:01:23.400","running":true,"direction":1,"rate":1}` – läuft die Uhr, mit jedem Takt (bis 60 Hz), sonst nur bei einer Änderung (Start, Stopp, Sprung, Tempo) |
| `events` | Status | wie `GET /events`: `{"op":"event","event":"cue","data":{...}}`; `"events": ["cue","blackout"]` wählt aus (ohne Angabe die Standardarten; `beat` und `hit` nur auf Wunsch). Zuerst kommt der aktuelle Stand |

### Audio hinein: ein Mikrofon am ESP32

Mit der Audio-Quelle **„Netzwerk (API)“** analysiert OpenCue Audio, das ein Gerät schickt – Pegel, Bänder, Bassdrum / Snare / Hi-Hat, Tempo und Beat stehen dann wie sonst als `a_`-Variablen für **Effekte, Cue-Auslöser und das Audio-Panel** zur Verfügung.

1. Quelle öffnen: im Audio-Panel *Netzwerk (API)* wählen, oder `PUT /audio` mit `{"device": "network"}`, oder gleich mit der Nachricht aus Schritt 2 (`"open": true`).
2. `{"op":"audio_in","rate":16000,"open":true}` – kündigt PCM an (`rate` 8000–48000 Hz, **16 Bit signed little endian, Mono**).
3. Dann **Binärrahmen** (WebSocket-Binary) mit den Samples schicken, z. B. 20 ms am Stück (bei 16 kHz 640 Bytes). Höchstens 64 KB je Rahmen.

Ist die Quelle nicht offen, antwortet OpenCue (höchstens einmal je Sekunde) mit dem Fehler `audio_source`. Ohne Daten rechnet die Analyse mit Stille weiter.

### Grenzen und Schutz

Die **DMX-Ausgabe hat immer Vorrang**: sie läuft in einem eigenen Thread (etwas höhere Priorität), und der Strom ist begrenzt – damit eine Hardware die Steuerung nie ausbremst. Höchstens 300 Nachrichten je Sekunde je Verbindung (Spitzen bis 600) und 1200 insgesamt – mehr bekommen `rate_limited` und werden verworfen; Textnachrichten bis 8 KB, Binärrahmen bis 64 KB; 10 Verbindungen; ein Joystick ändert höchstens im 40-Hz-Takt. Eine Verbindung ohne Anmeldung wird nach 5 s geschlossen.

### Beispiel: ESP32 mit Joystick (Arduino)

```cpp
#include <WiFi.h>
#include <WebSocketsClient.h>          // Bibliothek "WebSockets" von Markus Sattler (arduinoWebSockets)

const char* WIFI_SSID = "MeinWLAN";
const char* WIFI_PASS = "geheim";
const char* TOKEN     = "oc_xxxxxxxx";      // Token mit "Programmer" (write.programmer)
const int PIN_X = 34, PIN_Y = 35;           // die beiden Achsen des Joysticks (ADC)

WebSocketsClient ws;
int centerX = 2048, centerY = 2048;

float norm(int raw, int center) {           // 0..4095 -> -1..1
  float f = (raw - center) / 2048.0f;
  return f < -1 ? -1 : (f > 1 ? 1 : f);
}

void onEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) Serial.println("OpenCue verbunden");
  if (type == WStype_TEXT)      Serial.printf("%s\n", payload);       // hello, Fehler, Rueckmeldungen
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(200);
  delay(300);
  centerX = analogRead(PIN_X);              // Ruhelage beim Start merken
  centerY = analogRead(PIN_Y);
  String path = String("/api/v1/ws?access_token=") + TOKEN;
  ws.begin("opencue.local", 8000, path);    // oder die IP-Adresse der Konsole
  ws.onEvent(onEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();
  static uint32_t last = 0;
  if (ws.isConnected() && millis() - last >= 20) {      // 50 Mal pro Sekunde
    last = millis();
    float x = norm(analogRead(PIN_X), centerX);
    float y = -norm(analogRead(PIN_Y), centerY);        // nach oben = Tilt mehr
    char msg[128];
    snprintf(msg, sizeof msg, "{\"op\":\"joystick\",\"selection\":true,\"x\":%.3f,\"y\":%.3f}", x, y);
    ws.sendTXT(msg);
  }
}
```

Das Gerät schickt auch im Ruhezustand weiter `x = 0, y = 0` – das schadet nicht (der Knüppel gilt dann als losgelassen). Die Auswahl am Pult bestimmt, was bewegt wird; mit `"fixtures": [1, 2]` oder `"group"` statt `"selection": true` ist das Ziel fest.

### Beispiel: Python

```python
import asyncio, json, websockets            # pip install websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws?access_token=oc_xxxxxxxx") as ws:
        print(json.loads(await ws.recv()))                           # hello
        await ws.send(json.dumps({"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80}}))
        await ws.send(json.dumps({"op": "subscribe", "topic": "audio", "hz": 30, "keys": ["a_level", "a_bass"]}))
        async for text in ws:
            frame = json.loads(text)
            if frame["op"] == "audio":
                print(frame["v"])

asyncio.run(main())
```

Eine Referenz aller Nachrichten steht auch auf der Seite `/api/v1/docs`.

---

## 11. Status-Ansichten: Bilder und Web-Seiten für einfache Geräte

Für Geräte, die nur **ein Bild abholen** oder eine **schlichte Seite** anzeigen können – ein ESP32 mit Display, ein altes Tablet als Wandanzeige, ein Browser-Tab auf dem Foyer-Monitor – gibt es **Status-Ansichten**. Sie sind **nur zum Ansehen** (keine Bedienung), brauchen **keine Bibliothek** auf dem Gerät und rechnen OpenCue selbst: Es ist derselbe Inhalt, ob als Bild oder als Seite.

| Ansicht | Zeigt | Berechtigung |
|---|---|---|
| `status` | Show, Blackout, Master, Timecode, aktiver Cue jeder Liste, Tempo | Status |
| `timecode` | die Uhr groß, „läuft / gestoppt“ | Status |
| `dmx` | die 512 Kanäle eines Universums als Raster (`?universe=1`), Helligkeit = Wert | DMX |
| `cue` | der aktive Cue einer Liste (`?list=Main`) und der nächste | Status |
| `audio` | Pegel, die acht Bänder, Tempo | Status |

Jede Ansicht gibt es in mehreren Formen (`GET /api/v1/views/<name>…`):

| Adresse | Ergebnis |
|---|---|
| `/views/status` | **Web-Seite**, aktualisiert sich selbst (`?refresh=2` Sekunden); ohne JavaScript per Meta-Refresh |
| `/views/status.png` | **PNG-Bild** (`?w=320&h=240&theme=dark`; Größe 64×48 bis 800×600; `theme`: `dark` oder `light`) |
| `/views/status.bmp` | 24-Bit-**BMP** – jeder kleine Decoder versteht es |
| `/views/status.rgb565` | **rohe Bildpunkte**, 16 Bit je Punkt (5-6-5, High-Byte zuerst), die Größe steht in den Kopfzeilen `X-Width` / `X-Height`: direkt an ein TFT übergeben (kein Decoder nötig) |
| `/views/status.json` | das Anzeigemodell (Teile: Titel, Zeilen, Balken, Raster) – wer selbst zeichnen will |
| `/views` | Liste aller Ansichten mit Parametern |

Anmeldung wie sonst. Ein Browser oder ein Gerät, das keinen Kopf senden kann, hängt das Token an (`access_token`, auch `token` geht; Leerzeichen und Anführungszeichen vom Kopieren stören nicht). Die Meldung sagt, ob das Token **fehlt** oder **ungültig / gelöscht** ist; die Konsole schreibt jede abgelehnte Anmeldung ins Protokoll. Hakt das erste Laden von `opencue.local` (Windows löst `.local`-Namen beim ersten Mal manchmal langsam auf), nimm die **IP-Adresse** – sie steht in *Einstellungen → REST-API* (zum Kopieren): `…/views/status?access_token=oc_xxxxxxxx` (das Token steht dann in der Adresse – dafür ein eigenes Token **nur mit „Status“ und „DMX“** anlegen). Der Schalter **Status-Ansichten** in *Einstellungen → REST-API* schaltet alles ab (Antwort `403 views_disabled`).

**Farbe:** `?color=green` (oder `amber`, `red`, `blue`, `cyan`, `white`, `magenta`, `violet`, `orange`, `yellow`, oder `#rrggbb`) ändert die Hervorhebungsfarbe; der DMX-Monitor ist standardmäßig **grün**.

**Fehler sieht man:** Stimmt etwas nicht (Token falsch, Ansichten aus, keine Berechtigung), kommt bei einem **Bild** (`.png` / `.bmp` / `.rgb565`) mit dem passenden Statuscode (401, 403 …) **ein Bild mit der Meldung** – ein Display zeigt es einfach an („TOKEN FEHLT ODER FALSCH“, „STATUS-ANSICHTEN SIND AUS“ …); die **Web-Seite** zeigt eine Seite mit der Meldung und lädt sich alle 5 s neu. Ist OpenCue nach dem Öffnen nicht mehr erreichbar, blendet die Seite oben **„Keine Verbindung zu OpenCue“** ein und dimmt das letzte Bild, bis es wieder klappt. `.json` bleibt bei der JSON-Fehlermeldung.

**Die DMX-Ausgabe hat immer Vorrang:** Bilder werden höchstens alle 0,4 s je Ansicht und Größe neu berechnet (viele Geräte teilen sich ein Bild), in einem Hintergrund-Thread, und es rechnen nie mehr als vier gleichzeitig. Ein 320×240-Bild kostet etwa 6 ms. Der DMX-Ausgabe-Thread läuft zusätzlich mit etwas höherer Priorität.

### ESP32 mit TFT: ein Bild alle zwei Sekunden

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>                       // 320 x 240 Display

TFT_eSPI tft;
uint16_t frame[320 * 240];                  // 150 KB: bei ESP32 ohne PSRAM besser 160 x 120 anfragen

void loop() {
  HTTPClient http;
  http.begin("http://opencue.local:8000/api/v1/views/status.rgb565?w=320&h=240&access_token=oc_xxxxxxxx");
  if (http.GET() == 200) {
    WiFiClient* s = http.getStreamPtr();
    s->readBytes((uint8_t*)frame, sizeof frame);
    tft.setSwapBytes(true);
    tft.pushImage(0, 0, 320, 240, frame);
  }
  http.end();
  delay(2000);
}
```

Für Geräte mit wenig Speicher: kleinere Größe wählen (`w=160&h=120`) oder den Strom Zeile für Zeile an das Display geben.

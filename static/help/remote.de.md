# Fernsteuerung (Tablet und Handy)

Mit der **Fernsteuerung** bedienst du OpenCue von einem iPad, Tablet, Handy oder einem anderen Computer im **selben Netzwerk** – während der Konsolen-Computer die Show weiterführt und das DMX sendet. Geh durch den Raum und stelle Lichter ein, löse Cues von der Bühne aus aus oder nutze ein Tablet als zweiten Bildschirm.

Die Fernsteuerung ist **standardmäßig aus**. Solange sie aus ist, ist OpenCue aus dem Netzwerk überhaupt nicht erreichbar (der Port ist wirklich zu, nicht nur per Passwort geschützt).

---

## 1. Die Idee in einer Minute

- Die **Konsole** ist der Computer, auf dem OpenCue installiert ist und läuft. Sie macht die ganze Arbeit: Sie hält die Show, berechnet die Cues und sendet DMX.
- Ein **Fernsteuer-Gerät** ist einfach ein Browser. Er öffnet eine Webadresse der Konsole, meldet sich mit dem Passwort an und zeigt **dieselbe OpenCue-Oberfläche** – dieselbe Werkzeugleiste, dieselben Panels, dieselben Rechte.
- Alles bleibt live synchron: Wählst du auf einem Gerät einen Scheinwerfer, bewegst einen Fader oder drückst *Go*, zeigen es alle anderen sofort.
- Internet ist nicht nötig. Alles geschieht in deinem lokalen Netzwerk.

---

## 2. Einschalten

1. Öffne auf der Konsole die **Einstellungen** (Werkzeugleiste) → Kategorie **Remote**.
2. Schalte **Zugriff aus dem Netzwerk erlauben** ein.
3. Vergib ein **Passwort** (mindestens 4 Zeichen). Mit *Anzeigen* kannst du kontrollieren, was du getippt hast.
4. Ändere bei Bedarf den **Port** (1024–65535, Standard 8000). Ein geänderter Port gilt nach einem Neustart von OpenCue.
5. Klicke auf **Speichern & Anwenden**. Ein Neustart ist nicht nötig.

OpenCue lauscht jetzt auf jeder Netzwerkadresse der Konsole. Die Seite zeigt:

| Eintrag | Bedeutung |
|---|---|
| **Status** | „Im Netzwerk erreichbar“ oder „Nur lokal“. |
| **Adressen** | Jede Adresse, unter der die Konsole erreichbar ist, jeweils mit einem Knopf **Kopieren**. |
| **QR-Code** | Für die gewählte Adresse – mit der Kamera eines iPads oder Handys scannen. Das Passwort wird beim Verbinden abgefragt. |
| **Adressen neu erkennen** | Nachdem du das WLAN gewechselt oder ein Kabel eingesteckt hast. |

Schaltest du es wieder aus, werden die Listener sofort wieder geschlossen.

> **Windows-Firewall:** Beim ersten Einschalten fragt Windows eventuell, ob OpenCue im Netzwerk kommunizieren darf. Erlaube es für dein **privates** Netzwerk, sonst können sich andere Geräte nicht verbinden.

---

## 3. Ein Gerät verbinden

1. Das Gerät muss im **selben Netzwerk** (gleiches WLAN oder LAN) wie die Konsole sein.
2. Öffne im Browser des Geräts die Adresse von der Einstellungsseite – zum Beispiel `http://192.168.1.20:8000/` – oder scanne den QR-Code. Die Adresse leitet auf die Remote-Seite `/remote/` weiter.
3. Gib das Passwort ein und tippe auf **Anmelden**.

**Passwort speichern** (Haken auf der Anmeldeseite) legt das Passwort im Browser **nur dieses Geräts** ab und füllt das Feld beim nächsten Mal vor. Eine automatische Anmeldung gibt es nicht – du tippst weiterhin auf *Anmelden*. Nimmst du den Haken weg, wird das gespeicherte Passwort sofort gelöscht.

**Falsches Passwort:** Mehrere falsche Versuche sperren das Gerät eine Weile (Schutz gegen Durchprobieren).

**Abmelden:** *Datei → Abmelden* (wird nur auf Fernsteuer-Geräten angezeigt).

Wenn sich nichts verbindet: Prüfe, ob beide Geräte im selben Netzwerk sind (Gast-WLANs trennen Geräte oft voneinander), ob die Adresse mit der auf der Einstellungsseite übereinstimmt, und die Firewall (siehe oben).

---

## 4. Was ein Fernsteuer-Gerät kann

- **Alles, was die Konsole kann.** Nach der Anmeldung hat ein Fernsteuer-Gerät dieselben Rechte: Programmieren, Cues, Effekte, Dateien, Einstellungen, DMX-Einstellungen und Remote-Einstellungen. Dazu gehören auch Dinge mit Folgen – die Fernsteuerung ausschalten (das sperrt dieses Gerät aus) oder **OpenCue beenden**, was das Programm für alle stoppt. Nimm ein Passwort, das nur Vertrauenspersonen kennen.
- **Eigenes Layout pro Gerät.** Jedes Gerät merkt sich, welches Layout es benutzt hat, und kann ein anderes zeigen als die Konsole. Baue für das Tablet ein Layout mit großen Knöpfen (siehe unten). Speichert ein Gerät ein Layout, das ein anderes Gerät gerade zeigt, übernimmt das andere es – oder bietet, falls es eigene ungespeicherte Änderungen hat, *Übernehmen* oder *Meine Version behalten* an.
- **Pro Gerät eigen:** nur der **Vollbildmodus** (der des jeweiligen Browsers) und die **GUI-Skalierung**.
- **Die Daten bleiben auf der Konsole.** Speichern und Laden laufen immer über die Konsole; Shows, Layouts und Scheinwerfer liegen auf dem Konsolen-Computer.

### Wer ist verbunden?

Ein Symbol in der Werkzeugleiste zeigt, **wie viele Fernsteuer-Geräte verbunden sind**. Ein Klick zeigt IP-Adresse, Gerät und Verbindungsdauer jedes Geräts – und lässt dich ein Gerät **trennen** (*Kick*). Ein getrenntes Gerät sieht einen Hinweis und muss die Seite neu laden, um sich wieder anzumelden.

---

## 5. Als App installieren (iPad / iPhone / Android)

Die Remote-Seite ist eine **Web-App**. Auf dem Gerät kannst du sie zum Home-Bildschirm hinzufügen:

- **iPad / iPhone (Safari):** Teilen-Knopf → **Zum Home-Bildschirm**.
- **Android (Chrome):** Menü → **App installieren** / **Zum Startbildschirm hinzufügen**.

Sie öffnet sich dann im Vollbild ohne Browserleisten, in den Farben deines aktuellen Themes.

**Einschränkung:** Installierbare Web-Apps und die Offline-Seite brauchen eine sichere Verbindung (HTTPS). OpenCue wird in deinem lokalen Netzwerk über einfaches `http://` erreicht; die App auf dem Home-Bildschirm funktioniert also, aber es gibt keine Offline-Seite, und das Gerät muss die Konsole erreichen, um etwas zu zeigen.

---

## 6. Tipps für ein gutes Tablet-Layout

- Lege für das Tablet ein **eigenes Layout** an (*Bearbeiten → Layouts verwalten…*): großer **Executor**, **Cue-Liste**, ein paar **Button**- oder **Fader**-Panels und die **Scheinwerfer-Steuerung**-Kategorie, die du am meisten brauchst. Fernsteuer-Geräte laden ihr eigenes Layout, das Konsolen-Layout bleibt, wie es ist.
- Für Touch nimmst du die Panels **Befehls-Ziffernblock** und **Befehls-Tasten**, statt auf der Bildschirmtastatur zu tippen.
- Vergrößere die **GUI-Skalierung** auf dem Tablet (`Strg +` oder *Ansicht → GUI-Skalierung…*) – sie gilt nur für dieses Gerät.
- Layouts lassen sich durch horizontales **Wischen** wechseln, wenn *Einstellungen → Allgemein → Layout per Wischgeste wechseln* an ist (pro Gerät).
- Cue-Listen mit Timecode-Triggern laufen auf der Konsole weiter, auch wenn ein Gerät die Verbindung verliert – die Show hängt nicht am Tablet.

---

## 7. Sicherheit und gute Praxis

- Nutze die Fernsteuerung nur in Netzwerken, denen du vertraust (dein eigener Router, ein eigenes Show-Netz). Die Verbindung ist **nicht verschlüsselt** (einfaches HTTP); jeder im Netzwerk könnte den Datenverkehr mitlesen.
- Wähle ein Passwort, das du sonst nirgends benutzt – es steht in der App-Konfiguration der Konsole und, wenn du *Passwort speichern* ankreuzt, im Browser des Geräts.
- Schalte die Fernsteuerung aus, wenn du sie nicht brauchst.
- Die DMX-Ausgabe läuft immer auf der Konsole – auch wenn alle Fernsteuer-Geräte die Verbindung verlieren, bleiben die Lichter, wie sie sind.

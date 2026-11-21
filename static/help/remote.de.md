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
2. Schalte ganz oben den **Hauptschalter Fernzugriff** ein. **Es gibt kein Standardpasswort:** beim ersten Mal fragt OpenCue nach deinem eigenen – **„Passwort festlegen“**, zweimal eingegeben (mindestens 4 Zeichen; *Abbrechen* schaltet den Fernzugriff wieder aus). Danach ist **HTTP** an.
3. Das **Passwort** legst du unter **Einstellungen → Sicherheit** fest und änderst es dort (Knopf *Passwort festlegen oder ändern …* im Bereich Fernzugriff); das geht auch von einem Fernzugriffs-Gerät aus (dessen Anmeldung wird dabei mitgezogen; alle anderen Geräte müssen sich neu anmelden). Mit *Anzeigen* kannst du kontrollieren, was du getippt hast. Dasselbe Passwort schützt den Sperrbildschirm (Abschnitt 8). Jedes Passwort ist erlaubt (mindestens 4 Zeichen) – die Wahl ist deine.
4. Ändere bei Bedarf den **HTTP-Port** (1024–65535, Standard 8000). Ein geänderter Port gilt nach einem Neustart von OpenCue.
   **HTTPS** ist ein eigener Bereich darunter mit eigenem Schalter und eigenem **HTTPS-Port** (Standard 8001, gilt sofort): Eine **sichere Seite (https)** brauchen manche Browser-Funktionen: den **iPad-Bildschirm wach halten** (Einstellungen → Weitere Optionen → *Bildschirm wach halten*), den VR-Modus der 3D-Simulation sowie Mikrofon und Kamera im Browser. Öffne am iPad deshalb die **https://-Adresse** (Zertifikat einmal bestätigen); über `http://` geht nur die Geräte-Einstellung „Automatische Sperre: Nie“. OpenCue erstellt das Zertifikat selbst; der Browser fragt beim ersten Öffnen einmal nach der Bestätigung. HTTP und HTTPS lassen sich unabhängig voneinander ein- und ausschalten und haben je eine Adresse mit eigenem QR-Code.
   **Netzwerk-Name:** Zusätzlich ist die Konsole unter `opencue.local` erreichbar (kommt automatisch mit dem Fernzugriff; ein kleiner Schalter unter *Erweitert*), zum Beispiel `http://opencue.local:8000` – die Adresse bleibt in jedem Netzwerk gleich. Ist der Name schon vergeben (etwa von einer zweiten Konsole), nimmt OpenCue `opencue-2.local` usw.; die Einstellungen zeigen, welcher gilt. iPad, iPhone, Mac und Windows 10/11 verstehen den Namen von selbst. Eine als App installierte Seite ist an ihre Adresse gebunden: Wechselst du auf den Namen, installiere sie einmal neu.
5. Klicke auf **Speichern** (der Dialog bleibt offen). Ein Neustart ist nicht nötig. Beim ersten Einschalten fragt Windows einmal nach der Firewall – erlaube **private Netzwerke**.

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
- **Vollzugriff auf alle Einstellungen, auch vom iPad.** Das ist wichtig, wenn OpenCue ohne Fenster läuft (*Nur Server*, Tray-Symbol): Alle Einstellungen – Ausgabe, Sicherheit und Sichermodus, REST-API, KI-Assistent, Sprachsteuerung, Sicherungen, Start mit Windows, Standardwerte, Ein-/Ausgänge … – lassen sich am iPad ändern und gelten **für den Server**. Auch der Mikrofon-Schalter der Sprachsteuerung ist am iPad da. **Ordner:** Wo der Hauptrechner den Windows-Explorer öffnen würde, bekommt ein Fernsteuer-Gerät den **OpenCue-Explorer** – ein großer Dialog für den OpenCue-Datenordner (Shows, Sicherungen, Protokolle, Scheinwerfer …): durchsuchen, herunterladen (ein Ordner als ZIP), hochladen, neuer Ordner, umbenennen, duplizieren, löschen. Er kommt nie aus dem Datenordner heraus. Derselbe Dialog (*Ordner wählen …*) sucht einen neuen Speicherort aus. **MIDI einlernen / mithören**, der **DMX-Eingang** und die **Firewall-Regel** (Windows fragt am Hauptrechner um Erlaubnis) gehen ebenfalls vom iPad aus. Nur wenige Dinge hängen **physisch am Hauptrechner**: sein Fenster (Vollbild), der **Sperrbildschirm** der Konsole (dort entsperren), die Taste einer **bestimmten Tastatur** aufnehmen, das **Mikrofon beim Diktieren** und der echte Windows-Explorer.
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

**Symbol:** Die App bekommt das OpenCue-Symbol und den Namen „OpenCue“ – auch über HTTPS. (Das Symbol ist in die Seite eingebettet; iOS holt es sonst bei einem selbst erstellten Zertifikat nicht ab und zeigt nur einen grauen Buchstaben.) Wenn sich das Symbol trotzdem nicht ändert, die App einmal vom Home-Bildschirm löschen und neu hinzufügen – iOS merkt sich das alte Symbol.

**Offline-Seite und Serverwahl (sichere Seite, HTTPS):** Ist der Server nicht erreichbar, zeigt die App statt einer Fehlerseite „**Server nicht erreichbar**“. Dort kannst du **Neu laden**, oder unter **Anderer Server** eine neue **Adresse oder IP**, den **Port** und **HTTPS** an / aus eintragen und **Verbinden** – hat der Rechner eine neue IP-Adresse, musst du die App nicht neu installieren. Die zuletzt benutzten Adressen stehen darunter zum Antippen. Reißt die Verbindung ab (WLAN weg, OpenCue beendet), erscheint der Hinweis „Verbindung wird wiederhergestellt“; nach 3 Sekunden mit dem Knopf „**Anderen Server wählen (7s)**“, dessen Zahl als **Countdown** herunterzählt; bei 0 öffnet sich die Offline-Seite von selbst und lädt OpenCue wieder, sobald der Server antwortet. Das gilt auch, wenn das WLAN da ist, der Rechner aber nicht antwortet – dann erscheint die Offline-Seite schon nach **etwa 1,5 Sekunden** statt eines weißen Bildschirms und blendet sich sofort wieder aus, sobald der Server doch antwortet. Öffnest du sie bewusst über den Knopf, bleibt sie stehen. Tipp: Der Name `opencue.local` findet den Rechner auch bei wechselnder IP.

**Wichtig am iPad – das Zertifikat einmal installieren:** Mit einem selbst erstellten Zertifikat kennt iOS nur die Ausnahme „Weiter trotz Warnung“ **im Safari-Tab**. Eine App vom Home-Bildschirm bleibt dann **weiß**, und der Service Worker (Offline-Seite) wird nicht zugelassen. Darum erstellt OpenCue eine eigene Zertifizierungsstelle („OpenCue Local CA“), die das https-Zertifikat unterschreibt. Du installierst sie **einmal** auf dem Gerät:

Die Schritte stehen als **Anleitungs-Seite** auf dem Server: *Einstellungen → Fernzugriff → Zertifikat für iPad und Browser* zeigt ihre Adresse und einen QR-Code (mit der iPad-Kamera scannen). Die Seite öffnet sich über **http://** ohne Anmeldung und folgt der Sprache des Geräts. Oben wählst du zwischen **iPad / iPhone** und **Android · Windows · macOS**. Für das iPad gibt es vier Schritte mit Merkzettel: **Laden → Installieren → Vertrauen → https öffnen**; erledigte Schritte kannst du abhaken (das merkt sich die Seite). **Wichtig: die Seite in Safari öffnen** – aus der App vom Home-Bildschirm, aus Chrome oder aus dem Browser einer anderen App lässt sich das Profil nicht installieren. „Einstellungen“ meint die **Einstellungen-App des iPads**, nicht eine Einstellung in Safari. Am Ende jeder Seite steht, wie du das Zertifikat **wieder entfernst** (iPad: Einstellungen → Allgemein → VPN & Geräteverwaltung → „OpenCue“ → Profil entfernen). In OpenCue steht dasselbe unter *Einstellungen → Fernzugriff → Zertifikat für iPad und Browser* (Kurzfassung zum Installieren und Entfernen). (Dafür muss der Zugang über HTTP an sein.)

Ab dann gilt https ohne Warnung, die App öffnet sich, der Service Worker und die Offline-Seite laufen – und das auch, wenn der Rechner eine **neue IP-Adresse** bekommt (OpenCue stellt nur das Server-Zertifikat neu aus, die Stelle bleibt). Die Stelle darf nur lokale Namen (`.local`, `localhost`) und private Adressen beglaubigen. Android / Windows / macOS: die Zertifikatsdatei (`opencue-ca.crt`) installieren und als vertrauenswürdige Stelle einrichten. Löschst du den Ordner `https` im Datenordner, entsteht eine neue Stelle – dann das Profil auf den Geräten erneut installieren.

**Einschränkung:** Installierbare Web-Apps und die Offline-Seite brauchen eine sichere Verbindung (HTTPS, am iPad mit dem installierten Zertifikat). Über einfaches `http://` funktioniert die App auf dem Home-Bildschirm, aber es gibt keine Offline-Seite, und das Gerät muss die Konsole erreichen, um etwas zu zeigen.

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

## 8. Sperren: Sperrbildschirm und Abmelden

Unter **Einstellungen → Sicherheit** gibt es den **Sichermodus** (standardmäßig aus, braucht das Passwort):

- **An der Konsole:** das **Schloss** in der Kopfleiste, **Strg+L** (änderbar unter *Steuerung → Tastenkürzel*) oder **Steuerung → Sperren** sperrt OpenCue. Eine gesperrte Konsole zeigt nur ein dunkles Passwortfenster – der Rest der Oberfläche ist verborgen, die Tastatur tut nichts, und die Konsole nimmt von diesem Fenster auch nichts mehr an (auch nicht an der Oberfläche vorbei). Ein Neuladen entsperrt **nicht**. **Die Show läuft weiter:** Cues, Effekte, MIDI, OSC, der Zeitplan und Fernzugriffs-Geräte arbeiten wie vorher. Fünf falsche Passwörter hintereinander legen das Entsperren eine Minute lang still. Das Passwort verlässt die Konsole nicht, solange sie gesperrt ist. Ein Neustart von OpenCue entsperrt.
- **An einem Fernzugriffs-Gerät:** das Schloss **meldet das Gerät ab**: die Sitzung endet, das *Passwort speichern* dieses Geräts wird gelöscht, und die Seite zeigt wieder die Anmeldung mit leerem Passwortfeld. Fernzugriffs-Geräte können weder das Passwort noch den Sichermodus ändern.
- **Automatisch sperren nach …** (1 bis 60 Minuten ohne jede Eingabe; standardmäßig aus): die Konsole sperrt sich selbst, Fernzugriffs-Geräte melden sich ab. Vorsicht bei einem Tablet, das nur anzeigt: dort die Einstellung aus lassen.

## 9. Einfache Steuerung und Bedienmodus (die Konsole jemand anderem geben)

- **Panel „Einfache Steuerung“** (*Bearbeiten → Panel hinzufügen → Eingabe*) ist die schlichte Schwester des Panels *Scheinwerfersteuerung* und nutzt das **ganze Panel** mit festen, prozentualen Feldern: Links (38 %) hat **jeder Scheinwerfer seine eigene Kachel** (Nummer, Name, Farbe und Helligkeit live), sortiert nach **Gruppen** (Klick auf den Gruppennamen = ganze Gruppe wählen; der Rest nach Typ; oben *Alle* / *Keine*); rechts **Helligkeit** (großer Fader, *Aus* / *Voll*), **Farbe** (Farbfeld – links nach rechts der Farbton, nach oben mehr Weiß – mit Farbknöpfen), **Bewegen** (**Joystick** mit Feder: schieben – je weiter, desto schneller; loslassen = Stopp; *Mitte*), **Zoom**, **Gobos** als Bilder, ein großer **Blackout**-Knopf und die **Looks**: *Regenbogen*, *Kreis* (Pan / Tilt), *Puls*, *Blitz* – fertige Standard-Effekte ohne jede Einstellung (nochmal tippen = aus, *Looks aus* nimmt alle weg; der Effekt wird beim ersten Mal automatisch in die Show übernommen). Ein Bedienelement, das die gewählten Lichter nicht haben, bleibt an seinem Platz, ist aber abgedunkelt. Bei einem **schmalen Panel** (unter etwa 720 px) wechselt es in einen **Kompaktmodus** mit einem Reiter je Bereich (*Lichter | Helligkeit | Farbe | Bewegen | Strahl | Looks*; Blackout bleibt sichtbar). Hier wird nichts an Gruppen oder Show geändert; Auswahl, Werte und Effekte sind die des ganzen Programms (Programmer, Cues, Effekt-Studio). Baue ein Layout nur mit diesem Panel (oder wenigen weiteren) für die Person, die bedienen soll.
- **Bedienmodus** (*Ansicht → Bedienmodus …* oder der Joystick-Knopf in der Kopfleiste; braucht das Passwort, *Einstellungen → Sicherheit*): Dieses Gerät kann nur noch **bedienen**, was auf dem Bildschirm steht – keine Menüs, keine Kopfleiste, keine Einstellungen oder anderen Dialoge, keine Tastenkürzel (Tippen in ein Textfeld geht weiter), kein Verschieben oder Umbauen von Panels, kein Wechsel von Layout oder Show. Verlassen geht über das kleine **Schloss unten rechts** und das Passwort – oder mit **Strg+L**. Gestartet wird er nur über das Menü oder den Knopf (kein Tastenkürzel). **Befehle** (Befehlszeile, Tasten, Widgets) führt der Server im Bedienmodus nur aus, wenn sie **bedienen**; was die Show verändert (*Store, Update, Delete, Move, Label, Set*, Cue-Zeiten, Cue-Listen anlegen / umbenennen / löschen), wird abgelehnt – auch in einer Befehlskette. **An der Konsole ist die Sprachsteuerung im Bedienmodus aus** (das Mikrofon bleibt zu) und geht danach wieder an, wenn sie eingeschaltet ist. Der **Server setzt das durch**: Von einem Gerät im Bedienmodus nimmt er nur Bedien-Nachrichten an (wählen, Werte setzen, Cues, Presets, Timecode, Befehlszeile …); Programmier-, Layout-, Show- und Einstellungs-Nachrichten werden verworfen, schreibende Anfragen mit `423` beantwortet. Neuladen verlässt den Modus nicht. Er gilt an der Konsole und an jedem Fernzugriffs-Gerät für sich (ein iPad mit der App im Bedienmodus übergeben); ein Neustart von OpenCue beendet ihn. Fünf falsche Passwörter hintereinander legen das Verlassen eine Minute still.
- **Gut zu wissen:** Die Befehlszeile kann, wenn du sie in dieses Layout legst, jeden Befehl ausführen – lass sie in Gast-Layouts weg. Tasten einer eigenen Zusatz-Tastatur (*Eigene Tastaturbelegung*, gerätespezifisch) und MIDI-/OSC-Geräte arbeiten weiter: Sie gehören zur Show, nicht zum Bildschirm.

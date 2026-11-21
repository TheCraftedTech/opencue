# Eigene Scheinwerfer (Editor)

Mit dem Editor legst du Geräte an, für die es keine passende GDTF-Datei gibt – eine Nebelmaschine, einen einfachen Dimmer, ein RGB-Par, einen Moving Head. Das Ergebnis ist eine **echte GDTF-Datei** (Format GDTF 1.2, aufgebaut wie die Dateien von GDTF Share). Du brauchst dafür **kein Konto** bei GDTF Share.

---

## 1. Öffnen

**Bibliothek → Scheinwerfer-Bibliothek… → „Eigener Scheinwerfer…“.** Das Fenster ist so groß wie die Bibliothek und hat drei Reiter: **Allgemein**, **Modi & Kanäle**, **Bild & 3D**.

- Einen eigenen Typ später ändern: in der Liste der installierten Typen auf **Bearbeiten** (nur bei Typen, die mit dem Editor gebaut wurden, Kennzeichen „Eigen · ungeprüft“).
- Einen vorhandenen Typ als Grundlage nehmen (**aus einem anderen Scheinwerfer laden**): im Editor oben im Reiter *Allgemein* die Auswahl **„Aus vorhandenem Scheinwerfer übernehmen“**, oder in der Bibliothek auf der Karte **Mehr → Kopie bearbeiten**. Übernommen werden Stammdaten, Modi, Kanäle, Funktionsnamen, Bereiche und das Profilbild. **Nicht** übernommen werden Räder (Gobos, Farbräder), die Geometrie und 3D-Teile; der Editor sagt dir, was weggefallen ist.

---

## 2. Allgemein

| Feld | Bedeutung |
|---|---|
| Hersteller, Name | Pflicht. Daraus wird der Dateiname `Hersteller@Name@Eigen.gdtf`. Gibt es den Typ schon, meldet der Editor es. |
| Kurzname | Optional, höchstens 8 Zeichen. |
| Kategorie | Moving Head, LED-Leiste, Par, Dimmer, Strobe, Effekt, Sonstiges – oder „Automatisch“ (wird aus den Kanälen erkannt). Nach der Kategorie lässt sich in der Bibliothek filtern. |
| Gewicht, Beschreibung | Optional. |
| Stichwörter | Eingeben und **Enter** drücken. Die Bibliothek durchsucht sie mit (z. B. „Nebel“, „Outdoor“, „12 V“). |
| Vorlage | Nur bei neuen Typen: Nebelmaschine, Dimmer, RGB, RGB + Dimmer, Moving Head. |

---

## 3. Modi & Kanäle

Ein **Modus** ist eine Kanalbelegung (viele Geräte haben mehrere, z. B. „3 Kanal“ und „8 Kanal“). Über **+ Modus (Kopie)** legst du einen weiteren als Kopie des gewählten an; den Namen änderst du oben rechts.

Je **Kanal**:

- **Attribut** – was der Kanal bewirkt. Die Liste ist nach Helligkeit, Farbe, Position, Strahl, Effekten (Nebel, Haze, Lüfter) und Steuerung sortiert. Ganz unten, getrennt: **Eigener Name …** für alles, was nicht in der Liste steht (z. B. „Bubbles“).
- **Beschriftung** – frei, z. B. „Nebelmenge“. Sie erscheint im DMX-Direct-Detailfeld.
- **8 / 16 Bit** – ein 16-Bit-Kanal belegt zwei DMX-Adressen (Grob + Fein).
- **Standardwert** (0–255) – der Wert, den das Gerät ohne Ansteuerung hat.
- **Bereiche** – benannte Stufen, z. B. ab 0 „Aus“, ab 10 „Nebel“. Der erste Bereich beginnt immer bei 0, jeder weitere endet vor dem Anfang des nächsten. Bei Pan, Tilt und Zoom gibst du zusätzlich den Winkelbereich in Grad an.

Mit den Pfeilen änderst du die Reihenfolge; die DMX-Adressen werden daraus berechnet (links in der Zeile).

### CSV-Import

**CSV importieren…** liest eine Kanalliste: eine Zeile je Kanal, mit Kopfzeile. Spalten (beliebige Reihenfolge, getrennt durch `;`, `,` oder Tab): `Attribut`, `Beschriftung`, `Bit`, `Standard`, `Bereiche`. Bereiche schreibst du als `0 Aus; 10 Nebel` oder `0-9 Aus; 10-255 Nebel` – enthält die Zelle ein Trennzeichen, setze sie in Anführungszeichen:

```
Attribut;Beschriftung;Bit;Standard;Bereiche
Fog1;Nebelmenge;8;0;"0 Aus; 10 Nebel"
Control1;Lüfter;8;0;"0-9 Aus; 10-255 An"
```

---

## 4. Bild & 3D

- **Profilbild** – beliebiges Bild; es wird als PNG (höchstens 512 Pixel) in die Datei geschrieben und erscheint in der Bibliothek.
- **3D-Modell** – optional eine `.glb`-, `.3ds`-, `.stl`- oder `.obj`-Datei (höchstens 25 MB, höchstens 250 000 Dreiecke; STL und OBJ werden in GLB umgewandelt) für **feststehende** Geräte; die Maße in Metern bestimmen die Größe in der 3D-Bühne. Moving Heads (Pan/Tilt) bekommen Sockel, Bügel und Kopf als Standardteile.

---

## 5. Die Datei weitergeben

Jede Karte in der Bibliothek hat **Mehr → Datei exportieren (.gdtf)** und **Im Ordner zeigen** (nur am Rechner des Programms). Die Datei lässt sich kopieren und auf einem anderen Rechner über **Import GDTF-Datei…** einbauen – oder in jeder anderen GDTF-Software öffnen. Die Beschreibung des Editors steckt als Zusatzdatei darin; andere Programme ignorieren sie.

---

## 6. Gut zu wissen

- Eigene Typen sind **ungeprüft**: Prüfe die Kanalbelegung am echten Gerät.
- Wird ein Typ geändert, den die Show benutzt, gelten die Änderungen sofort. Ändert sich dabei die **Kanalzahl eines benutzten Modus** (oder wird so ein Modus gelöscht oder umbenannt), zeigt der Editor einen **Hinweis** – er verhindert nichts; prüfe danach die DMX-Adressen.
- **Abbrechen fragt nach:** Hast du etwas geändert, öffnet *Abbrechen*, das × und Escape den Dialog „Ungespeicherte Änderungen“ (*Weiter bearbeiten*, *Änderungen verwerfen* oder *Speichern*). Ohne Änderung schließt der Editor sofort.
- **Löschen fragt nach:** Modus, Kanal, Bereich, Profilbild und 3D-Modell werden erst nach einer Rückfrage entfernt.
- Grand Master und Blackout wirken nur auf den **Dimmer** (bzw. die Farbe ohne Dimmer-Kanal) – ein Nebelkanal läuft davon unberührt weiter.
- Nebel, Haze und Co. bedienst du in der Scheinwerfersteuerung im Reiter **DMX Direkt**. Hover über der Beschriftung, Klick auf die Beschriftung oder Rechtsklick auf einen Fader zeigt Funktionsnamen und Bereiche des Kanals.

# defaults/ - mitgelieferte Vorlagen

Dieser Ordner gehoert zum Programm und wird zur Laufzeit **nur gelesen** (bei einer installierten Fassung steckt er im Programmpaket).
Beim ersten Start kopiert OpenCue die Vorlagen einmalig in den Benutzerordner (`%LOCALAPPDATA%\OpenCue`); danach gehoert das Kopierte dem Benutzer.

| Ordner | Inhalt | Ziel im Benutzerordner |
|---|---|---|
| `effects/` | Effekt-Skripte (`.fx`, 60 Vorlagen für Dimmer, Farbe, Position, Zoom, Fokus und Gobo; siehe `static/help/effect-studio.de.md` / `.en.md`) | `effects/` |
| `layouts/` | Beispiel-Layouts (`.json`), sortiert nach Dateiname - zur Zeit nur **Default_1** | `layouts/` |
| `fixtures/` | Standard-Scheinwerfer (GDTF-Dateien `.gdtf`): **zur Zeit leer** - aus rechtlichen Gründen liefert OpenCue keine GDTF-Share-Dateien mit (siehe unten); der Mechanismus bleibt für Dateien, deren Weitergabe erlaubt ist | `fixtures/` |
| `showfiles/` | **Demo-Shows** (`.json`, in OpenCue gespeichert): zur Zeit **Default_1** (5 Dimmer vom eingebauten Typ *Generic Dimmer*, Cue-Liste mit 2 Cues, ohne 3D-Bühne). Eine Demo darf nur Scheinwerfer-Typen nennen, die es immer gibt (die drei eingebauten) oder die in `fixtures/` mitgeliefert werden | `showfiles/` |

Gemeinsame Regeln: einmalig pro Datenordner (Markierung `.defaults_seeded`), nie etwas überschreiben, was der Benutzer löscht, kommt nicht zurück; fehlen die Vorlagen, wird nichts markiert.
Die drei eingebauten Geräte *Generic Dimmer*, *Generic RGBW LED Par* und *Generic Moving Head Spot 16ch* (ohne 3D-Modell) gibt es immer zusätzlich (`app/fixture_manager.py`);
eine GDTF-Datei mit genau diesem Namen ersetzt das eingebaute Gerät.

**Eigene Layouts als Vorlagen übernehmen:** Layouts in OpenCue bauen und als `Standard_1`, `Standard_2` … speichern, dann `venv\Scripts\python.exe packaging\export_default_layouts.py --write --replace`
(ohne `--write` nur Vorschau). Das Werkzeug wandelt sie in Vorlagen um (Panel-Ids und Standardwerte werden weggelassen) und ersetzt die alten.

## Layout-Vorlage (`layouts/*.json`)

```json
{
  "name": {"de": "Anzeigename", "en": "Display name"},
  "panels": [
    {"type": "cuelist", "x": 0.0, "y": 0.0, "width": 100.0, "height": 100.0}
  ]
}
```

- `name`: Text oder je Sprache (`de`, `en`); fehlt die Sprache, gilt `en`, sonst der erste Eintrag. Der Name wird zum Dateinamen des Layouts.
- `panels`: je Panel `type`, `x`, `y`, `width`, `height` (Prozent der Arbeitsflaeche). Weitere Panel-Felder (z. B. `module_config`) sind erlaubt;
  Farben und Schatten kommen sonst aus den Panel-Standards der App, die Panel-Id wird neu vergeben.

## Scheinwerfer und GDTF Share (warum `fixtures/` leer ist)

Immer vorhanden sind die drei **eingebauten Geräte** *Generic Dimmer*, *Generic RGBW LED Par* und *Generic Moving Head Spot 16ch* (ohne 3D-Modell, Teil des Programms, `app/fixture_manager.py`).
Weitere Scheinwerfer lädt der Benutzer selbst aus der Scheinwerfer-Bibliothek (Reiter *Online*, GDTF Share).

Die Nutzungsbedingungen von GDTF Share (https://gdtf-share.com/landing/pages/termsAndConditions.php, gelesen am 2026-10-19) geben die Rechte an hochgeladenen Dateien den jeweiligen Urhebern/Herstellern, erlauben das Herunterladen
zur eigenen Verwendung, verbieten das Verändern und Kopieren über das Erlaubte hinaus und verlangen für kommerzielle Nutzung der Inhalte eine Lizenz. Eine ausdrückliche Erlaubnis, Dateien in einem anderen Programm mitzuliefern, steht dort nicht.
Darum liegen hier keine GDTF-Share-Dateien. Soll später ein Gerät (z. B. der Eurolite TMH-S400) mitgeliefert werden: die Erlaubnis des Herstellers/Hochladers (bzw. von GDTF Share, info@gdtf-share.com) einholen, die Datei
nach `fixtures/` legen und den Hinweis in `packaging/license-extra/gdtf-share.txt` anpassen.

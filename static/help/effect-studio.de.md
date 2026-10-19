# Effekt-Studio – Anleitung

Ein **Effekt** ist ein kleines Programm, das Licht über die Zeit verändert: ein Dimmer, der pulsiert, eine Farbe, die durch den Regenbogen wandert, ein Kopf, der einen Kreis fährt. Effekte schreibst du im **Effekt-Studio** (Panel *Effekt-Studio*) in einer Sprache, die wie C++ oder Arduino aussieht: mit Variablen, `if`, `for`, `while` und eigenen Funktionen. Du musst kein Programmierer sein – die Vorlagen unter **Neu...** laufen sofort und sind zum Abschauen gedacht.

Diese Anleitung ist auch im Studio über den Knopf **Hilfe** erreichbar.

---

## 1. Das Prinzip in einer Minute

- Ein **Skript** ist eine Textdatei (`.fx`). Es beschreibt, was in **einem Durchlauf** passiert. Dieser Durchlauf heißt `loop()` und wird **`#RATE`-mal pro Sekunde** ausgeführt (1 bis 40, Vorgabe 40).
- In jedem Durchlauf rechnet das Skript neue **Ausgabewerte** aus: `dimmer`, oder `r`/`g`/`b`, oder `pan`/`tilt`. Welche, bestimmt die **Kategorie** (`#CATEGORY`).
- Zwischen zwei Durchläufen **bleibt der Ausgang stehen**. Bei 10 Durchläufen pro Sekunde ändert sich der Wert also zehnmal pro Sekunde – gewollt, so baust du Schritt-Effekte.
- Das Skript läuft **für jeden Scheinwerfer einzeln**. Jeder kennt seine Nummer (`index`) und die Gesamtzahl (`count`); damit verteilst du Wellen und Lauflichter über mehrere Scheinwerfer.
- Variablen, die du außerhalb von `loop()` anlegst, **bleiben zwischen den Durchläufen erhalten**: Zähler, Zustände, Timer.

```
#NAME Sinus
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05

loop() {
  dimmer = 50 + 50 * sin(2 * PI * speed * elapsed);
}
```

Das ist ein kompletter Effekt: Der Dimmer schwingt mit `speed` Wellen pro Sekunde zwischen 0 und 100 %.

---

## 2. Befehlsübersicht (Spickzettel)

Alle Befehle auf einen Blick. Die Kapitel danach erklären sie mit Beispielen.

| Bereich | Befehle |
|---|---|
| Kopfzeilen | `#NAME`, `#DESCRIPTION`, `#CATEGORY dimmer` / `color` / `position`, `#RATE 1` bis `40`, `#VAR name Slider` / `NumberInput` / `ColorPicker` / `Internal ...` |
| Aufbau | `setup() { }` (einmal beim Start), `loop() { }` (`#RATE`-mal pro Sekunde) |
| Typen | `float` (`double`), `int` (`long`, `short`, `byte`), `bool` (`boolean`), `void`, `const` |
| Zuweisen | `x = 1;`, `x += 1;` (auch `-=` `*=` `/=` `%=`), `x++;`, `x--;` |
| Verzweigen | `if (...) { } else if (...) { } else { }`, `bedingung ? a : b` |
| Schleifen | `for (int i = 0; i < n; i++) { }`, `while (...) { }`, `do { } while (...);`, `break;`, `continue;` |
| Funktionen | `float name(float x) { return x * 2; }`, `void name() { }`, `return wert;` |
| Rechnen | `+ - * / %`, `== != < <= > >=`, `&& \|\| !` |
| Kommentare | `// bis zum Zeilenende`, `/* über mehrere Zeilen */` |
| Ausgaben | Dimmer: `dimmer` · Farbe: `r`, `g`, `b` oder `hsv(h, s, v);` · Position: `pan`, `tilt` · Zoom: `zoom` · Fokus: `focus` · Gobo: `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin` |
| Zeit | `t` (gemeinsame Systemzeit), `elapsed` (seit Effektstart), `dt`, `tick` (`loop_count`), `rate` |
| Scheinwerfer | `index`, `count`, `phase` (= `index / count`), `slots`, `slots2` (Anzahl der Gobos von Rad 1 und Rad 2) |
| Konstanten | `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false` |
| Mathe | `sin` `cos` `tan` `asin` `acos` `atan` `atan2` `sqrt` `pow` `exp` `log` `abs` `sign` `min` `max` `floor` `ceil` `round` `fract` `mod` |
| Hilfsfunktionen | `constrain(x, lo, hi)` `map(x, inMin, inMax, outMin, outMax)` `lerp(a, b, k)` `smoothstep(e0, e1, x)` `radians(g)` `degrees(r)` |
| Wellenformen | `saw(x)` `tri(x)` `square(x)` `square(x, duty)` – je 0 bis 1 pro Periode |
| Zufall, Farbe, Gobo | `random()` `random(max)` `random(min, max)` · `hsv(h, s, v)` · `slot(n)` `slot(n, rad)` |

---

## 3. Das Studio bedienen

| Bereich | Was er tut |
|---|---|
| **Öffnen...** | Dialog mit allen Effekten, **Lieblinge zuerst** (Suche, Kategorie, Durchläufe pro Sekunde, Herkunft; mitgelieferte Effekte tragen die Marke **Standard**). Die Liste scrollt. Klick auf eine Zeile öffnet sie, der **Stern** macht einen Effekt zum Liebling (gilt für alle Geräte), der Papierkorb löscht ihn aus dem Benutzerordner. Unten: **Standard-Effekte wiederherstellen**. |
| **Neu...** | Dialog: zuerst die **Kategorie** (Dimmer, Farbe, Position, Zoom, Fokus, Gobo) oder **Leere Datei**, dann eine **Vorlage** (vorgewählt ist *Leer*), dann die **Durchläufe pro Sekunde**. *Leere Datei* erzeugt einen völlig leeren Editor ohne Kopfzeilen. **Erstellen** lädt das Ergebnis in den Editor – gespeichert wird erst, wenn du es sagst. |
| **Speichern** | Speichert in die Datei des Effekts. Ein neuer Effekt fragt nach dem Dateinamen. Ein Punkt neben dem Namen zeigt ungespeicherte Änderungen. Tastatur: **Strg+S** im Text (speichert den Effekt, nicht die Show). |
| **Speichern unter...** | Neuer Dateiname. Gibt es ihn schon, fragt das Studio, ob es überschrieben werden soll. |
| **Löschen** | Löscht den geladenen Effekt (nur aus dem Benutzerordner; vorher wird gefragt). Danach ist der Editor leer. Ist der Knopf grau, zeigt ein Hinweis warum (noch nicht gespeichert, oder nicht im Benutzerordner). |
| **Hilfe** | Öffnet diese Anleitung. Der Spickzettel (Kapitel 2) listet alle Befehle. |
| **Vorschau** | Blendet die Vorschau rechts ein oder aus. |
| **Statusleiste** | Grün = in Ordnung. Rot = Fehler mit Zeilennummer. Rechts: Zeile und Spalte der Schreibmarke. |

Im Editor sind Schlüsselwörter, Typen, Zahlen, Kommentare, Funktionen, Systemvariablen, Ausgaben und deine Regler (`#VAR`) **farbig** hervorgehoben. **Enter** übernimmt die Einrückung der Zeile (nach `{` zwei Leerzeichen mehr), **Tab** rückt zwei Leerzeichen ein.

### Die Vorschau

Die Vorschau rechnet dein Skript beim Tippen **ohne Scheinwerfer** durch – mit genau den Durchläufen pro Sekunde, die du mit `#RATE` gewählt hast – und zeichnet das Ergebnis:

- **Dimmer:** eine Kurve je Scheinwerfer, 0 bis 100 %.
- **Farbe:** R/G/B als Kurven und darunter ein **Farbstreifen** je Scheinwerfer.
- **Position:** Pan und Tilt als Kurven und die **Bahn** im Pan/Tilt-Feld.

Standard: **1 Scheinwerfer, 2 Sekunden**. Oben stellst du die Zahl der Scheinwerfer (1 bis 16) und die Dauer (1 bis 20 s) ein; mehrere Scheinwerfer zeigen, wie `index`, `count` und `phase` die Wellen versetzen. Darunter stehen **Regler für deine `#VAR`-Parameter** – ziehen, und die Kurve folgt sofort. Bei niedriger Rate (bis 20 Durchläufe pro Sekunde) zeichnet die Vorschau Treppen, bei bis zu 10 zusätzlich die einzelnen Punkte.

Hat das Skript einen Fehler, bleibt die Vorschau als **letzter fehlerfreier Stand blass** stehen, die Fehlerzeile ist rot markiert und die Statusleiste nennt Zeile und Meldung.

---

## 4. Dein erster Effekt

1. **Neu...** → Kategorie **Dimmer** → Vorlage **Sinus** → **Erstellen**.
2. In der Vorschau siehst du zwei Wellen in zwei Sekunden (`speed` ist 1).
3. Schiebe `speed` auf 2: doppelt so schnell. Setze in der Vorschau 3 Scheinwerfer und schiebe `spread` auf 0,33: die Wellen sind gegeneinander versetzt.
4. Ändere im Text `0.5 + 0.5 * sin(...)` und beobachte die Kurve.
5. **Speichern** (Strg+S), Dateiname eingeben. Der Effekt steht jetzt in der Effekt-Liste des Programmers.

---

## 5. Aufbau eines Skripts

Ein Skript besteht aus drei Teilen:

```
#NAME Mein Effekt                          // 1. Kopfzeilen (beginnen mit #)
#CATEGORY dimmer
#RATE 25
#VAR speed Slider 1 0.1 8 0.1

float level = 0;                           // 2. Variablen und Funktionen (optional)

setup() {                                  //    setup(): einmal beim Start des Effekts (optional)
  level = 50;
}

loop() {                                   // 3. loop(): Pflicht, wird #RATE-mal pro Sekunde ausgeführt
  dimmer = level;
}
```

### Kopfzeilen

| Zeile | Bedeutung |
|---|---|
| `#NAME Text` | Anzeigename im Programm. Ohne ihn gilt der Dateiname. |
| `#DESCRIPTION Text` | Kurzbeschreibung (erscheint in der Effekt-Auswahl und im Öffnen-Dialog). |
| `#CATEGORY dimmer` / `color` / `position` | **Pflicht.** Was der Effekt steuert. |
| `#RATE n` | Wie oft pro Sekunde `loop()` läuft: ganze Zahl von **1 bis 40**. Ohne Angabe 40 – der Takt der DMX-Ausgabe. |
| `#VAR ...` | Ein **Regler** (siehe Abschnitt 9) oder eine interne Variable. |

---

## 6. Zeit und Rate

**Die wichtigste Regel:** `loop()` läuft genau `#RATE`-mal pro Sekunde – egal wie schnell der Rechner ist. Deshalb kannst du **exakt in Sekunden denken**.

| Name | Bedeutung |
|---|---|
| `elapsed` | **Sekunden seit dem Start des Effekts** auf diesem Scheinwerfer. Beginnt bei 0. Genau `tick / rate`. Damit programmierst du „in Sekunde 3 soll das passieren“. |
| `t` | Gemeinsame Systemzeit in Sekunden. Für **alle** Effekte gleich – Effekte, die mit `t` rechnen, bleiben zueinander **synchron**, auch wenn sie zu verschiedenen Zeiten gestartet wurden. |
| `tick` | Nummer des Durchlaufs, beginnt bei 0. |
| `rate` | Durchläufe pro Sekunde (der Wert aus `#RATE`). |
| `dt` | Zeit zwischen zwei Durchläufen in Sekunden (`1 / rate`). |

Welche Rate wähle ich?

- **40** (Vorgabe): weichste Kurven – für Wellen, Kreise, Überblendungen.
- **10 bis 25**: genügt für Farbwechsel und Effekte, die ohnehin stufig sind.
- **1 bis 5**: Schritt-Effekte (ein Schritt pro Sekunde, Lauflicht „klick-klick“), sparsam im Rechenaufwand.

**Konvention „speed“:** Die mitgelieferten Effekte und alle Vorlagen haben einen Regler `speed` mit der Vorgabe **1**: Das ist **eine Periode pro Sekunde**. `sin(2 * PI * speed * elapsed)` ist eine Welle pro Sekunde bei `speed = 1`.

### In der Sekunde X ...

```
#NAME Ablauf
#CATEGORY dimmer
#RATE 20
#VAR laenge Slider 8 2 30 1       // Dauer des Ablaufs in Sekunden

loop() {
  float s = elapsed % laenge;     // Zeit im Ablauf; springt nach "laenge" Sekunden auf 0
  if (s < 2) {
    dimmer = map(s, 0, 2, 0, 100);                 // Sekunde 0 bis 2: einblenden
  } else if (s < 5) {
    dimmer = 100;                                  // Sekunde 2 bis 5: voll
  } else {
    dimmer = 100 * (1 - (s - 5) / (laenge - 5));   // danach ausblenden
  }
}
```

---

## 7. Die Sprache

Alles ist eine **Zahl**. Es gibt die Typen `float` (Kommazahl, auch `double`), `int` (ganze Zahl, auch `long`, `short`, `byte`) und `bool` (0 oder 1, auch `boolean`). `true` und `false` sind 1 und 0.

### Variablen

```
float x = 1.5;          // Kommazahl (Punkt, kein Komma)
int n = 3;              // ganze Zahl: beim Zuweisen wird abgeschnitten (7.9 wird 7)
bool an = true;         // 0 oder 1: jeder Wert ungleich 0 wird 1
const float K = 0.25;   // Konstante, nicht änderbar
float a = 1, b2 = 2;    // mehrere in einer Zeile
```

- **Außerhalb** von Funktionen angelegte Variablen sind **global** und **behalten ihren Wert** von Durchlauf zu Durchlauf. Ihr Anfangswert gilt beim Start des Effekts (und danach nur dann, wenn du `setup()` schreibst, dort neu zu setzen).
- **Innerhalb** von `{ }` angelegte Variablen sind **lokal**: sie gelten bis zur schließenden Klammer und beginnen bei jedem Durchlauf neu.
- Wer einer **nicht deklarierten** Variablen etwas zuweist (`zaehler = zaehler + 1;`), legt automatisch eine globale `float`-Variable an – so liefen ältere Skripte. Besser: deklarieren.
- Die Namen `t`, `elapsed`, `dt`, `tick`, `rate`, `index`, `count`, `phase`, `dimmer`, `r`, `g`, `b`, `pan`, `tilt`, `PI` und alle Schlüsselwörter und Funktionsnamen sind vergeben.

### Rechnen und Vergleichen

| Zeichen | Bedeutung |
|---|---|
| `+ - * /` | Grundrechenarten. Division durch 0 ergibt 0. |
| `%` | Rest (auch bei Kommazahlen): `5.5 % 2` ist 1.5. |
| `== != < <= > >=` | Vergleiche; Ergebnis 1 (wahr) oder 0 (falsch). |
| `&& \|\| !` | Und, Oder, Nicht. Bedingungen sind wahr, wenn sie ungleich 0 sind. |
| `bedingung ? a : b` | Auswahl: `a`, wenn die Bedingung wahr ist, sonst `b`. |
| `= += -= *= /= %=` | Zuweisung; `x += 2;` ist `x = x + 2;`. |
| `x++;` `x--;` | Um 1 erhöhen / verringern. |

### Verzweigen und wiederholen

```
if (x > 10) {                 // wenn ...
  dimmer = 100;
} else if (x > 5) {           // sonst wenn ...
  dimmer = 50;
} else {                      // sonst
  dimmer = 0;
}

for (int i = 0; i < 5; i++) { // zähle i von 0 bis 4
  summe += i;
}

while (n > 0) { n--; }        // solange n größer als 0 ist

do { n++; } while (n < 3);    // mindestens einmal ausführen

break;                        // Schleife sofort verlassen
continue;                     // zum nächsten Schleifendurchlauf
```

Klammern `{ }` sind bei einer einzelnen Anweisung optional (`if (a) b = 1;`), mit Klammern ist es aber übersichtlicher. `switch` gibt es nicht – nimm `if` / `else if`.

### Eigene Funktionen

```
float welle(float x) {                    // Rückgabetyp, Name, Parameter
  return 0.5 + 0.5 * sin(2 * PI * x);     // return liefert den Wert zurück
}

void setzeHell(float v) {                 // void: liefert nichts
  dimmer = v;
}

loop() {
  setzeHell(100 * welle(speed * elapsed));
}
```

Funktionen dürfen vor oder nach der Stelle stehen, an der sie aufgerufen werden, und sich selbst aufrufen (Rekursion, begrenzt). Parameter sind lokal; globale Variablen und Ausgaben (`dimmer` ...) sind überall erreichbar.

### Kommentare

```
// Rest der Zeile ist Kommentar
/* mehrere
   Zeilen */
```

### Grenzen

- Ein Durchlauf darf höchstens **60 000 Schleifendurchläufe und Funktionsaufrufe** machen; eine Endlosschleife bricht mit der Meldung „Endlosschleife?“ ab.
- Ein Effekt, der **einen Fehler wirft oder mehr als 50 ms pro Durchlauf braucht**, wird abgeschaltet („ruht“), damit er die anderen nicht aufhält. Speichere das Skript neu, dann läuft er wieder.
- Es gibt nur Zahlen: keine Texte, Listen (Arrays) oder Zeiger.

---

## 8. Ausgaben je Kategorie

Das Skript schreibt sein Ergebnis in Variablen, die zur Kategorie passen:

| `#CATEGORY` | Ausgaben | Bereich |
|---|---|---|
| `dimmer` | `dimmer` | 0 bis 100 (%) |
| `color` | `r`, `g`, `b` | 0 bis 255 |
| `position` | `pan`, `tilt` | 0 bis 100 (%), 50 ist die Mitte. Hat das Gerät Fein-Kanäle (16 Bit), werden Nachkommastellen genutzt: `pan = 33.3333;` stellt genauer ein als `pan = 33;` |
| `zoom` | `zoom` | 0 bis 100 (%) – 0 und 100 sind die Enden des Zoom-Kanals (weit/eng, je nach Gerät) |
| `focus` | `focus` | 0 bis 100 (%) – die Enden des Fokus-Kanals (nah/fern) |
| `gobo` | `gobo` | 0 bis 100 (%) – die Stellung des Gobo-Kanals von Rad 1; Gobos wählst du am besten mit `slot(n)` (siehe unten) |
| `gobo` | `gobo_spin` | 0 bis 100 (%) – Drehung bzw. Pendeln von Rad 1 (der Bereich bestimmt Richtung und Tempo, je nach Gerät) |
| `gobo` | `gobo2` | 0 bis 100 (%) – Gobo-Rad 2 (nur Geräte mit zweitem Rad), Gobos mit `slot(n, 2)` |
| `gobo` | `gobo2_spin` | 0 bis 100 (%) – Drehung von Rad 2 |

Werte außerhalb des Bereichs werden begrenzt. **Ein Effekt steuert nur die Ausgaben, denen sein Skript irgendwo einen Wert zuweist** (`hsv()` zählt als `r`, `g`, `b`; bei Farbe immer alle drei). Schreibt ein Skript nur `pan`, bleibt `tilt` unberührt: Der Kanal läuft nicht mit, und im Programmer ist nur der Pan-Fader gesperrt – Tilt kannst du weiter von Hand einstellen. Wird ein Ausgang in einem Durchlauf nicht erreicht (z. B. weil die Zuweisung in einem `if` steht), steht er in diesem Durchlauf auf 0 (`pan`/`tilt`: Mitte, 50). Gibt es am Gerät den Kanal nicht, wird die Ausgabe still ignoriert. Ausgaben einer anderen Kategorie werden ignoriert. Mit `hsv(h, s, v);` setzt du `r`, `g`, `b` aus Farbton, Sättigung und Helligkeit (je 0 bis 1) in einem Schritt.

Achtung: Ausgaben gelten **nur für den aktuellen Durchlauf** – wer sich einen Wert merken will, legt dafür eine eigene Variable an (`float level = 0;` ... `dimmer = level;`).

---

## 9. Regler: `#VAR`

```
#VAR <name> <Typ> <Vorgabe> [min max schritt]
```

| Typ | Vorgabe | Bedienelement |
|---|---|---|
| `Slider` | Zahl, dazu `min max schritt` | Schieberegler |
| `NumberInput` | Zahl, dazu `min max schritt` | Zahlenfeld |
| `ColorPicker` | Hex-Farbe, z. B. `#ff8800` | Farbwähler; im Skript als `name_r`, `name_g`, `name_b` (0 bis 255) |
| `Internal` | Zahl | kein Regler – eine globale Variable mit Anfangswert (wie `float name = 0;`) |

```
#VAR speed Slider 1 0.05 8 0.05          // Perioden pro Sekunde
#VAR size Slider 100 0 100 1             // Stärke in %
#VAR farbe ColorPicker #00aaff           // farbe_r, farbe_g, farbe_b
```

Die Regler erscheinen im Dialog **Effekt erstellen / bearbeiten** und in der Studio-Vorschau. Im Skript sind sie **nur lesbar**.

---

## 10. Systemvariablen

| Name | Bedeutung |
|---|---|
| `t` | Gemeinsame Systemzeit in Sekunden (hält Effekte synchron). |
| `elapsed` | Sekunden seit dem Start dieses Effekts auf diesem Scheinwerfer. |
| `dt` | Sekunden zwischen zwei Durchläufen (`1 / rate`). |
| `tick` | Nummer des Durchlaufs (0, 1, 2 ...). Auch `loop_count`. |
| `rate` | Durchläufe pro Sekunde. |
| `index` | Nummer dieses Scheinwerfers in der Auswahl-Reihenfolge des Programmers (0, 1, 2 ...). |
| `count` | Anzahl der Scheinwerfer, auf denen der Effekt läuft. |
| `phase` | `index / count`: gleichmäßiger Versatz über die Auswahl (0 bis fast 1). |
| `slots` | Anzahl der festen Gobos von Rad 1 (nur in der Kategorie `gobo`, sonst 0). Die Vorschau rechnet mit 8 Gobos. |
| `slots2` | Dasselbe für Rad 2 (0, wenn das Gerät nur ein Rad hat). |

Die Auswahl-Reihenfolge ist die Reihenfolge, in der du die Scheinwerfer angewählt hast.

---

## 11. Funktionen

| Funktion | Bedeutung |
|---|---|
| `sin(x)`, `cos(x)`, `tan(x)` | Winkel im Bogenmaß (Vollkreis = `2 * PI`). |
| `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y, x)` | Umkehrfunktionen. |
| `sqrt(x)`, `pow(x, y)`, `exp(x)`, `log(x)` | Wurzel, Potenz, e-Funktion, natürlicher Logarithmus. Ungültige Eingaben ergeben 0. |
| `abs(x)`, `sign(x)` | Betrag; Vorzeichen (-1, 0, 1). |
| `min(a, b)`, `max(a, b)` | Kleinerer bzw. größerer Wert. |
| `floor(x)`, `ceil(x)`, `round(x)` | Abrunden, Aufrunden, Runden. |
| `fract(x)` | Nachkommaanteil: `fract(2.25)` ist 0.25. Nützlich für „Position in der Periode“. |
| `mod(a, b)` | Rest, der nie negativ ist (anders als `%` bei negativen Zahlen). |
| `constrain(x, low, high)` | Begrenzt `x` auf den Bereich. |
| `map(x, inMin, inMax, outMin, outMax)` | Rechnet `x` von einem Bereich in einen anderen um (wie in Arduino). |
| `lerp(a, b, k)` | Linear von `a` nach `b`: `a + (b - a) * k`. |
| `smoothstep(e0, e1, x)` | Weicher Übergang von 0 nach 1 zwischen `e0` und `e1`. |
| `saw(x)`, `tri(x)`, `square(x)`, `square(x, duty)` | Wellenformen mit 0 bis 1 pro Periode `x`: Sägezahn, Dreieck, Rechteck (`duty` = Anteil „an“, Vorgabe 0.5). |
| `radians(g)`, `degrees(r)` | Grad ↔ Bogenmaß. |
| `random()`, `random(max)`, `random(min, max)` | Zufallszahl (0 bis 1, 0 bis `max`, `min` bis `max`). Jeder Scheinwerfer hat seine eigene, **reproduzierbare** Folge. |
| `hsv(h, s, v)` | Setzt `r`, `g`, `b` aus Farbton `h` (0 bis 1, springt zyklisch), Sättigung `s` und Helligkeit `v` (0 bis 1). |
| `slot(n)` | Der Wert (in %) des n-ten Gobos von Rad 1; `slot(0)` ist das erste (meist offen). Nur in der Kategorie `gobo`; die Liste kommt aus der Gerätedatei, ohne Angaben liefert `slot()` 0. |
| `slot(n, rad)` | Wie `slot(n)`, aber für Rad `rad` (1 oder 2): `gobo2 = slot(3, 2);` |

Konstanten: `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false`.

---

## 12. Beispiele

### Puls (Dimmer)

Hart an und aus; `duty` ist der Anteil der Periode, in dem das Licht an ist.

```
#NAME Puls
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR duty Slider 0.25 0.05 1 0.05
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * elapsed + index * spread);
  dimmer = p < duty ? 100 : 0;
}
```

### Lauflicht (Dimmer)

Ein Licht wandert über alle ausgewählten Scheinwerfer.

```
#NAME Lauflicht
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * elapsed) * count;   // aktueller Schritt (Kommazahl)
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;             // Abstand auf dem Kreis
  dimmer = d < width ? 100 : 0;
}
```

### Zufallsfarbe (Farbe)

Wechselt `speed`-mal pro Sekunde zu einem zufälligen Farbton. Die globale Variable `hue` merkt ihn sich.

```
#NAME Zufallsfarbe
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float hue = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    hue = random();
  }
  hsv(hue, 1, 1);
}
```

### Vier Positionen (Position, Zustandsmaschine)

Der Kopf springt alle `dauer` Sekunden zur nächsten von vier Ecken. Der Zustand steckt in `schritt`.

```
#NAME Vier Positionen
#CATEGORY position
#RATE 10
#VAR dauer Slider 1 0.2 10 0.1

int schritt = 0;
float start = 0;

loop() {
  if (elapsed - start >= dauer) {
    schritt = (schritt + 1) % 4;
    start = elapsed;
  }
  pan = (schritt == 0 || schritt == 3) ? 20 : 80;
  tilt = (schritt < 2) ? 20 : 80;
}
```

### Obertöne (Dimmer, Schleife)

Addiert mit einer `for`-Schleife mehrere Wellen (je höher, desto leiser).

```
#NAME Obertoene
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 4 0.1
#VAR harmonics Slider 3 1 8 1

loop() {
  float sum = 0;
  float norm = 0;
  for (int k = 1; k <= harmonics; k++) {
    sum += sin(2 * PI * k * speed * elapsed) / k;
    norm += 1.0 / k;
  }
  dimmer = 50 + 50 * sum / norm;
}
```

### Zoom-Atmen (Zoom)

Der Zoom schwingt zwischen `low` und `high` (0 und 100 sind die Enden des Zoom-Kanals).

```
#NAME Zoom-Atmen
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 20 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * speed * elapsed);
  zoom = lerp(low, high, k);
}
```

### Gobo-Wechsel (Gobo)

Schaltet der Reihe nach durch die Gobos des Geräts. `slots` ist ihre Anzahl, `slot(n)` der Wert des n-ten (0 = erstes, meist offen). Jedes Gerät hat andere Gobos – deshalb fragt der Effekt das Gerät, statt Prozentwerte zu raten.

```
#NAME Gobo-Wechsel
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * elapsed), n));
}
```

### Gobo mit Drehung und zweitem Rad (Gobo)

Die Ausgaben `gobo`, `gobo_spin`, `gobo2` und `gobo2_spin` sind einzeln wählbar. Dieses Beispiel schaltet Rad 1 durch, lässt Rad 2 gegenläufig versetzt mitwechseln und dreht das gewählte Gobo:

```
#NAME Zwei Räder
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05

loop() {
  float n  = max(1, slots);
  float n2 = max(1, slots2);
  gobo  = slot(mod(floor(speed * elapsed), n));
  gobo2 = slot(mod(floor(speed * elapsed) + 1, n2), 2);
  gobo_spin = 70;                    // Drehung von Rad 1 (nur setzen, wenn gewünscht)
}
```

### Farblauflicht mit zwei Farben (Farbe)

Alle Scheinwerfer haben Farbe A, einer oder zwei laufen in Farbe B durch die Reihe (Auswahl-Reihenfolge). Mit `direction` stellst du die Richtung ein – das Beispiel ist das mitgelieferte *Color Runner* in Kurzform:

```
#NAME Farblauflicht
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR width Slider 1.5 0.5 8 0.5
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float run = fract(speed * t);
  if (direction < 0.5) run = 1 - run;
  float d = abs(index - run * count);
  if (d > count / 2) d = count - d;
  float k = d < width ? 1 : 0;
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
```

### Eigene Funktion (Dimmer)

```
#NAME Dreieck mit Funktion
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float dreieck(float x) {
  return 1 - abs(2 * fract(x) - 1);
}

loop() {
  dimmer = 100 * dreieck(speed * elapsed + phase);
}
```

---

## 13. Fehler und Prüfung

Das Studio prüft beim Tippen. Typische Meldungen (immer mit Zeilennummer):

| Meldung | Ursache |
|---|---|
| `Unbekannte Variable 'x'` | Name nie deklariert oder zugewiesen (Tippfehler?). |
| `Unbekannte Funktion 'foo()'` | Die Funktion gibt es nicht. |
| `sin() erwartet 1 Argument(e)` | Falsche Anzahl an Argumenten. |
| `';' erwartet, gefunden '}'` | Ein Semikolon fehlt (die Meldung steht oft in der Zeile danach). |
| `Ausdruck erwartet, gefunden ';'` | Ein Wert fehlt, z. B. `dimmer = 1 +;`. |
| `'speed' ist ein Regler (#VAR) und kann im Skript nicht geändert werden` | Regler sind nur lesbar; lege dafür eine eigene Variable an. |
| `'b' ist eine Ausgabe des Effekts ... kann nicht als eigener Name dienen` | `dimmer`, `r`, `g`, `b`, `pan`, `tilt` und die Systemnamen sind vergeben. |
| `'break' ist nur in einer Schleife erlaubt` | `break` / `continue` außerhalb von `for` / `while`. |
| `#RATE erwartet eine ganze Zahl von 1 bis 40` | Ungültige Rate. |
| `#CATEGORY fehlt` | Der Kopf hat keine Kategorie. |
| `loop() erwartet` | Das Skript hat keine `loop()`-Funktion. |
| `Zu viele Schritte in einem Durchlauf ... Endlosschleife?` | Eine Schleife endet nie (Laufzeitfehler, erscheint in der Vorschau). |

**Speichern** speichert auch fehlerhafte Skripte, damit du weiterarbeiten kannst. Ein fehlerhaftes Skript wird nicht ausgeführt; laufende Effekte behalten die **letzte fehlerfreie Fassung**.

Wird ein Skript gespeichert, während Effekte laufen, übernehmen sie den neuen Code beim nächsten Durchlauf. Ihr **Speicher** (globale Variablen, Zähler, Zustand) bleibt erhalten; neu hinzugekommene Variablen starten mit ihrem Anfangswert.

---

## 14. So wirken Effekte im Programm

- **Skript und Effekt:** Das Skript (`.fx`) ist die Datei. Ein **Effekt** (in der Effekt-Liste des Programmers) ist eine **Definition**: ein Name, ein Skript und Werte für dessen Regler. Mehrere Effekte können dasselbe Skript mit verschiedenen Reglerwerten nutzen. Beim Anlegen zeigt der Dialog die Beschreibung und die Durchläufe pro Sekunde des Skripts.
- **Anwenden:** Im Programmer weist du den ausgewählten Scheinwerfern je **Kategorie** (Dimmer, Farbe, Position, Zoom, Fokus, Gobo) einen Effekt zu: die Zeile **Variable:/Effekt** in der jeweiligen Ansicht des Programmers (Fokus und Zoom in der Fokus-Ansicht, Gobo im Gobo-Reiter des Beam-Bereichs; während ein Effekt läuft, ist der zugehörige Fader gesperrt). Die Reihenfolge der Auswahl bestimmt `index` und damit die Verteilung über die Scheinwerfer. Ein Effekt steuert nur die Kanäle seiner Kategorie.
- **In Cues:** Ein Cue speichert die Effekt-Zuweisungen mit (samt Auswahl-Reihenfolge) und startet sie beim Abspielen; **Effekt-Einblendzeit** und **Ausblendzeit** des Cues überblenden die Amplitude von bzw. zum vorherigen Wert. Setzt ein Cue für eine Kategorie einen festen Wert, endet dort der laufende Effekt, und der Cue blendet von dessen zuletzt ausgegebenem Wert aus.
- **Synchronität:** Effekte, die `t` (oder `phase`/`index` mit `t`) benutzen, laufen zueinander im Gleichtakt. Mit `elapsed` beginnt dagegen jeder Effekt bei seinem Start von vorn – richtig für Abläufe „ab jetzt“.
- **Zustand:** Jeder Effekt hat für jeden Scheinwerfer und jede Kategorie einen **eigenen Speicher**. Er beginnt neu, wenn der Effekt neu zugewiesen wird.
- **Dateien:** Skripte liegen im Ordner `effects/` des Datenordners. Das Studio, der **Dateimanager** (Art *Effekte*: umbenennen, duplizieren, herunterladen, hochladen) und der **Export** einer Show (benutzte Skripte kommen ins Paket) arbeiten mit denselben Dateien. Die mitgelieferten Effekte kommen beim ersten Start in den Ordner; **Standard-Effekte wiederherstellen** (im Öffnen-Dialog oder im Dateimanager) legt fehlende wieder an und überschreibt **nie** etwas.
- **Die Show speichert die Definitionen** (Name, Skriptname, Reglerwerte), nicht den Skripttext. Fehlt das Skript, verlieren die Definitionen ihre Wirkung und funktionieren wieder, wenn es zurück ist; ein Cue mit fehlendem Effekt lässt den Kanal unverändert.

### Grenzen heute

- Es gibt sechs Kategorien (Dimmer, Farbe, Position, Zoom, Fokus, Gobo). Weitere (Prisma, Strobe, rohe DMX-Werte) sind vorbereitet, aber noch nicht eingebaut.
- Zoom und Fokus laufen je Gerät über ihren eigenen Kanal und müssen vorhanden sein; Gobos hängen von der Gerätedatei ab. Die Vorschau zeigt für Gobos nur die Werte, nicht das Bild.
- Ein Effekt steuert je Scheinwerfer eine Kategorie; zwei Kategorien gleichzeitig brauchen zwei Effekte.
- Die Rate ist höchstens 40 pro Sekunde, weil die DMX-Ausgabe nicht schneller sendet.

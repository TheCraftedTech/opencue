# Eigen projectoren (editor)

De editor maakt apparaten waarvoor geen geschikt GDTF-bestand bestaat – een rookmachine, een gewone dimmer, een RGB-par, een moving head. Het resultaat is een **echt GDTF-bestand** (formaat GDTF 1.2, opgebouwd zoals de bestanden op GDTF Share). Hiervoor heeft u **geen** GDTF Share-account nodig.

---

## 1. Openen

**Bibliotheek → Projectorbibliotheek… → "Eigen armatuur…".** Het venster is even groot als de bibliotheek en heeft drie tabbladen: **Algemeen**, **Modi & kanalen**, **Afbeelding & 3D**.

- Een eigen type later wijzigen: klik op **Bewerken** in de lijst met geïnstalleerde typen (alleen voor typen die met de editor zijn gemaakt, gemarkeerd met "Eigen · ongecontroleerd").
- Een bestaand type als uitgangspunt gebruiken (**laden vanuit een andere projector**): in de editor, op het tabblad *Algemeen* bovenaan, de keuze **"Beginnen met een bestaand armatuur"**, of op de kaart in de bibliotheek **Meer → Kopie bewerken**. Overgenomen worden: stamgegevens, modi, kanalen, functienamen, bereiken en de profielafbeelding. **Niet** overgenomen: wielen (gobo's, kleurenwielen), de geometrie en 3D-onderdelen; de editor meldt wat is weggelaten.

---

## 2. Algemeen

| Veld | Betekenis |
|---|---|
| Fabrikant, Naam | Verplicht. De bestandsnaam wordt `Fabrikant@Naam@Eigen.gdtf`. Bestaat het type al, dan meldt de editor dat. |
| Korte naam | Optioneel, maximaal 8 tekens. |
| Categorie | Moving head, LED-bar, par, dimmer, strobe, effect, overig – of "Automatisch" (herkend aan de kanalen). U kunt de bibliotheek op categorie filteren. |
| Gewicht, Beschrijving | Optioneel. |
| Tags | Typ en druk op **Enter**. De bibliotheek doorzoekt ze ook (bijv. "rook", "buiten", "12 V"). |
| Sjabloon | Alleen voor nieuwe typen: rookmachine, dimmer, RGB, RGB + dimmer, moving head. |

---

## 3. Modi & kanalen

Een **modus** is één kanaalindeling (veel apparaten hebben er meerdere, bijv. "3 kanalen" en "8 kanalen"). **+ Modus (kopie)** voegt een nieuwe toe als kopie van de gekozen modus; wijzig de naam rechtsboven.

Per **kanaal**:

- **Attribuut** – wat het kanaal doet. De lijst is gesorteerd in intensiteit, kleur, positie, bundel, effecten (rook, haze, ventilator) en besturing. Helemaal onderaan, apart: **Eigen naam …** voor alles wat niet in de lijst staat (bijv. "Bellen").
- **Label** – vrije tekst, bijv. "Rookuitvoer". Het verschijnt in het detailpaneel van DMX direct.
- **8 / 16 bit** – een 16-bitkanaal gebruikt twee DMX-adressen (grof + fijn).
- **Standaardwaarde** (0–255) – de waarde die het apparaat heeft als het niet wordt aangestuurd.
- **Bereiken** – benoemde stappen, bijv. vanaf 0 "Uit", vanaf 10 "Rook". Het eerste bereik begint altijd bij 0; elk ander eindigt vlak voor het begin van het volgende. Bij pan, tilt en zoom voert u ook het hoekbereik in graden in.

Met de pijlen wijzigt u de volgorde; de DMX-adressen worden daaruit berekend (links van elke rij).

### CSV-import

**CSV importeren…** leest een kanalenlijst: één regel per kanaal, met een kopregel. Kolommen (in willekeurige volgorde, gescheiden door `;`, `,` of tab): `Attribute`, `Label`, `Bit`, `Default`, `Ranges`. Schrijf bereiken als `0 Off; 10 Fog` of `0-9 Off; 10-255 Fog` – bevat de cel het scheidingsteken, zet haar dan tussen aanhalingstekens:

```
Attribute;Label;Bit;Default;Ranges
Fog1;Fog output;8;0;"0 Off; 10 Fog"
Control1;Fan;8;0;"0-9 Off; 10-255 On"
```

---

## 4. Afbeelding & 3D

- **Profielafbeelding** – elke afbeelding; ze wordt als PNG in het bestand geschreven (maximaal 512 pixels) en verschijnt in de bibliotheek.
- **3D-model** – optioneel een `.glb`-, `.3ds`-, `.stl`- of `.obj`-bestand (maximaal 25 MB en 250.000 driehoeken; STL en OBJ worden naar GLB omgezet) voor **vaste** apparaten; de afmeting in meters bepaalt hoe groot het op het 3D-podium verschijnt. Moving heads (pan/tilt) krijgen voet, beugel en kop als standaardonderdelen.

---

## 5. Het bestand doorgeven

Elke kaart in de bibliotheek heeft **Meer → Bestand exporteren (.gdtf)** en **Tonen in map** (alleen op de computer waarop het programma draait). Het bestand kan worden gekopieerd en op een andere computer worden toegevoegd met **GDTF-bestand importeren…** – of in elke andere GDTF-software worden geopend. De beschrijving van de editor wordt als extra bestand erin opgeslagen; andere programma's negeren die.

---

## 6. Goed om te weten

- Eigen typen zijn **ongecontroleerd**: controleer de kanaalindeling op het echte apparaat.
- Wijzigt u een type dat de show gebruikt, dan gelden de wijzigingen meteen. Verandert het **aantal kanalen van een gebruikte modus** (of wordt zo'n modus verwijderd of hernoemd), dan toont de editor een **opmerking** – die verhindert niets; controleer daarna de DMX-adressen.
- **Annuleren vraagt eerst bevestiging:** als u iets hebt gewijzigd, openen *Annuleren*, het kruisje × en Escape het venster "Niet-opgeslagen wijzigingen" (*Verder bewerken*, *Wijzigingen verwerpen* of *Opslaan*). Zonder wijzigingen sluit de editor meteen.
- **Verwijderen vraagt eerst bevestiging:** een modus, kanaal, bereik, profielafbeelding of 3D-model wordt pas na bevestiging verwijderd.
- Grand master en blackout werken alleen op de **dimmer** (of op de kleur als er geen dimmerkanaal is) – een rookkanaal blijft ongestoord doorlopen.
- Rook, haze en dergelijke bedient u in de projectorbediening op het tabblad **DMX direct**. Met de muis boven het label, klikken op het label of rechtsklikken op een fader ziet u de functienamen en bereiken van het kanaal.

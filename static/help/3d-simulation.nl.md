# 3D-simulatie

Het paneel **3D-simulatie** toont je podium in 3D; elke projector brandt live volgens zijn DMX-waarden. Voeg het toe met **Paneel toevoegen**. Deze handleiding legt de knoppen uit, de instellingen in **Ruimte en licht** en wat je kunt controleren als het beeld niet is zoals verwacht (niet elke projector belicht het podium, kegels of schaduwen ontbreken, het is traag).

---

## 1. Het paneel

- Drie modi linksboven: **Weergave**, **Bouwen** (objecten en 3D-modellen) en **Projectoren** (projectoren plaatsen, moving heads richten).
- Knoppen rechtsboven: VR-bril (alleen als de browser er een aanbiedt), camera delen tussen apparaten, **Ruimte en licht** (tandwiel), **3D-simulatie stoppen / starten**, **Blackout** (gloeilamp), **Weergave resetten**, **Volledig scherm**.
- Linksonder: de kwaliteitsknop toont beeldsnelheid en resolutie; een klik schakelt Automatisch → Laag → Gemiddeld → Hoog.

## 2. De 3D-simulatie stoppen en starten

De pauzeknop stopt de simulatie volledig: scène, grafische context en modellen worden opgeruimd, er wordt niets berekend of getekend en de rest van OpenCue wordt niet vertraagd. Het paneel blijft in je layout en toont een afspeelknop; **Starten** bouwt alles opnieuw op. De keuze wordt **per apparaat** onthouden en geldt voor alle 3D-panelen van dat apparaat. Is een 3D-paneel leeg en meldt het dat het gestopt is, druk dan op de afspeelknop.

Na het starten, na het laden van een grote show of na het wijzigen van de lichtlimieten toont het paneel even *Verlichting wordt voorbereid …*: de grafische kaart bereidt zijn programma's op de achtergrond voor en de rest van OpenCue blijft bruikbaar.

## 3. Ruimte en licht

Open het dialoogvenster met het tandwiel. Het bestaat uit twee delen.

**Voor alle apparaten** – geldt voor elk apparaat dat met de show verbonden is (console, iPad, toegang op afstand): *Verlichting* (werklicht in de bouwmodus, zaallicht), *Gereflecteerd licht* (ruimtelicht, wandreflectie, kleurafstraling), *Afbeelding* (objectreflectie, belichting, **Brume**) en *Raster en assen in de weergave*. **Brume op 0 %** schakelt de mist helemaal uit: geen lichtkegels en geen mistberekening – dit bespaart de meeste prestaties.

**Alleen dit apparaat** – prestaties en kwaliteit. Ze gelden alleen op dit apparaat, elk apparaat kan zijn eigen keuze maken:

| Instelling | Betekenis |
|---|---|
| **Kwaliteit** | Automatisch (past zich aan de beeldsnelheid aan), Laag, Gemiddeld, Hoog: resolutie en schaduwdetail. |
| **Max. lichten** | Hoeveel projectoren tegelijk een eigen licht op de vlakken krijgen (standaard 32). De helderste winnen. |
| **Max. schaduwen** | Hoeveel van deze lichten schaduwen werpen. 0 = zoveel als de grafische kaart toestaat. |
| **Max. spiegelstralen** | Weerspiegelingen op metaal en spiegels. |
| **Max. eenvoudige lichtkegels** | Hoeveel eenvoudige lichtkegels worden getekend. 0 = alle. Met een limiet houdt elke projector eerst zijn eerste kegel, daarna de helderste. |
| **Max. beeldsnelheid** | Beperkt hoe vaak per seconde het beeld opnieuw wordt getekend (bijvoorbeeld 30). 0 = onbeperkt. |
| **Projectoren werpen schaduwen** | De behuizingen van de projectoren werpen schaduwen in de lichtkegels (standaard aan). |

De regel onder de instellingen toont wat nu geldt (lichten, schaduwen, geplaatste projectoren) en wat de grafische kaart toestaat. **Limieten resetten** herstelt de standaardwaarden.

## 4. Als het beeld niet is zoals verwacht

- **Niet elke projector belicht het podium, sommige hebben geen schaduw, slechts enkele tonen een gobo.** Dit komt door de limieten van dit apparaat. Alleen de helderste *Max. lichten* projectoren (standaard 32) belichten de vlakken, slechts *Max. schaduwen* daarvan werpen schaduwen (de grafische kaart stelt een bovengrens, te zien in de infoplaats) en een gobo- of prismapatroon verschijnt op de eerste **3** van zulke lichten; de andere tonen open licht. Verhoog *Max. lichten* en *Max. schaduwen* (0 = zoveel mogelijk) als je alles wilt zien – bij veel projectoren wordt het beeld dan trager of loopt het wat achter.
- **Een projector brandt maar zijn kegel ontbreekt.** Controleer **Brume** (0 % = geen kegels), *Max. eenvoudige lichtkegels*, Blackout, de Grand Master, de dimmer van de projector en of de 3D-simulatie niet gestopt is.
- **Het beeld is donker.** Het werklicht bestaat alleen in de bouwmodus; controleer de regelaar *Belichting*, Blackout en de Grand Master.
- **De 3D-simulatie is traag.** Probeer in deze volgorde: Brume 0 % (als je geen mist nodig hebt), minder *Max. lichten* / *Max. schaduwen*, *Max. eenvoudige lichtkegels* (bijvoorbeeld 200), *Projectoren werpen schaduwen* uitschakelen, kwaliteit Laag of Automatisch, een *Max. beeldsnelheid* van 30, of de 3D-simulatie stoppen zolang je haar niet nodig hebt. Podia met 100 of meer tegelijk brandende projectoren zijn veeleisend; tot ongeveer 16 tegelijk brandende projectoren volstaan de standaardwaarden.
- **Een projector beweegt niet in 3D.** Zijn type heeft een 3D-model met beweegbare beugel / kop en Pan- / Tilt-kanalen nodig; typen zonder die (LED-panelen, balken, blinders) blijven stil. De projector moet ook op het podium geplaatst zijn (modus Projectoren → *Alles plaatsen*).
- **Een lichtkegel wijst de verkeerde kant op.** OpenCue draait de richting automatisch om als een GDTF-bestand de straal in de behuizing laat wijzen. Klopt een projectortype toch niet, noteer dan de naam en meld die aan de ontwikkelaar.

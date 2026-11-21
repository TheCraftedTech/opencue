# Toegang op afstand (tablet en telefoon)

Met **toegang op afstand** bedien je OpenCue vanaf een iPad, tablet, telefoon of een andere computer in **hetzelfde netwerk** – terwijl de consolecomputer de show blijft afspelen en het DMX blijft verzenden. Loop door de zaal en pas lampen aan, start cues vanaf het podium, of gebruik een tablet als tweede scherm.

Toegang op afstand staat **standaard uit**. Zolang het uit staat, is OpenCue helemaal niet bereikbaar vanuit het netwerk (de poort is echt dicht, niet alleen met een wachtwoord beveiligd).

---

## 1. Het idee in één minuut

- De **console** is de computer waarop OpenCue is geïnstalleerd en draait. Die doet al het werk: hij bewaart de show, berekent de cues en verzendt DMX.
- Een **apparaat op afstand** is gewoon een browser. Het opent een webadres van de console, logt in met het wachtwoord en toont **dezelfde OpenCue-interface** – dezelfde werkbalk, dezelfde panelen, dezelfde rechten.
- Alles blijft live gesynchroniseerd: selecteer je een projector, schuif je een fader of druk je op *Go* op één apparaat, dan tonen alle andere het meteen.
- Er is geen internet nodig. Alles gebeurt binnen je lokale netwerk.

---

## 2. Inschakelen

1. Open op de console **Instellingen** (werkbalk) → categorie **Toegang op afstand**.
2. Zet de **hoofdschakelaar Toegang op afstand** bovenaan aan. **Er is geen standaardwachtwoord:** de eerste keer vraagt OpenCue om je eigen – **“Kies een wachtwoord”**, twee keer ingevoerd (minstens 4 tekens; *Annuleren* schakelt toegang op afstand weer uit). **HTTP** staat daarna aan.
3. Het **wachtwoord** stel je in en wijzig je onder **Instellingen → Beveiliging** (knop *Wachtwoord instellen of wijzigen ...* in de sectie Toegang op afstand); dit werkt ook vanaf een apparaat op afstand (zijn eigen aanmelding blijft behouden; alle andere apparaten moeten opnieuw inloggen). Gebruik *Tonen* om te controleren wat je typte. Hetzelfde wachtwoord beschermt het vergrendelscherm (sectie 8). Elk wachtwoord is toegestaan (minstens 4 tekens) – de keuze is aan jou.
4. Wijzig desgewenst de **HTTP-poort** (1024–65535, standaard 8000). Een gewijzigde poort geldt na het herstarten van OpenCue.
   **HTTPS** is hieronder een eigen sectie met een eigen schakelaar en een eigen **HTTPS-poort** (standaard 8001, werkt direct): sommige browserfuncties hebben een **beveiligde pagina (https)** nodig: **het iPad-scherm wakker houden** (Instellingen → Meer opties → *Scherm wakker houden*), de VR-modus van de 3D-simulatie, en microfoon en camera in de browser. Open dus op de iPad het **https://-adres** (bevestig het certificaat één keer); via `http://` werkt alleen de apparaatinstelling “Automatisch vergrendelen: Nooit”. OpenCue maakt het certificaat zelf; de browser vraagt bij het eerste bezoek eenmalig om bevestiging. HTTP en HTTPS zijn onafhankelijk aan en uit te zetten en hebben elk een eigen adres met een eigen QR-code.
   **Netwerknaam:** de console is ook bereikbaar als `opencue.local` (komt automatisch met toegang op afstand; een kleine schakelaar onder *Geavanceerd*), bijvoorbeeld `http://opencue.local:8000` – het adres blijft in elk netwerk gelijk. Is de naam al bezet (bijvoorbeeld door een tweede console), dan gebruikt OpenCue `opencue-2.local` enzovoort; de instellingen tonen welke geldt. iPad, iPhone, Mac en Windows 10/11 begrijpen de naam zelf. Een geïnstalleerde web-app is aan zijn adres gebonden: schakel je over op de naam, installeer hem dan nog eens.
5. Klik op **Opslaan** (de dialoog blijft open). Herstarten is niet nodig. De eerste keer vraagt Windows eenmalig naar de firewall – sta **privénetwerken** toe.

OpenCue luistert nu op elk netwerkadres van de console. De pagina toont:

| Onderdeel | Betekenis |
|---|---|
| **Status** | “Bereikbaar in het netwerk” of “Alleen lokaal”. |
| **Adressen** | Elk adres waarop de console bereikbaar is, elk met een knop **Kopiëren**. |
| **QR-code** | Voor het gekozen adres – scan hem met de camera van een iPad of telefoon. Bij het verbinden wordt het wachtwoord gevraagd. |
| **Adressen opnieuw detecteren** | Nadat je van wifi bent gewisseld of een kabel hebt aangesloten. |

Zet je het weer uit, dan worden de luisteraars direct weer gesloten.

> **Windows-firewall:** als toegang op afstand voor het eerst wordt ingeschakeld, kan Windows vragen of OpenCue in het netwerk mag communiceren. Sta het toe voor je **privénetwerk**; anders kunnen andere apparaten niet verbinden.

---

## 3. Een apparaat verbinden

1. Zorg dat het apparaat in **hetzelfde netwerk** (zelfde wifi of LAN) zit als de console.
2. Open het adres van de instellingenpagina in de browser van het apparaat – bijvoorbeeld `http://192.168.1.20:8000/` – of scan de QR-code. Het adres stuurt door naar de pagina `/remote/`.
3. Voer het wachtwoord in en tik op **Aanmelden**.

**Wachtwoord onthouden** (selectievakje op de aanmeldpagina) bewaart het wachtwoord alleen in de browser van **dat apparaat** en vult het veld de volgende keer vooraf in. Er is geen automatische aanmelding – je tikt nog steeds op *Aanmelden*. Haal het vinkje weg om het bewaarde wachtwoord direct te wissen.

**Verkeerd wachtwoord:** herhaalde foute pogingen blokkeren het apparaat een tijdje (bescherming tegen brute kracht).

**Afmelden:** *Bestand → Afmelden* (alleen zichtbaar op apparaten op afstand).

Verbindt niets: controleer of beide apparaten in hetzelfde netwerk zitten (gastwifi scheidt apparaten vaak van elkaar), of het adres overeenkomt met dat op de instellingenpagina, en de firewall (zie boven).

---

## 4. Wat een apparaat op afstand kan

- **Alles wat de console kan.** Na het inloggen heeft een apparaat op afstand dezelfde rechten: programmeren, cues, effecten, bestanden, instellingen, DMX-instellingen en instellingen voor toegang op afstand. Dat omvat dingen met gevolgen – toegang op afstand uitschakelen (waardoor dat apparaat buitengesloten wordt) of **OpenCue afsluiten**, wat het programma voor iedereen stopt. Gebruik een wachtwoord dat alleen vertrouwde mensen kennen.
- **Eigen lay-out per apparaat.** Elk apparaat onthoudt welke lay-out het gebruikte en kan een andere tonen dan de console. Bouw voor de tablet een lay-out met grote knoppen (zie hieronder). Slaat één apparaat een lay-out op die een ander apparaat nu toont, dan neemt het andere die over – of, als het eigen niet-opgeslagen wijzigingen heeft, biedt het *Toepassen* of *Mijn versie behouden* aan.
- **Volledige toegang tot alle instellingen, ook vanaf de iPad.** Dat is belangrijk als OpenCue zonder venster draait (*alleen server*, systeemvakpictogram): alle instellingen – uitgang, beveiliging en vergrendelmodus, REST API, AI-assistent, spraakbesturing, back-ups, starten met Windows, standaardwaarden, ingangen / uitgangen ... – zijn op de iPad te wijzigen en gelden **voor de server**. De microfoonschakelaar van de spraakbesturing is er op de iPad ook. **Mappen:** waar de hoofdcomputer de Windows Verkenner zou openen, krijgt een apparaat op afstand de **OpenCue-verkenner** – een groot venster voor de OpenCue-gegevensmap (shows, back-ups, logs, projectoren ...): bladeren, downloaden (een map als ZIP), uploaden, nieuwe map, hernoemen, dupliceren, verwijderen. Het kan de gegevensmap niet verlaten. Hetzelfde venster (*Map kiezen...*) laat een nieuwe opslaglocatie kiezen. **MIDI leren / meekijken**, de **DMX-ingang** en de **firewallregel** (Windows vraagt toestemming op de hoofdcomputer) werken ook vanaf de iPad. Slechts enkele dingen hangen **fysiek aan de hoofdcomputer**: zijn venster (volledig scherm), het **vergrendelscherm** van de console (daar ontgrendelen), het opnemen van de toets van een **specifiek toetsenbord**, de **microfoon tijdens dicteren** en de echte Windows Verkenner.
- **Per apparaat:** alleen de **modus volledig scherm** (die van elke browser) en de **GUI-schaal**.
- **De gegevens blijven op de console.** Opslaan en laden lopen altijd via de console; shows, lay-outs en projectoren staan op de consolecomputer.

### Wie is verbonden?

Een werkbalkpictogram toont **hoeveel apparaten op afstand verbonden zijn**. Klik erop om IP-adres, apparaat en verbindingstijd van elk te zien – en om een apparaat te **verbreken** (*Verwijderen*). Een verbroken apparaat ziet een melding en moet de pagina herladen om opnieuw in te loggen.

---

## 5. Als app installeren (iPad / iPhone / Android)

De pagina voor toegang op afstand is een **web-app**. Op het apparaat kun je haar aan het beginscherm toevoegen:

- **iPad / iPhone (Safari):** deelknop → **Zet op beginscherm**.
- **Android (Chrome):** menu → **App installeren** / **Toevoegen aan startscherm**.

Ze opent daarna schermvullend zonder browserbalken, met de kleuren van je huidige thema.

**Pictogram:** de app krijgt het OpenCue-pictogram en de naam “OpenCue” – ook via HTTPS. (Het pictogram zit in de pagina ingebed; anders haalt iOS het bij een zelfgemaakt certificaat niet op en toont alleen een grijze letter.) Verandert het pictogram toch niet, verwijder dan de app van het beginscherm en voeg haar opnieuw toe – iOS onthoudt het oude pictogram.

**Offline-pagina en serverkeuze (beveiligde pagina, HTTPS):** kan de server niet worden bereikt, dan toont de app “**Server niet bereikbaar**” in plaats van een foutpagina. Daar kun je **Herladen**, of onder **Andere server** een nieuw **adres of IP**, de **poort** en **HTTPS** aan / uit invoeren en **Verbinden** – krijgt de computer een nieuw IP-adres, dan hoef je de app niet opnieuw te installeren. De recent gebruikte adressen staan eronder om aan te tikken. Valt de verbinding weg (wifi weg, OpenCue gesloten), dan verschijnt de melding “Verbinding wordt hersteld”; na 3 seconden met de knop “**Andere server kiezen (7s)**” waarvan het getal **aftelt**; bij 0 opent de offline-pagina vanzelf en laadt OpenCue opnieuw zodra de server antwoordt. Dit geldt ook als wifi er is maar de computer niet antwoordt – dan verschijnt de offline-pagina na **ongeveer 1,5 seconde** in plaats van een wit scherm en verdwijnt weer meteen zodra de server antwoordt. Open je haar bewust met de knop, dan blijft ze staan. Tip: de naam `opencue.local` vindt de computer ook als het IP verandert.

**Belangrijk op de iPad – installeer het certificaat eenmalig:** bij een zelfgemaakt certificaat kent iOS de uitzondering “toch doorgaan ondanks de waarschuwing” alleen **binnen het Safari-tabblad**. Een app vanaf het beginscherm blijft dan **wit**, en de service worker (offline-pagina) is niet toegestaan. Daarom maakt OpenCue een eigen certificeringsinstantie (“OpenCue Local CA”) die het https-certificaat ondertekent. Die installeer je **eenmalig** op het apparaat:

De stappen staan op een **gidspagina** op de server: *Instellingen → Toegang op afstand → Certificaat voor iPad en browsers* toont het adres en een QR-code (scan hem met de iPad-camera). De pagina opent via **http://** zonder aanmelding en volgt de taal van het apparaat. Bovenaan kies je tussen **iPad / iPhone** en **Android · Windows · macOS**. Voor de iPad zijn er vier stappen met een herinnering: **Downloaden → Installeren → Vertrouwen → https openen**; afgeronde stappen kun je afvinken (de pagina onthoudt ze). **Belangrijk: open de pagina in Safari** – het profiel kan niet worden geïnstalleerd vanuit de app op het beginscherm, vanuit Chrome of vanuit de browser binnen een andere app. “Instellingen” betekent de **Instellingen-app van de iPad**, niet een instelling in Safari. Aan het einde van elke pagina staat hoe je het **certificaat weer verwijdert** (iPad: Instellingen → Algemeen → VPN en apparaatbeheer → “OpenCue” → Verwijder profiel). In OpenCue staat hetzelfde onder *Instellingen → Toegang op afstand → Certificaat voor iPad en browsers* (korte versie voor installeren en verwijderen). (Toegang via HTTP moet hiervoor aan staan.)

Vanaf dan werkt https zonder waarschuwing, opent de app, draaien de service worker en de offline-pagina – ook als de computer een **nieuw IP-adres** krijgt (OpenCue geeft alleen het servercertificaat opnieuw uit, de instantie blijft). De instantie mag alleen instaan voor lokale namen (`.local`, `localhost`) en privéadressen. Android / Windows / macOS: installeer het certificaatbestand (`opencue-ca.crt`) en stel het in als vertrouwde instantie. Verwijder je de map `https` in de gegevensmap, dan wordt een nieuwe instantie gemaakt – installeer het profiel dan opnieuw op de apparaten.

**Beperking:** installeerbare web-apps en de offline-pagina hebben een beveiligde verbinding nodig (HTTPS, op de iPad met het geïnstalleerde certificaat). Via gewoon `http://` werkt de app op het beginscherm wel, maar er is geen offline-pagina en het apparaat moet de console bereiken om iets te tonen.

---

## 6. Tips voor een goede tablet-lay-out

- Maak een **aparte lay-out** voor de tablet (*Bewerken → Lay-outs beheren…*): een grote **Executor**, de **Cuelijst**, een paar **Knop**- of **Fader**-panelen en de categorie van de **Projectorbediening** die je het meest nodig hebt. Apparaten op afstand laden hun eigen lay-out, dus de lay-out van de console blijft zoals hij is.
- Gebruik voor aanraking de panelen **Opdracht-numpad** en **Opdrachtknoppen** in plaats van te typen op het schermtoetsenbord.
- Vergroot de **GUI-schaal** op de tablet (`Ctrl +` of *Weergave → GUI-schaal…*) – die geldt alleen voor dat apparaat.
- Lay-outs kunnen door horizontaal **vegen** worden gewisseld als *Instellingen → Algemeen → Lay-outs wisselen door vegen* aan staat (per apparaat).
- Cuelijsten met timecodetriggers blijven op de console doorlopen, ook als een apparaat de verbinding verliest – de show hangt niet af van de tablet.

---

## 7. Veiligheid en goede gewoonten

- Gebruik toegang op afstand alleen in netwerken die je vertrouwt (je eigen router, een apart shownetwerk). De verbinding is **niet versleuteld** (gewone HTTP); iedereen in het netwerk zou het verkeer kunnen lezen.
- Kies een wachtwoord dat je nergens anders gebruikt – het wordt bewaard in de appconfiguratie op de console en, als je *Wachtwoord onthouden* aanvinkt, in de browser van dat apparaat.
- Schakel toegang op afstand uit als je haar niet nodig hebt.
- De DMX-uitgang draait altijd op de console – ook als alle apparaten op afstand de verbinding verbreken, blijven de lampen zoals ze zijn.

## 8. Vergrendelen: vergrendelscherm en afmelden

**Instellingen → Beveiliging** bevat de **vergrendelmodus** (standaard uit, vraagt het wachtwoord):

- **Bij de console:** het **hangslot** in de bovenbalk, **Ctrl+L** (te wijzigen onder *Bedieningen → Toetsenbordsnelkoppelingen*) of **Bedieningen → Vergrendelen** vergrendelt OpenCue. Een vergrendelde console toont alleen een donker wachtwoordvenster – de rest van de interface is verborgen, het toetsenbord doet niets, en de console accepteert geen wijzigingen meer vanuit dit venster (ook niet langs de interface om). Herladen ontgrendelt **niet**. **De show blijft doorlopen:** cues, effecten, MIDI, OSC, het schema en apparaten op afstand werken als eerder. Vijf foute wachtwoorden achter elkaar pauzeren het ontgrendelen een minuut. Het wachtwoord verlaat de console nooit zolang ze vergrendeld is. Herstarten van OpenCue ontgrendelt.
- **Bij een apparaat op afstand:** het hangslot **meldt het apparaat af**: de sessie eindigt, het *Wachtwoord onthouden* van dat apparaat wordt gewist, en de pagina toont weer de aanmelding met een leeg wachtwoordveld. Apparaten op afstand kunnen het wachtwoord of de vergrendelmodus niet wijzigen.
- **Automatisch vergrendelen na ...** (1 tot 60 minuten zonder invoer; standaard uit): de console vergrendelt zichzelf, apparaten op afstand melden zich af. Wees voorzichtig met een tablet die alleen weergeeft: laat de instelling daarvoor uit.

## 9. Eenvoudige bediening en operatormodus (om de console aan iemand anders te geven)

- Het **paneel “Eenvoudige bediening”** (*Bewerken → Paneel toevoegen → Invoer*) is de eenvoudige zus van het paneel *Projectorbediening* en gebruikt het **hele paneel** met vaste velden in procenten: links (38 %) heeft **elke projector een eigen tegel** (nummer, naam, live kleur en helderheid), gesorteerd op **groepen** (op de groepsnaam tikken = de hele groep selecteren; de rest gesorteerd op type; *Alles* / *Geen* bovenaan); rechts **helderheid** (grote fader, *Off* / *Full*), **kleur** (kleurveld – tint van links naar rechts, meer wit naar boven – plus kleurknoppen), **bewegen** (veerbelaste **joystick**: duwen – hoe verder, hoe sneller; loslaten = stoppen; *Midden*), **zoom**, **gobo's** als plaatjes, een grote **Blackout**-knop en de **looks**: *Regenboog*, *Cirkel* (pan / tilt), *Pulseren*, *Strobe* – kant-en-klare standaardeffecten zonder enige instelling (nogmaals tikken = uit, *Looks uit* verwijdert alles; het effect wordt de eerste keer automatisch aan de show toegevoegd). Een bediening die de geselecteerde lampen niet hebben blijft op zijn plaats maar is gedimd. Op een **smal paneel** (onder circa 720 px) schakelt het over naar een **compacte modus** met één tabblad per gebied (*Lampen | Helderheid | Kleur | Bewegen | Bundel | Looks*; Blackout blijft zichtbaar). Niets hier wijzigt groepen of de show; selectie, waarden en effecten zijn die van het hele programma (programmer, cues, effectenstudio). Maak een lay-out met alleen dit paneel (of een paar andere) voor de persoon die moet bedienen.
- **Operatormodus** (*Weergave → Operatormodus ...* of de joystickknop in de bovenbalk; vraagt het wachtwoord, *Instellingen → Beveiliging*): dit apparaat kan **alleen bedienen** wat op het scherm staat – geen menu's, geen bovenbalk, geen instellingen of andere dialogen, geen sneltoetsen (typen in een tekstveld werkt nog), geen verplaatsen of ombouwen van panelen, geen wisselen van lay-out of show. Je verlaat de modus met het kleine **hangslot rechtsonder** en het wachtwoord, of met **Ctrl+L**. Ze wordt alleen gestart vanuit het menu of de knop (geen sneltoets). **Opdrachten** (opdrachtregel, toetsen, widgets) voert de server in operatormodus alleen uit als ze **bedienen**; alles wat de show wijzigt (*Store, Update, Delete, Move, Label, Set*, cuetijden, aanmaken / hernoemen / verwijderen van cuelijsten) wordt geweigerd – ook binnen een opdrachtketen. **Bij de console is spraakbesturing in operatormodus uit** (de microfoon blijft dicht) en komt daarna terug als ze is ingeschakeld. De **server dwingt het af**: van een apparaat in operatormodus worden alleen bedienende berichten geaccepteerd (selecteren, waarden instellen, cues, presets, timecode, opdrachtregel ...); berichten voor programmeren, lay-out, show en instellingen worden genegeerd en schrijfverzoeken krijgen het antwoord `423`. Herladen verlaat de modus niet. Ze werkt bij de console en op elk apparaat op afstand afzonderlijk (geef een iPad met de app in operatormodus uit handen); herstarten van OpenCue beëindigt haar. Vijf foute wachtwoorden achter elkaar pauzeren het verlaten een minuut.
- **Goed om te weten:** de opdrachtregel, als je haar in die lay-out zet, kan elke opdracht uitvoeren – laat haar weg uit een lay-out voor gasten. Toetsen van een aparte extra toetsenbord (*Eigen toetsenbordsnelkoppelingen*, apparaatspecifiek) en MIDI-/OSC-controllers blijven werken: ze horen bij de show, niet bij het scherm.

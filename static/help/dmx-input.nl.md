# DMX-ingang (Art-Net en sACN ontvangen)

OpenCue kan DMX niet alleen verzenden maar ook **via het netwerk ontvangen** – van een lichttafel, een programma (bijvoorbeeld een visualiser of een showcontroller) of een apparaat. De ontvangen waarden kunnen in de uitgang worden **doorgestuurd en gemengd** of als **triggers** worden gebruikt.

Open het met **Bedieningen → DMX-ingang…** (het kan ook vanaf een tablet worden gewijzigd).

---

## 1. Inschakelen

- Zet **DMX ontvangen** aan (uit is de standaard – DMX heeft geen wachtwoord, iedereen in het netwerk kan zenden).
- **Protocollen:** Art-Net (UDP 6454) en/of sACN / E1.31 (UDP 5568, multicast). Art-Net-universum = *poortadres* (precies zoals OpenCue het verzendt: universum 1 = poortadres 1).
- **Toegestane afzenders:** leeg = iedereen; anders IP-adressen of het begin ervan (bijv. `192.168.1.`).
- **Netwerkadapter:** alleen nodig als de computer er meerdere heeft en de ingang op een bepaalde moet luisteren.
- **Bron weg na:** zo lang zonder pakket, dan laat OpenCue de waarden van de bron los (sACN: direct bij “stream beëindigd”).

**Geziene bronnen** toont live alles wat wordt verzonden: protocol, universum, afzender, pakketten per seconde en hoeveel kanalen niet nul zijn. **Bekijken** toont de 512 kanalen als raster; **Doorsturen** maakt meteen een toewijzing.

---

## 2. Doorsturen / mengen (bron → uitgang)

Een **toewijzing** mengt een *ingangsuniversum* in een *uitgangsuniversum* van OpenCue:

| Modus | Betekenis |
|---|---|
| **Hoogste wint** (HTP) | Per kanaal telt de grootste waarde van OpenCue en de ingang. De standaard, veilig om in te mengen. |
| **Vervangen** | De ingang telt zolang de bron er is (nullen inbegrepen). Eventueel alleen voor een kanaalbereik. |

- Meerdere bronnen voor hetzelfde universum: **hoogste wint**. Bij sACN tellen alleen de bronnen met de hoogste **prioriteit**.
- Heeft het uitgangsuniversum **geen projectoren**, dan wordt het toch uitgestuurd – dat geeft een **zuiver doorsturen** (bijv. Art-Net → sACN of → een USB-adapter).
- De ingang ligt **boven alles** (programmer, cues, effecten). De waarden binnen OpenCue blijven ongewijzigd; het mengen gebeurt alleen in de **uitgang**.
- Eigen pakketten worden herkend en genegeerd – een doorsturing veroorzaakt geen terugkoppelingslus.
- Het draait in het **DMX-uitgangsproces**: het doorsturen gaat ongewijzigd door, ook als het hoofdprogramma vastloopt. Valt dat proces uit en draait de uitgang als noodoplossing in het hoofdprogramma, dan blijven triggers en weergave werken maar het mengen niet (de dialoog zegt dat).

---

## 3. Triggers (kanaal → opdracht)

Een **trigger** voert een opdracht van de opdrachtregel uit als een kanaal verandert:

- **Knop:** stijgt de waarde boven de **drempel**, dan wordt de eerste opdracht uitgevoerd (bijv. `Go`); zakt ze er weer onder, dan de tweede (optioneel, bijv. `Blackout Off`).
- **Fader:** elke nieuwe waarde wordt als opdracht uitgevoerd; `{value}` staat voor de waarde omgerekend naar het **bereik** (standaard 0–100), bijv. `Master {value}`.
- **Leren:** klik op **Leren** en beweeg een kanaal op de tafel – protocol, universum en kanaal worden ingevuld.
- De eerste geziene waarde wordt alleen onthouden, er wordt niets getriggerd (geen sprong bij het verbinden). Faderopdrachten lopen hoogstens 20 keer per seconde; de laatste waarde komt altijd aan.

Voorbeelden: kanaal 1 = `Go` (knop), kanaal 2 = `Blackout` (knop), kanaal 3 = `Master {value}` (fader), kanaal 10 = `Goto Cue 5`.

**Laatste triggers** toont wat er is getriggerd.

---

## 4. Goed om te weten

- De ingang hoort bij de **appconfiguratie** (niet bij de show) en geldt voor deze computer.
- Om OpenCue te bereiken moet een tafel naar het IP-adres van de computer of via broadcast zenden; de Windows-firewall moet UDP 6454 / 5568 voor OpenCue toestaan – de dialoog toont of de regel bestaat en maakt hem met één klik aan (Windows vraagt toestemming op de hoofdcomputer).
- **Aankondigen als Art-Net-apparaat:** OpenCue beantwoordt de zoekopdracht (ArtPoll) van andere apparaten en verschijnt in hun lijst met Art-Net-apparaten – een tafel kan het als doel kiezen zonder het IP-adres te typen.
- Een overzicht van alle ingangen en uitgangen staat in **Instellingen → Overzicht**.

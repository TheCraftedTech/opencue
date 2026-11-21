# Editor timeline e LTC

Con l'**editor timeline** collocate graficamente cue e comandi su un asse temporale – con le forme d'onda dei vostri brani sotto. Con l'**LTC** OpenCue va a tempo con una sorgente esterna (un lettore, un software DJ o di show, una console) oppure invia esso stesso un clock ad altri dispositivi. Tutto si basa sul **timecode globale**.

---

## 1. L'idea in un minuto

- OpenCue ha **un solo** clock, il **timecode** (pannello *Timecode*, visualizzazione in alto nella barra degli strumenti). Scorre, si ferma, salta – su tutti i dispositivi contemporaneamente.
- In certi momenti di questo clock succede qualcosa: parte un **cue** con il trigger *Timecode*, viene eseguito un **comando** di una traccia di comandi, un **lettore multimediale** avvia il suo brano (*ora di inizio*). Questo accade solo quando il clock **attraversa** quell'istante **in avanti** – i salti e la riproduzione all'indietro non attivano nulla.
- Il clock può essere guidato da **tre sorgenti**: questo computer (premete Start), il **timecode MIDI** (*Impostazioni → MIDI*) o l'**LTC** (*Impostazioni → Timecode*). Guida chi c'è per primo.
- L'**editor timeline** mostra tutto questo su un asse temporale e permette di impostarlo e spostarlo comodamente – invece di digitare ogni ora nella finestra del cue.

---

## 2. Aprire l'editor timeline

- Come pannello nel layout: *Modifica → Aggiungi pannello → Media → **Editor timeline*** (meglio se largo).
- Brevemente come finestra: *Visualizza → Apri pannello come finestra → **Editor timeline*** (vi sono elencati tutti i pannelli, ad esempio anche **Controllo semplice**).

---

## 3. Che aspetto ha

- **Righello** in alto: un clic o un trascinamento salta a quell'istante.
- **Una traccia per lista di cue**: ogni cue con il trigger *Timecode* è un **marcatore** con numero e nome. Il nome della lista a sinistra la seleziona (per il vassoio e «Imposta cue qui»).
- **Tracce di comandi** (rosse / rosa): comandi della riga di comando a certi istanti – vedi la sezione 6.
- **Tracce audio** in basso: **automatiche** per ogni brano che un lettore multimediale riproduce insieme al timecode, con una **forma d'onda** e sottili linee in corrispondenza di ogni marcatore – si vede se qualcosa cade esattamente sul tempo (sezione 5).
- **Vassoio** in fondo: i **cue senza ora** della lista selezionata.
- La **testina** gialla è il timecode globale.

---

## 4. Modificare i marcatori e scorrere

| Azione | Come |
|---|---|
| **Spostare** un marcatore | trascinarlo di lato con il mouse o il dito; si aggancia alla **griglia** (tenete premuto **Maiusc** = nessuna griglia) |
| **Spostare con precisione** un marcatore | fare clic sul marcatore, poi `←` / `→` (un passo di griglia; `Maiusc` = dieci volte tanto) |
| Mettere sulla timeline un cue **senza ora** | trascinarlo dal **vassoio** sulla traccia – oppure selezionare il chip e premere **Imposta cue qui** |
| **Griglia** | *disattivata*, 10 ms, fotogramma (25 fps), 0,1 s, 1 s |
| **Zoom** | tasti `+` / `−`, Ctrl + rotellina, **due dita** (iPad); *Mostra tutto* (`F`) |
| **Segui** | la vista scorre insieme alla testina |

Lo **scorrimento** funziona in tutti i modi:

| Tasto / pulsante | Effetto |
|---|---|
| **Trascinare** il righello o la forma d'onda | salta continuamente lì (il suono segue) |
| Pulsanti **±5 s** | cinque secondi indietro / avanti (i clic rapidi si sommano) |
| Pulsanti **marcatore precedente / successivo** (`[` / `]`) | salta al cue o all'ora di comando successivi |
| `←` / `→` (focus nel pannello) | 1 s; con `Maiusc` 10 s; con `Alt` un fotogramma (40 ms) |
| `Home` / `Fine` | all'inizio / alla fine dei marcatori |
| `Spazio`, `L`, `K`, `J` | riproduci / pausa · avanti · pausa · riproduci **all'indietro** |
| Pulsante **Inverti** | riproduce il timecode all'indietro (non attiva cue né comandi) |

---

## 5. Audio: automaticamente dai lettori multimediali

Non dovete scegliere un brano nella timeline. La timeline guarda da sola **cosa viene riprodotto insieme al timecode**:

- Ogni **lettore multimediale** in modalità **Timecode** con un supporto scelto e la sua **ora di inizio** compare come traccia audio: con nome, **forma d'onda** e un **marcatore di inizio** (simbolo di nota) all'ora di inizio. Compaiono anche un lettore su **un altro dispositivo** (ad esempio sul computer principale mentre lavorate sull'iPad) e gli **schermi della simulazione 3D**.
- **Trascinare il marcatore di inizio** (o fare doppio clic su di esso e digitare l'ora) cambia l'**ora di inizio del lettore multimediale** – il brano parte allora alla nuova ora.
- **Aggiungi audio ...** crea un **audio proprio** di questa timeline (va in sincrono con il timecode) nel caso in cui non sia ancora configurato alcun lettore multimediale. Il pulsante dell'altoparlante silenzia solo questi audio propri. Sull'iPad il browser ha bisogno di un tocco sul pannello prima che il suono sia consentito.
- OpenCue calcola la **forma d'onda** una volta con *ffmpeg* incluso (un valore ogni 10 ms) e la memorizza. Se ffmpeg manca, la traccia lo segnala.
- Con l'**LTC** vale lo stesso: i lettori multimediali seguono il timecode chiunque lo guidi – le tracce audio mostrano quindi sempre cosa gira a quale ora.

---

## 6. Tracce di comandi

Una **traccia di comandi** esegue **comandi della riga di comando** a certi istanti del timecode – indipendentemente dai cue, ad esempio `Blackout Off` a 1:30, `Cuelist Show Go` a 2:00 o `Effect Off` al ritornello. Appartiene allo **show** (salvata ed esportata con esso).

- **Nuova traccia di comandi**: pulsante **+**. Possono essercene diverse (ad esempio «Luci», «Fumo», «Video»); un doppio clic sul nome rinomina, la **×** elimina (cliccare due volte).
- **Aggiungere un comando**: il pulsante **Comando qui** (o `C`) inserisce un comando all'istante attuale sulla traccia selezionata – oppure fate **doppio clic** sulla traccia in quel punto.
- Una piccola finestra chiede **ora** e **comando**; `Invio` conferma. Ogni marcatore può essere **trascinato**, spostato con i tasti freccia, modificato di nuovo con un **doppio clic** ed eliminato con `Canc`.
- Il **server** esegue il comando quando il timecode **attraversa** il suo istante **in avanti** – esattamente come i cue (anche con LTC / timecode MIDI). Compare nella cronologia dei comandi. Un salto lo salta.
- In **modalità operatore** le tracce di comandi non possono essere modificate; girano come al solito.

---

## 7. Impostare i cue con la musica (registrazione)

Come su una console, solo in forma grafica:

1. Create i vostri cue (lista di cue) – la loro ora può ancora essere vuota. Compaiono nel **vassoio**.
2. Configurate un **lettore multimediale** con il vostro brano (modalità Timecode, ora di inizio 0) – la forma d'onda compare da sola.
3. Scegliete la lista di cue e il primo cue nel vassoio.
4. Avviate la riproduzione (Spazio) e a ogni attacco premete **Imposta cue qui** (o `Invio`): il cue selezionato riceve l'**ora attuale**, poi viene selezionato il cue **successivo**.
5. Poi ritoccate con calma: trascinate i marcatori sulla forma d'onda e lasciate che si aggancino.

Suggerimento: con *griglia 1 s* o *fotogramma* i marcatori cadono su tempi tondi, con *disattivata* sul millisecondo esatto.

---

## 8. LTC: il timecode come segnale audio

L'**LTC** (Linear Timecode) è un segnale udibile – suona come rumore – che trasporta l'ora. Sta su un canale (di solito il sinistro), la musica sull'altro. *Impostazioni → Timecode* mostra in alto **chi guida attualmente il clock** (questo computer, il timecode MIDI o l'LTC) e ha due aree:

**Ingresso: leggere il timecode (Segui LTC)**

1. Attivate **Segui LTC**, scegliete l'**ingresso audio** (ingresso linea, interfaccia USB o il *suono di sistema* di un dispositivo di uscita). Per provare c'è il **segnale di prova** (25 fotogrammi/s, nessun dispositivo necessario).
2. Scegliete il **canale** (sinistro / destro / somma), **Salva**. Sotto vedete in diretta **«Segnale trovato: 00:01:12:05 · 25 fps»** e una barra del livello.
3. Appena arriva un segnale valido, il **timecode globale scorre insieme**. Tutti i cue, i comandi e i lettori multimediali seguono. Una **pausa o uno stop della sorgente** ferma il timecode anche qui, un **salto** della sorgente viene seguito.
4. Vengono riconosciuti **24, 25, 29,97 (drop frame) e 30 fotogrammi al secondo**.
5. Per suonare voi stessi, disattivate di nuovo **Segui LTC**.

**Uscita: inviare il timecode (Invia LTC)**

OpenCue diventa il clock per altri dispositivi: quando avviate il timecode (ad esempio Play nel pannello *Timecode*), l'**LTC esce da un'uscita audio** – un lettore, una console o un registratore può andare a tempo.

1. Attivate **Invia LTC**, scegliete l'**uscita audio** e il **canale** (*entrambi*, *solo sinistro* o *solo destro* – usate un canale se l'altro porta musica).
2. Impostate la **frequenza fotogrammi** (24 / 25 / 29,97 drop frame / 30) e il **livello** (forte ma senza clipping; molti dispositivi si aspettano il livello di linea), **Salva**.
3. Viene inviato **solo mentre il timecode scorre in avanti**; quando è fermo o va all'indietro l'uscita è silenziosa. Se saltate, il segnale riparte subito alla nuova ora.
4. Se OpenCue stesso segue una sorgente LTC o MIDI, il clock viene inoltrato anch'esso.

**Se non arriva nulla:** controllate la barra del livello (troppo basso?), il canale (sinistro / destro), se l'ingresso è usato da un altro programma.

---

## 9. Note

- Una **sorgente LTC o MIDI guida** il clock: Start / Stop nel pannello Timecode vengono scavalcati dalla sorgente finché è attiva.
- Le ore appartengono ai **cue**, alle **tracce di comandi** e ai **lettori multimediali** dello show e vengono salvate con esso; l'editor timeline è solo lo strumento per questo.
- *Impostazioni → Ingressi e uscite* mostra nel gruppo **Timecode** a colpo d'occhio: chi guida il clock, lettura / invio LTC, timecode MIDI.
- Altro sulle sorgenti: guida **MIDI** (timecode MIDI), guida **Accesso remoto** (iPad), pannello **Timecode** (avvio, pausa, salto, velocità), **lettore multimediale** (ora di inizio).

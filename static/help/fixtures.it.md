# Apparecchi e patch

Un **apparecchio** è una luce che controllate: un dimmer, un par LED, una testa mobile. Per controllarlo, OpenCue deve sapere **che tipo di dispositivo è** (i suoi canali) e **dove ascolta** (il suo indirizzo DMX). Comunicare entrambe le cose a OpenCue si chiama **patch**. Questa guida vi accompagna attraverso la libreria apparecchi, il patch, i gruppi e il programmer.

---

## 1. L'idea in un minuto

- Un **tipo di apparecchio** descrive un modello di dispositivo: quanti canali DMX usa in quale modalità e cosa fa ogni canale (dimmer, pan, tilt, colore, gobo …). OpenCue usa per questo il formato standard **GDTF** – un piccolo file per dispositivo pubblicato dal produttore.
- Un **apparecchio** nel vostro show è un dispositivo reale di un tale tipo, con un **numero** (FID), un **nome**, un **universo** e un **canale iniziale** (l'indirizzo DMX che impostate sul dispositivo).
- Lo show memorizza gli apparecchi (tipo, modalità, indirizzo, nome, gruppo). I file GDTF stessi si trovano nella **libreria apparecchi** sul vostro computer.
- Tre tipi di apparecchio **integrati** sono sempre disponibili, anche senza alcun file GDTF: **Generic Dimmer** (1 canale), **Generic RGBW LED Par** (4 canali) e **Generic Moving Head Spot 16ch** (16 canali, con pan/tilt fine). Perfetti per provare.

---

## 2. Ottenere tipi di apparecchio: la libreria

Aprite **Libreria → Libreria apparecchi…**. La grande finestra ha queste schede:

| Scheda | Cosa mostra |
|---|---|
| **Installati** | Ogni file GDTF su questo computer come scheda: immagine di anteprima, nome, produttore, tipo, modalità, numero di canali, revisione e *In uso (N)* quando lo show lo usa. |
| **In questo show** | I tipi che lo show caricato usa, con il numero («4× nello show») e la revisione. Se il file di un tipo non è nella libreria, la scheda mostra *Sostituto integrato* o *File mancante*. Solo visualizzazione. |
| **Online (GDTF Share)** | Cerca nel database ufficiale GDTF (vedi sotto). |

Nella scheda *Installati* potete **cercare** per nome o produttore e filtrare per **tipo** (testa mobile, barra LED, PAR / wash, dimmer, strobo / blinder, effetto / fumo, altro – ricavato dai canali reali) e per **produttore**. Ogni scheda mantiene i propri filtri.

### Importare un file GDTF che avete già

Fate clic su **Importa file GDTF…** oppure **trascinate semplicemente il file** nella finestra. Il file deve essere un file GDTF valido (al massimo 30 MB). I file vengono copiati nella cartella `fixtures` all'interno della cartella dati di OpenCue (Impostazioni → Archiviazione mostra dove si trova).

### Scaricare da GDTF Share

GDTF Share (gdtf-share.com) è la raccolta ufficiale e gratuita di file GDTF di produttori e utenti.

1. Aprite la scheda **Online (GDTF Share)**.
2. **Accedete** con il vostro account GDTF Share. Per scaricare serve un account gratuito; nella finestra c'è un link *Crea un account gratuito*. La vostra password viene tenuta in memoria solo per questa sessione – a meno che non spuntiate *Resta connesso*, che la memorizza **cifrata su questo computer**.
3. Cercate, ordinate (nome, più recenti, più votati), filtrate per **file dei produttori** / valutazione. Ogni scheda mostra se il file è stato caricato **dal produttore** o **da un utente**, quante modalità ha (con il numero di canali) e quanto è grande.
4. Fate clic su **Dettagli** per **guardare un apparecchio prima di installarlo**: il file viene caricato solo temporaneamente (non installato) e si apre nella stessa vista di dettaglio dei tipi installati – con tutti i canali, le ruote e il modello 3D. **Installa** e **Torna alla ricerca** sono in alto. Oppure fate subito clic su **Installa**.
5. La scheda mostra poi *Installato*. Se in seguito compare una revisione più recente, viene offerto un pulsante **Aggiorna**.

Questo è l'unico posto in cui OpenCue usa internet per gli apparecchi; tutto il resto funziona offline. OpenCue non include file GDTF di GDTF Share, perché i loro termini non consentono la ridistribuzione – li scaricate voi stessi.

### Dettagli di un apparecchio

Fate clic su una scheda per aprirne i **dettagli**:

- **Panoramica** – dati di base, ottica per fascio (tipo di fascio, lampada, potenza, flusso luminoso, temperatura di colore, angolo del fascio e del campo), connettori, emettitori.
- **Anteprima 3D** – l'apparecchio come modello 3D. Trascinate per ruotare, rotellina o due dita per zoomare, trascinamento con il tasto destro per spostare, doppio clic per reimpostare. Pulsanti *Obliqua / Fronte / Lato / Alto*, interruttori per il *fascio di luce* e una *griglia*, e **cursori Pan / Tilt** per muovere una testa mobile. Senza un file 3D nel GDTF, OpenCue disegna le forme di base (cilindro, forcella, testa …) con le dimensioni indicate.
- **Canali DMX** – il selettore di modalità e una tabella di tutti i canali con funzioni e intervalli di valori.
- **Gobo e colori** – ogni ruota con i suoi slot: motivi dei gobo come immagini, slot colore come campioni.

### Rimozione e aggiornamento

- **Disinstalla** (chiede una seconda volta) rimuove un tipo dalla libreria – ma viene **rifiutato finché lo show lo usa ancora**.
- **Aggiorna** installa una revisione più recente. Se lo show usa quella vecchia, la vecchia revisione resta installata.

---

## 3. Aggiungere apparecchi allo show (patch)

Gli apparecchi si creano nel pannello **Elenco apparecchi**.

1. Nel pannello **Elenco apparecchi** fate clic su **Aggiungi apparecchi**.
2. **Tipo di apparecchio** – sceglietene uno con *Seleziona tipo...* (produttore → dispositivo → modalità, più una ricerca) o uno dei generici integrati.
3. **Modalità** – la modalità DMX del dispositivo (decide il numero di canali).
4. **Nome** (facoltativo) – ad esempio «Testa»; vuoto significa il nome del tipo. Con più apparecchi OpenCue numera i nomi.
5. **Quantità** – quanti apparecchi identici aggiungere. Vengono collocati **uno dopo l'altro** su indirizzi consecutivi.
6. **Universo** e **Canale iniziale** – l'indirizzo del primo. Deve corrispondere all'indirizzo impostato sul dispositivo (display o DIP switch).
7. Fate clic su **Aggiungi apparecchi**.

La finestra vi avvisa se l'ultimo apparecchio finirebbe oltre il canale **512** di un universo («l'indirizzo finale supera 512 … Riducete la quantità o l'indirizzo iniziale»). Un universo contiene 512 canali; per averne di più usate l'universo successivo.

Ogni apparecchio riceve un **FID** stabile (numero dell'apparecchio) usato dalla riga di comando (`Fixture 1 Thru 5`).

### Molti apparecchi in una volta: un elenco da CSV o Excel

La finestra *Aggiungi apparecchi* ha in fondo **Importazione avanzata ...** (anche nel menu **Libreria → Importa elenco apparecchi**). Con essa create un intero impianto da una tabella:

1. **Scegli file ...** – un file `.csv` o Excel (`.xlsx`). La **prima riga** contiene i titoli delle colonne. Serve solo il **tipo**; *nome*, *modalità*, *universo*, *indirizzo*, *numero* (FID) e *quantità* sono facoltativi. **Scarica il patch attuale come CSV** vi dà un modello.
2. OpenCue **indovina le colonne** (titoli come *Name*, *Type*, *Device*, *Universe*, *Address*, *Count* ...); potete modificare ogni assegnazione. Un indirizzo può anche essere `2.045` o `2/45` (universo 2, indirizzo 45). Se l'indirizzo manca, prosegue dopo il dispositivo precedente dello stesso universo.
3. L'**anteprima** mostra ogni riga – in rosso con il motivo quando qualcosa non va (tipo sconosciuto o ambiguo, modalità sconosciuta, non entra nell'universo, numero già usato). **Tipo quando la cella è vuota** e **Universo quando manca** colmano le lacune.
4. **Importa** crea gli apparecchi. In caso di problemi spuntate prima **Salta le righe con problemi**. Prima di allora non viene creato nulla.

### L'elenco apparecchi e la scheda Apparecchi

Due posti mostrano i vostri apparecchi:

- Il pannello **Elenco apparecchi** è la tabella del patch: una riga per apparecchio con FID, nome, tipo, universo, indirizzo e numero di canali, più il pulsante **Aggiungi apparecchi**.
- La scheda **Apparecchi** del pannello **Controllo apparecchi** mostra gli stessi apparecchi come griglia di riquadri (come su una console luci) per selezionare rapidamente.

| Azione | Come |
|---|---|
| Selezionare | Clic / tocco su una riga o un riquadro |
| Selezionarne diversi | Nella griglia di riquadri trascinate un **lazo** sui riquadri (mouse e touch) |
| Modificare un apparecchio | Clic destro / pressione lunga → **Modifica apparecchio…** |
| Eliminare | Selezionate, premete `Canc` o usate il menu contestuale (chiede conferma) |

### Modifica apparecchio

Una sola finestra cambia tutto: **Nome**, **Universo**, **Canale iniziale**, **Gruppo** e un **Indice di ordinamento** libero.

- L'indice di ordinamento decide dove compare il riquadro. Vuoto significa il FID; un numero (decimali ammessi, ad esempio 2,5) lo colloca di conseguenza.
- Un apparecchio appartiene al massimo a **un gruppo**.
- Con **più apparecchi selezionati** il menu offre anche *Sposta N apparecchi nel gruppo…*.

Cambiare l'indirizzo cambia il punto in cui OpenCue invia i dati – fatelo quindi quando spostate un dispositivo su un altro indirizzo.

---

## 4. Gruppi

I gruppi sono puramente organizzativi: ordinare e selezionare più apparecchi con un clic o un comando. Vengono memorizzati con lo show.

- **Creare:** nella scheda **Apparecchi** del pannello Controllo apparecchi, clic destro / pressione lunga sull'area vuota → *Aggiungi nuovo gruppo…* e inserite un nome (i nomi sono univoci, senza distinzione tra maiuscole e minuscole).
- **Riempire:** il menu a discesa *Gruppo* in *Modifica apparecchio…*, oppure *Sposta N apparecchi nel gruppo…* per una selezione.
- **Selezionare:** fate clic sul gruppo, oppure usate la riga di comando: `Group Front`, `Group 1 Thru 4`.
- **Da una selezione:** `Store Group "Front"` memorizza la selezione attuale come gruppo (vedi *Riferimento dei comandi*).

---

## 5. Controllare gli apparecchi: il pannello Controllo apparecchi

Selezionate gli apparecchi, poi usate il pannello **Controllo apparecchi** (sulle console spesso chiamato «Programmer»). Un pannello può mostrare tutto (una barra laterale con tutte le categorie) o una sola categoria (*Proprietà pannello → Visualizzazione*).

| Categoria | Controlli |
|---|---|
| **Apparecchi** | La griglia di riquadri per selezionare; commutare **Elenco / Layout** (vedi sotto) |
| **Dimmer** | Fader e pulsanti rapidi |
| **Posizione** | Commutare **Grossolano / Fine**. *Grossolano*: fader pan/tilt, **Centro / Home / Inverti**, campi numerici in gradi. *Fine*: i canali fini (16 bit) come campi numerici; scorrete un campo numerico verso l'alto o il basso per modificarlo con precisione. Gli apparecchi senza canali fini agiscono a 8 bit. |
| **Colore** | **Fader** (HSV, CMY o RGB) o **Selettore colore** (ruota dei colori) |
| **Fascio** | Sottopagine **Shutter/Strobe** (aperto, chiuso, lento, veloce, strobo, impulso …), **Gobo** (con miniature della ruota), **Prisma** |
| **Focus** | Fuoco e zoom |
| **DMX diretto** | Ogni canale della modalità come fader a sé (per numero di canale, 0–255) |

Ogni canale descritto dal file GDTF riceve un controllo, così potete raggiungere anche funzioni insolite (frost, iride, ruote colori, velocità).

**Puntare a un punto (3D):** se gli apparecchi sono collocati nella **Simulazione 3D**, il riquadro posizione offre *Imposta punto nella simulazione 3D*: toccate un bersaglio nella vista 3D e le teste mobili selezionate lo puntano. Nel riquadro focus, *Focus automatico (3D)* e *Zoom automatico (3D) …* impostano fuoco e zoom dalla distanza da quel punto.

### Cosa vi dice il colore dei controlli

I controlli mostrano sempre ciò che viene emesso in quel momento (gli stessi valori del monitor DMX) – anche mentre un cue o un effetto è in esecuzione. Una sottile linea colorata accanto a un apparecchio o a una scheda di categoria mostra cosa è **cambiato rispetto al cue attivo** – operato a mano o da un *Clear* che ha reso tutto buio. *Store Cue* memorizza sempre la differenza rispetto al cue che verrebbe riprodotto prima (anche inserendo con `2.5`). Dopo la memorizzazione, il nuovo cue è quello attivo e le linee scompaiono. Con più liste di cue conta il cue attivo della lista usata più di recente.

---

### Apparecchi: elenco o layout

In alto nella scheda **Apparecchi** si commuta tra due viste (come *Colore* tra Fader / Selettore / Ruota):

- **Elenco:** i riquadri ordinati per gruppi e numeri.
- **Layout:** ogni apparecchio è un **riquadro quadrato** su una griglia. Disponete gli apparecchi come sono appesi sul palco e raggiungeteli più in fretta. I riquadri mostrano lo stesso dell'elenco (numero, luminosità, anteprima di colore e fascio).

Nel layout:

- **Selezionare** come nell'elenco: clic o uno **scorrimento** (lazo) sull'area vuota.
- **Area illimitata:** continua in **ogni direzione** (anche a sinistra e in alto; le posizioni possono essere negative). Spostate la vista con la rotellina / le barre di scorrimento / lo scorrimento, **trascinate con il tasto centrale**, oppure andate al bordo mentre trascinate un riquadro. **Ctrl + rotellina** zooma.
- **Mostra tutto:** il pulsante in alto a destra zooma e centra in modo che **tutti gli apparecchi** siano al centro.
- **Viste (aree):** *Salva vista…* (clic destro) memorizza il centro e lo zoom attuali con un nome, ad esempio «Palco sinistra». In alto compare un pulsante; un clic vi salta, clic destro sul pulsante: sovrascrivi, rinomina, elimina. Con molti apparecchi non dovete tenere tutto in vista contemporaneamente.
- **Clic destro** (touch: pressione lunga) sull'area libera o su un riquadro apre il menu: *Modalità costruzione*, *Mostra tutto*, *Salva vista…*, *Griglia* (riquadro intero, metà o quarto), *I riquadri possono sovrapporsi*, *Reimposta zoom*, *Riorganizza tutti gli apparecchi…*.
- **Modalità costruzione:** trascinare sposta un riquadro; con più selezionati si spostano insieme. I riquadri si agganciano alla griglia; senza *Sovrapposizione* non si coprono mai, con *Sovrapposizione* potete incastrarli (l'ultimo spostato sta sopra) e sfalsarli di poco con la griglia fine (1/4). L'area vuota seleziona ancora con lo scorrimento. **Fatto** o **Esc** termina la modalità costruzione.
- **Memorizzato nello show:** le posizioni, la risoluzione della griglia, la *Sovrapposizione* e le viste salvate. **Sul vostro dispositivo** (non nello show): lo zoom, l'ultimo centro mostrato e l'ultima sottovista usata.

**Viste ricordate:** ovunque un pannello commuti tra viste, il vostro dispositivo ricorda l'ultima e la ripristina la volta successiva: in Controllo apparecchi (Elenco / Layout, Fader / Selettore / Ruota, Strobe / Gobo / Prisma, Grossolano / Fine), in *Variabili / Effetti* (variabili o effetti, filtro di tipo, ordinamento), nello *Studio effetti* (anteprima attiva / disattiva), nella *Simulazione 3D* (Vista / Costruzione / Apparecchi) e nel selettore di effetti (categoria e tag come *Base*).

## 6. Variabili ed effetti (preset)

Il pannello **Variabili / Effetti** contiene valori riutilizzabili: un colore «Bianco caldo», una posizione «Fronte», un fascio «Largo». Una variabile è un **riferimento vivo**: applicatela agli apparecchi e la seguono; cambiate la variabile in seguito e tutti gli apparecchi che la usano cambiano con essa – compresi i cue che la usano. Gli effetti sono piccoli programmi che cambiano valori nel tempo; vedi la guida *Studio effetti*.

---

## 7. Apparecchi e file dello show

- Un file show memorizza gli apparecchi **con** il loro tipo, modalità, indirizzo e gruppo, oltre a cue, effetti, variabili e preset.
- I file GDTF **non** sono nello show – ma quando **esportate uno show** (gestore file → esporta), i file GDTF e gli script di effetti che lo show usa vengono impacchettati nello ZIP, così potete aprire lo show su un altro computer senza installare nulla. All'importazione un file locale con lo stesso nome non viene mai sostituito.
- **Stampa / PDF** (menu File): documentazione dello show per i tecnici – **elenco del patch**, **mappa dei canali DMX** (quale apparecchio occupa quali canali di ogni universo, sovrapposizioni in rosso), **gruppi**, **pianta (vista dall'alto)** degli apparecchi (dal palco 3D, altrimenti dalla vista layout) e **liste di cue**. La finestra mostra un'**anteprima** del PDF accanto alle scelte (segue ogni modifica delle scelte e del formato carta; sugli schermi piccoli l'anteprima viene omessa). I nomi lunghi vengono **mandati a capo** nelle tabelle e nella pianta (un nome molto lungo senza spazi viene spezzato). Nella pianta ogni apparecchio porta il suo numero, e un elenco sotto la pianta dice quale numero è quale apparecchio; i nomi degli oggetti di palco stanno dentro la loro forma. *Salva come PDF* scarica il file, *Apri per stampare* lo mostra nel visualizzatore PDF (stampate lì con Ctrl+P).
- **File show `.ocshow`:** *File → Esporta show* scrive un file `.ocshow` (uno ZIP con lo show e i suoi file). Un **doppio clic** lo apre in OpenCue (l'installatore lo configura; per la versione non installata usate *Impostazioni → Generale → Apri i file .ocshow con OpenCue*). Se OpenCue è già in esecuzione, prende il file e chiede prima delle modifiche non salvate. **File → Apri recenti** elenca gli ultimi show.
- **Palco 3D come JSON:** nel pannello 3D (modalità *Costruzione* o *Apparecchi*) portate la barra laterale da **Strumenti** a **JSON** (interruttore sotto il pulsante Salva; il pulsante *Modifica come JSON* in fondo agli strumenti fa lo stesso). Gli strumenti (aggiungere corpi, elenco, proprietà) vengono sostituiti dal testo del palco (stanza, oggetti, posizioni degli apparecchi; metri, gradi, Z in alto; apparecchi per numero); nome del palco, annulla e **Salva** restano uguali, **Strumenti** riporta la vista normale. **La larghezza della barra laterale si può cambiare:** trascinate il suo bordo sinistro (doppio clic = larghezza standard); la larghezza viene ricordata come quota del pannello (al massimo tre quarti), così resta proporzionale a schermo intero. Le modifiche vengono controllate e **applicate in diretta** (un errore di sintassi indica la riga e non cambia nulla); ciò che spostate nella vista 3D compare nel testo. *Salva* salva il palco, *Chiudi JSON* riporta la barra laterale. Lo stesso testo è disponibile come finestra in *Libreria → Modifica palco 3D come JSON* (con *Controlla* e *Applica*).
- Se uno show usa un tipo di apparecchio il cui file manca, OpenCue usa un sostituto integrato così lo show funziona comunque; la scheda *In questo show* lo mostra come *Sostituto integrato* o *File mancante*.

---

## 8. Suggerimenti rapidi

- **Iniziate con un generico:** aggiungete alcuni apparecchi *Generic Dimmer* per imparare il programmer, i cue e la riga di comando prima di cercare veri file GDTF.
- **Fate corrispondere gli indirizzi:** il canale iniziale in OpenCue deve essere uguale all'indirizzo sul dispositivo. Le teste mobili di solito richiedono un blocco di canali (ad esempio 16 canali), quindi l'apparecchio successivo parte 16 canali più avanti – OpenCue lo calcola per voi quando aggiungete una quantità.
- **Più modalità:** molti dispositivi offrono più modalità (ad esempio 8 bit e 16 bit). Scegliete la modalità su cui il dispositivo è realmente impostato.
- **Manca un dispositivo?** Cercate su GDTF Share per produttore; se il modello non c'è, partite dal più vicino o usate *Generic* e costruite i vostri cue.

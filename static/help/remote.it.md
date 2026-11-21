# Accesso remoto (tablet e telefono)

Con l'**accesso remoto** usi OpenCue da un iPad, un tablet, un telefono o qualsiasi altro computer nella **stessa rete** – mentre il computer console continua a eseguire lo show e a inviare il DMX. Cammina per la sala e regola le luci, avvia cue dal palco, oppure usa un tablet come secondo schermo.

L'accesso remoto è **spento per impostazione predefinita**. Finché è spento, OpenCue non è raggiungibile dalla rete in alcun modo (la porta è davvero chiusa, non solo protetta da password).

---

## 1. L'idea in un minuto

- La **console** è il computer in cui OpenCue è installato e in esecuzione. Fa tutto il lavoro: contiene lo show, calcola le cue e invia il DMX.
- Un **dispositivo remoto** è semplicemente un browser. Apre un indirizzo web della console, accede con la password e mostra **la stessa interfaccia di OpenCue** – stessa barra, stessi pannelli, stessi diritti.
- Tutto resta sincronizzato dal vivo: quando selezioni un apparecchio, muovi un fader o premi *Go* su un dispositivo, tutti gli altri lo mostrano subito.
- Non serve Internet. Tutto avviene nella tua rete locale.

---

## 2. Attivarlo

1. Sulla console apri **Impostazioni** (barra degli strumenti) → categoria **Accesso remoto**.
2. Attiva l'**interruttore principale dell'accesso remoto** in alto. **Non c'è una password predefinita:** la prima volta OpenCue chiede la tua – **“Scegli una password”**, inserita due volte (almeno 4 caratteri; *Annulla* disattiva di nuovo l'accesso remoto). Dopo, **HTTP** è attivo.
3. La **password** si imposta e si cambia in **Impostazioni → Sicurezza** (pulsante *Imposta o cambia password ...* nella sezione Accesso remoto); funziona anche da un dispositivo remoto (il suo accesso viene mantenuto; tutti gli altri dispositivi devono riaccedere). Usa *Mostra* per controllare cosa hai scritto. La stessa password protegge il blocco schermo (sezione 8). È permessa qualsiasi password (almeno 4 caratteri) – la scelta è tua.
4. Se vuoi, cambia la **porta HTTP** (1024–65535, predefinita 8000). Una porta modificata ha effetto dopo il riavvio di OpenCue.
   **HTTPS** è una sezione a sé più sotto con il proprio interruttore e la propria **porta HTTPS** (predefinita 8001, effetto immediato): alcune funzioni del browser richiedono una **pagina sicura (https)**: **tenere acceso lo schermo dell'iPad** (Impostazioni → Altre opzioni → *Mantieni lo schermo acceso*), la modalità VR della simulazione 3D, e microfono e fotocamera nel browser. Apri quindi l'**indirizzo https://** sull'iPad (conferma il certificato una volta); con `http://` funziona solo l'impostazione del dispositivo “Blocco automatico: Mai”. OpenCue crea da solo il certificato; il browser chiede di confermarlo una volta alla prima visita. HTTP e HTTPS si attivano e disattivano indipendentemente e ciascuno ha il proprio indirizzo con il proprio codice QR.
   **Nome di rete:** la console è raggiungibile anche come `opencue.local` (arriva automaticamente con l'accesso remoto; un piccolo interruttore in *Avanzate*), per esempio `http://opencue.local:8000` – l'indirizzo resta lo stesso in ogni rete. Se il nome è già occupato (per esempio da una seconda console), OpenCue usa `opencue-2.local` e così via; le impostazioni mostrano quale vale. iPad, iPhone, Mac e Windows 10/11 capiscono il nome da soli. Una web app installata è legata al suo indirizzo: se passi al nome, installala ancora una volta.
5. Clicca su **Salva** (la finestra resta aperta). Non serve riavviare. La prima volta Windows chiede una volta del firewall – consenti le **reti private**.

OpenCue ora ascolta su ogni indirizzo di rete della console. La pagina mostra:

| Voce | Significato |
|---|---|
| **Stato** | “Raggiungibile in rete” oppure “Solo locale”. |
| **Indirizzi** | Ogni indirizzo con cui la console è raggiungibile, ciascuno con un pulsante **Copia**. |
| **Codice QR** | Per l'indirizzo selezionato – scansionalo con la fotocamera di un iPad o di un telefono. Alla connessione viene chiesta la password. |
| **Rileva di nuovo gli indirizzi** | Dopo aver cambiato Wi-Fi o collegato un cavo. |

Quando lo spegni di nuovo, gli ascoltatori vengono richiusi subito.

> **Firewall di Windows:** quando l'accesso remoto viene attivato per la prima volta, Windows può chiedere se OpenCue può comunicare in rete. Consentilo per la tua rete **privata**; altrimenti gli altri dispositivi non possono connettersi.

---

## 3. Collegare un dispositivo

1. Assicurati che il dispositivo sia nella **stessa rete** (stesso Wi-Fi o LAN) della console.
2. Apri l'indirizzo della pagina delle impostazioni nel browser del dispositivo – per esempio `http://192.168.1.20:8000/` – oppure scansiona il codice QR. L'indirizzo reindirizza alla pagina remota `/remote/`.
3. Inserisci la password e tocca **Accedi**.

**Ricorda la password** (casella nella pagina di accesso) memorizza la password nel browser di **quel dispositivo soltanto** e precompila il campo la volta successiva. Non c'è accesso automatico – tocchi comunque *Accedi*. Deseleziona la casella per cancellare subito la password memorizzata.

**Password errata:** tentativi errati ripetuti bloccano il dispositivo per un po' (protezione contro la forza bruta).

**Esci dall'account:** *File → Esci dall'account* (mostrato solo sui dispositivi remoti).

Se non si connette nulla: controlla che entrambi i dispositivi siano nella stessa rete (le reti Wi-Fi per ospiti spesso separano i dispositivi tra loro), che l'indirizzo corrisponda a quello della pagina delle impostazioni, e il firewall (vedi sopra).

---

## 4. Cosa può fare un dispositivo remoto

- **Tutto ciò che può fare la console.** Dopo l'accesso, un dispositivo remoto ha gli stessi diritti: programmazione, cue, effetti, file, impostazioni, impostazioni DMX e impostazioni dell'accesso remoto. Questo include cose con conseguenze – disattivare l'accesso remoto (che esclude quel dispositivo) o **chiudere OpenCue**, il che ferma il programma per tutti. Usa una password che conoscono solo persone di fiducia.
- **Layout proprio per dispositivo.** Ogni dispositivo ricorda quale layout ha usato e può mostrarne uno diverso dalla console. Crea per il tablet un layout con pulsanti grandi (vedi sotto). Se un dispositivo salva un layout che un altro sta mostrando, l'altro lo adotta – oppure, se ha modifiche proprie non salvate, offre *Applica* o *Mantieni la mia versione*.
- **Accesso completo a tutte le impostazioni, anche dall'iPad.** Questo conta quando OpenCue gira senza finestra (*solo server*, icona nell'area di notifica): tutte le impostazioni – uscita, sicurezza e modalità blocco, API REST, assistente IA, controllo vocale, backup, avvio con Windows, predefiniti, ingressi / uscite ... – si cambiano dall'iPad e valgono **per il server**. Anche l'interruttore del microfono del controllo vocale è presente sull'iPad. **Cartelle:** dove il computer principale aprirebbe Esplora risorse di Windows, un dispositivo remoto ottiene l'**Esplora risorse di OpenCue** – una grande finestra per la cartella dei dati di OpenCue (show, backup, registri, apparecchi ...): sfogliare, scaricare (una cartella come ZIP), caricare, nuova cartella, rinominare, duplicare, eliminare. Non può uscire dalla cartella dei dati. La stessa finestra (*Scegli cartella...*) permette di scegliere una nuova posizione di archiviazione. Anche l'**apprendimento / il monitoraggio MIDI**, l'**ingresso DMX** e la **regola del firewall** (Windows chiede il permesso sul computer principale) funzionano dall'iPad. Solo poche cose dipendono **fisicamente dal computer principale**: la sua finestra (schermo intero), il **blocco schermo** della console (sbloccarlo lì), la registrazione del tasto di una **tastiera specifica**, il **microfono durante la dettatura** e il vero Esplora risorse di Windows.
- **Per dispositivo:** solo la **modalità schermo intero** (quella di ciascun browser) e la **scala dell'interfaccia**.
- **I dati restano sulla console.** Salvare e caricare passano sempre dalla console; show, layout e apparecchi vivono sul computer console.

### Chi è collegato?

Un'icona della barra degli strumenti mostra **quanti dispositivi remoti sono collegati**. Cliccala per vedere indirizzo IP, dispositivo e durata del collegamento di ciascuno – e per **scollegare** (*Espelli*) un dispositivo. Un dispositivo scollegato vede un avviso e deve ricaricare la pagina per riaccedere.

---

## 5. Installare come app (iPad / iPhone / Android)

La pagina remota è una **web app**. Sul dispositivo puoi aggiungerla alla schermata Home:

- **iPad / iPhone (Safari):** pulsante Condividi → **Aggiungi a Home**.
- **Android (Chrome):** menu → **Installa app** / **Aggiungi a schermata Home**.

Si apre poi a schermo intero senza barre del browser, con i colori del tuo tema attuale.

**Icona:** l'app riceve l'icona di OpenCue e il nome “OpenCue” – anche tramite HTTPS. (L'icona è incorporata nella pagina; altrimenti iOS non la scarica con un certificato autocreato e mostra solo una lettera grigia.) Se l'icona non cambia ancora, elimina l'app dalla Home e aggiungila di nuovo – iOS ricorda la vecchia icona.

**Pagina offline e scelta del server (pagina sicura, HTTPS):** quando il server non è raggiungibile, l'app mostra “**Server non raggiungibile**” invece di una pagina di errore. Lì puoi **Ricaricare**, oppure inserire un nuovo **indirizzo o IP**, la **porta** e **HTTPS** on / off in **Altro server** e **Connettere** – se il computer ha un nuovo indirizzo IP non devi reinstallare l'app. Gli indirizzi usati di recente sono elencati sotto da toccare. Se la connessione cade (Wi-Fi sparito, OpenCue chiuso), compare l'avviso “Ripristino della connessione”; dopo 3 secondi con il pulsante “**Scegli un altro server (7s)**” il cui numero **conta alla rovescia**; a 0 la pagina offline si apre da sola e ricarica OpenCue appena il server risponde. Vale anche quando il Wi-Fi c'è ma il computer non risponde – allora la pagina offline compare dopo **circa 1,5 secondi** invece di una schermata bianca e scompare subito quando il server risponde. Se la apri di proposito con il pulsante, resta. Suggerimento: il nome `opencue.local` trova il computer anche quando l'IP cambia.

**Importante sull'iPad – installa il certificato una volta:** con un certificato autocreato, iOS conosce l'eccezione “continua nonostante l'avviso” solo **dentro la scheda di Safari**. Un'app dalla schermata Home resta allora **bianca**, e il service worker (pagina offline) non è consentito. Per questo OpenCue crea una propria autorità di certificazione (“OpenCue Local CA”) che firma il certificato https. La installi **una volta** sul dispositivo:

I passaggi sono una **pagina guida** sul server: *Impostazioni → Accesso remoto → Certificato per iPad e browser* ne mostra l'indirizzo e un codice QR (scansionalo con la fotocamera dell'iPad). La pagina si apre via **http://** senza accesso e segue la lingua del dispositivo. In alto scegli tra **iPad / iPhone** e **Android · Windows · macOS**. Per l'iPad ci sono quattro passaggi con un promemoria: **Scarica → Installa → Autorizza → Apri https**; puoi spuntare i passaggi completati (la pagina li ricorda). **Importante: apri la pagina in Safari** – il profilo non si può installare dall'app della Home, da Chrome o dal browser dentro un'altra app. “Impostazioni” significa l'**app Impostazioni dell'iPad**, non un'impostazione di Safari. In fondo a ogni pagina è spiegato come **rimuovere di nuovo il certificato** (iPad: Impostazioni → Generali → VPN e gestione dispositivo → “OpenCue” → Rimuovi profilo). In OpenCue la stessa cosa si trova in *Impostazioni → Accesso remoto → Certificato per iPad e browser* (versione breve per installare e rimuovere). (L'accesso via HTTP deve essere attivo per questo.)

Da allora https funziona senza avviso, l'app si apre, il service worker e la pagina offline funzionano – anche quando il computer riceve un **nuovo indirizzo IP** (OpenCue riemette solo il certificato del server, l'autorità resta). L'autorità può garantire solo per nomi locali (`.local`, `localhost`) e indirizzi privati. Android / Windows / macOS: installa il file del certificato (`opencue-ca.crt`) e impostalo come autorità attendibile. Se elimini la cartella `https` nella cartella dei dati, viene creata una nuova autorità – reinstalla il profilo sui dispositivi.

**Limite:** le web app installabili e la pagina offline richiedono una connessione sicura (HTTPS, sull'iPad con il certificato installato). Con semplice `http://` l'app della Home funziona, ma non c'è pagina offline e il dispositivo deve raggiungere la console per mostrare qualcosa.

---

## 6. Consigli per un buon layout da tablet

- Crea un **layout separato** per il tablet (*Modifica → Gestisci layout…*): un grande **Executor**, la **Lista cue**, alcuni pannelli **Pulsante** o **Fader** e la categoria del **Controllo apparecchi** che ti serve di più. I dispositivi remoti caricano il proprio layout, quindi il layout della console resta com'è.
- Per il touch usa i pannelli **Tastierino numerico comandi** e **Pulsanti comando** invece di scrivere con la tastiera sullo schermo.
- Aumenta la **scala dell'interfaccia** sul tablet (`Ctrl +` o *Visualizza → Scala dell'interfaccia…*) – vale solo per quel dispositivo.
- I layout si possono cambiare **scorrendo** in orizzontale se *Impostazioni → Generale → Cambia layout con lo scorrimento* è attivo (per dispositivo).
- Le liste di cue con trigger timecode continuano a girare sulla console anche se un dispositivo si scollega – lo show non dipende dal tablet.

---

## 7. Sicurezza e buone pratiche

- Usa l'accesso remoto solo in reti di cui ti fidi (il tuo router, una rete dedicata allo show). La connessione **non è cifrata** (HTTP semplice); chiunque nella rete potrebbe leggere il traffico.
- Scegli una password che non usi altrove – è memorizzata nella configurazione dell'app sulla console e, se spunti *Ricorda la password*, nel browser di quel dispositivo.
- Spegni l'accesso remoto quando non serve.
- L'uscita DMX gira sempre sulla console – anche se tutti i dispositivi remoti si scollegano, le luci restano come sono.

## 8. Blocco: blocco schermo e uscita dall'account

**Impostazioni → Sicurezza** contiene la **modalità blocco** (spenta per impostazione predefinita, richiede la password):

- **Alla console:** il **lucchetto** nella barra in alto, **Ctrl+L** (modificabile in *Controlli → Scorciatoie da tastiera*) o **Controlli → Blocca** blocca OpenCue. Una console bloccata mostra solo una finestra scura per la password – il resto dell'interfaccia è nascosto, la tastiera non fa nulla, e la console non accetta più modifiche da questa finestra (nemmeno aggirando l'interfaccia). Un ricaricamento **non** sblocca. **Lo show continua:** cue, effetti, MIDI, OSC, la pianificazione e i dispositivi remoti funzionano come prima. Cinque password errate di fila sospendono lo sblocco per un minuto. La password non lascia mai la console mentre è bloccata. Riavviare OpenCue sblocca.
- **A un dispositivo remoto:** il lucchetto **fa uscire il dispositivo dall'account**: la sessione termina, la *password ricordata* di quel dispositivo viene cancellata, e la pagina mostra di nuovo l'accesso con un campo password vuoto. I dispositivi remoti non possono cambiare la password né la modalità blocco.
- **Blocca automaticamente dopo ...** (da 1 a 60 minuti senza alcun input; spento per impostazione predefinita): la console si blocca da sola, i dispositivi remoti escono dall'account. Attenzione con un tablet che serve solo a visualizzare: lascia l'impostazione spenta per quelli.

## 9. Controllo semplice e modalità operatore (per consegnare la console a qualcun altro)

- Il **pannello “Controllo semplice”** (*Modifica → Aggiungi pannello → Input*) è la sorella semplice del pannello *Controllo apparecchi* e usa **tutto il pannello** con campi fissi in percentuale: a sinistra (38 %) **ogni apparecchio ha una propria tessera** (numero, nome, colore e luminosità dal vivo), ordinate per **gruppi** (toccare il nome del gruppo = selezionare tutto il gruppo; il resto ordinato per tipo; *Tutti* / *Nessuno* in alto); a destra **luminosità** (grande fader, *Off* / *Full*), **colore** (campo colore – tonalità da sinistra a destra, più bianco verso l'alto – più pulsanti colore), **movimento** (**joystick** a molla: spingi – più lontano, più veloce; lascia = stop; *Centro*), **zoom**, **gobo** come immagini, un grande pulsante **Blackout** e i **look**: *Arcobaleno*, *Cerchio* (pan / tilt), *Pulsazione*, *Strobo* – effetti standard pronti senza alcuna impostazione (toccare di nuovo = spento, *Look off* rimuove tutto; l'effetto viene aggiunto automaticamente allo show la prima volta). Un comando che le luci selezionate non hanno resta al suo posto ma è attenuato. Su un **pannello stretto** (sotto circa 720 px) passa a una **modalità compatta** con una scheda per area (*Luci | Luminosità | Colore | Movimento | Fascio | Look*; Blackout resta visibile). Nulla qui modifica i gruppi o lo show; selezione, valori ed effetti sono quelli dell'intero programma (programmer, cue, studio effetti). Crea un layout con solo questo pannello (o pochi altri) per la persona che deve operare.
- La **modalità operatore** (*Visualizza → Modalità operatore ...* o il pulsante joystick nella barra in alto; richiede la password, *Impostazioni → Sicurezza*): questo dispositivo può **solo usare** ciò che è sullo schermo – niente menu, niente barra in alto, niente impostazioni o altre finestre, niente scorciatoie da tastiera (scrivere in un campo di testo funziona ancora), niente spostamento o ricostruzione dei pannelli, niente cambio di layout o show. Si esce con il piccolo **lucchetto in basso a destra** e la password, oppure con **Ctrl+L**. Si avvia solo dal menu o dal pulsante (nessuna scorciatoia da tastiera). I **comandi** (riga di comando, tasti, widget) il server li esegue in modalità operatore solo se **servono a usare**; tutto ciò che modifica lo show (*Store, Update, Delete, Move, Label, Set*, tempi delle cue, creazione / rinomina / eliminazione di liste cue) viene rifiutato – anche dentro una catena di comandi. **Alla console il controllo vocale è spento in modalità operatore** (il microfono resta chiuso) e torna dopo se è attivato. Il **server lo impone**: da un dispositivo in modalità operatore si accettano solo messaggi di utilizzo (selezionare, impostare valori, cue, preset, timecode, riga di comando ...); i messaggi di programmazione, layout, show e impostazioni vengono scartati e le richieste di scrittura ricevono la risposta `423`. Un ricaricamento non esce dalla modalità. Funziona alla console e su ogni dispositivo remoto per conto suo (consegna un iPad con l'app in modalità operatore); riavviare OpenCue la termina. Cinque password errate di fila sospendono l'uscita per un minuto.
- **Da sapere:** la riga di comando, se la metti in quel layout, può eseguire qualsiasi comando – lasciala fuori da un layout per gli ospiti. I tasti di una tastiera aggiuntiva dedicata (*Scorciatoie da tastiera personalizzate*, specifiche del dispositivo) e i controller MIDI / OSC continuano a funzionare: appartengono allo show, non allo schermo.

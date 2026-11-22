# Codici di errore e risoluzione dei problemi

Quando qualcosa va storto, OpenCue non scompare semplicemente: mostra una piccola **finestra di errore** con una breve spiegazione e un **codice di errore** come `OC-1002`. Lo stesso codice viene scritto nel **file di registro**. Questa pagina spiega ogni codice: cosa significa e come risolverlo.

Se non riuscite a risolvere un problema, copiate i dettagli (vedi la sezione 1) e inviateli con la vostra domanda – il codice ci dice subito dove cercare.

---

## 1. La finestra di errore

La finestra ha un titolo, una breve spiegazione, il **CODICE ERRORE**, a volte un riquadro con dettagli tecnici, e questi pulsanti:

| Pulsante | Cosa fa |
|---|---|
| **Copia i dettagli** | Mette negli appunti tutto ciò che serve per una segnalazione di bug: codice di errore, versione di OpenCue, versioni di Windows e Python, il testo dell'errore e le **ultime 40 righe del registro**. Incollatelo in un'e-mail, in una issue di GitHub o in una chat con un assistente. (Scorciatoia: **Ctrl+C**) |
| **Apri cartella registri** | Apre in Esplora risorse la cartella con i file di registro. |
| **Apri file registro** | Apre il registro attuale (`opencue.log`) nel vostro editor di testo. |
| **Chiudi** | Chiude la finestra (anche **Esc** o la **×**). Se l'errore ha fermato OpenCue, il programma termina dopo la chiusura della finestra. |

Potete spostare la finestra dalla barra del titolo. La finestra di errore compare nella lingua di OpenCue (in inglese se non è determinabile); il testo copiato con *Copia i dettagli* è sempre in inglese, così che una segnalazione possa essere letta da chiunque.

---

## 2. Dove si trovano i file di registro

Ogni avvio di OpenCue scrive un registro:

| File | Contenuto |
|---|---|
| `opencue.log` | L'avvio **attuale**: tutto ciò che OpenCue segnala – messaggi, avvisi, errori con i loro codici e tracce di crash. |
| `opencue.previous.log` | Il registro dell'avvio **precedente**. Dopo un crash e un riavvio la causa si trova ancora qui. |

Si trovano nella cartella `logs` all'interno della cartella dati di OpenCue – normalmente `%LOCALAPPDATA%\OpenCue\logs` (digitatelo nella barra degli indirizzi di Esplora risorse). La finestra di errore la apre per voi.

**Cercare nel registro:** i codici sono scritti come `OC-1234`. Cercate `OC-` per trovarli tutti, oppure `OC-3` per i piccoli problemi di una singola funzione (sezione 5).

---

## 3. Problemi di avvio (OC-1xxx)

OpenCue controlla queste cose **prima** che parta qualsiasi altra cosa. La finestra dice cosa non va; OpenCue poi si chiude.

### OC-1001 – OpenCue è già in esecuzione

**Significato:** Per ogni cartella dati può girare un solo OpenCue alla volta. Un secondo si contenderebbe le stesse impostazioni, la stessa porta e la stessa uscita DMX.

**Cosa succede:** La finestra dell'OpenCue in esecuzione viene portata in primo piano e compare questa finestra. (Se l'OpenCue in esecuzione è un **server senza finestra**, vedi la guida *Opzioni di avvio e modalità server*: non compare alcun errore, il browser si apre invece sulla console in esecuzione.)

**Cosa fare:**
- Usate la finestra portata in primo piano. Se non la vedete, guardate sugli **altri schermi** e nella **barra delle applicazioni**.
- Avete appena chiuso OpenCue e ricevete comunque questo messaggio? Può servirgli qualche secondo per chiudersi. Aspettate un attimo e riavviate.
- Non si vede proprio nulla? Aprite **Gestione attività**, cercate `OpenCue` (o `python`/`pythonw` se avviato dal sorgente) e terminate il processo rimasto.
- Avanzato: per un secondo OpenCue separato (ad esempio per prove) impostate la variabile d'ambiente `OPENCUE_DATA_DIR` su un'altra cartella **e** assegnategli un'altra porta nel suo `app_config.json` (vedi OC-1002).

### OC-1002 – La porta di rete è già in uso

**Significato:** OpenCue ha un piccolo server integrato con cui parla la sua finestra. Gli serve una porta di rete libera (predefinita **8000**). Un altro programma usa quella porta. Senza questo controllo, la finestra di OpenCue mostrerebbe la pagina dell'*altro* programma.

**Cosa fare:**
1. Chiudete l'altro programma. Cause frequenti: un altro server web o strumento di sviluppo, o un processo OpenCue rimasto (vedi OC-1001, Gestione attività).
2. Per scoprire chi usa la porta, aprite un prompt dei comandi e digitate `netstat -ano | findstr :8000` (con il vostro numero di porta). L'ultima colonna è l'ID del processo; cercatelo in Gestione attività (scheda *Dettagli*).
3. Oppure lasciate che OpenCue usi un'altra porta: chiudete OpenCue, aprite in un editor di testo il file delle impostazioni indicato nella finestra (normalmente `%LOCALAPPDATA%\OpenCue\config\app_config.json`) e cambiate `"server_port": 8000` in un numero libero tra **1024 e 65535**, ad esempio `8010`. Se la riga manca, aggiungetela. Salvate e riavviate OpenCue. (Quando OpenCue è in esecuzione, potete cambiarla in **Impostazioni → Accesso remoto → Porta HTTP**.)

### OC-1003 – Microsoft Edge WebView2 Runtime non trovato

**Significato:** OpenCue mostra la sua finestra con il **Microsoft Edge WebView2 Runtime** gratuito. Windows 11 ce l'ha; Windows 10 di solito lo ha tramite Edge o Office, ma non sempre.

**Cosa fare:** Fate clic su **Apri la pagina di download**, installate il runtime *Evergreen* di Microsoft e riavviate OpenCue. Se siete sicuri che il runtime sia installato, fate clic su **Avvia comunque**. L'installatore di OpenCue scarica automaticamente il runtime quando manca e c'è internet.

### OC-1004 – La cartella dati non è utilizzabile

**Significato:** OpenCue salva impostazioni, show, layout e registri nella sua **cartella dati** (normalmente `%LOCALAPPDATA%\OpenCue`) e non riesce a crearla o a scriverci. La riga sotto la spiegazione mostra il motivo tecnico.

**Cosa fare:** Controllate che la cartella esista e che il vostro account Windows possa scriverci; che il disco non sia pieno, non sia di sola lettura e (per un'unità di rete o USB) sia collegato; che nessun antivirus o «accesso controllato alle cartelle» blocchi OpenCue. Se durante l'installazione è stata scelta una cartella dati personalizzata, assicuratevi che quell'unità sia disponibile. Anche il nome di una cartella che in realtà è un **file** esistente causa questo errore.

---

## 4. Errori imprevisti (OC-2xxx)

Sono errori che OpenCue non si aspettava – di solito un bug. **Copiate i dettagli e segnalateli.** Il testo dell'errore e il registro mostrano dove è successo.

### OC-2001 – OpenCue non è riuscito ad avviarsi

Un errore imprevisto ha fermato OpenCue durante l'avvio. Riavviate una volta. Se si ripresenta: copiate i dettagli e segnalatelo. Come rimedio provvisorio, la causa può essere un file di impostazioni danneggiato: chiudete OpenCue, rinominate `config\app_config.json` nella cartella dati in `app_config.old.json` e riavviate (OpenCue parte allora con le impostazioni predefinite; show e layout sono file separati e restano).

### OC-2002 – Un'attività in background è fallita

Qualcosa è andato storto in un'attività in background, ad esempio l'analisi audio, il MIDI o la rete. **OpenCue continua a funzionare.** La finestra compare solo per il *primo* errore di questo tipo a ogni avvio (tutti sono nel registro). Se qualcosa si comporta in modo strano, salvate lo show e riavviate OpenCue. Segnalatelo con i dettagli copiati.

### OC-2003 – Il server di OpenCue si è fermato

Il server integrato si è fermato in modo imprevisto o non è riuscito ad avviarsi, quindi la finestra non può funzionare. OpenCue si chiude dopo la finestra e prima rilascia l'uscita DMX e le telecamere. Riavviate OpenCue. Se succede di nuovo, segnalatelo; controllate anche OC-1002 (anche un problema di porta può finire qui).

### OC-2004 – OpenCue si è fermato in modo imprevisto

Si è verificato un errore imprevisto mentre OpenCue era in esecuzione e il programma deve chiudersi. **Le modifiche non salvate possono andare perse.** Riavviate OpenCue e segnalate l'errore con i dettagli copiati. Suggerimento: salvate regolarmente lo show (**Ctrl+S**) durante le sessioni lunghe.

---

## 5. Problemi di una singola funzione (OC-3xxx, solo registro)

Questi **non** aprono una finestra e OpenCue continua a funzionare. Compaiono all'inizio di una **riga del registro** (ad esempio `... [DMX] OC-3103 USB DMX: COM3 ...`) e spesso come messaggio nella pagina di impostazioni corrispondente. Cercate `OC-3` nel registro.

| Codice | Significato | Cosa fare |
|---|---|---|
| **OC-3001** | Il file delle impostazioni `app_config.json` non ha potuto essere letto. OpenCue ha usato il backup automatico (`.bak`) o, se era danneggiato anch'esso, le impostazioni predefinite. Il file danneggiato viene conservato accanto come `.corrupt`. | Controllate le vostre impostazioni. Per conservare impostazioni più vecchie, copiate i valori dal file `.corrupt` nel nuovo `app_config.json` (chiudete prima OpenCue). |
| **OC-3101** | Si è verificato un errore nel thread di uscita DMX. | Controllate le impostazioni DMX (Impostazioni → Uscita DMX) e la connessione di rete o USB. Segnalatelo se si ripete. |
| **OC-3102** | L'uscita Art-Net non ha potuto essere (ri)configurata con le impostazioni attuali. | Controllate la destinazione e l'indirizzo IP di binding nelle impostazioni DMX. La scheda di rete deve esistere ed essere connessa. |
| **OC-3103** | L'interfaccia DMX USB è stata scollegata o ha segnalato un errore di invio. | Ricollegatela e premete *Aggiorna porte* nelle impostazioni DMX. Provate un'altra porta USB o un altro cavo; controllate che nessun altro programma usi la porta. |
| **OC-3104** | Si è verificato un errore nel clock dell'uscita DMX (che invia i frame ad Art-Net, sACN e USB). | OpenCue continua a funzionare e il clock prosegue con il frame successivo. Segnalatelo se si ripete (Aiuto → Segnala un problema). |
| **OC-3105** | Il **processo di uscita DMX separato** (un secondo processo OpenCue in Gestione attività) è terminato o non è riuscito ad avviarsi. | OpenCue lo riavvia automaticamente (l'uscita torna in meno di un secondo). Se muore cinque volte in un minuto o non parte affatto, l'uscita continua all'interno del programma principale – senza la separazione, ma senza interruzione. Controllate l'antivirus (deve permettere a `OpenCue.exe` di avviare un secondo processo); segnalatelo se si ripete. |
| **OC-3201** | L'analisi audio non ha potuto aprire il suo ingresso o la sua sorgente (dispositivo occupato, rimosso o bloccato dalle impostazioni di privacy di Windows). | Scegliete un'altra sorgente nel pannello Audio. Chiudete i programmi che usano il dispositivo in modo esclusivo. Per un microfono consentite l'accesso in *Impostazioni di Windows → Privacy → Microfono*. |
| **OC-3202** | Il controllo vocale non ha potuto aprire il microfono selezionato (OpenCue riprova più volte). | Scegliete di nuovo il microfono in Impostazioni → Parola di attivazione; chiudete gli altri programmi che lo occupano; controllate l'impostazione di privacy del microfono di Windows. |
| **OC-3301** | Un dispositivo MIDI non ha potuto essere aperto. Sotto Windows la maggior parte dei dispositivi può essere usata da **un solo programma** alla volta. | Chiudete l'altro programma (software musicale, DAW) o disattivate lì il dispositivo. Scollegate e ricollegate il dispositivo. |
| **OC-3401** | Il nome `opencue.local` non ha potuto essere annunciato in rete (mDNS). I dispositivi remoti possono comunque usare l'indirizzo IP. | Usate l'indirizzo con il numero IP mostrato nelle impostazioni dell'Accesso remoto. Controllate che la rete consenta il multicast e che il firewall di Windows consenta OpenCue sulle reti private. |
| **OC-3402** | OpenCue non ha potuto mettersi in ascolto su un indirizzo di rete per i dispositivi remoti. | Un altro programma potrebbe usare quella porta, oppure l'indirizzo è scomparso (Wi-Fi cambiato). Disattivate e riattivate l'accesso remoto in Impostazioni → Accesso remoto, oppure scegliete un'altra porta. |
| **OC-3501** | L'aggiornamento non ha potuto essere scaricato o la somma di controllo non corrispondeva. | Controllate la connessione a internet e riprovate più tardi, oppure scaricate l'installatore dalla pagina delle release. |
| **OC-3502** | L'installatore di aggiornamento scaricato non ha potuto essere avviato. | Scaricate l'installatore dalla pagina delle release ed eseguitelo voi stessi. |
| **OC-3601** | L'interfaccia utente ha segnalato un errore JavaScript. La riga del registro mostra il messaggio, il file e la riga e su quale dispositivo è successo (la console o un dispositivo remoto). Spesso non si vede nulla; a volte un pannello resta vuoto. | Ricaricate la finestra (o la pagina sul dispositivo remoto). Se succede di nuovo, segnalatelo con *Aiuto → Segnala un problema* – la riga fa parte dei dettagli. |
| **OC-3701** | Un backup in background dello show non ha potuto essere scritto (disco pieno, cartella non scrivibile o protetta da un antivirus). Lo show stesso non è interessato. | Liberate spazio su disco o scegliete un'altra cartella dati (*Impostazioni → Generale → Cartella dati e gestione file*). *File → Ripristina backup* mostra quali backup esistono; la cartella è `backups` nella cartella dati. |
| **OC-3801** | OSC non ha potuto mettersi in ascolto sulla sua porta UDP (la usa un altro programma). | Scegliete un'altra porta in **Controlli → OSC ...** o chiudete l'altro programma. |

---

## 6. Segnalare un problema

1. Il più semplice: **Aiuto → Segnala un problema...** copia i dettagli negli appunti e apre la pagina di segnalazione. (Nella finestra di errore: **Copia i dettagli**.) **Aiuto → Apri cartella registri** apre la cartella con `opencue.log`.
2. Sulla pagina **Issues** del progetto OpenCue su GitHub descrivete cosa avete fatto prima dell'errore.
3. Incollate il testo copiato. Non contiene dati dello show, solo le informazioni tecniche descritte nella sezione 1.

Non inviate password o chiavi di accesso; se avete incollato righe del registro da una schermata di impostazioni, rimuovetele prima.

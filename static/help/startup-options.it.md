# Opzioni di avvio e modalità server

OpenCue può essere avviato con delle opzioni – in un collegamento, in un file batch, nell'Utilità di pianificazione o in un terminale. Questa guida le elenca, spiega la **modalità server senza finestra** (`--no-ui`), l'**avvio con Windows**, cosa cambiano (e cosa non cambiano) i **diritti di amministratore** e la regola del **firewall di Windows**.

---

## 1. Le opzioni

Mettetele dopo il programma: `OpenCue.exe --no-ui --open-browser` (dal codice sorgente: `python main.py ...`). In un collegamento: *Proprietà → Destinazione*, dopo le virgolette di chiusura del percorso.

| Opzione | Cosa fa |
|---|---|
| `--no-ui` o `--server-only` | Avvia **senza finestra del programma** (sezione 2). Implica `--no-splash`. |
| `--open-browser` | Con `--no-ui`: all'avvio apre il browser predefinito sulla console. |
| `SHOWFILE` o `--show FILE` | Carica questo show invece dell'ultimo. Un file di show come primo parametro funziona come un avvio con doppio clic; vale anche per un file `.ocshow` (pacchetto di esportazione). Se OpenCue è già in esecuzione, il programma in esecuzione prende il file (e chiede prima delle modifiche non salvate). |
| `--new-show` | Avvia con uno **show vuoto** invece dell'ultimo. Non viene eliminato nulla; lo show «usato per ultimo» resta com'era. |
| `--port N` | Porta del server **solo per questa esecuzione** (1–65535). L'impostazione salvata non cambia. |
| `--remote` | Attiva l'**accesso di rete** (come in *Impostazioni → Accesso remoto*) – questa impostazione viene **salvata**. |
| `--data-dir CARTELLA` | Usa un'altra **cartella dei dati** per questa esecuzione (uso portatile, test). Come la variabile `OPENCUE_DATA_DIR`. |
| `--fullscreen` | Avvia la finestra del programma a schermo intero. |
| `--priority normal`, `above` o `high` | Priorità del processo; predefinita `above` (superiore al normale), vedi la sezione 5. |
| `--no-splash` | Nessuna schermata iniziale (anche: `OPENCUE_NO_SPLASH=1`). |
| `--version`, `--help` | Stampa la versione o l'elenco delle opzioni. |

Il programma compilato non ha una propria console: `--help` e `--version` scrivono nella console da cui è stato avviato (cmd, PowerShell).

---

## 2. Modalità server senza finestra (`--no-ui`)

OpenCue si avvia come al solito – uscita DMX, cue, effetti, MIDI, accesso remoto, API REST – ma **non si apre alcuna finestra del programma**. Lo si controlla da

- **un browser su questo computer:** `http://127.0.0.1:8000` (la porta di *Impostazioni → Accesso remoto*, oppure `--port`) – esattamente la stessa console della finestra, oppure
- **un tablet o un telefono** in rete (attivate l'**Accesso remoto** nelle impostazioni o avviate una volta con `--remote`).

Un'**icona nell'area di notifica** della barra delle applicazioni mostra che OpenCue è in esecuzione: un **clic** apre la console nel browser; il **clic destro** apre il menu *Apri OpenCue nel browser*, *Apri la cartella dei log* ed *Esci da OpenCue*. Se lo show ha modifiche non salvate, l'uscita chiede conferma una volta (in ogni caso viene salvata una copia di backup).

Il menu mostra in alto il **nome dello show**, l'avviso **⚠ Modifiche non salvate** quando ce ne sono (anche il suggerimento dell'icona) e gli **indirizzi** a cui la console è raggiungibile (con l'accesso remoto attivo anche quelli in rete) – un clic ne apre uno nel browser.

Altri modi per uscire: **File → Esci** nel browser, **Ctrl+C** se è stato avviato da un terminale, e la disconnessione o lo spegnimento di Windows (OpenCue cerca allora di chiudersi in modo pulito, con il solito backup).

**Avviare OpenCue una seconda volta** mentre il server è in esecuzione non mostra alcun errore: apre semplicemente il browser sulla console in esecuzione.

Cosa **può non funzionare** senza la finestra: ciò che richiede la finestra nativa del programma – ad esempio il selettore di file per *collegare* un file video o audio, o il passaggio a schermo intero della finestra. Tutto il resto è disponibile nel browser.

Suggerimento: per un PC di palco che emette solo DMX, attivate *Avvia OpenCue quando accedo a Windows* + *Avvia senza finestra* (sezione 3).

---

## 3. Avvio con Windows

**Impostazioni → Generale → Comportamento:**

- **Avvia OpenCue quando accedo a Windows** – una voce per il **vostro utente Windows** (non servono diritti di amministratore; rimuovetela disattivando l'opzione).
- **Avvia senza finestra (solo server)** – avvia con `--no-ui`.

Questa funzione è disponibile nel **programma installato**, non quando si avvia dal codice sorgente. (Uno show esportato con l'estensione `.ocshow` si apre sempre in OpenCue con un doppio clic – non c'è un interruttore per questo.) La voce punta al file del programma: se spostate o reinstallate OpenCue altrove, disattivate e riattivate l'opzione.

---

## 4. Diritti di amministratore e firewall

**OpenCue gira come amministratore?** Il registro (`opencue.log`, prime righe) e i dettagli di un rapporto di errore indicano *«Administrator: yes»* o *«no»*. Se sì, OpenCue scrive anche una nota nel registro.

**Non serve – e non andrebbe usato:** Windows blocca il **trascinamento di file da Esplora risorse** in un programma eseguito come amministratore, e un server web con diritti di amministratore è un bersaglio più grosso. I diritti di amministratore servono per **una** cosa: creare la **regola del firewall di Windows**.

**Regola del firewall:** senza di essa Windows chiede la prima volta che OpenCue usa la rete; una domanda senza risposta o rifiutata blocca tablet, sACN e il nome di rete `opencue.local`. **Impostazioni → Accesso remoto → Firewall di Windows → Consenti OpenCue nel firewall** crea una regola esattamente per questo programma, **in entrata, solo nelle reti private e di dominio** (mai in quelle pubbliche). Windows chiede il permesso **una sola volta** (richiesta di amministratore) – solo questo piccolo comando viene avviato con diritti elevati, OpenCue stesso continua a girare normalmente. *Rimuovi la regola firewall* la elimina di nuovo. La riga di stato mostra se la regola esiste.

---

## 5. Priorità e tempi esatti

All'avvio OpenCue imposta la **priorità del processo** su *superiore al normale* e la **risoluzione del timer a 1 ms** (Windows normalmente batte ogni 15,6 ms). Entrambe mantengono fluidi i cicli a 40 Hz di cue, effetti e DMX quando il computer è occupato – non servono diritti di amministratore. `--priority high` la alza ancora (per un PC che non fa altro), `--priority normal` la disattiva.

---

## 6. Esempi

- Server su un PC di palco, il browser si apre: `OpenCue.exe --no-ui --open-browser`
- Aprire uno show da *Apri con* di Esplora risorse: `OpenCue.exe "D:\Shows\Concert.json"`
- Avviare vuoto senza toccare l'ultimo show: `OpenCue.exe --new-show`
- Provare su un'altra porta con dati propri: `OpenCue.exe --port 8080 --data-dir D:\OpenCueTest`

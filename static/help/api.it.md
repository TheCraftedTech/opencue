# API REST

Con l'**API REST** altri programmi possono **leggere** lo stato di OpenCue e **controllarlo e modificarlo** – script, un controller di show, domotica, una pagina web per lo stage manager, un'app per tablet o uno strumento vostro. Parla semplice **HTTP** e risponde in **JSON**. Non serve alcun software aggiuntivo e funziona completamente offline all'interno della vostra rete.

L'accesso è protetto da **token** che create in OpenCue. Ogni token ha i propri **permessi**, così un'app per tablet può solo leggere, un altro strumento può anche attivare cue e un terzo può costruire interi show.

---

## 1. L'idea in un minuto

- L'API si trova sotto **`/api/v1/`** allo stesso indirizzo e sulla stessa porta di OpenCue stesso (ad esempio `http://127.0.0.1:8000/api/v1/`).
- Voi **create un token** in *Impostazioni → API* e lo inviate con ogni richiesta.
- Le richieste di **lettura** (`GET`) restituiscono lo stato: apparecchi, liste di cue, cue, variabili, effetti, il segnale DMX, il timecode, il programmer.
- Le richieste di **esercizio** (`POST` / `PUT`) fanno girare lo show: comandi, cue, timecode, blackout, audio, il programmer.
- Le richieste di **modifica** cambiano lo show stesso: creare e modificare liste di cue e cue, variabili, effetti e script di effetti, patchare apparecchi, salvare e caricare file show, caricare media.
- I **pulsanti, fader e interruttori** propri della console possono essere premuti, mossi e commutati dall'esterno.
- Tutto ciò che un operatore fa nella finestra compare **subito in tutte le finestre aperte** – anche ciò che l'API modifica.
- Un **flusso in diretta** (`GET /events`) segnala le modifiche mentre accadono, così una dashboard non deve chiedere continuamente.
- Per l'**hardware** (un ESP32 con joystick, manopole, pulsanti, microfono) c'è un **WebSocket** (`/api/v1/ws`): joystick relativo o assoluto, valori assoluti o relativi, DMX e valori in diretta, invio e ricezione del timecode, valori audio e dati audio in entrambe le direzioni (sezione 10). Per dispositivi semplici senza un'interfaccia propria ci sono **viste di stato** come immagine o pagina web (sezione 11).
- Ogni funzione richiede **un permesso**. Un token senza di esso riceve `403`. I permessi di modifica sono **disattivati di default**.
- L'API è un'interfaccia propria e stabile. Le route interne che la finestra del programma usa *non* ne fanno parte.

---

## 2. Avvio rapido

1. Aprite **Impostazioni → API REST** (possibile anche da un dispositivo remoto connesso). Di default **non c'è alcun token** e l'API risponde solo su **questo computer**.
2. Fate clic su **Nuovo token**, dategli un nome, scegliete i permessi (o un preset) e fate clic su **Crea token**. Un **nuovo token viene creato subito** (senza *Salva*) e mostrato subito dopo.
3. **Copiate il token adesso.** Viene mostrato una sola volta; poi sono visibili solo i primi caratteri. Se va perso, create un nuovo token o usate *Genera nuovo token*.
4. Provate:

```
curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status
```

La risposta è un oggetto JSON con il nome dello show, blackout, grand master, timecode e altro (vedi la sezione 6).

L'indirizzo negli esempi (`127.0.0.1:8000`) è la console stessa. Per l'indirizzo da altri dispositivi vedi la sezione 8. Una pagina con tutte le route, ricercabile e leggibile offline, si trova in `/api/v1/docs`.

---

## 3. Token e permessi

### Gestire i token

In **Impostazioni → API REST** potete:

| Azione | Significato |
|---|---|
| **API REST attiva/spenta** | L'interruttore principale. Quando è spento, ogni richiesta riceve la risposta `403 api_disabled`. |
| **Raggiungibile da** | *Solo questo computer* (predefinito) o *La rete*. Gli altri dispositivi richiedono anche che l'**accesso remoto** sia attivo; altrimenti la pagina lo segnala (con un link). Dall'esterno l'API risponde `403 api_local_only` quando è impostato *Solo questo computer*. |
| **Consenti pagine web su altri indirizzi** | Le pagine del browser aperte da un altro indirizzo possono chiamare l'API (CORS, sezione 8). Attivo di default. |
| **Viste di stato (immagine / web)** | Interruttore per le viste della sezione 11. Attivo di default (ognuna richiede un token). |
| **Connessi ora (WebSocket)** | Elenco dei dispositivi connessi in questo momento tramite il WebSocket (token, indirizzo, cosa ricevono, joystick attivo, messaggi al secondo) – in diretta, con **Disconnetti**. |
| **Nuovo token** | Crea un token. Una finestra ampia permette di scegliere i permessi in tre colonne: *Lettura*, *Esercizio*, *Modifica dello show*. |
| **Modifica** | Cambia nome e permessi. |
| **Interruttore Attivo** | Spegne e riaccende un token senza eliminarlo (`403 token_disabled` finché è spento). |
| **Genera nuovo token** (in *Modifica*) | Sostituisce il segreto. Il vecchio token smette di funzionare non appena salvate. |
| **Elimina** | Chiede in una finestra propria (disattivabile, vedi *Predefiniti → Eliminazione*) e poi elimina il token **subito**. |
| **Ultimo utilizzo** | Mostra quando un token è stato usato l'ultima volta. |

Un **nuovo token** viene creato e mostrato subito, un'**eliminazione** vale subito dopo la domanda. Tutto il resto è una **bozza** come in tutte le impostazioni (interruttore, modifica, rigenerazione): le righe modificate sono segnate e contate, solo **Salva** applica tutto (la finestra resta aperta), *Chiudi* scarta dopo una domanda. I token si possono gestire solo sul computer della console stessa, non da dispositivi remoti.

Sul disco viene memorizzato solo un **hash** del token, mai il token stesso.

### I permessi

**Lettura**

| Permesso | Consente | Predefinito |
|---|---|---|
| **Stato** | Stato: nome dello show, blackout, grand master, timecode, selezione, programmer, analisi audio, uscite, il flusso di eventi in diretta | attivo |
| **Dati dello show** | Apparecchi, tipi di apparecchio, gruppi, variabili, effetti, script di effetti, file show, liste di cue e cue, media, layout | attivo |
| **Uscita DMX** | Valori DMX attuali e stato in diretta di ogni apparecchio | attivo |

**Esercizio**

| Permesso | Consente | Predefinito |
|---|---|---|
| **Comandi della console** | Eseguire qualsiasi comando della riga di comando (può anche modificare ed eliminare dati dello show) – *critico* | attivo |
| **Liste di cue** | Go, Back, salto a un cue, pausa, ripresa, stop, fader | attivo |
| **Timecode** | Avvio, pausa, stop, ricerca, velocità | attivo |
| **Blackout e master** | Commutare il blackout, impostare il grand master | attivo |
| **Audio** | Aprire / chiudere la sorgente audio, cambiarne le impostazioni, battere il tempo | attivo |
| **Programmer e selezione** | Selezionare apparecchi, impostare valori e variabili in diretta, svuotare il programmer | attivo |
| **Pulsanti, fader, interruttori della console** | Premere, muovere e commutare i pannelli Pulsante, Fader e Interruttore propri della console (eseguono i comandi impostati in essi) | attivo |
| **Imposta DMX direttamente** | Scrivere canali DMX – prevale sullo show in esecuzione – *critico* | **spento** |

**Modifica dello show**

| Permesso | Consente | Predefinito |
|---|---|---|
| **Liste di cue e cue** | Creare, modificare, copiare, rinumerare ed eliminare liste di cue e cue; memorizzare il programmer come cue | **spento** |
| **Variabili** | Creare, modificare ed eliminare variabili e gruppi di variabili | **spento** |
| **Effetti** | Creare, modificare ed eliminare effetti e gruppi di effetti; avviare e fermare effetti sugli apparecchi | **spento** |
| **Script di effetti** | Controllare, salvare ed eliminare tipi di effetto (file di script) | **spento** |
| **Patch e gruppi di apparecchi** | Patchare, modificare ed eliminare apparecchi; gestire gruppi di apparecchi; installare e rimuovere tipi di apparecchio GDTF – *critico* | **spento** |
| **File show** | Nuovo, carica, salva, rinomina, copia ed elimina file show – *critico* | **spento** |
| **Media** | Caricare, rinominare ed eliminare file video e audio | **spento** |
| **Layout** | Mostrare un layout di pannelli salvato nella finestra della console | **spento** |
| **Uscite DMX e lingua** | Commutare Art-Net, sACN e DMX USB, cambiare indirizzi, universo predefinito, lingua – *critico* | **spento** |

**Preset** nella finestra: *Sola lettura* (i tre permessi di lettura), *Esercizio* (lettura più liste di cue, timecode, blackout/master, audio, programmer e i pulsanti / fader / interruttori della console – niente comandi, niente DMX diretto), *Modifica show* (Esercizio più liste di cue e cue, variabili, effetti), *Accesso completo* e *Predefinito*.

---

## 4. Regole per tutte le richieste

- **Accesso:** inviate il token come `Authorization: Bearer oc_…`. Funziona anche l'intestazione `X-API-Key: oc_…`.
- **Formato:** le richieste con un corpo usano JSON e `Content-Type: application/json`. Le risposte sono sempre JSON (tranne il flusso di eventi e i download di file).
- **Scegliere le cose:**
  - un *apparecchio* per il suo **numero (FID)**, il suo id o un nome non ambiguo; un *gruppo* di apparecchi per il suo nome;
  - una *lista di cue* per il suo **nome** o id; un *cue* per il suo **numero** (ad esempio `1.5`) o id;
  - una *variabile*, un *effetto* o un *file show* per il suo **nome** (maiuscole / minuscole non contano) o id.
  - I nomi con spazi vanno codificati come URL nel percorso (`Par%20links`).
- **Scegliere più apparecchi** in un corpo: `"fixtures": [1, 2, "Front"]`, `"fixture": 3` e / o `"group": "Wash"`. Per le chiamate del programmer `"selection": true` indica gli apparecchi selezionati sulla console, e una chiamata senza nessuno di essi usa la selezione.
- **Percentuali e byte:** dimmer, posizione e simili si indicano in **percentuale (0–100)**, i canali DMX grezzi in **0–255**, i colori come `"#rrggbb"`, `[r, g, b]` o `{"r": …, "g": …, "b": …}` (0–255).
- **Tempi** in secondi; il timecode come secondi o testo (`00:01:04.300`).
- **Controlli accurati dell'input:** un campo che non esiste viene rifiutato (`422`), un valore o un nome sbagliato dà `400`, un nome già occupato dà `409 duplicate`. Nulla viene indovinato o ignorato in silenzio.
- **Controllato prima che cambi qualcosa:** una chiamata con un valore, un nome o un apparecchio sbagliato viene rifiutata per intero – un cue con un apparecchio sbagliato non viene memorizzato a metà.

### Errori

Gli errori hanno sempre lo stesso aspetto:

```json
{ "error": { "code": "not_found", "message": "No fixture '99' (use the fixture number, id or an unambiguous name)." } }
```

| HTTP | `code` | Significato |
|---|---|---|
| 400 | `bad_request` | La richiesta è errata (un valore fuori intervallo, un attributo sconosciuto, un comando vuoto …) |
| 401 | `unauthorized` | Token mancante o non valido |
| 403 | `forbidden` | Il token non ha il permesso per questa funzione |
| 403 | `token_disabled` / `api_disabled` | Il token o l'intera API è spento |
| 404 | `not_found` | Apparecchio, lista di cue, cue, variabile, effetto, file show … non esiste |
| 409 | `duplicate` | Il nome è occupato (lista di cue, variabile, effetto, gruppo …) |
| 409 | `cue_exists` | Esiste un cue con questo numero – inviate `on_conflict` (`merge` / `overwrite`) |
| 409 | `address_conflict` | Gli indirizzi DMX si sovrappongono a un altro apparecchio – `allow_overlap: true` patcha comunque |
| 409 | `unsaved_changes` | Lo show ha modifiche non salvate – salvatelo, o inviate `force: true` |
| 409 | `exists` / `in_use` / `never_saved` | Esiste un file show o uno script con quel nome / il file show è quello caricato / lo show non ha ancora un file |
| 409 | `no_active_cue` / `programmer_empty` | *Update* senza cue attivo o con un programmer vuoto |
| 409 | `audio_failed` | La sorgente audio non ha potuto essere aperta (il motivo è nel messaggio) |
| 415 | `invalid_type` | Un caricamento di media che non è un file video / audio supportato |
| 422 | `invalid` | Un campo manca, è sconosciuto o ha un tipo sbagliato |
| 422 | `invalid_script` | Uno script non compila o fallisce la prova (con la riga) |
| 429 | `rate_limited` | Troppi token sbagliati da questo indirizzo – attendete il tempo indicato in `Retry-After` |

Un **comando di console rifiutato** (ad esempio un errore di battitura) *non* è un errore HTTP: la risposta è `200` con `"success": false` e il messaggio della riga di comando.

---

## 5. Panoramica degli endpoint

Tutti i percorsi iniziano con `/api/v1`. Il permesso nella colonna di destra è ciò che serve al token. Nei percorsi `{list}` è una lista di cue, `{cue}` un cue, `{fixture}` un apparecchio, `{ref}` una variabile / un effetto / un nome.

### Lettura

| Metodo | Percorso | Restituisce | Permesso |
|---|---|---|---|
| GET | `/` | Indice: versione, link, cosa può fare questo token | Stato |
| GET | `/status` | Stato complessivo: show, blackout, master, timecode, selezione, lista di cue attiva, uscite DMX, numeri | Stato |
| GET | `/blackout` · `/master` · `/timecode` · `/selection` | Una parte dello stato | Stato |
| GET | `/system` | Versione, lingua, uscite DMX (Art-Net, sACN, USB), universi, accesso remoto, cartella dati | Stato |
| GET | `/showfile` | Nome dello show caricato, se ha modifiche non salvate e un file | Stato |
| GET | `/programmer` | Selezione, i valori impostati a mano (percentuale, colore + hex, canali grezzi), le variabili che seguono, gli effetti in esecuzione | Stato |
| GET | `/audio` · `/audio/devices` | L'analisi audio in diretta e le impostazioni / ogni ingresso audio | Stato |
| GET | `/system/usb-ports` · `/command/suggest?text=` | Porte seriali per DMX USB / completamenti per un comando (come Tab nella riga di comando) | Stato |
| GET | `/events` | **Flusso in diretta** delle modifiche (Server-Sent Events, sezione 6) | Stato |
| GET | `/fixtures` | Tutti gli apparecchi. Facoltativi `?universe=`, `?group=`, `?include_state=true` | Dati dello show |
| GET | `/fixtures/{fixture}` | Un apparecchio con ogni canale (indirizzo, valore DMX attuale) e il suo stato | Dati dello show |
| GET | `/fixture-types` | La libreria apparecchi: id, nome, produttore, modalità con numero di canali (`?q=` filtra) | Dati dello show |
| GET | `/groups` · `/variable-groups` · `/effect-groups` | Gruppi di apparecchi, gruppi di variabili, gruppi di effetti | Dati dello show |
| GET | `/variables` · `/variables/{ref}` | Tutte le variabili / una (con quante voci di cue la usano) | Dati dello show |
| GET | `/effects` · `/effects/{ref}` · `/effects/assignments` | Effetti / un effetto con le informazioni del suo tipo / quale effetto gira su quale apparecchio | Dati dello show |
| GET | `/effect-scripts` · `/effect-scripts/{name}` | Tutti i tipi di effetto (categoria, tag, impostazioni) / il testo sorgente di uno | Dati dello show |
| GET | `/cuelists` · `/cuelists/{list}` | Tutte le liste di cue con cue attivo, fader e stato di riproduzione / una lista con tutti i suoi cue | Dati dello show |
| GET | `/cuelists/{list}/cues` | I cue di una lista; `?detail=true` aggiunge **cosa modifica ogni cue** | Dati dello show |
| GET | `/cuelists/{list}/cues/{cue}` | Un cue in dettaglio completo | Dati dello show |
| GET | `/showfiles` | Nomi dei file show salvati (e di quello caricato) | Dati dello show |
| GET | `/media` · `/media/{id}/file` | I media dello show / scaricarne uno | Dati dello show |
| GET | `/layouts` | Layout salvati della console | Dati dello show |
| GET | `/widgets` | I pannelli Pulsante / Fader / Interruttore della console: comandi, limiti e valore del fader, stato dell'interruttore | Dati dello show |
| GET | `/dmx` · `/dmx/{universe}` | Gli universi e i loro valori (`?first=&last=`, `?nonzero=true`) | Uscita DMX |
| GET | `/fixtures/state` | Lo stato in diretta di **ogni** apparecchio (ciò che la console emette ora) | Uscita DMX |

### Esercizio

| Metodo | Percorso | Corpo | Permesso |
|---|---|---|---|
| POST | `/command` | `{"command": "Fixture 1 At 80"}` | Comandi della console |
| POST | `/commands` | `{"commands": ["…", "…"], "stop_on_error": false}` – fino a 100 | Comandi della console |
| POST | `/cuelists/{list}/go` | `{"cue": "2"}` facoltativo (senza: il cue successivo) | Liste di cue |
| POST | `/cuelists/{list}/back` · `/pause` · `/resume` · `/stop` | – | Liste di cue |
| PUT | `/cuelists/{list}/fader` | `{"value": 70}` (percentuale) | Liste di cue |
| PUT | `/timecode` | `{"action": "play" \| "pause" \| "stop" \| "seek" \| "rate", "position": …, "direction": 1, "rate": 1}` | Timecode |
| PUT | `/blackout` | `{"enabled": true}` (senza valore: commuta) | Blackout e master |
| PUT | `/master` | `{"value": 80}` (percentuale) | Blackout e master |
| PUT | `/audio` | `{"running": true, "device": "demo", "settings": {"mode": "manual", "bpm": 128}}` – ogni campo facoltativo | Audio |
| POST | `/audio/tap` | – (un tocco del pulsante del tempo) | Audio |
| PUT | `/selection` | `{"fixtures": [1, 2], "mode": "set" \| "add" \| "remove" \| "clear"}` (anche `group`) | Programmer e selezione |
| PUT | `/programmer/values` | `{"fixtures": [1, 2], "values": {"dimmer": 80, "color": "#ff0000"}}` | Programmer e selezione |
| POST | `/programmer/variables` | `{"variable": "Warm white", "fixtures": [1, 2]}` – applica e collega una variabile | Programmer e selezione |
| POST | `/widgets/{id}/press` | – (esegue il comando di un pulsante) | Pulsanti, fader, interruttori della console |
| PUT | `/widgets/{id}/value` | `{"value": 70}` (fader; limitato al suo minimo / massimo, arrotondato) | Pulsanti, fader, interruttori della console |
| PUT | `/widgets/{id}/state` | `{"on": true}` (interruttore; senza valore commuta) | Pulsanti, fader, interruttori della console |
| POST | `/programmer/clear` | `{"fixtures": [1]}` dimentica i loro valori; `{"all": true}` = *Clear Clear*: tutto buio | Programmer e selezione |
| PUT | `/dmx/{universe}/{channel}` | `{"value": 255}` o `{"percent": 100}` | Imposta DMX direttamente |
| PUT | `/dmx/{universe}` | `{"channels": {"1": 255, "2": 0}}` | Imposta DMX direttamente |
| PUT | `/fixtures/{fixture}/channels/{channel}` | `{"value": 128}` o `{"percent": 50}`; `{channel}` è il numero di canale dell'apparecchio (1 = primo) o il suo nome (`Dimmer`) | Imposta DMX direttamente |

### Modifica: liste di cue e cue – permesso *Liste di cue e cue*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/cuelists` | `{"name": "Act 1"}` | Crea una lista di cue (201) |
| PUT | `/cuelists/{list}` | `{"name": "…", "active": true}` | Rinomina; `active` la rende la lista mostrata dai pannelli delle liste di cue |
| PUT | `/cuelists/order` | `{"order": ["Act 2", "Act 1"]}` | Ordine delle liste |
| POST | `/cuelists/{list}/duplicate` | `{"name": "Copy"}` | Copia con tutti i cue |
| DELETE | `/cuelists/{list}` | – | Elimina la lista |
| POST | `/cuelists/{list}/cues` | vedi sotto | Crea un cue (201) |
| PUT | `/cuelists/{list}/cues/{cue}` | vedi sotto | Modifica proprietà e / o contenuto, rinumera |
| DELETE | `/cuelists/{list}/cues/{cue}` | – | Elimina un cue |
| POST | `/cuelists/{list}/cues/delete` | `{"cues": ["1", "2.5"]}` | Ne elimina diversi (tutti o nessuno) |
| POST | `/cuelists/{list}/cues/{cue}/duplicate` | `{"number": 9, "name": "…"}` | Copia un cue |
| POST | `/cuelists/{list}/update-active` | `{"mode": "normal" \| "only"}` | Porta il programmer nel cue attivo (come *Update*) |

**Corpo del cue** (creazione e modifica; ogni campo facoltativo in modifica):

| Campo | Significato |
|---|---|
| `number` | Numero del cue, decimali ammessi. Omesso alla creazione: il prossimo numero libero. |
| `name`, `fade`, `delay` | Nome e tempi generali in secondi |
| `trigger` | `go` · `follow` · `timecode` · `audio` · `midi` · `clock` |
| `timecode` | Per `timecode`: secondi o `1:04.300` |
| `audio` | Per `audio`: `{"source": "beat" \| "kick" \| "snare" \| "hat" \| "level" \| "bass" \| "mid" \| "high" \| "b1" … "b8", "value": 4}` (ogni n-esimo colpo, o una soglia in %) |
| `midi` | Per `midi`: `{"type": "note" \| "cc" \| "pc", "number": 60, "channel": 0, "value": 64}` – il cue scatta quando arriva questo segnale mentre è il cue successivo di una lista in esecuzione; `channel` 0 = qualsiasi (1–16 = un canale), `value` = la soglia di un `cc` (1–127) |
| `clock` | Per `clock`: `{"time": "19:30", "days": "Mon-Fri"}` (o `"days": [0,1,2,3,4]`, lunedì = 0; vuoto = ogni giorno) – il cue aspetta, come cue successivo di una lista in esecuzione, quest'ora dell'orologio da parete. |
| `mib`, `command` | Move in black (`Off` / `Auto` / `On`); comandi di console eseguiti con il cue |
| `times` | Tempi propri per gruppo: `{"color": {"fade": 2, "delay": 0}, "position": {…}, "beam": {…}, "zoom": {…}}`; `null` = usare di nuovo il tempo generale |
| `effect_fade` | `{"in": 1, "out": 2}` |
| `changes` | Cosa modifica il cue (sotto) |
| `effects` | Gli effetti che il cue avvia: `[{"fixtures": [2, 3], "effects": {"dimmer": "Strobe"}}]` (categoria → nome dell'effetto) |
| `from_programmer` | *(creazione)* memorizza anche ciò che è nel programmer **e ogni modifica dell'immagine rispetto al cue precedente** (come *Store Cue*; se nulla è cambiato: `409 nothing_changed`); `clear_programmer` lo svuota poi |
| `on_conflict` | *(creazione / rinumerazione)* il numero esiste: `merge` (solo gli attributi inviati si uniscono al cue esistente) o `overwrite` |
| `content` | *(modifica)* `merge` (predefinito) o `replace`: il contenuto del cue è esattamente ciò che viene inviato |

`changes` è una lista; ogni voce nomina apparecchi e ciò che ricevono:

```json
{ "fixtures": [2, 3], "values": { "dimmer": 80, "color": "#00ff00", "pan": 40 }, "variables": { "color": "Warm white" } }
```

`values`: `dimmer`, `pan`, `tilt`, `strobe`, `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin`, `prism`, `focus`, `zoom` in percentuale, `color`, canali grezzi `ch<N>` (0–255). `variables` associa un tipo (`dimmer`, `position`, `color`, `focus`, `zoom`, `gobo`) a una variabile: il cue **fa allora riferimento alla variabile** (un segnaposto, risolto in diretta quando il cue gira) invece di memorizzare il valore.

### Modifica: variabili – permesso *Variabili*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/variables` | `{"name": "Warm white", "type": "color", "group": "Colours", "values": {"hex": "#ffb060"}}` | Crea |
| PUT | `/variables/{ref}` | `{"name": "…", "group": "…", "values": {…}}` | Modifica; il tipo non può cambiare. Un nuovo valore raggiunge il programmer, i cue in esecuzione e **ogni cue che usa la variabile** |
| DELETE | `/variables/{ref}` | – | Elimina (i collegamenti del programmer vengono rilasciati) |
| POST · DELETE | `/variable-groups` · `/variable-groups/{name}` | `{"name": "Colours"}` | Crea / elimina un gruppo (le sue variabili restano) |

`values` per tipo: `dimmer`, `focus`, `zoom`: `{"level": 0-100}` · `position`: `{"pan": 0-100, "tilt": 0-100}` · `color`: `{"r","g","b"}` o `{"hex": "#ff8000"}` · `gobo`: `{"level", "spin", "gobo2", "gobo2_spin"}`.

### Modifica: effetti – permesso *Effetti*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/effects` | `{"script": "strobe", "name": "Blink", "group": "…", "params": {"rate_hz": 8}}` | Crea un effetto da un tipo di effetto (`GET /effect-scripts`); `params` vengono controllati rispetto ai limiti del tipo |
| PUT | `/effects/{ref}` | `{"name", "group", "params"}` | Modifica (il tipo non può cambiare) |
| DELETE | `/effects/{ref}` | – | Elimina; si ferma ovunque |
| POST | `/effects/{ref}/assign` | `{"fixtures": [2, 3]}` (anche `group`) | **Avvia** l'effetto sugli apparecchi (l'ordine distribuisce le onde) |
| POST | `/effects/release` | `{"fixtures": [2], "categories": ["dimmer"]}` | **Ferma** gli effetti sugli apparecchi (i valori restano) |
| POST · DELETE | `/effect-groups` · `/effect-groups/{name}` | `{"name": "…"}` | Crea / elimina un gruppo |

### Modifica: script di effetti – permesso *Script di effetti*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/effect-scripts/check` | `{"text": "…"}` | Compila e prova uno script senza salvare: `{ok, line, message}` |
| POST | `/effect-scripts/preview` | `{"text": "…", "count": 3, "duration": 4, "bpm": 120, "params": {…}}` | Simula le curve senza apparecchi |
| PUT | `/effect-scripts/{name}` | `{"text": "…", "overwrite": false}` | Salva come file nella cartella effetti dell'utente – **solo se compila e gira** (`422 invalid_script` con la riga). Un nome esistente richiede `overwrite` |
| DELETE | `/effect-scripts/{name}` | – | Elimina uno script della cartella utente; gli effetti di questo tipo si fermano |

Il linguaggio degli script è descritto nella guida *Studio effetti*.

### Modifica: patch e gruppi di apparecchi – permesso *Patch e gruppi di apparecchi*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/fixtures` | `{"type": "Generic RGBW LED Par", "mode": "…", "name": "Par", "quantity": 4, "universe": 1, "address": 11, "group": "Wash"}` | Patcha uno o più apparecchi uno dopo l'altro. Gli indirizzi vengono controllati (devono stare in 512 e non sovrapporsi – `allow_overlap: true` forza) |
| PUT | `/fixtures/{fixture}` | `{"name", "universe", "address", "sort_index", "group", "allow_overlap"}` | Modifica; `"group": ""` lo toglie dal suo gruppo |
| DELETE | `/fixtures/{fixture}` · POST `/fixtures/delete` | `{"fixtures": [1, 2]}` | Elimina (i cue mantengono le loro voci per l'apparecchio mancante, come nella finestra) |
| POST | `/groups` | `{"name": "Wash", "fixtures": [2, 3]}` | Crea un gruppo di apparecchi |
| POST | `/fixture-types` | il file `.gdtf` grezzo; intestazione `X-Filename` (codificata come URL) | Installa un tipo di apparecchio (fino a 30 MB; controllato prima dell'installazione) |
| DELETE | `/fixture-types/{id}` | – | Rimuove un tipo installato (`409 in_use` finché lo show lo usa) |
| PUT · DELETE | `/groups/{name}` | `{"name": "…", "fixtures": […]}` | Rinomina / imposta i membri (sostituisce l'elenco) / elimina (gli apparecchi restano) |

### Modifica: file show – permesso *File show*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/showfile/new` | `{"force": false}` | Avvia un nuovo show vuoto |
| POST | `/showfile/save` | – | Salva con il nome attuale (`409 never_saved` se non ha ancora un file) |
| POST | `/showfile/save-as` | `{"name": "Concert", "overwrite": false}` | Salva con un nome (i caratteri non ammessi nei nomi di file vengono rimossi) |
| POST | `/showfile/load` | `{"name": "Concert", "force": false}` | Carica uno show salvato – sostituisce quello in esecuzione |
| POST | `/showfiles/{name}/rename` | `{"new_name": "…", "overwrite": false}` | Rinomina un file salvato |
| POST | `/showfiles/{name}/duplicate` | – | Copia un file salvato |
| DELETE | `/showfiles/{name}` | `?force=true` per quello caricato | Elimina un file salvato |

**Nuovo** e **Carica** sostituiscono lo show in esecuzione. Con modifiche non salvate vengono rifiutati con `409 unsaved_changes` finché non salvate prima o inviate `"force": true`.

### Modifica: media – permesso *Media*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/media` | il file grezzo; intestazione `X-Filename` (codificata come URL) | Carica un file video / audio (fino a 1 GB; lo stesso file due volte è una sola voce) |
| PUT | `/media/{id}` | `{"name": "…"}` | Rinomina |
| DELETE | `/media/{id}` | – | Rimuove dallo show ed elimina la copia |

### Modifica: layout e impostazioni – permessi *Layout* e *Uscite DMX e lingua*

| Metodo | Percorso | Corpo | Cosa fa |
|---|---|---|---|
| POST | `/layouts/{filename}/load` | – | Mostra un layout salvato (`Name.json` come in `GET /layouts`) nella finestra della console; le modifiche non salvate del layout lì vanno perse |
| PUT | `/system` | `{"artnet": {"enabled": true, "ip": "2.255.255.255", "bind_ip": ""}, "sacn": {"enabled": true}, "enttec": {"enabled": false, "port": "COM3", "universe": 1}, "default_universe": 1, "language": "de"}` – ogni campo facoltativo | Commuta le uscite DMX e cambia lingua / universo predefinito; la risposta è `GET /system` |
| POST | `/system/dmx/reinitialize` | – | Riavvia le uscite DMX senza riavviare il programma |

### Documentazione (senza token)

| Metodo | Percorso | Restituisce |
|---|---|---|
| GET | `/docs` | Una panoramica leggibile e ricercabile di tutte le route (funziona offline) |
| GET | `/openapi.json` | La descrizione leggibile dalle macchine (OpenAPI 3.1); ogni route elenca il suo permesso come `x-capability` |

---

## 6. Esempi con risposte reali

### Stato

```
GET /api/v1/status
```

```json
{
  "app": { "name": "OpenCue", "version": "1.0.0" },
  "show": { "name": "Concert", "unsaved_changes": true },
  "blackout": false,
  "grand_master": 100.0,
  "timecode": { "running": false, "direction": 1, "rate": 1.0, "position_ms": 0.0, "position": "00:00:00.000" },
  "selection": { "fixture_ids": ["228a68e5-…"], "fids": [2] },
  "active_cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "dmx": { "universes": [1], "artnet": true, "sacn": false, "usb": false },
  "counts": { "fixtures": 2, "groups": 1, "variables": 0, "effects": 0, "cuelists": 1, "cues": 2 }
}
```

### Quali apparecchi ci sono nello show, e di che colore sono?

```
GET /api/v1/fixtures?include_state=true
GET /api/v1/fixtures/state
```

```json
{
  "fixtures": [
    { "id": "9ea4feaa-…", "fid": 1, "name": "Front", "state": { "dimmer": 80.0 } },
    { "id": "228a68e5-…", "fid": 2, "name": "Par left",
      "state": { "dimmer": 100.0, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } } }
  ]
}
```

`state` contiene esattamente ciò che la console emette attualmente, letto dal buffer DMX: `dimmer`, `pan`, `tilt`, `zoom`, `focus` … in percentuale e `color` come r/g/b. Gli attributi che un apparecchio non ha mancano. (Con grand master 0 o in blackout il dimmer non può essere ricostruito e viene omesso.)

### Un apparecchio con tutti i canali

```
GET /api/v1/fixtures/2
```

```json
{
  "id": "228a68e5-…", "fid": 2, "name": "Par left", "type": "Generic RGBW LED Par", "manufacturer": "Generic",
  "universe": 1, "start_channel": 11, "end_channel": 14, "channel_count": 4, "mode": "default", "group": "Wash",
  "channels": [
    { "channel": 1, "name": "ColorAdd_R", "address": 11, "value": 255 },
    { "channel": 2, "name": "ColorAdd_G", "address": 12, "value": 0 },
    { "channel": 3, "name": "ColorAdd_B", "address": 13, "value": 0 },
    { "channel": 4, "name": "ColorAdd_W", "address": 14, "value": 0 }
  ],
  "state": { "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }
}
```

### Cosa modifica un cue?

```
GET /api/v1/cuelists/Show/cues/1
```

```json
{
  "id": "700571ee-…", "number": 1, "name": "Auf", "active": false,
  "trigger": "go", "timecode_ms": null, "timecode": null, "audio": null, "midi": null, "clock": null,
  "fade": 2.0, "delay": 0.0,
  "times": { "color": { "fade": null, "delay": null }, "position": { "fade": null, "delay": null },
             "beam": { "fade": null, "delay": null }, "zoom": { "fade": null, "delay": null } },
  "effect_fade": { "in": 0.0, "out": 0.0 }, "mib": "Off", "command": "", "fixture_count": 2,
  "changes": [
    { "fixture_id": "9ea4feaa-…", "fid": 1, "name": "Front", "values": { "dimmer": 50 }, "variables": {} },
    { "fixture_id": "228a68e5-…", "fid": 2, "name": "Par left",
      "values": { "dimmer": 100, "color": { "r": 255, "g": 0, "b": 0, "hex": "#ff0000" } }, "variables": {} }
  ],
  "effects": [],
  "cuelist": { "id": "7e5d274f-…", "name": "Show" }
}
```

- `fade` / `delay` sono i tempi generali; `times` contiene i tempi facoltativi per gruppo di attributi (`null` = usa il tempo generale).
- `changes[].values` sono i valori fissi memorizzati nel cue. `variables` elenca le variabili (segnaposto) a cui il cue fa riferimento, per tipo e nome – una variabile viene risolta in diretta quando il cue gira.
- `effects` elenca gli effetti che il cue avvia, per apparecchio.
- Tutti i cue di una lista in una volta con i loro dettagli: `GET /api/v1/cuelists/Show/cues?detail=true`.

### Il segnale DMX

```
GET /api/v1/dmx/1?first=1&last=14
GET /api/v1/dmx/1?nonzero=true
```

```json
{ "universe": 1, "first": 1, "last": 14, "values": [0,0,0,0,0,0,0,0,0,0,255,0,0,0] }
{ "universe": 1, "first": 1, "last": 512, "channels": { "11": 255 } }
```

### Eseguire un comando di console

```
POST /api/v1/command
{ "command": "Fixture 1 Thru 4 At 80" }
```

```json
{ "command": "Fixture 1 Thru 4 At 80", "success": true, "message": "OK: 4 fixtures selected; At 80 applied" }
```

Funzionano tutti i comandi della riga di comando, anche concatenati con `;` (vedi la guida *Riferimento dei comandi*).

### Attivare un cue

```
POST /api/v1/cuelists/Show/go            { "cue": "2" }
```

```json
{ "cuelist": { "id": "7e5d274f-…", "name": "Show" }, "command": "Cuelist \"Show\" Go Cue 2", "success": true, "message": "OK: Go Cue 2 [Show]" }
```

Senza corpo `go` avvia il cue successivo. Nota: una lista di cue il cui **nome contiene un apice doppio** non si può indirizzare così; rinominatela.

### Timecode

```
PUT /api/v1/timecode   { "action": "seek", "position": "1:04.300" }
PUT /api/v1/timecode   { "action": "play", "position": 10 }
GET /api/v1/timecode
```

```json
{ "running": false, "direction": 1, "rate": 1.0, "position_ms": 64300.0, "position": "00:01:04.300" }
```

`position` è un numero in **secondi** o un testo come `1:04.300` o `00:00:04.300`. `play` può partire da una `position` e girare all'indietro con `"direction": -1`; `rate` è la velocità tra 0,1 e 8. Saltare con `seek` non fa scattare i cue a timecode.

### Impostare canali DMX

```
PUT /api/v1/dmx/1/200                      { "value": 255 }
PUT /api/v1/dmx/1                          { "channels": { "201": 10, "202": 20 } }
PUT /api/v1/fixtures/Front/channels/Dimmer { "percent": 50 }
```

```json
{ "universe": 1, "channel": 1, "value": 128, "fixture": { "fid": 1, "name": "Front" }, "channel_of_fixture": 1 }
```

Un canale che appartiene a un **apparecchio** viene impostato come il fader *DMX diretto* del programmer: diventa un valore manuale che i cue in esecuzione non mescolano più. Gli altri canali vengono scritti direttamente nell'uscita. Questo permesso è **spento di default**.

### Audio: leggere e controllare

```
GET  /api/v1/audio/devices                    -> { "devices": [ { "id": "demo", "kind": "demo", "name": "Demo beat" }, ... ] }
PUT  /api/v1/audio    { "device": "demo" }    open that source (`running` false closes it)
PUT  /api/v1/audio    { "settings": { "mode": "manual", "bpm": 128, "sensitivity": 0.7 } }
POST /api/v1/audio/tap                        tap the tempo (about 4 taps in a row set it, the tempo switches to manual)
GET  /api/v1/audio                            level, bands, kick / snare / hat, bpm, beat_phase ... and the settings
```

`PUT /audio` applica prima le `settings`, poi apre (`running: true`, o un `device`) o chiude (`running: false`) la sorgente, e risponde come `GET /audio`. Se la sorgente non si può aprire la risposta è `409 audio_failed` con il motivo. Impostazioni: `gain`, `auto_gain`, `sensitivity`, `smoothing`, `latency_ms`, `mode` (`auto` | `manual`), `bpm` (tempo manuale), `phase_follow`, `demo_bpm`, `autostart`; le chiavi sconosciute vengono ignorate e i numeri vengono limitati al loro intervallo.

### Costruire un cue

```
POST /api/v1/cuelists/Show/cues
{
  "number": 3, "name": "Blue wash", "fade": 3,
  "changes": [
    { "group": "Wash", "values": { "dimmer": 80, "color": "#0000ff" } },
    { "fixtures": [1], "values": { "dimmer": 20 } }
  ],
  "effects": [ { "fixtures": [2, 3], "effects": { "dimmer": "Blink" } } ]
}
```

```json
{ "status": "created", "cuelist": { "id": "7e5d274f-…", "name": "Show" },
  "cue": { "id": "5c0b…", "number": 3, "name": "Blue wash", "fade": 3.0, "changes": [ … ], "effects": [ … ], … } }
```

La risposta è l'intero cue come lo mostrerebbe `GET …/cues/3`. Se il cue 3 esiste ricevete `409 cue_exists`; inviate `"on_conflict": "merge"` per aggiungervi gli attributi inviati, o `"overwrite"` per sostituirne il contenuto (stato `merged` / `overwritten`).

La stessa cosa dal programmer, come *Store Cue*:

```
PUT  /api/v1/programmer/values   { "fixtures": [2, 3], "values": { "color": "#ff8000", "dimmer": 100 } }
POST /api/v1/cuelists/Show/cues  { "number": 4, "name": "Orange", "from_programmer": true, "clear_programmer": true }
```

### Modificare ed eliminare cue

```
PUT    /api/v1/cuelists/Show/cues/3   { "name": "Deep blue", "fade": 5, "times": { "color": { "fade": 8 } } }
PUT    /api/v1/cuelists/Show/cues/3   { "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] }                       (adds to the content)
PUT    /api/v1/cuelists/Show/cues/3   { "content": "replace", "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] } (content = exactly this)
PUT    /api/v1/cuelists/Show/cues/3   { "number": 2.5 }                                                                          (renumber)
DELETE /api/v1/cuelists/Show/cues/3
```

Cambia solo ciò che inviate. Una modifica a un cue in esecuzione ha effetto al suo prossimo *Go*.

### Variabili ed effetti

```
POST /api/v1/variables  { "name": "Warm white", "type": "color", "values": { "hex": "#ffb060" } }
PUT  /api/v1/variables/Warm white   { "values": { "hex": "#ffa040" } }      -> every cue that uses it is warmer now
POST /api/v1/effects    { "script": "strobe", "name": "Blink", "params": { "rate_hz": 8 } }
POST /api/v1/effects/Blink/assign   { "fixtures": [2, 3] }                  -> it runs now
POST /api/v1/effects/release        { "fixtures": [2, 3] }                  -> stop it
```

`GET /api/v1/effect-scripts` elenca i tipi di effetto con le loro impostazioni (`variables`: nome, genere, limiti, predefinito, etichette in entrambe le lingue).

### Scrivere un proprio tipo di effetto

```
POST /api/v1/effect-scripts/check   { "text": "…" }                  -> { "ok": false, "line": 3, "message": "…" }
PUT  /api/v1/effect-scripts/my_wave { "text": "…", "overwrite": true }
POST /api/v1/effects                { "script": "my_wave" }
```

Uno script viene salvato solo se compila e gira. Il linguaggio è documentato nella guida *Studio effetti*.

### Patchare apparecchi

```
GET  /api/v1/fixture-types?q=par
POST /api/v1/fixtures  { "type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "universe": 1, "address": 11, "group": "Wash" }
```

```json
{ "created": [ { "fid": 4, "name": "Par 1", "universe": 1, "start_channel": 11, "end_channel": 14, … },
               { "fid": 5, "name": "Par 2", "universe": 1, "start_channel": 15, … }, … ] }
```

Gli indirizzi che si sovrappongono ad altri apparecchi vengono rifiutati (`409 address_conflict`); `"allow_overlap": true` patcha comunque.

### Il programmer

```
GET  /api/v1/programmer
PUT  /api/v1/selection            { "group": "Wash" }
PUT  /api/v1/programmer/values    { "values": { "dimmer": 100, "color": [255, 0, 0] } }       (without fixtures: the selection)
POST /api/v1/programmer/variables { "variable": "Warm white" }
POST /api/v1/programmer/clear     { "fixtures": [2] }          forget their values (the output stays)
POST /api/v1/programmer/clear     { "all": true }              Clear Clear: every fixture dark, effects end
```

I valori impostati così si comportano come i fader della finestra del programmer: l'uscita cambia subito, contano come toccati e il successivo *Store Cue* li riprende.

### Valori relativi (ritoccare invece di impostare)

```
curl -X PUT -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/json" \
  -d '{"group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}' \
  http://127.0.0.1:8000/api/v1/programmer/values
```

Con `"mode": "relative"` i numeri sono **variazioni in punti percentuali** (da −100 a 100); ogni apparecchio parte dal proprio valore ed è limitato a 0 / 100 %. Colori e canali grezzi esistono solo come valori assoluti. Per sequenze rapide di modifiche (manopole, joystick) è meglio il WebSocket (sezione 10).

### File show

```
POST /api/v1/showfile/save-as  { "name": "Concert" }
POST /api/v1/showfile/load     { "name": "Concert", "force": false }
POST /api/v1/showfile/new      { "force": true }
```

Senza `force`, *load* e *new* si fermano con `409 unsaved_changes` quando lo show in esecuzione ha modifiche non salvate. `GET /api/v1/showfile` dice se ne ha.

### Pulsanti, fader e interruttori della console

```
GET /api/v1/widgets
POST /api/v1/widgets/b1/press
PUT  /api/v1/widgets/f1/value   { "value": 70 }
PUT  /api/v1/widgets/t1/state   { "on": true }
```

`GET /widgets` elenca i pannelli con il loro `id`, `label`, comando e il valore attuale (fader) o lo stato (interruttori). Premere, muovere o commutare esegue il comando impostato nel pannello – lo stesso che attiva un operatore – e i pannelli su ogni dispositivo seguono (un pulsante premuto pulsa, fader e interruttori con lo stesso comando si muovono insieme). Il valore di un fader è limitato al suo minimo / massimo. Un pannello senza comando risponde `409 no_command` (un interruttore senza comandi si limita a commutare). I pannelli sono quelli del layout della **console**; i dispositivi remoti hanno layout propri.

### Uscite e layout

```
PUT  /api/v1/system   { "artnet": { "ip": "192.168.1.255" }, "sacn": { "enabled": false } }
POST /api/v1/layouts/Concert.json/load
POST /api/v1/fixture-types   (raw .gdtf file, header X-Filename: my_fixture.gdtf)
```

### Caricare un supporto

```
curl -X POST -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/octet-stream" \
     -H "X-Filename: intro.mp4" --data-binary @intro.mp4 http://127.0.0.1:8000/api/v1/media
```

### Eventi in diretta (flusso)

```
curl -N -H "Authorization: Bearer oc_xxxxxxxx" "http://127.0.0.1:8000/api/v1/events?events=cue,blackout,command"
```

```
event: hello
data: {"app": "OpenCue", "events": ["blackout", "cue", "command"]}

event: cue
data: {"cuelists": [{"id": "7e5d…", "name": "Show", "active_cue": {"id": "700…", "number": 2, "name": "Blue", …}}]}

event: command
data: {"command": "Fixture 1 At 10", "success": true, "message": "OK: …", "time": "21:14:03"}
```

La connessione resta aperta. Arrivano prima `hello` e un messaggio per genere con lo **stato attuale**, poi ogni modifica. Generi: `cue` (il cue attivo di una lista è cambiato), `cuelists` (liste / cue aggiunti, rimossi, rinominati), `blackout`, `master`, `timecode` (avviato, fermato, velocità), `selection`, `effects`, `fixtures`, `variables`, `show` (nome / modifiche non salvate), `command` (è stato eseguito un comando di console, da qualsiasi parte), `audio` (sorgente aperta / chiusa, tempo, segnale presente). Solo su richiesta (`?events=beat,hit`): `beat` (ogni battito, con il tempo) e `hit` (ogni colpo di cassa / rullante / hi-hat: `{"drum": "kick", "strength": 0.9}`). `?events=` limita il flusso. Le modifiche vengono rilevate entro circa 0,1 s. Ogni 15 s arriva una riga di commento (`: keep-alive`); al massimo 20 flussi girano contemporaneamente. Richiede il permesso *Stato*.

In un browser `EventSource` non può inviare intestazioni: usate invece `?access_token=<token>`, oppure `fetch()` con un'intestazione e leggete il flusso. Il token compare allora nell'indirizzo, quindi date a una tale pagina un token proprio con solo *Stato*.

---

## 7. Piccoli programmi

Python, con la libreria `requests` (funziona qualsiasi libreria HTTP):

```python
import requests

BASE = "http://127.0.0.1:8000/api/v1"
HEAD = {"Authorization": "Bearer oc_xxxxxxxx"}

# What is the colour of every fixture?
for fx in requests.get(f"{BASE}/fixtures/state", headers=HEAD).json()["fixtures"]:
    color = fx["state"].get("color")
    print(fx["fid"], fx["name"], color["hex"] if color else "-")

# Dim the front lights, then start the next cue
requests.post(f"{BASE}/command", headers=HEAD, json={"command": "Fixture 1 At 30"})
requests.post(f"{BASE}/cuelists/Show/go", headers=HEAD)
```

Costruire un piccolo show (richiede i permessi di modifica):

```python
requests.post(f"{BASE}/fixtures", headers=HEAD, json={"type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "address": 1, "group": "Wash"})
requests.post(f"{BASE}/variables", headers=HEAD, json={"name": "Warm", "type": "color", "values": {"hex": "#ffb060"}})
requests.post(f"{BASE}/cuelists", headers=HEAD, json={"name": "Show"})
requests.post(f"{BASE}/cuelists/Show/cues", headers=HEAD, json={
    "number": 1, "name": "Warm", "fade": 3,
    "changes": [{"group": "Wash", "values": {"dimmer": 80}, "variables": {"color": "Warm"}}]})
requests.post(f"{BASE}/showfile/save-as", headers=HEAD, json={"name": "From the API"})
```

Una pagina web che mostra il cue attivo in diretta (JavaScript nel browser; la pagina può provenire da qualsiasi indirizzo, vedi la sezione 8):

```javascript
const res = await fetch("http://192.168.1.20:8000/api/v1/events?events=cue", { headers: { Authorization: "Bearer oc_xxxxxxxx" } });
const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log(value);          // "event: cue\ndata: {...}\n\n"
}
```

---

## 8. Altri dispositivi e sicurezza

- **Da un altro computer o tablet** l'API è raggiungibile non appena **Consenti l'accesso via HTTP** (Impostazioni → Accesso remoto) è attivo. Usate l'indirizzo della console (mostrato in quella pagina) invece di `127.0.0.1`, ad esempio `http://192.168.1.20:8000/api/v1/status`. Con l'accesso remoto spento la porta è chiusa alla rete. Il **token sostituisce la password** in quel caso – non serve alcun accesso.
- I token danno un vero controllo sulle luci. Date a ogni programma il **proprio token con solo i permessi di cui ha bisogno** ed eliminate i token che non usate più.
- I **permessi di modifica sono spenti di default** e possono cambiare o distruggere dati dello show: *Patch*, *File show* e *Comandi della console* sono contrassegnati come **critici**. *Carica* e *Nuovo* rifiutano di buttare via modifiche non salvate senza `force`.
- Il traffico è semplice HTTP all'interno della vostra rete. Non esponete la porta a internet.
- Le **pagine web su altri indirizzi** (la vostra dashboard, uno strumento web nel browser) possono chiamare direttamente l'API: le risposte portano le intestazioni per l'accesso cross-origin (CORS) e la richiesta preliminare del browser (`OPTIONS`, che non può portare un token) riceve risposta. La pagina ha comunque bisogno di un token nell'intestazione `Authorization`, e deve tenere il token per sé (non mettete un token potente in una pagina web pubblica). Disattivatelo in *Impostazioni → API → Consenti pagine web su altri indirizzi* se non vi serve; i browser bloccano allora di nuovo tali pagine (programmi e script non sono interessati).
- L'API modifica lo show **in memoria**, come la finestra. Nulla viene scritto su disco finché lo show non viene salvato (`POST /showfile/save`, o *Salva* nella finestra).

---

## 9. Quando qualcosa non funziona

| Problema | Controllare |
|---|---|
| `401 unauthorized` | Intestazione scritta `Authorization: Bearer oc_…` con il token completo? Token eliminato o rigenerato? |
| `403 forbidden` | Al token manca questo permesso – aprite il token in *Impostazioni → API* e attivatelo (il messaggio lo nomina). |
| `403 api_disabled` | L'interruttore principale in *Impostazioni → API* è spento. |
| `403 remote access disabled` | Chiamate da un altro dispositivo mentre *Consenti l'accesso via HTTP* è spento. |
| `404 not_found` | Controllate il numero dell'apparecchio, il nome della lista di cue (esattamente) e il numero del cue. |
| `409 duplicate` | Il nome è occupato (maiuscole / minuscole non contano). Scegliete un altro nome o modificate quello esistente con `PUT`. |
| `409 cue_exists` | Nella lista c'è un cue con questo numero: `on_conflict` o `PUT`. |
| `409 unsaved_changes` | Salvate prima (`POST /showfile/save`) o inviate `force: true`. |
| `409 no_command` / `409 wrong_type` | Un pannello non ha comando impostato / avete premuto un fader, mosso un pulsante … (vedi `GET /widgets` per il tipo). |
| `422` | Un campo che non esiste (errore di battitura?) o un tipo sbagliato – il messaggio nomina il campo. |
| `422 invalid_script` | Lo script contiene un errore – il messaggio nomina la riga. `POST /effect-scripts/check` prova senza salvare. |
| `200` ma `"success": false` | Il comando è stato rifiutato – leggete `message`. |
| `429` | Troppi token sbagliati da questo indirizzo. Attendete `Retry-After` secondi. |
| Pagina del browser: «bloccato da CORS» | *Impostazioni → API → Consenti pagine web su altri indirizzi* è spento, o la richiesta non ha un token (la risposta di errore dell'API porta le intestazioni, così il vero motivo è visibile). |
| Nessuna risposta | OpenCue è in esecuzione e la porta è giusta (la mostra Impostazioni → Accesso remoto)? |

---

## 10. Hardware e controllo rapido: il flusso WebSocket

Per l'**hardware** (ESP32, Arduino, Raspberry Pi, un banco autocostruito) e ogni applicazione che invia o riceve **molti piccoli valori rapidamente**, accanto alle route HTTP c'è un **WebSocket**: `ws://<console>:8000/api/v1/ws`. Una connessione resta aperta ed entrambe le parti inviano piccoli **messaggi JSON** (frame di testo) – senza il costo di una nuova richiesta HTTP per ogni valore. Non richiede alcun permesso aggiuntivo: ogni messaggio richiede **lo stesso permesso della route HTTP corrispondente** (tabella sotto). Con il preset *Esercizio* funziona tutto tranne il DMX grezzo.

### Connettersi e accedere

Il token si può inviare in tre modi (i microcontrollori trovano l'indirizzo più facilmente):

1. nell'indirizzo: `ws://opencue.local:8000/api/v1/ws?access_token=oc_xxxxxxxx`
2. nell'intestazione: `Authorization: Bearer oc_xxxxxxxx` (o `X-API-Key`)
3. come **primo messaggio** entro 5 s: `{"op": "auth", "token": "oc_xxxxxxxx"}`

Poi OpenCue invia `{"op": "hello", ...}` con i permessi, le operazioni, gli argomenti e i limiti consentiti. Gli errori chiudono la connessione con un codice: `4401` (token mancante / sbagliato), `4403` (API spenta, solo questo PC, accesso remoto spento, token disattivato), `4429` (troppi tentativi falliti / troppe connessioni). Valgono le stesse regole di HTTP: *API REST attiva*, *Raggiungibile da*, blocco dopo tentativi falliti. Al massimo 10 connessioni sono aperte contemporaneamente.

Ogni messaggio è un oggetto JSON con `"op"`. Un **`"id"`** facoltativo (qualsiasi numero o testo) torna nella risposta: `{"op": "ack", "id": 7, ...}` in caso di successo, `{"op": "error", "id": 7, "code": "...", "message": "..."}` in caso di errore. Senza `id` vengono risposti solo gli errori. Un messaggio difettoso non termina mai la connessione.

### Messaggi dall'hardware

| `op` | Permesso | Cosa fa |
|---|---|---|
| `joystick` | Programmer | Un joystick – vedi sotto |
| `set` | Programmer | Impostare valori, **assoluti** o **relativi** – vedi sotto |
| `select` | Programmer | Cambiare la selezione: `{"op":"select","mode":"set","fixtures":[1,2]}` (`mode`: `set`, `add`, `remove`, `clear`) |
| `cmd` | Comandi | Comando di console: `{"op":"cmd","line":"Cuelist Main Go"}` (risposta: `success`, `message`) |
| `cue` | Cue | `{"op":"cue","list":"Main","action":"go"}`; `action`: `go` (con `"cue": 5` salta), `back`, `pause`, `resume`, `stop`, `fader` (con `"value"`) |
| `master`, `blackout` | Blackout / Master | `{"op":"master","value":70}`, `{"op":"blackout","on":true}` |
| `dmx` | Canali DMX | `{"op":"dmx","universe":1,"channels":{"1":255,"2":0}}` – valori di canale grezzi come `PUT /dmx/{universe}` |
| `tap` | Audio | Battere il tempo (un pulsante sull'ESP32) |
| `timecode` | Timecode | Controllare il timecode: `{"op":"timecode","action":"play"}` (anche `pause`, `stop`, `seek`, `rate`) – oppure `{"op":"timecode","action":"sync","position":12345,"running":true}`: OpenCue **segue** un clock esterno (posizione in ms o `"0:12.345"`; gli scostamenti sotto 60 ms non vengono corretti così il clock non trema; un salto lo sposta senza far scattare i cue) |
| `audio_in` | Audio | Audio **in ingresso** – vedi sotto |
| `subscribe`, `unsubscribe` | per argomento | **Sottoscrivere** valori in diretta – vedi sotto |
| `ping` | – | Risposta `{"op":"pong","t":<il vostro t>,"server_ms":...}`: misurare il tempo di andata e ritorno, confrontare i clock |

Le destinazioni (`set`, `joystick`, `select`) si chiamano come nelle route HTTP: `"fixtures": [1, 2, "Front 3"]`, `"fixture": 5`, `"group": "Front"` e / o `"selection": true` (la selezione della console). Senza nessuna di esse si usa la selezione.

### Impostare valori: assoluti e relativi

```json
{"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80, "pan": 25, "color": "#ff8800"}}
{"op": "set", "group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}
```

- **assoluto** (predefinito): i valori sono i nuovi valori – percentuale 0–100, colore come `#rrggbb` / `[r,g,b]`, canali grezzi come `ch<N>` (0–255).
- **relativo** (`"mode": "relative"`): i numeri sono **variazioni in punti percentuali** (da −100 a 100); ogni apparecchio parte dal **proprio** valore ed è limitato a 0 / 100 %. Va bene per le manopole rotative e i pulsanti «un po' più avanti». Colori e canali grezzi non possono essere relativi.

HTTP ha lo stesso: `PUT /programmer/values` con `"mode": "relative"`. Pan e tilt vengono impostati con la piena **risoluzione a 16 bit** (grossolano e fine).

### Joystick

```json
{"op": "joystick", "selection": true, "x": 0.35, "y": -0.8}
```

`x` e `y` vanno da −1 a 1 (destra / su positivi). Di default pilota pan (`x`) e tilt (`y`) degli apparecchi selezionati; `"axes": {"x": "pan", "y": "zoom"}` assegna qualsiasi attributo (`dimmer`, `zoom`, `focus`, `strobe`, `gobo`, `prism` ...). Due modalità (`"mode"`):

- **`rate`** (predefinita, **relativa**): la deflessione stabilisce la **velocità**, non la posizione – come il joystick nel programmer. Piccole deflessioni sono molto precise (vicino al centro circa 1° al secondo), grandi veloci (all'estremo esterno l'intero intervallo scorre in pochi secondi); la curva è esponenziale. OpenCue integra il movimento **da sé a 40 Hz** dall'ultima deflessione segnalata – il dispositivo deve solo inviare le modifiche e il valore attuale ogni 20–50 ms; il jitter del WLAN non rende il movimento a scatti. Più apparecchi selezionati si muovono della stessa quantità dal **loro** valore di partenza; a fine intervallo si fermano. Con `x = y = 0` (o dentro la zona morta) la leva è rilasciata: **gli apparecchi restano dove sono**.
- **`position`** (**assoluta**): la deflessione è la posizione – `x = −1` è pan 0 %, `x = 1` pan 100 %. Non utile per una leva a molla, ma per un encoder o un cursore.

Altri campi: `stick` (un nome quando un dispositivo ha più leve; predefinito `main`, fino a 4), `speed` (fattore 0,05–4 per la velocità, predefinito 1), `deadzone` (0–0,5, predefinito 0,04), `timeout_ms` (100–5000, predefinito 500), `invert_y`, `release: true` (rilasciare subito). Le destinazioni vengono fissate al primo tocco della leva e mantenute fino al rilascio.

**Dispositivo di sicurezza (uomo morto):** se non arriva alcun messaggio per più di `timeout_ms` (cavo staccato, WLAN assente, dispositivo bloccato) la leva si ferma e OpenCue segnala `{"op":"joystick","stick":"main","state":"timeout"}`. Se la connessione cade, tutti gli apparecchi restano dove sono.

### Sottoscrivere valori in diretta

`{"op":"subscribe","topic":"<topic>","hz":30}` – `hz` è la frequenza massima (1–60, predefinita 30). OpenCue invia solo ciò che è **cambiato**. `unsubscribe` con `"topic"` termina la sottoscrizione.

| `topic` | Permesso | Messaggi |
|---|---|---|
| `audio` | Stato | `{"op":"audio","t":ms,"running":true,"v":{"a_level":0.62,"a_bass":0.9,"a_bpm":124,...}}` – le variabili audio dell'analisi audio; `"keys": ["a_level","a_bass"]` le limita |
| `dmx` | DMX | `"universes": [1]` (fino a 8): prima `{"op":"dmx","universe":1,"full":true,"values":[512 numbers]}`, poi solo `{"op":"dmx","universe":1,"changes":{"17":255}}` (canale → valore) |
| `fixtures` | DMX | `{"op":"fixtures","values":{"3":{"pan":12.5,"tilt":50,"dimmer":100,"color":{...}}}}` – valori in diretta per **numero** di apparecchio, solo quelli cambiati |
| `timecode` | Stato | `{"op":"timecode","ms":83400,"text":"00:01:23.400","running":true,"direction":1,"rate":1}` – mentre il clock scorre a ogni tick (fino a 60 Hz), altrimenti solo a una modifica (avvio, stop, salto, velocità) |
| `events` | Stato | come `GET /events`: `{"op":"event","event":"cue","data":{...}}`; `"events": ["cue","blackout"]` sceglie (predefinito: i generi standard; `beat` e `hit` solo su richiesta). Prima viene lo stato attuale |

### Audio in ingresso: un microfono sull'ESP32

Con la sorgente audio **«Rete (flusso API)»** OpenCue analizza l'audio che un dispositivo invia – livello, bande, cassa / rullante / hi-hat, tempo e battito esistono allora come variabili `a_` per **effetti, trigger di cue e il pannello Audio** come al solito.

1. Aprite la sorgente: scegliete *Rete (flusso API)* nel pannello Audio, oppure `PUT /audio` con `{"device": "network"}`, oppure fatelo con il messaggio del passo 2 (`"open": true`).
2. `{"op":"audio_in","rate":16000,"open":true}` – annuncia PCM (`rate` 8000–48000 Hz, **16 bit con segno little endian, mono**).
3. Poi inviate **frame binari** (WebSocket binario) con i campioni, ad es. 20 ms alla volta (640 byte a 16 kHz). Al massimo 64 KB per frame.

Se la sorgente non è aperta OpenCue risponde (al massimo una volta al secondo) con l'errore `audio_source`. Senza dati l'analisi continua sul silenzio.

### Limiti e protezione

**L'uscita DMX ha sempre la priorità**: gira in un thread proprio (priorità leggermente superiore) e il flusso è limitato – l'hardware non può quindi mai rallentare la console. Al massimo 300 messaggi al secondo per connessione (raffiche fino a 600) e 1200 in totale – i successivi ricevono `rate_limited` e vengono scartati; messaggi di testo fino a 8 KB, frame binari fino a 64 KB; 10 connessioni; un joystick cambia al massimo a 40 Hz. Una connessione che non accede viene chiusa dopo 5 s.

### Esempio: ESP32 con un joystick (Arduino)

```cpp
#include <WiFi.h>
#include <WebSocketsClient.h>          // Bibliothek "WebSockets" von Markus Sattler (arduinoWebSockets)

const char* WIFI_SSID = "MeinWLAN";
const char* WIFI_PASS = "geheim";
const char* TOKEN     = "oc_xxxxxxxx";      // Token mit "Programmer" (write.programmer)
const int PIN_X = 34, PIN_Y = 35;           // die beiden Achsen des Joysticks (ADC)

WebSocketsClient ws;
int centerX = 2048, centerY = 2048;

float norm(int raw, int center) {           // 0..4095 -> -1..1
  float f = (raw - center) / 2048.0f;
  return f < -1 ? -1 : (f > 1 ? 1 : f);
}

void onEvent(WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_CONNECTED) Serial.println("OpenCue verbunden");
  if (type == WStype_TEXT)      Serial.printf("%s\n", payload);       // hello, Fehler, Rueckmeldungen
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(200);
  delay(300);
  centerX = analogRead(PIN_X);              // Ruhelage beim Start merken
  centerY = analogRead(PIN_Y);
  String path = String("/api/v1/ws?access_token=") + TOKEN;
  ws.begin("opencue.local", 8000, path);    // oder die IP-Adresse der Konsole
  ws.onEvent(onEvent);
  ws.setReconnectInterval(2000);
  ws.enableHeartbeat(15000, 3000, 2);
}

void loop() {
  ws.loop();
  static uint32_t last = 0;
  if (ws.isConnected() && millis() - last >= 20) {      // 50 Mal pro Sekunde
    last = millis();
    float x = norm(analogRead(PIN_X), centerX);
    float y = -norm(analogRead(PIN_Y), centerY);        // nach oben = Tilt mehr
    char msg[128];
    snprintf(msg, sizeof msg, "{\"op\":\"joystick\",\"selection\":true,\"x\":%.3f,\"y\":%.3f}", x, y);
    ws.sendTXT(msg);
  }
}
```

Il dispositivo continua a inviare `x = 0, y = 0` a riposo – non fa danni (la leva conta come rilasciata). La selezione sulla console decide cosa si muove; con `"fixtures": [1, 2]` o `"group"` al posto di `"selection": true` la destinazione è fissa.

### Esempio: Python

```python
import asyncio, json, websockets            # pip install websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws?access_token=oc_xxxxxxxx") as ws:
        print(json.loads(await ws.recv()))                           # hello
        await ws.send(json.dumps({"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80}}))
        await ws.send(json.dumps({"op": "subscribe", "topic": "audio", "hz": 30, "keys": ["a_level", "a_bass"]}))
        async for text in ws:
            frame = json.loads(text)
            if frame["op"] == "audio":
                print(frame["v"])

asyncio.run(main())
```

Un riferimento di tutti i messaggi si trova anche nella pagina `/api/v1/docs`.

---

## 11. Viste di stato: immagini e pagine web per dispositivi semplici

Per i dispositivi che sanno solo **recuperare un'immagine** o mostrare una **pagina semplice** – un ESP32 con un display, un vecchio tablet come display a parete, una scheda del browser sul monitor del foyer – ci sono le **viste di stato**. Sono **di sola lettura** (nessun comando), non richiedono **alcuna libreria** sul dispositivo e OpenCue le genera da sé: il contenuto è lo stesso come immagine o come pagina.

| Vista | Mostra | Permesso |
|---|---|---|
| `status` | show, blackout, master, timecode, il cue attivo di ogni lista, tempo | Stato |
| `timecode` | il clock, grande, «in esecuzione / fermo» | Stato |
| `dmx` | i 512 canali di un universo come griglia (`?universe=1`), luminosità = valore | DMX |
| `cue` | il cue attivo di una lista (`?list=Main`) e il successivo | Stato |
| `audio` | livello, le otto bande, tempo | Stato |

Ogni vista esiste in più forme (`GET /api/v1/views/<name>…`):

| Indirizzo | Risultato |
|---|---|
| `/views/status` | **pagina web** che si aggiorna da sola (`?refresh=2` secondi); senza JavaScript tramite meta refresh |
| `/views/status.png` | **immagine PNG** (`?w=320&h=240&theme=dark`; dimensioni da 64×48 a 800×600; `theme`: `dark` o `light`) |
| `/views/status.bmp` | **BMP** a 24 bit – qualsiasi piccolo decoder lo capisce |
| `/views/status.rgb565` | **pixel grezzi**, 16 bit ciascuno (5-6-5, byte alto per primo); la dimensione è nelle intestazioni `X-Width` / `X-Height`: datelo direttamente a un TFT (nessun decoder necessario) |
| `/views/status.json` | il modello di visualizzazione (parti: titolo, righe, barre, griglia) – per chi vuole disegnare da sé |
| `/views` | elenco di tutte le viste con i loro parametri |

Accedete come al solito. Un browser o un dispositivo che non può inviare un'intestazione aggiunge il token (`access_token`, funziona anche `token`; spazi e virgolette portati con la copia non contano). Il messaggio dice se il token è **mancante** o **non valido / eliminato**; la console registra ogni accesso rifiutato. Se il primo caricamento di `opencue.local` si blocca (Windows a volte risolve lentamente i nomi `.local` la prima volta), usate l'**indirizzo IP** – è elencato in *Impostazioni → API REST* (da copiare): `…/views/status?access_token=oc_xxxxxxxx` (il token fa allora parte dell'indirizzo – create per questo un token separato **con solo «Stato» e «DMX»**). L'interruttore **Viste di stato** in *Impostazioni → API REST* spegne tutto (risposta `403 views_disabled`).

**Colore:** `?color=green` (o `amber`, `red`, `blue`, `cyan`, `white`, `magenta`, `violet`, `orange`, `yellow`, oppure `#rrggbb`) cambia il colore di evidenziazione; il monitor DMX è **verde** di default.

**Gli errori sono visibili:** se qualcosa non va (token sbagliato, viste spente, nessun permesso) torna un'**immagine** (`.png` / `.bmp` / `.rgb565`) con il giusto codice di stato (401, 403 ...) **come immagine con il messaggio** – un display la mostra semplicemente («TOKEN MISSING OR WRONG», «STATUS VIEWS ARE OFF» ...); la **pagina web** mostra una pagina con il messaggio e si ricarica ogni 5 s. Se OpenCue non è raggiungibile dopo l'apertura della pagina, la pagina mostra in alto **«Nessuna connessione a OpenCue»** e attenua l'ultima immagine finché non funziona di nuovo. `.json` mantiene il messaggio di errore JSON.

**L'uscita DMX ha sempre la priorità:** le immagini vengono ricalcolate al massimo ogni 0,4 s per vista e dimensione (molti dispositivi condividono un'immagine), in un thread in background, e mai più di quattro contemporaneamente. Un'immagine 320×240 costa circa 6 ms. Il thread di uscita DMX gira inoltre con una priorità leggermente superiore.

### ESP32 con un TFT: un'immagine ogni due secondi

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>                       // 320 x 240 display

TFT_eSPI tft;
uint16_t frame[320 * 240];                  // 150 KB: on an ESP32 without PSRAM ask for 160 x 120 instead

void loop() {
  HTTPClient http;
  http.begin("http://opencue.local:8000/api/v1/views/status.rgb565?w=320&h=240&access_token=oc_xxxxxxxx");
  if (http.GET() == 200) {
    WiFiClient* s = http.getStreamPtr();
    s->readBytes((uint8_t*)frame, sizeof frame);
    tft.setSwapBytes(true);
    tft.pushImage(0, 0, 320, 240, frame);
  }
  http.end();
  delay(2000);
}
```

Per dispositivi con poca memoria: scegliete una dimensione più piccola (`w=160&h=120`) oppure passate il flusso al display riga per riga.

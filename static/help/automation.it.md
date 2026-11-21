# Pianificazione, ora del giorno e OSC

Tre modi per avviare cose **senza premere Go**: una **pianificazione** che esegue comandi a una certa ora, cue che **aspettano un'ora** e messaggi **OSC** di altri programmi e dispositivi. Tutti e tre si trovano nel menu **Controlli**.

---

## 1. Pianificazione: comandi a una certa ora

**Controlli → Pianificazione...** elenca i comandi che OpenCue esegue da solo – per l'illuminazione di una facciata, «apertura porte alle 19:00», una pausa, «avvia la lista di cue alle 18:55».

- **Nuova voce** aggiunge una riga. Ogni riga ha: l'interruttore **acceso / spento**, l'**ora** (`19:00` o `19:00:30`), la **ripetizione** (**Ogni giorno** – predefinita, non serve la data; **Nei giorni della settimana** – poi fate clic sui pulsanti dei giorni, lun–ven è preselezionato; **Una volta, a una data** – la voce viene eseguita **una volta** in quel giorno e poi si disattiva da sola), un **nome** e il **comando** – qualsiasi comando della riga di comando, ad esempio `Cuelist Main Go`, `Blackout Off` o `Master 60` (vedi la guida *Riga di comando*).
- **prossima: ...** mostra quando la voce verrà eseguita la prossima volta. **Esegui ora** esegue subito il comando, per provarlo. Il pulsante cestino elimina la voce – OpenCue chiede prima (una riga nuova e vuota scompare senza chiedere). Il comando può contenere più comandi separati da `,` o `;` (`Blackout Off; Cuelist Main Go`).
- L'orologio nel titolo è quello del computer della console. Una voce scatta **una volta** alla sua ora, anche oltre la mezzanotte. Se il computer era in sospensione, contano solo le ore dell'**ultimo minuto** – nulla viene «recuperato».
- La pianificazione **appartiene allo show**: è salvata nel file dello show, fa parte dei backup e modificarla segna lo show come non salvato. Ogni esecuzione compare nella cronologia dei comandi e come breve messaggio.

---

## 2. Un cue che aspetta un'ora

Nella finestra del cue scegliete il trigger **Ora del giorno** (oppure scrivete `clock 19:30` / `clock 20:00 sat,sun` nella cella del trigger, o usate il comando `Cue 3 Trigger Clock 19:30 Mon-Fri`). Il cue si comporta allora come gli altri trigger (audio, MIDI, timecode): quando è il **cue successivo di una lista in esecuzione**, scatta non appena l'**orologio raggiunge quell'ora** in uno dei giorni scelti. Se la sua ora è già passata quando diventa il cue successivo, aspetta la volta seguente – non scatta subito.

Uso tipico: *Cue 1 (Go, luci di sala) – Cue 2 (Ora del giorno 19:30, inizio dello spettacolo) – Cue 3 (Follow)*. La pianificazione può avviare la lista alle 18:55, il cue a orario aspetta poi le 19:30.

---

## 3. OSC

**OSC (Open Sound Control)** è un protocollo di rete che molte app e dispositivi parlano – **TouchOSC** (fader e pulsanti su tablet / telefono), **QLab**, **Ableton**, controller di show. Con esso un altro software controlla OpenCue, e OpenCue può inviare messaggi.

**Controlli → OSC ...** (l'interruttore e la porta si trovano anche in **Impostazioni → OSC**; entrambi modificano la stessa impostazione):

1. Attivate **Ricevi OSC**. Vengono mostrati la **porta UDP** (predefinita `9000`) e gli indirizzi di questo computer; inseriteli nell'altra app (`192.168.1.20:9000`). È **disattivato** finché non lo attivate; Windows può chiedere una volta del firewall (*Impostazioni → Accesso remoto → Firewall di Windows* lo configura).
2. Gli **indirizzi integrati** funzionano subito: `/opencue/go`, `/opencue/back`, `/opencue/pause`, `/opencue/resume`, `/opencue/stop`, `/opencue/blackout` (1 = acceso, 0 = spento, nessun valore = commuta), `/opencue/master` e `/opencue/fader` (valore da 0 a 1), `/opencue/cue/<numero>` (salta a quel cue). Un pulsante che invia 1 alla pressione e 0 al rilascio viene gestito correttamente: conta solo la pressione.
3. **I vostri indirizzi**: **Nuova mappatura** – l'**indirizzo** (`/my/button1`, `*` e `?` sono ammessi), il **comando** e quando viene eseguito: **solo alla pressione** (valore superiore a 0) oppure **a ogni messaggio** (per i fader). Nel comando, `{value}` è il primo valore del messaggio **convertito in un intervallo** (di default 0..1 diventa 0..100): `Master {value}` con un fader. **Impara** prende l'indirizzo del prossimo messaggio in arrivo – premete il pulsante nell'altra app. *Nella cronologia* mostra il comando nella cronologia dei comandi (un flusso di fader la inonderebbe). Il pulsante cestino elimina la mappatura – OpenCue chiede prima. Anche qui il comando può essere concatenato (`Blackout On, Cuelist Main Stop`).
4. Il **monitor** in basso mostra ogni messaggio in arrivo e cosa ne è stato (*integrato*, *mappatura*, *nessuna mappatura*, *bloccato*).
5. **Indirizzi integrati** (da espandere): disattivarli tutti, cambiare il **prefisso** (`/opencue/go` diventa ad esempio `/light/go` se un altro programma usa già `/opencue`) e disattivare **singoli** indirizzi.
6. **Invia a** imposta la destinazione dei messaggi propri di OpenCue: **Invia messaggio di prova** o il comando `Osc /address 0.5` (vedi *Riga di comando*).
7. **Restituire lo stato (feedback)**: OpenCue segnala il proprio stato **da solo** alla destinazione (e, se *Anche a ogni mittente* è attivo, a ogni dispositivo che gli ha inviato un messaggio nell'ultima ora – sulla porta della destinazione). È ciò che serve ai display e alle luci dei pulsanti di TouchOSC. Vengono inviate solo le **modifiche**, più tutto in una volta all'attivazione, quando compare un nuovo dispositivo e con **Invia tutto ora**. Vengono segnalati (con lo stesso prefisso degli indirizzi integrati): `/opencue/cuelist` (nome della lista attiva), `/opencue/cue` (numero del cue attivo, `-1` = nessuno), `/opencue/cuename`, `/opencue/state` (`running`, `paused`, `stopped`, `done` o `idle`), `/opencue/fader` e `/opencue/master` (da 0 a 1), `/opencue/blackout` (1 / 0) e `/opencue/cue/<numero>` = `1` per il cue attivo e `0` quando termina (la luce di un pulsante cue). Sotto **Cosa viene segnalato** si possono disattivare singoli messaggi. È **disattivato** finché non lo attivate.

**Sicurezza:** OSC **non ha password** – chiunque nella rete può inviare. Per questo è disattivato di default; **Mittenti consentiti** lo limita a degli indirizzi (`192.168.1.` = l'intera sottorete, o un singolo indirizzo); e un'ondata di messaggi viene rallentata (300 messaggi al secondo). `/opencue/cmd "<comando>"` potrebbe eseguire **qualsiasi** comando (anche *Delete*), perciò funziona solo se attivate **Consenti qualsiasi comando**.

---

## 4. DMX plug and play

(Anche nella guida *Primi passi*, sezione 6.) **Art-Net: Impostazioni → Uscita DMX → Trova dispositivi automaticamente** cerca i dispositivi in rete e invia a ciascuno di essi. **Scansiona rete** li elenca. **DMX USB**: lasciate la porta COM su **Automatico** – collegate l'adattatore e si connette, anche dopo averlo scollegato e ricollegato.

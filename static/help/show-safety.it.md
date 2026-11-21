# Backup, blocchi e chiusura sicura

Hai programmato lo show prima dell'evento e ora **non salvi di proposito** mentre è in corso – niente deve essere sovrascritto per sbaglio. OpenCue ti protegge in quattro modi: **backup in background**, **ripristino** dopo un arresto anomalo, un **blocco** per gli show finiti e una **finestra di chiusura prudente**. Questa guida spiega tutti e quattro, e come segnalare un problema.

---

## 1. Backup in background

OpenCue scrive regolarmente lo **stato attuale del tuo show** – comprese le modifiche che *non* hai salvato – in una cartella nascosta. Non la vedi finché non ti serve. Un backup **non sostituisce mai il tuo file show**.

- **Quando:** ogni **15 minuti** per impostazione predefinita, ma **solo se** lo show ha modifiche non salvate e qualcosa è cambiato dall'ultimo backup. Nulla cambiato = nulla scritto.
- **Anche:** quando esci senza salvare, quando il salvataggio è fallito (per esempio perché lo show è bloccato), e subito prima di aprire o avviare un altro show mentre questo ha ancora modifiche non salvate.
- **Quanti:** vengono tenuti i **10** più recenti per show, al massimo 100 in totale; quelli più vecchi vengono eliminati automaticamente.
- **Dove:** la cartella `backups` dentro la cartella dei dati (`%LOCALAPPDATA%\OpenCue\backups`). Un backup è un normale file show.

### Impostazioni

**Impostazioni → Generale → Backup degli show**:

| Impostazione | Significato |
|---|---|
| **Esegui il backup dello show in background** | Attiva o disattiva l'intera funzione (predefinito: attiva). |
| **Ogni (minuti)** | L'intervallo, da 1 a 240 (predefinito 15). |
| **Conserva per show** | Quanti backup di uno show vengono conservati, da 1 a 50 (predefinito 10). |
| **Ripristina backup...** / **Apri cartella** | Apre la finestra di ripristino (sezione 2) o la cartella in Esplora risorse. |

Le impostazioni valgono per l'intero programma e si possono cambiare da qualsiasi dispositivo, anche da un dispositivo remoto.

---

## 2. Ripristinare un backup

**File → Ripristina backup...** (o il pulsante nelle impostazioni) elenca tutti i backup, dal più recente: nome dello show, ora, motivo (automatico, alla chiusura, manuale, prima di un ripristino, salvataggio fallito) e dimensione.

- **Ripristina** carica il backup come **show non salvato**. Il file show su disco resta esattamente com'è, anche se è bloccato. Poi **Salva** (o **Salva file show con nome...**) quando sei soddisfatto.
- Lo stato che avevi prima viene prima salvato in backup – anche un ripristino non può far perdere nulla.
- **Esegui backup ora** fa subito un backup; **Elimina** ne rimuove uno. Tutto questo funziona anche da un dispositivo remoto (*Apri cartella* vi mostra l'Esplora risorse di OpenCue).
- Show, layout, palchi e impostazioni vengono scritti **in sicurezza**: prima in un file accanto, poi scambiati – un arresto anomalo o un'interruzione di corrente a metà del salvataggio non può distruggere il file esistente.

### Dopo un arresto anomalo

Se OpenCue non è stato chiuso correttamente (arresto anomalo, interruzione di corrente, processo terminato), al prossimo avvio **propone l'ultimo backup di quella sessione**: *“OpenCue non è stato chiuso correttamente … Ripristinarlo?”* – **Ripristina**, **Mostra tutti i backup** oppure **Non ora** (i backup restano disponibili in *File → Ripristina backup...*).

---

## 3. Bloccare uno show

Uno show finito può essere **bloccato** perché nessuno lo modifichi per sbaglio. Nel **gestore file** (*File → Gestore file...*, tipo *Show*) clicca sul **simbolo del lucchetto** nella riga dello show; clicca di nuovo per sbloccare.

Uno show bloccato:

- è contrassegnato **Bloccato** nell'elenco e mostra un piccolo **lucchetto** accanto al nome dello show nella barra in alto finché è caricato,
- **non può essere sovrascritto, rinominato né eliminato** – il salvataggio mostra *“Non salvato: … è bloccato”*,
- può ancora essere **caricato**, **duplicato** (la copia non è bloccata) e salvato con **un altro nome** con *Salva file show con nome...*.

Il blocco protegge dalle distrazioni, non dalla copia: il file stesso può ancora essere modificato con qualsiasi altro programma.

---

## 4. Chiudere in sicurezza

**File → Esci** (o il pulsante di chiusura) chiede: **Salva ed esci**, **Esci senza salvare** oppure **Annulla**.

Se lo show **non può essere salvato** ma ha modifiche – è bloccato, il file è protetto da scrittura, la cartella non è scrivibile o l'ultimo salvataggio è fallito – la finestra cambia:

- Un **riquadro arancione** in alto dice *“Questo show non può essere salvato”* e indica i motivi. Dice anche se viene conservata una copia di backup delle tue modifiche.
- **Salva come copia ed esci...** sostituisce *Salva ed esci*: scegli un nuovo nome, lo show viene salvato lì, poi OpenCue si chiude.
- **Esci senza salvare** richiede **due clic**: il primo rende il pulsante rosso (*“Clicca di nuovo: esci e perdi le modifiche”*), solo il secondo esce.

Anche allora alla chiusura viene scritto un backup delle tue modifiche (se i backup sono attivi), così *File → Ripristina backup...* può ancora riportarle indietro.

---

## 5. Segnalare un problema

- **Aiuto → Apri cartella dei registri** apre la cartella con `opencue.log`.
- **Aiuto → Segnala un problema...** copia la **diagnostica** (versione, sistema, le ultime righe del registro – senza token di accesso né password) negli appunti e apre la pagina di segnalazione del progetto nel browser. Descrivi cosa hai fatto, incolla la diagnostica.
- Gli errori dell'interfaccia utente vengono scritti nel registro come **OC-3601**; un backup che non è stato possibile scrivere come **OC-3701** (vedi la guida *Codici di errore*).

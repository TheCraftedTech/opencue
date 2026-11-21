# Éditeur de frise et LTC

Avec l'**éditeur de frise**, vous placez graphiquement des cues et des commandes sur un axe temporel – avec les formes d'onde de vos morceaux en dessous. Avec le **LTC**, OpenCue suit une source extérieure (un lecteur, un DJ ou un logiciel de show, une console) ou envoie lui-même une horloge à d'autres appareils. Tout repose sur le **timecode global**.

---

## 1. L'idée en une minute

- OpenCue a **une seule** horloge, le **timecode** (panneau *Code temporel*, affichage en haut de la barre d'outils). Elle démarre, s'arrête, saute – sur tous les appareils en même temps.
- Des choses se produisent à certains moments de cette horloge : un **cue** avec le déclencheur *Code temporel* démarre, une **commande** d'une piste de commandes est exécutée, un **lecteur multimédia** lance son morceau (*heure de début*). Cela n'arrive que lorsque l'horloge **traverse** ce moment **en avant** – les sauts et la lecture à l'envers ne déclenchent rien.
- L'horloge peut être menée par **trois sources** : cet ordinateur (vous appuyez sur Démarrer), le **timecode MIDI** (*Paramètres → MIDI*) ou le **LTC** (*Paramètres → Code temporel*). Celle qui est là en premier mène.
- L'**éditeur de frise** montre tout cela sur un axe temporel et vous permet de le placer et de le déplacer confortablement – au lieu de saisir chaque heure dans la boîte de dialogue du cue.

---

## 2. Ouvrir l'éditeur de frise

- Comme panneau dans la disposition : *Modifier → Ajouter un panneau → Médias → **Éditeur de frise*** (de préférence large).
- Brièvement comme fenêtre : *Affichage → Ouvrir le panneau dans une fenêtre → **Éditeur de frise*** (tous les panneaux y figurent, par exemple aussi **Commande simple**).

---

## 3. À quoi ça ressemble

- **Règle** en haut : un clic ou un glissement saute à ce moment.
- **Une piste par liste de cues** : chaque cue avec le déclencheur *Code temporel* est un **repère** avec numéro et nom. Le nom de la liste à gauche la sélectionne (pour le plateau et « Placer le cue ici »).
- **Pistes de commandes** (rouge / rose) : des commandes de la ligne de commande à certains moments – voir la section 6.
- **Pistes audio** en bas : **automatiques** pour chaque morceau qu'un lecteur multimédia joue avec le timecode, avec une **forme d'onde** et de fines lignes à chaque repère – vous voyez si quelque chose tombe exactement sur le temps (section 5).
- **Plateau** tout en bas : les **cues sans heure** de la liste sélectionnée.
- La **tête de lecture** jaune est le timecode global.

---

## 4. Modifier les repères et naviguer

| Action | Comment |
|---|---|
| **Déplacer** un repère | le faire glisser latéralement à la souris ou au doigt ; il s'accroche à la **grille** (maintenez **Maj** = pas de grille) |
| **Déplacer finement** un repère | cliquer sur le repère, puis `←` / `→` (un pas de grille ; `Maj` = dix fois plus) |
| Placer sur la frise un cue **sans heure** | le faire glisser du **plateau** vers la piste – ou sélectionner la pastille et appuyer sur **Placer le cue ici** |
| **Grille** | *désactivée*, 10 ms, image (25 i/s), 0,1 s, 1 s |
| **Zoom** | touches `+` / `−`, Ctrl + molette, **deux doigts** (iPad) ; *Tout afficher* (`F`) |
| **Suivre** | la vue défile avec la tête de lecture |

Le **défilement** fonctionne de toutes les façons :

| Touche / bouton | Effet |
|---|---|
| **Faire glisser** la règle ou la forme d'onde | saute en continu à cet endroit (le son suit) |
| Boutons **±5 s** | cinq secondes en arrière / en avant (des clics rapides s'additionnent) |
| Boutons **repère précédent / suivant** (`[` / `]`) | saute au cue ou à l'heure de commande suivant(e) |
| `←` / `→` (focus dans le panneau) | 1 s ; avec `Maj` 10 s ; avec `Alt` une image (40 ms) |
| `Début` / `Fin` | au début / à la fin des repères |
| `Espace`, `L`, `K`, `J` | lecture / pause · avant · pause · lecture **à l'envers** |
| Bouton **Inverser** | lit le timecode à l'envers (ne déclenche ni cues ni commandes) |

---

## 5. Audio : automatiquement depuis les lecteurs multimédias

Vous n'avez pas à choisir un morceau dans la frise. La frise regarde d'elle-même **ce qui est joué avec le timecode** :

- Chaque **lecteur multimédia** en mode **Code temporel** avec un média choisi et son **heure de début** apparaît comme piste audio : avec nom, **forme d'onde** et un **repère de début** (symbole de note) à l'heure de début. Un lecteur sur **un autre appareil** (par exemple sur l'ordinateur principal pendant que vous travaillez sur l'iPad) et les **écrans de la simulation 3D** apparaissent aussi.
- **Faire glisser le repère de début** (ou double-cliquer dessus et saisir l'heure) change l'**heure de début du lecteur multimédia** – le morceau commence alors à la nouvelle heure.
- **Ajouter un son ...** crée un **son propre** à cette frise (il tourne en synchronisation avec le timecode) au cas où aucun lecteur multimédia n'est encore configuré. Le bouton haut-parleur coupe seulement ces sons propres. Sur l'iPad, le navigateur a besoin d'un toucher du panneau avant d'autoriser le son.
- OpenCue calcule la **forme d'onde** une fois avec *ffmpeg* fourni (une valeur toutes les 10 ms) et la mémorise. Si ffmpeg manque, la piste l'indique.
- Avec le **LTC**, c'est pareil : les lecteurs multimédias suivent le timecode quelle que soit la source qui le mène – les pistes audio montrent donc toujours ce qui tourne à quel moment.

---

## 6. Pistes de commandes

Une **piste de commandes** exécute des **commandes de la ligne de commande** à des moments du timecode – indépendamment des cues, par exemple `Blackout Off` à 1:30, `Cuelist Show Go` à 2:00 ou `Effect Off` au refrain. Elle appartient au **show** (enregistrée et exportée avec lui).

- **Nouvelle piste de commandes** : bouton **+**. Il peut y en avoir plusieurs (par exemple « Lumière », « Fumée », « Vidéo ») ; un double-clic sur le nom renomme, la **×** supprime (cliquer deux fois).
- **Ajouter une commande** : le bouton **Commande ici** (ou `C`) place une commande au moment actuel sur la piste sélectionnée – ou **double-cliquez** sur la piste à cet endroit.
- Une petite fenêtre demande l'**heure** et la **commande** ; `Entrée` valide. Chaque repère peut être **glissé**, déplacé avec les flèches, modifié de nouveau par un **double-clic** et supprimé avec `Suppr`.
- Le **serveur** exécute la commande lorsque le timecode **traverse** son moment **en avant** – exactement comme les cues (aussi avec le LTC / le timecode MIDI). Elle apparaît dans l'historique des commandes. Un saut l'ignore.
- En **mode opérateur**, les pistes de commandes ne peuvent pas être modifiées ; elles s'exécutent comme d'habitude.

---

## 7. Placer les cues avec la musique (enregistrement)

Comme sur une console, mais en graphique :

1. Créez vos cues (liste de cues) – leur heure peut encore être vide. Ils apparaissent dans le **plateau**.
2. Configurez un **lecteur multimédia** avec votre morceau (mode Code temporel, heure de début 0) – la forme d'onde apparaît d'elle-même.
3. Choisissez la liste de cues et le premier cue dans le plateau.
4. Lancez la lecture (Espace) et appuyez sur **Placer le cue ici** (ou `Entrée`) à chaque entrée : le cue sélectionné reçoit l'**heure actuelle**, puis le cue **suivant** est sélectionné.
5. Peaufinez ensuite tranquillement : faites glisser les repères sur la forme d'onde, laissez-les s'accrocher.

Astuce : avec la *grille 1 s* ou *image*, les repères tombent sur des temps ronds, avec *désactivée* sur la milliseconde exacte.

---

## 8. LTC : le timecode comme signal audio

Le **LTC** (Linear Timecode) est un signal audible – il sonne comme du bruit – qui transporte l'heure. Il se trouve sur un canal (généralement le gauche), la musique sur l'autre. *Paramètres → Code temporel* montre en haut **qui mène actuellement l'horloge** (cet ordinateur, le timecode MIDI ou le LTC) et comporte deux zones :

**Entrée : lire le timecode (Suivre le LTC)**

1. Activez **Suivre le LTC**, choisissez l'**entrée audio** (entrée ligne, interface USB ou le *son du système* d'un périphérique de sortie). Pour essayer, il y a le **signal de test** (25 images/s, aucun appareil nécessaire).
2. Choisissez le **canal** (gauche / droite / mélange), **Enregistrer**. En dessous, vous voyez en direct **« Signal trouvé : 00:01:12:05 · 25 i/s »** et une barre de niveau.
3. Dès qu'un signal valide arrive, le **timecode global suit**. Tous les cues, commandes et lecteurs multimédias suivent. Une **pause ou un arrêt de la source** arrête aussi le timecode ici, un **saut** de la source est suivi.
4. **24, 25, 29,97 (drop frame) et 30 images par seconde** sont reconnus.
5. Pour jouer vous-même, désactivez de nouveau **Suivre le LTC**.

**Sortie : envoyer le timecode (Envoyer le LTC)**

OpenCue devient l'horloge d'autres appareils : lorsque vous démarrez le timecode (par exemple Lecture dans le panneau *Code temporel*), le **LTC sort d'une sortie audio** – un lecteur, une console ou un enregistreur peut suivre.

1. Activez **Envoyer le LTC**, choisissez la **sortie audio** et le **canal** (*les deux*, *gauche seulement* ou *droite seulement* – utilisez un seul canal si l'autre porte de la musique).
2. Réglez la **cadence d'images** (24 / 25 / 29,97 drop frame / 30) et le **niveau** (fort mais sans écrêtage ; beaucoup d'appareils attendent un niveau ligne), **Enregistrer**.
3. Il n'est envoyé **que pendant que le timecode avance** ; à l'arrêt ou en marche arrière, la sortie est silencieuse. Si vous sautez, le signal repart aussitôt à la nouvelle heure.
4. Si OpenCue suit lui-même une source LTC ou MIDI, l'horloge est également retransmise.

**Si rien n'arrive :** vérifiez la barre de niveau (trop faible ?), le canal (gauche / droite), si l'entrée est utilisée par un autre programme.

---

## 9. Remarques

- Une **source LTC ou MIDI mène** l'horloge : Démarrer / Arrêter dans le panneau Code temporel sont supplantés par la source tant qu'elle tourne.
- Les heures appartiennent aux **cues**, aux **pistes de commandes** et aux **lecteurs multimédias** du show et sont enregistrées avec lui ; l'éditeur de frise n'est que l'outil pour cela.
- *Paramètres → Entrées et sorties* montre dans le groupe **Code temporel**, d'un coup d'œil : qui mène l'horloge, lecture / envoi du LTC, timecode MIDI.
- Plus de détails sur les sources : guide **MIDI** (timecode MIDI), guide **Accès distant** (iPad), panneau **Code temporel** (démarrer, pause, saut, vitesse), **lecteur multimédia** (heure de début).

# Raccourcis clavier et gestes

Tous les raccourcis clavier et gestes tactiles d'OpenCue au même endroit. Dans le programme, la même liste est disponible sous **Aide → Raccourcis clavier** et **Contrôles → Raccourcis clavier ...** – et vous pouvez aussi y **modifier** les raccourcis propres au programme (section 11b).

Sur un clavier Mac (ou dans un navigateur sur un Mac), `Cmd` fonctionne comme `Ctrl`.

---

## 1. Vue d'ensemble

La plupart des raccourcis sont **globaux** : ils fonctionnent où que se trouve le focus, avec une règle – **pendant que vous saisissez du texte dans un champ, seuls quelques raccourcis restent actifs** : `Ctrl+S`, `Ctrl+Shift+S`, `Ctrl+F`, `F1`, `F5`, `Ctrl+F5`, `F11` et `Ctrl+L`. Tout le reste (`Ctrl+N`, `Ctrl+O`, `Ctrl+Q`, `Ctrl+E`, touches fléchées, `Ctrl+1–9`, échelle, presse-papiers et annulation) reste silencieux afin que la saisie ne soit jamais perturbée.

---

## 2. Fichier de show

| Raccourci | Action |
|---|---|
| `Ctrl+N` | Nouveau fichier de show (demande d'abord s'il y a des modifications non enregistrées) |
| `Ctrl+O` | Ouvrir un fichier de show (ouvre le gestionnaire de fichiers sur *Shows*) |
| `Ctrl+M` | Gestionnaire de fichiers (tous les fichiers : shows, dispositions, scènes, modèles, médias, effets ...) |
| `Ctrl+L` | **Verrouiller l'écran** (menu *Contrôles → Verrouiller l'écran* ; nécessite *Paramètres → Sécurité → Utiliser le mode verrouillage* ; sur un appareil distant : se déconnecter ; en mode opérateur : demande le mot de passe pour le quitter) |
| `Ctrl+S` | Enregistrer le fichier de show **et** la disposition de cette console (un show sans nom ouvre *Enregistrer sous*) |
| `Ctrl+Shift+S` | Enregistrer le fichier de show sous un nouveau nom |
| `Ctrl+Q` | Quitter OpenCue (demande d'abord d'enregistrer) |

`Ctrl+S` fonctionne aussi pendant la saisie dans un champ de nom, par exemple dans la boîte de dialogue *Enregistrer sous*.

---

## 3. Affichage et interface

| Raccourci | Action |
|---|---|
| `?` | **Afficher / masquer ce récapitulatif de tous les raccourcis clavier** (pas pendant la saisie dans un champ ni quand une autre boîte de dialogue est ouverte) |
| `F1` | Ouvrir les **Guides** (tous les manuels dans le programme, aussi hors ligne). À l'intérieur, `Ctrl+F` cherche, `Entrée` / `Maj+Entrée` sautent à la correspondance suivante / précédente, `Échap` efface la recherche |
| `F5` | **Recharger la disposition** : la disposition actuelle est rechargée comme lors d'un changement de disposition et **tous les panneaux sont reconstruits** (utile si quelque chose – par exemple la simulation 3D – ne s'est pas affiché correctement après le démarrage). Avec des modifications de disposition non enregistrées, rien n'est relu depuis le fichier : les panneaux sont seulement reconstruits et vos modifications restent. Aussi dans *Affichage → Recharger la mise en page* |
| `Ctrl+F5` | **Recharger toute l'interface** (comme recharger une page web ; l'appareil récupère ensuite sa disposition). Aussi dans *Affichage → Recharger l'interface* |
| `F11` | Plein écran (fenêtre de la console, ou navigateur de cet appareil) |
| `Ctrl +` / `Ctrl =` | Agrandir l'interface (échelle de l'interface, par pas de 5 %) |
| `Ctrl -` | Réduire l'interface |
| `Ctrl+0` | Remettre l'échelle à 100 % |
| `Ctrl+Shift+L` | Changer de langue (l'une après l'autre : anglais, allemand, français, néerlandais, italien, espagnol) |
| `Ctrl+F` | Ouvrir / fermer la **console de commandes** : ligne de commande avec pavé et touches de commande dans une seule fenêtre – même sans ces panneaux dans la disposition ; le curseur est aussitôt dans la saisie |
| `Échap` | Fermer / annuler la boîte de dialogue, la fenêtre de panneau ou le menu du dessus – une pression ferme **une** boîte de dialogue (les Paramètres demandent d'abord s'il y a des modifications) |

L'échelle de l'interface (50–200 %) est enregistrée **par appareil** : une tablette peut être grande pendant que la console reste petite.

---

## 4. Dispositions

| Raccourci | Action |
|---|---|
| `Ctrl+1` … `Ctrl+9` | Charger la disposition 1 à 9 (favorites d'abord, puis A–Z) |
| `←` / `→` | Disposition précédente / suivante (pas dans les champs de texte, les boîtes de dialogue, les menus ni en mode édition) |
| Balayage horizontal | Disposition précédente / suivante sur les appareils tactiles (*Paramètres → Général → Changer de mise en page en glissant*, par appareil) |

Charger une disposition abandonne les modifications non enregistrées de la disposition actuelle. L'ordre est le même que sous **Affichage → Mises en page**.

---

## 5. Mode édition des panneaux

Le mode édition (**Modifier → Modifier les panneaux**) permet de déplacer, redimensionner et configurer les panneaux.

| Raccourci | Action |
|---|---|
| `Ctrl+E` | Activer / désactiver le mode édition |
| Clic sur un panneau | Le marque (fin cadre d'accentuation) |
| `Maj`/`Ctrl` + clic | Ajouter un panneau à la sélection / l'en retirer |
| Clic sur l'espace de travail vide | Efface la sélection |
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Copier / couper / coller les panneaux marqués (le presse-papiers survit à un changement de disposition) |
| `Ctrl+Z` | Annuler la dernière modification de panneau |
| `Ctrl+Y` ou `Ctrl+Shift+Z` | Rétablir |
| Clic droit → *Dupliquer* | Copie les panneaux marqués (ou cliqués) avec un petit décalage |

En **mode édition**, `Ctrl+Z` / `Ctrl+Y` s'appliquent à la disposition des panneaux. **En dehors**, ils annulent les modifications du **contenu du show** (voir *Annuler et rétablir* plus bas).

Quitter le mode édition avec des modifications non enregistrées pose la question : **Enregistrer**, **Abandonner les modifications** (recharge la disposition enregistrée) ou **Continuer l'édition**.

---

## 6. Liste des projecteurs et programmeur

| Action | Comment |
|---|---|
| Sélectionner un projecteur | Cliquer / toucher sa tuile |
| En sélectionner plusieurs | **Lasso** : tracer un cadre sur les tuiles (souris et tactile) ; le lasso reste à l'intérieur de son panneau |
| Supprimer les projecteurs sélectionnés | `Suppr` ou `Retour arrière` (demande confirmation) |
| Modifier finement une valeur de Pan/Tilt | **Balayer** vers le haut/bas sur le champ numérique (grossier : 2 px par pas, fin : 4 px par pas fin) ; toucher pour saisir |
| Ouvrir le menu contextuel | Clic droit (souris) ou appui long (tactile) sur un projecteur ou sur un espace vide |

---

## 7. Ligne de commande

| Touche | Effet |
|---|---|
| `Entrée` | Exécuter la commande |
| `↑` / `↓` | Commande plus ancienne / plus récente de l'historique (la flèche bas revient à votre brouillon) |
| `Tab` | Prendre la première suggestion ; chaque `Tab` suivant passe à la suivante |
| `Shift+Tab` | Parcourir les suggestions à l'envers |
| `Échap` | Fermer la liste des suggestions (dans la console de commandes : fermer la console) |

Détails sur les commandes : *Référence des commandes*.

---

## 8. Atelier d'effets

| Raccourci | Action |
|---|---|
| `Ctrl+S` | Enregistrer l'effet (**pas** le show) quand le curseur est dans le script |
| `Tab` | Insère deux espaces |
| `Entrée` | Nouvelle ligne avec l'indentation de la précédente (deux espaces de plus après `{`) |

---

## 9. Simulation 3D – mode construction

Ces raccourcis n'agissent dans la simulation 3D que pendant la construction (modes *Construction* / *Projecteurs*), pas en mode *Vue*.

| Raccourci | Action |
|---|---|
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | Copier / couper / coller des objets |
| `Ctrl+D` | Dupliquer l'objet sélectionné (appuyer de nouveau pour répéter le décalage) |
| `Suppr` / `Retour arrière` | Supprimer l'objet sélectionné (demande confirmation) ; en mode projecteur : retirer le projecteur de la scène |
| `Échap` | Effacer la sélection |
| `Maj` + clic | Ajouter un objet à la sélection / l'en retirer |
| Touches fléchées | Déplacer la sélection (avec `Maj` cinq fois plus loin) ; tant que quelque chose est sélectionné, les flèches ne changent pas de disposition |
| `Ctrl+Z` | Annuler |
| `Ctrl+Y` ou `Ctrl+Shift+Z` | Rétablir |

Les projecteurs n'existent qu'une fois sur une scène ; en mode projecteur, copier, couper et dupliquer sont donc désactivés.

Pendant le pointage (*Définir le point dans la simulation 3D* dans le contrôle du projecteur), `Échap` termine le pointage.

---

## 10. Gestes tactiles

| Geste | Équivaut à |
|---|---|
| Appui long | Clic droit (menu contextuel) |
| Appui long sur un élément avec info-bulle | Affiche l'info-bulle |
| Double toucher | Double-clic |
| Balayage horizontal (si activé) | Disposition précédente / suivante |
| Balayage sur un champ numérique Pan/Tilt | Modifier la valeur (grossier / fin) |

Les poignées de panneaux et les boutons de la barre d'outils ont une zone tactile d'au moins 44 × 44 px. Le balayage de disposition est reconnu à la direction du premier mouvement (au plus 25° par rapport à l'horizontale, au moins 40 % de la largeur) et ne démarre jamais sur des éléments ayant leur propre fonction de glissement (faders, tuiles de lasso, champs numériques à balayage, champs de saisie, la roue des couleurs, poignées de colonnes et de panneaux). Le défilement vertical reste du défilement.

---

## 11. Raccourcis clavier personnalisés

Une touche ou une combinaison de touches de votre choix peut déclencher une **commande de la ligne de commande** – par exemple `Ctrl+H` pour `Blackout` ou la barre d'espace pour `Cuelist Main Go`. Ouvrez la liste avec **Contrôles → Raccourcis clavier personnalisés ...** ou avec le bouton en bas de la boîte de dialogue *Raccourcis clavier*.

**Une touche pour le cue suivant :** sous *Démarrage rapide* en haut de la boîte de dialogue, cliquez sur **Cue suivant (Go)** (ou *Cue précédent*, *Pause*, *Blackout*) : une nouvelle ligne avec la commande `Go` apparaît, cliquez alors sur son champ de touche et appuyez sur la touche – par exemple la barre d'espace ou une touche d'un second clavier / pavé numérique (choisissez *Seulement ce clavier* dans la boîte de dialogue *Définir la touche*). `Go` démarre le cue suivant de la liste de cues active ; `Cuelist Main Go` toujours cette liste.

Chaque ligne comporte, de gauche à droite :

| Champ | Signification |
|---|---|
| **Actif** | Active ou désactive la ligne sans la supprimer. |
| **Touche** | Montre la touche ou la combinaison. Cliquer dessus ou sur le **bouton clavier** à côté ouvre la boîte de dialogue **Définir la touche** : vous avez **10 secondes** pour appuyer sur la touche ou la combinaison (par exemple `Ctrl` et `H` ensemble) – tout ce qui se passe de la première pression jusqu'au relâchement de toutes les touches est enregistré. `Échap` annule, le bouton à côté du champ enregistre de nouveau. En dessous, vous choisissez à quoi cela s'applique : **Tous les claviers** ou **Seulement ce clavier**. Une ligne ne reçoit sa touche que par cette boîte de dialogue. |
| **Commande** | La commande telle que vous la saisiriez dans la ligne de commande. |
| **Exécuter** | Activé : la commande s'exécute aussitôt. Désactivé : elle est seulement **écrite** dans la ligne de commande (vous la validez vous-même). |
| **Dans l'historique** | Activé : la commande apparaît dans l'historique de la ligne de commande. |
| Corbeille | Supprime la ligne (après confirmation). |

**Nouvelle combinaison de touches** en bas ajoute autant de lignes vides que vous voulez (sans enregistrement). Les modifications s'appliquent immédiatement et sur chaque appareil muni d'un clavier (aussi un iPad).

**Sauvegarder et partager :** En bas de la boîte de dialogue, **Exporter ...** enregistre l'assignation dans un fichier (`opencue-keyboard-mapping.json`), **Importer ...** lit un tel fichier. Les lignes sont **ajoutées** ; les touches que le programme ou une autre ligne utilise déjà sont ignorées (le message en donne le nombre).

**Bon à savoir**

- Les combinaisons déjà utilisées par le programme ou le navigateur (`Ctrl+S`, `Ctrl+1...9`, `Gauche`/`Droite`, `F5` ...) sont refusées pendant l'enregistrement ; chaque combinaison ne peut être utilisée qu'une fois.
- Pendant la **saisie dans un champ**, seules les combinaisons avec `Ctrl` s'appliquent. Avec une boîte de dialogue ouverte, les touches simples ne font rien, et avec la boîte de dialogue *Raccourcis clavier personnalisés* ouverte, rien ne se déclenche.
- La commande s'exécute à l'**appui** de la touche (pas au relâchement). Une touche maintenue ne la déclenche **qu'une seule fois**.
- Une combinaison peut comporter **plusieurs touches principales**, p. ex. `Ctrl+H+J` : elle s'applique dès que toutes sont enfoncées (l'ordre n'a pas d'importance). Si `Ctrl+H` existe aussi, cette combinaison plus courte attend un instant pour voir si `J` s'ajoute.
- Si une combinaison est déjà utilisée par le programme ou le navigateur (aussi comme partie d'une plus longue, p. ex. `Ctrl+S+J`), OpenCue ne l'accepte pas et affiche un message en haut de la boîte de dialogue.
- Les touches sont enregistrées indépendamment de la disposition du clavier (la touche `Z` reste la touche à cet emplacement). Le pavé numérique s'appelle `Num1` ... `Num9`.

**Touche d'un clavier précis (p. ex. macro pad, Windows seulement)**

Dans la boîte de dialogue **Définir la touche** (bouton clavier d'une ligne), vous appuyez sur la touche du clavier voulu. Sur la console sous Windows, OpenCue détecte de **quel** clavier elle provient (le nom apparaît sous le champ), et vous choisissez **Tous les claviers** ou **Seulement ce clavier**. Sur une tablette ou sans Windows, c'est le navigateur qui enregistre et cela s'applique toujours à « Tous les claviers ». Une touche s'applique soit à tous les claviers, soit à des claviers précis – pas aux deux à la fois. Une ligne réglée sur « seulement ce clavier » ne se déclenche que lorsque la touche est enfoncée sur exactement ce clavier – même quand OpenCue n'est pas au premier plan. La ligne affiche le clavier sous la touche.

- Cela ne fonctionne **sur la console elle-même** que sous Windows, pas depuis une tablette.
- OpenCue **n'écoute que lorsqu'il** existe au moins une ligne activée pour un clavier précis (ou pendant l'enregistrement). Il n'évalue que les claviers de la liste ; tout le reste est aussitôt écarté et jamais enregistré.
- Windows ne fait que signaler la touche, il ne la **bloque pas** : la touche parvient aussi au programme actif (par exemple comme caractère dans un champ de texte). Pour un macro pad, choisissez des touches qui ne font rien par ailleurs – comme `F13` à `F24` ou le pavé numérique.
- Certains claviers se déclarent comme plusieurs périphériques (par exemple touches et touches multimédias séparément). OpenCue le détecte tout seul pendant l'enregistrement.
- Deux claviers différents peuvent attribuer la même touche différemment. Un double signalement du même appui (en moins de 80 ms) ne déclenche qu'une fois.

## 11b. Modifier les raccourcis propres au programme

Les raccourcis que le programme possède déjà (`Ctrl+S`, `F11`, `Ctrl+E` ...) peuvent être déplacés sur d'autres touches ou désactivés. Ouvrez **Contrôles → Raccourcis clavier ...** et cliquez sur **Modifier les raccourcis** en bas :

1. Chaque ligne modifiable montre un cadre en pointillés autour de sa touche. **Cliquez sur la touche**, appuyez sur la nouvelle combinaison et **relâchez-la** – elle est appliquée aussitôt (la touche affiche *Appuyez sur les touches...* tant que vous la maintenez). `Échap` annule.
2. La **croix** à côté d'une ligne **désactive** ce raccourci, la **flèche** rétablit sa touche standard. **Restaurer toutes les touches standard** réinitialise tout. **Terminé** quitte le mode édition.
3. Les touches modifiées sont affichées dans la couleur d'accentuation ici, dans les menus (par exemple *Fichier → Enregistrer le fichier de show*) et dans la boîte de dialogue *Raccourcis clavier personnalisés*, qui refuse les touches déjà prises.

OpenCue refuse une combinaison déjà utilisée (par un autre raccourci, par une commande à touche personnalisée, ou par le navigateur / Windows – par exemple `Ctrl+W`). Un raccourci du programme comporte **une touche principale plus Ctrl, Alt ou Maj** ; une lettre ou un chiffre seul est refusé car il bloquerait la saisie – les touches de fonction (`F1` ... `F24`) fonctionnent seules. La modification s'applique à **tous les appareils** de la console.

Non modifiables (elles dépendent de la situation) : `Échap`, `Ctrl+C / X / V` pour les panneaux, `Ctrl+1 ... 9` pour les dispositions, les touches fléchées et les touches d'édition 3D.

---

## Annuler et rétablir (contenu du show)

En dehors du mode édition des panneaux, `Ctrl+Z` et `Ctrl+Y` (ou `Ctrl+Shift+Z`) – et *Modifier → Annuler / Rétablir* – annulent et rétablissent tout ce qui est **enregistré dans le fichier du show**, ainsi que l'opération qui précède :

- **cues et listes de cues :** enregistrer, mettre à jour, changer les heures / déclencheurs / noms (aussi plusieurs à la fois), copier, supprimer, créer, renommer, réordonner et supprimer des listes ;
- les **variables** et leurs groupes, les **groupes de projecteurs**, le **patch** (ajouter, supprimer, changer d'adresse, renommer, organiser les projecteurs), les **effets** (définitions et groupes), la **planification** et les **pistes de commandes de la frise** ;
- la **sélection** de projecteurs ;
- les **valeurs du programmeur** (couleur, position, luminosité, faisceau …) – un glissement de fader ou une commande telle que `At 80` constitue **une** étape ; l'état DMX des projecteurs concernés revient aussi en arrière ;
- les **effets en cours :** appliquer ou désélectionner un effet sur des projecteurs ;
- le **fader d'exécuteur** d'une liste de cues (un glissement = une étape).

Un court message nomme ce qui a été annulé. Des changements rapides du même genre (par exemple un balayage sur une heure ou un glissement de fader) comptent pour **une** étape ; l'historique conserve les 100 dernières étapes. Démarrer un nouveau show (*Nouveau*, *Ouvrir*) l'efface.

**Go et Back (interrupteur) :** détermine si **Go / Back / Jump** (et un `Go` saisi comme commande) sont aussi annulés – `Ctrl+Z` revient alors au cue précédent. Par défaut : **désactivé**, afin que vous ne repreniez jamais un cue par accident pendant une représentation. L'interrupteur est une icône (flèche d'annulation avec un petit triangle de lecture) dans la barre d'outils **et** sous *Paramètres → Options supplémentaires → Interrupteurs rapides* – il y fonctionne même quand l'icône est masquée dans la barre d'outils.

**Non inclus :** les paramètres, le Go via MIDI / OSC / timecode et les modifications faites par l'interface REST. Dans une boîte de dialogue ouverte et dans les champs de texte, les raccourcis ne font rien. Vous pouvez réassigner les touches sous *Raccourcis clavier → Modifier les raccourcis*.

## 12. Aide-mémoire

```
Ctrl+N  Nouveau show       Ctrl+O  Ouvrir un show     Ctrl+S  Enregistrer   Ctrl+Shift+S  Enregistrer sous
Ctrl+E  Modifier panneaux  Ctrl+Z / Ctrl+Y  Annuler / Rétablir (panneaux en mode édition, sinon contenu du show)
Ctrl+C / X / V  Copier / couper / coller des panneaux (mode édition)
Ctrl+1…9  Charger disposition   ← / →  Disposition précédente / suivante
Ctrl +  Ctrl -  Ctrl+0     Échelle de l'interface plus grande / plus petite / 100 %
Ctrl+Shift+L  Langue       F11  Plein écran     Ctrl+Q  Quitter      Échap  Fermer la boîte de dialogue
Ctrl+F  Console de commandes (ligne de commande + pavé + touches)
```

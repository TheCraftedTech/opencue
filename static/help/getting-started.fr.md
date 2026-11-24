# Premiers pas avec OpenCue

OpenCue est une console d'éclairage pour votre PC. Ce guide vous mène de l'installateur à votre première cue en une dizaine de minutes – sans aucun projecteur branché, car les premiers pas utilisent le show de démonstration intégré.

Tous les guides sont aussi dans le programme, même hors ligne : **Aide → Guides** (ou **F1**) les ouvre avec une recherche (`Ctrl+F` à l'intérieur).

---

## 1. Ce qu'il vous faut

- Un PC sous **Windows 10 ou 11** (64 bits). Le **Microsoft Edge WebView2 Runtime** affiche la fenêtre d'OpenCue ; il fait partie des versions actuelles de Windows, et l'installateur le met en place s'il manque (Internet est alors nécessaire une fois).
- Pour de vrais projecteurs : une liaison DMX – par le réseau (**Art-Net** ou **sACN**) ou une **interface USB DMX** (Enttec DMX USB Pro et compatibles). Sans matériel, vous pouvez tout programmer et le regarder dans la **simulation 3D**.
- Ni compte, ni clé de licence, ni connexion Internet pendant le travail.

---

## 2. Installation

1. Téléchargez `OpenCue-Setup-v<version>.exe` depuis la page des versions (Releases) du projet et lancez-le.
2. L'installation commence par une page d'accueil où vous choisissez la **langue** (anglais ou allemand ; c'est aussi la langue d'OpenCue lui-même – vous pourrez en choisir d'autres plus tard dans le menu *Langue*).
3. Cliquez pas à pas : **Licence** (la GNU GPL, à lire), **Dossier du programme**, **Dossier de données**, **Raccourcis** (menu Démarrer, bureau), le récapitulatif, **Installer**.
4. Terminez et lancez OpenCue.

Le **dossier de données** contient vos shows, mises en page, projecteurs et réglages. L'emplacement par défaut (`%LOCALAPPDATA%\OpenCue`) convient à la plupart des gens ; vous pouvez en choisir un autre dans l'installation et le modifier plus tard dans OpenCue sous *Paramètres → Stockage*.

Si OpenCue est déjà installé, l'installateur le reconnaît et propose *Mettre à jour*, *Réinstaller* ou *Désinstaller* – vos données restent toujours. OpenCue cherche aussi de nouvelles versions au démarrage (désactivable dans *Paramètres → Général*) et propose de les installer ; *Aide → Rechercher des mises à jour…* le fait à la demande. La fenêtre de mise à jour affiche les notes de version ; après une mise à jour, une fenêtre **Nouveautés** s'ouvre une fois avec les nouveautés de chaque version sautée (aussi sous *Aide → Nouveautés*).

OpenCue se trouve avec la recherche Windows (touche Windows, puis tapez « OpenCue »).

---

## 3. Le premier démarrage

Sur une installation neuve, OpenCue ouvre un **show de démonstration** tout prêt nommé **Default_1** :

- cinq **Generic Dimmers** (« Dimmer 1 » … « Dimmer 5 ») dans l'univers 1, canaux 1 à 5,
- une liste de cues « Default » avec deux cues (« Cue 1 » et « Cue 2 », une seconde de fondu chacune),
- une **mise en page** avec les panneaux dont vous avez besoin en premier : liste de cues, liste des projecteurs, contrôle des projecteurs, exécuteur, ligne de commande, boutons de commande et pavé numérique.

Une courte **fenêtre de bienvenue** s'ouvre au tout premier démarrage : la langue, puis – seulement si vous le souhaitez – le réseau (Art-Net, accès distant avec votre propre mot de passe, OSC). On ne peut pas la fermer, on la parcourt (ou on appuie sur *Passer* sur la première page). Rien n'est activé sans votre accord ; si vous activez quelque chose qui utilise le réseau, Windows peut demander une fois si OpenCue peut l'utiliser. Après une mise à jour, **Aide → Nouveautés** liste les changements (elle s'ouvre une fois d'elle-même).

Il n'existe encore aucune scène dans la simulation 3D – vous en créez une quand vous en avez besoin. Les fichiers de démonstration sont des fichiers ordinaires : modifiez-les ou supprimez-les comme vous voulez.

---

## 4. L'interface en une minute

### Menus (en haut à gauche)

| Menu | Contenu |
|---|---|
| **Fichier** | Nouveau / Ouvrir / Enregistrer / Enregistrer sous (fichiers de show), Se déconnecter (appareils distants seulement), Quitter |
| **Édition** | **Modifier les panneaux** (mode édition), Annuler / Rétablir, **Ajouter un panneau…**, Ajouter un bouton / un fader, **Gérer les mises en page…** |
| **Bibliothèque** | **Bibliothèque de projecteurs…**, scènes 3D, et le gestionnaire de fichiers liste *Shows*, *Mises en page*, *Scènes 3D*, *Effets* |
| **Affichage** | Plein écran, échelle de l'interface, mises en page |
| **Langue** | English / Deutsch / Français / Nederlands / Italiano / Español |
| **Aide** | Raccourcis clavier, dépôt GitHub, Nouveautés, Rechercher des mises à jour…, À propos d'OpenCue |

### Barre d'outils (en haut)

La barre d'outils montre la **mise en page** et la **scène** actuelles, le **nom du fichier de show** (cliquez dessus pour ouvrir le gestionnaire de fichiers), un bouton **Blackout** pulsant (ampoule), le **timecode**, un indicateur DMX, le nombre d'**appareils distants** connectés et le bouton **Paramètres**. Quand vous passez la souris sur une entrée, elle s'allume et une **info-bulle** dit ce que c'est. Ce qui apparaît dans la barre dépend de vous sous *Paramètres → Barre d'outils et Internet* (chaque entrée séparément ; seulement pour cet appareil ; la roue dentée est toujours visible).

**Le mode opérateur en clair** (*Affichage → Mode opérateur …*) : vous confiez la console à quelqu'un qui doit seulement **utiliser** – pousser des faders, appuyer sur des boutons, lancer des cues – mais rien modifier. En mode opérateur, les menus, les paramètres et la reconstruction sont verrouillés, et la **commande vocale est coupée** (le microphone reste fermé). On n'en sort qu'avec le **mot de passe** (cadenas en bas à droite ou `Ctrl+L`). Il faut le mot de passe de *Paramètres → Sécurité*. Le **verrouillage de l'écran** est autre chose (*Contrôles → Verrouiller l'écran*, `Ctrl+L`) : il assombrit tout jusqu'à la saisie du mot de passe – plus rien n'est utilisable.

### Panneaux

Tout le reste, ce sont des **panneaux** que vous placez librement. Les plus importants :

| Panneau | Usage |
|---|---|
| **Liste des projecteurs** | Le patch : ajouter, modifier et supprimer des projecteurs |
| **Contrôle des projecteurs** | Gradateur, position, couleur, faisceau, focus et DMX direct pour les projecteurs sélectionnés ; aussi la grille de tuiles de sélection |
| **Liste de cues** | Les cues d'une liste : enregistrer, mettre à jour, modifier, supprimer, lire |
| **Exécuteur** | Lecture avec Go / Pause / Back / Stop et un fader de mélange |
| **Ligne de commande**, **Pavé numérique de commande**, **Boutons de commande** | Saisie au clavier et au toucher des commandes |
| **Variables / Effets** | Couleurs, positions, faisceaux et effets réutilisables |
| **Atelier d'effets** | Écrire vos propres effets |
| **Moniteur DMX** | Voir les valeurs envoyées |
| **Simulation 3D** | Voir votre scène et vos projecteurs en direct |
| **Timecode**, **Éditeur de frise**, **Lecteur vidéo/audio**, **Flux en direct / Caméra** | Temps et médias (guide *Éditeur de frise et LTC*) |
| **Audio** | Analyse musicale en direct (spectre, beat, tempo) : les lumières et les cues peuvent réagir à la musique |
| **Commande simple** | Une surface de commande simple à confier : choisir les projecteurs par tuile, **joystick**, luminosité, champ de couleur, zoom, gobos – voir *Accès distant → Mode opérateur* |
| **Bouton**, **Fader**, **Interrupteur** | Vos propres boutons, faders et interrupteurs qui lancent des commandes (ou les écrivent dans la ligne de commande) |

Ajoutez des panneaux avec **Édition → Ajouter un panneau…**.

---

## 5. Votre première cue

Vous pouvez suivre ceci avec le show de démonstration.

### Étape 1 – Sélectionner

Cliquez sur des projecteurs dans l'onglet **Projecteurs** du panneau Contrôle des projecteurs (ou dans la liste des projecteurs) – ou tapez dans la ligne de commande :

```
Fixture 1 Thru 3
```

### Étape 2 – Créer un look

Utilisez le fader **Gradateur** – ou tapez :

```
At 80
```

Choisissez une couleur si vos projecteurs en ont une (`Color Red`). Les projecteurs modifiés reçoivent un repère rouge : ils sont maintenant dans le **programmeur**.

Pour les lyres, **Position** a trois vues : **Grossier** (faders pour pan et tilt), **Fin** (une bande à balayer par axe : balayez vers le haut ou le bas, les repères suivent votre doigt – un pas du canal fin tous les 4 pixels) et **Joystick**. Le joystick est un bouton rond à deux axes, **relatif** : plus vous le poussez, plus le projecteur bouge vite ; le cercle intérieur est très précis, l'extérieur rapide. Quand vous le lâchez, il revient au centre et le projecteur reste où il est. Il modifie la valeur grossière et la valeur fine, et plusieurs projecteurs sélectionnés bougent du même écart (leurs décalages restent). Souris et toucher fonctionnent.

### Étape 3 – Enregistrer une cue

Cliquez sur **Enregistrer la cue** dans le panneau Liste de cues. Une fenêtre demande la **position** (à la fin, après une cue, ou libre), le **numéro de cue** et un **nom** facultatif. Cliquez sur **Enregistrer**. Ou tapez :

```
Store Cue 3 "Warm look"
```

Si le numéro existe déjà, vous choisissez **Fusionner** (seuls les canaux modifiés sont pris) ou **Écraser**.

### Étape 4 – La jouer

Appuyez sur **Go** dans le panneau Liste de cues ou Exécuteur – ou tapez `Go`. Le look apparaît en fondu pendant la durée de fondu de la cue. `Go Cue 3` saute directement à une cue ; **Back** recule d'une cue ; **Pause** et **Stop** pilotent un fondu en cours.

Utilisez le **fader de l'exécuteur** pour mélanger entre vos valeurs manuelles (0 %) et la cue (100 %). Pour un grand show, ajoutez **plusieurs panneaux Exécuteur**, chacun lié à sa propre liste de cues (paramètres du panneau → liste) : chacun a son fader et ses Go / Pause / Back / Stop – avec le grand master (*Master*), ils fonctionnent comme des sous-masters.

### Étape 5 – Enregistrer

Appuyez sur `Ctrl+S`. Cela enregistre le **fichier de show** et votre **mise en page**. Sans enregistrement, les modifications ne vivent qu'en mémoire ; OpenCue demande avant de se fermer.

---

## 6. Brancher de vrais projecteurs

1. Ouvrez **Paramètres → Sortie DMX**.
2. Pour **Art-Net** : il est **désactivé** au premier démarrage (il envoie dans le réseau) – activez-le. **Trouver les appareils automatiquement** est activé par défaut : OpenCue cherche les appareils Art-Net dans le réseau (toutes les quelques secondes) et envoie à chacun directement, de sorte qu'un nœud que vous branchez fonctionne simplement. **Analyser le réseau** liste ce qu'il a trouvé (nom, adresse, univers) ; **Utiliser** fait d'un appareil une cible fixe. Désactivez le mode automatique pour saisir vous-même une **IP cible** fixe (par exemple l'adresse de diffusion Art-Net) et, si besoin, l'**IP de liaison** (quelle carte réseau utiliser).
3. Pour **sACN (E1.31)** : activez-le. Il est aussi désactivé par défaut pour que Windows n'affiche pas de question de pare-feu au premier démarrage.
4. Pour **USB DMX** (Enttec DMX USB Pro ou compatible) : activez-le. Le **port COM** reste sur **Automatique (recommandé)** : OpenCue reconnaît l'adaptateur tout seul quand vous le branchez, se connecte, et se reconnecte après un débranchement et un rebranchement (même sur un autre port USB). Choisissez l'**univers** ; ne choisissez un port COM à la main que si vous avez plusieurs adaptateurs.
5. Si une interface ne démarre pas, utilisez **Réinitialiser les interfaces DMX** – pas besoin de redémarrer.

Ensuite, **patchez** vos projecteurs (guide *Projecteurs et patch*) : l'univers et le canal de départ doivent correspondre à l'adresse réglée sur chaque appareil.

Le panneau **Moniteur DMX** montre exactement ce qui est envoyé. Le bouton **Blackout** met toute la luminosité à 0 instantanément ; un second clic ramène le look.

---

## 7. Personnaliser l'interface

- **Mode édition** (**Édition → Modifier les panneaux**, `Ctrl+E`) : déplacer et redimensionner les panneaux (très petit est possible, le contenu défile alors), modifier leurs propriétés et couleurs, les copier et les coller. Un **clic droit sur l'espace de travail vide** ajoute un panneau, un bouton, un interrupteur ou un fader à l'endroit du clic. La case **Édition → Repères** active ou désactive les repères d'alignement pendant le déplacement (maintenez `Alt` : désactivés brièvement).
- Les **mises en page** sont des fichiers. Construisez-en plusieurs (par exemple une petite pour programmer et une grande pour jouer) et changez avec `Ctrl+1` … `Ctrl+9` ou **Affichage → Mises en page**. Enregistrez avec `Ctrl+S` ou dans le gestionnaire de fichiers. Créez un nouveau layout vide avec **Édition → Nouveau layout…**.
- **Thèmes** (profils de couleurs) : *Paramètres → Apparence* – sombre, clair ou le vôtre.
- **Échelle de l'interface** (`Ctrl +` / `Ctrl -`) : agrandit tout pour les écrans tactiles ; elle est mémorisée par appareil.
- **Langue** : menu *Langue* (English, Deutsch, Français, Nederlands, Italiano, Español) ou `Ctrl+Maj+L`. Les guides existent dans les six langues.

### Les paramètres en un coup d'œil

La roue dentée (**Paramètres**) ouvre une fenêtre avec les catégories à gauche, groupées par tâche. Les catégories importantes commencent par un **grand interrupteur marche/arrêt** : quand il est éteint, tout ce qui suit est grisé et verrouillé. Rien ne s'applique avant de cliquer sur **Enregistrer** (la fenêtre reste ouverte) ; **Fermer** demande confirmation s'il y a des modifications non enregistrées. Le champ **Rechercher dans les paramètres …** trouve aussi des réglages dans des catégories que vous n'avez jamais ouvertes et liste les résultats dans **toutes les catégories** (*réglage - catégorie / section*) ; un clic saute à la ligne. Le petit **(i)** derrière un réglage affiche son explication ; le **bouton (i) à côté du champ de recherche** affiche ou masque toutes les explications (mémorisé par appareil).

**Sauvegarder les paramètres :** en bas de *Général*, **Exporter les paramètres** enregistre tous les réglages dans un fichier (`opencue-settings.json`), **Importer les paramètres …** en relit un. Les valeurs importées apparaissent comme des **modifications** (marquées et comptées) – seul **Enregistrer** les applique, **Fermer** les écarte. Ne sont pas inclus : les mots de passe et clés d'accès, les valeurs propres à l'appareil ou à l'ordinateur (échelle, dossier de données, microphones, appareils MIDI) et les assignations de clavier et de MIDI – elles ont leur propre export.

| Groupe | Catégorie | À quoi ça sert |
|---|---|---|
| Programme | **Général** | L'essentiel : langue, échelle de l'interface, changement de mise en page par balayage, démarrage avec Windows, mises à jour, sauvegardes de show, dossier de données, sauvegarde des paramètres |
| Programme | **Apparence** | Couleurs, thèmes, valeurs par défaut des nouveaux panneaux |
| Sortie | **Sortie DMX** | Art-Net, sACN, USB DMX – chacun avec son interrupteur, **tout est désactivé au premier démarrage** |
| Réseau | **Accès distant** | Tablette / téléphone comme télécommande : interrupteur principal, HTTP / HTTPS, mot de passe, adresses et codes QR, nom réseau `opencue.local` |
| Réseau | **API REST** | D'autres programmes pilotent OpenCue : interrupteur, *Accessible depuis* (cet ordinateur seulement / le réseau), jetons |
| Contrôles | **Clavier** | Voir les raccourcis clavier, **assignation de touches personnalisée** (guide *Raccourcis clavier*) |
| Contrôles | **MIDI** | Utiliser le MIDI, choisir les appareils, la sortie, le timecode / tempo depuis le MIDI, **assignation MIDI** (guide *MIDI*) |
| Voix et audio | **Mot de réveil** | Commande vocale avec son propre microphone : mot de réveil + commande en anglais, p. ex. « OpenCue, blackout on » (guide *Commandes vocales*) ; marche/arrêt avec le symbole de microphone en haut à droite |
| Voix et audio | **Dictée** | Microphone et modèle vocal pour dicter dans le chat IA |
| Assistant | **Assistant IA** | Interrupteur principal, connexion à Ollama, comportement, autorisations |
| Avancé | **Options suppl.** | **Interrupteurs rapides** (commande vocale, MIDI, blackout, annuler y compris Go – ils agissent immédiatement, même si leur bouton est masqué dans la barre d'outils), **Garder l'écran allumé** (ordinateur et tablettes ; sur l'iPad seulement sur une page sécurisée, https), ce qui apparaît en haut à droite de la barre (chaque entrée séparément, par appareil) et la **connexion Internet** (bouton *Tester la connexion*) |
| Avancé | **Valeurs par défaut** | Valeurs par défaut des nouvelles cues, état de base après *Clear Clear*, valeurs de départ et **Suppression** : une confirmation avant de supprimer par catégorie (cues, projecteurs, bibliothèque, fichiers, autres) – activée par défaut |
| Avancé | **Entrées et sorties** | Affichage seulement : chaque connexion, à quoi elle sert et **jusqu'où elle porte** (*ce PC seulement*, *réseau local*, *Internet*), avec un lien vers le réglage correspondant |

**Rien ne quitte l'ordinateur au premier démarrage :** l'accès distant, Art-Net, sACN et l'API REST vers l'extérieur sont désactivés. Seule la recherche de mises à jour est active (elle peut être désactivée) ; elle nécessite Internet. Si Internet fonctionne dans le navigateur mais pas dans OpenCue (pare-feu, antivirus, réseau d'entreprise), *Général → Connexion Internet → Tester la connexion* montre **ce qui** gêne.

---

## 8. À explorer ensuite

| Sujet | Où |
|---|---|
| Projecteurs, bibliothèque GDTF, patch, groupes | *Projecteurs et patch* |
| Toutes les commandes tapées | *Référence des commandes* |
| Vos propres effets avec un petit langage de script | *Atelier d'effets* |
| Tablette et téléphone comme télécommande | *Accès distant* |
| Chaque raccourci et geste | *Raccourcis clavier* (aussi **Aide → Raccourcis clavier**) |
| Scène en 3D, pointer des lyres vers un point | Panneau **Simulation 3D** (ajoutez-le via *Ajouter un panneau* ; modes Vue / Construction / Projecteurs) |
| Vos propres modèles 3D (STL ou OBJ) sur la scène | Simulation 3D → **Construction** → **Modèle 3D …** (importer ou choisir dans la bibliothèque ; l'unité du fichier mm/cm/m/pouce détermine la taille d'origine). **Importer plusieurs fichiers à la fois** (sélectionnez-les dans la fenêtre de fichiers ou glissez-les depuis l'Explorateur sur la scène en mode *Construction*) : ils sont placés côte à côte autour du milieu de la vue et sélectionnés ensemble. Gérés dans le gestionnaire de fichiers sous **Modèles 3D** |
| Utiliser brièvement un panneau sans le mettre dans la mise en page | **Affichage → Ouvrir le panneau en fenêtre** ; ligne de commande avec pavé et touches : **Ctrl+F** (console de commande) |
| Cues qui démarrent à une heure | Panneau **Timecode** et déclencheur de cue *Timecode* |
| Lumières et cues qui réagissent à la musique | Panneau **Audio**, effets avec l'étiquette *Audio*, déclencheur de cue *Audio* (guide *Audio*) |
| Cues qui attendent une touche, un pad ou un fader d'un appareil MIDI | déclencheur de cue *MIDI* (guide *MIDI*, section 5c) |
| Piloter OpenCue depuis d'autres programmes | **API REST** (Paramètres → API ; guide *API REST*) |
| Fichiers : shows, mises en page, scènes, modèles 3D, effets | **Bibliothèque → Shows… / Mises en page… / Scènes 3D… / Effets…** (le gestionnaire de fichiers, avec import et export en ZIP ; le paquet d'export d'un show peut aussi inclure les modèles 3D de sa scène) |

---

## 9. Où sont vos données et comment les sauvegarder

Vos données sont de simples fichiers dans le dossier de données (`%LOCALAPPDATA%\OpenCue` par défaut) :

| Dossier | Contenu |
|---|---|
| `showfiles` | Shows (projecteurs, groupes, cues, presets, effets) |
| `layouts` | Mises en page des panneaux |
| `themes` | Profils de couleurs |
| `fixtures` | Fichiers de projecteurs GDTF |
| `effects` | Scripts d'effets (`.fx`) |
| `stages` | Scènes 3D |
| `media` | Vidéos et audio de vos shows |
| `config` | Paramètres (`app_config.json`, y compris la source audio choisie) et jetons d'API (`api_tokens.json`, seulement des empreintes) |

Pour sauvegarder, copiez le dossier – ou utilisez l'**export** du gestionnaire de fichiers (un show en ZIP avec les projecteurs et effets dont il a besoin), qui permet aussi de déplacer un show vers un autre ordinateur.

Dans le **gestionnaire de fichiers**, les listes *Modèles 3D*, *Médias*, *Effets* et *Projecteurs* ont un commutateur **Liste | Groupes** (OpenCue mémorise votre choix). *Groupes* montre d'abord les groupes : effets par type (Dimmer, Couleur, Position, Gobo, Zoom, Focus), médias par genre (Audio, Image, Vidéo), projecteurs par marque et modèles 3D par **show** dans lequel ils sont utilisés (un modèle utilisé dans deux shows figure dans les deux groupes ; la liste ne le montre qu'une fois). Un clic ouvre un groupe, *Tous les groupes* ramène en arrière. **Supprimer les inutilisés** (liste *Modèles 3D*) supprime chaque modèle 3D qui n'est sur aucune scène – ni la scène chargée ni une scène enregistrée – pour que les anciens imports ne s'accumulent pas.

La désinstallation d'OpenCue demande s'il faut aussi supprimer ces données ; la réponse par défaut est **Non**.

# Projecteurs et patch

Un **projecteur** est une lumière que vous pilotez : un gradateur, un par LED, un projecteur asservi. Pour le piloter, OpenCue doit savoir **de quel type d'appareil il s'agit** (ses canaux) et **où il écoute** (son adresse DMX). Communiquer les deux à OpenCue s'appelle le **patch**. Ce guide vous accompagne à travers la bibliothèque de projecteurs, le patch, les groupes et le programmeur.

---

## 1. L'idée en une minute

- Un **type de projecteur** décrit un modèle d'appareil : combien de canaux DMX il utilise dans quel mode et ce que fait chaque canal (gradateur, pan, tilt, couleur, gobo …). OpenCue utilise pour cela le format standard **GDTF** – un petit fichier par appareil, publié par le fabricant.
- Un **projecteur** dans votre show est un appareil réel d'un tel type, avec un **numéro** (FID), un **nom**, un **univers** et un **canal de départ** (l'adresse DMX que vous réglez sur l'appareil).
- Le show enregistre les projecteurs (type, mode, adresse, nom, groupe). Les fichiers GDTF eux-mêmes se trouvent dans la **bibliothèque de projecteurs** de votre ordinateur.
- Trois types de projecteurs **intégrés** sont toujours disponibles, même sans fichier GDTF : **Generic Dimmer** (1 canal), **Generic RGBW LED Par** (4 canaux) et **Generic Moving Head Spot 16ch** (16 canaux, avec pan/tilt fin). Parfaits pour essayer.

---

## 2. Obtenir des types de projecteurs : la bibliothèque

Ouvrez **Bibliothèque → Bibliothèque de projecteurs…**. La grande boîte de dialogue comporte ces onglets :

| Onglet | Ce qu'il montre |
|---|---|
| **Installés** | Chaque fichier GDTF de cet ordinateur sous forme de carte : image d'aperçu, nom, fabricant, type, modes, nombre de canaux, révision et *En cours d'utilisation (N)* quand le show l'utilise. |
| **Dans ce show** | Les types que le show chargé utilise, avec le nombre (« 4× dans le show ») et la révision. Si le fichier d'un type n'est pas dans la bibliothèque, l'onglet indique *Substitut intégré* ou *Fichier manquant*. Consultation seulement. |
| **En ligne (GDTF Share)** | Recherche dans la base de données officielle GDTF (voir ci-dessous). |

Dans l'onglet *Installés*, vous pouvez **chercher** par nom ou fabricant et filtrer par **type** (projecteur asservi, barre LED, PAR / wash, gradateur, stroboscope / blinder, effet / fumée, autre – déduit des canaux réels) et par **fabricant**. Chaque onglet garde ses propres filtres.

### Importer un fichier GDTF que vous avez déjà

Cliquez sur **Importer un fichier GDTF…** ou **déposez simplement le fichier** dans la boîte de dialogue. Le fichier doit être un fichier GDTF valide (30 Mo au maximum). Les fichiers sont copiés dans le dossier `fixtures` du dossier de données d'OpenCue (Paramètres → Stockage indique où il se trouve).

### Télécharger depuis GDTF Share

GDTF Share (gdtf-share.com) est la collection officielle et gratuite de fichiers GDTF des fabricants et des utilisateurs.

1. Ouvrez l'onglet **En ligne (GDTF Share)**.
2. **Connectez-vous** avec votre compte GDTF Share. Un compte gratuit est nécessaire pour télécharger ; la boîte de dialogue propose un lien *Créer un compte gratuit*. Votre mot de passe n'est conservé en mémoire que pour cette session – sauf si vous cochez *Rester connecté*, ce qui l'enregistre **chiffré sur cet ordinateur**.
3. Cherchez, triez (nom, plus récent, mieux noté), filtrez par **fichiers de fabricants** / note. Chaque carte indique si le fichier a été envoyé **par le fabricant** ou **par un utilisateur**, combien de modes il a (avec les nombres de canaux) et sa taille.
4. Cliquez sur **Détails** pour **regarder un projecteur avant de l'installer** : le fichier n'est chargé que temporairement (pas installé) et s'ouvre dans la même vue de détail que les types installés – avec tous les canaux, roues et le modèle 3D. **Installer** et **Retour à la recherche** sont en haut. Ou cliquez tout de suite sur **Installer**.
5. La carte indique ensuite *Installé*. Si une révision plus récente apparaît plus tard, un bouton **Mettre à jour** est proposé.

C'est le seul endroit où OpenCue utilise Internet pour les projecteurs ; tout le reste fonctionne hors ligne. OpenCue ne livre pas de fichiers GDTF de GDTF Share, car leurs conditions n'autorisent pas la redistribution – vous les téléchargez vous-même.

### Détails d'un projecteur

Cliquez sur une carte pour ouvrir ses **détails** :

- **Aperçu** – données de base, optique par faisceau (type de faisceau, lampe, puissance, flux lumineux, température de couleur, angle de faisceau et de champ), connecteurs, émetteurs.
- **Aperçu 3D** – le projecteur sous forme de modèle 3D. Faites glisser pour tourner, molette ou deux doigts pour zoomer, glisser avec le clic droit pour déplacer, double-clic pour réinitialiser. Boutons *Oblique / Face / Côté / Dessus*, interrupteurs pour le *faisceau lumineux* et une *grille*, et **curseurs Pan / Tilt** pour bouger un projecteur asservi. Sans fichier 3D dans le GDTF, OpenCue dessine les formes de base (cylindre, lyre, tête …) avec les dimensions données.
- **Canaux DMX** – le sélecteur de mode et un tableau de tous les canaux avec fonctions et plages de valeurs.
- **Gobos et couleurs** – chaque roue avec ses emplacements : motifs de gobos en images, emplacements de couleur en échantillons.

### Supprimer et mettre à jour

- **Désinstaller** (demande une seconde confirmation) retire un type de la bibliothèque – mais c'est **refusé tant que le show l'utilise encore**.
- **Mettre à jour** installe une révision plus récente. Si le show utilise l'ancienne, l'ancienne révision reste installée.

---

## 3. Ajouter des projecteurs au show (patch)

Les projecteurs se créent dans le panneau **Liste des projecteurs**.

1. Dans le panneau **Liste des projecteurs**, cliquez sur **Ajouter des projecteurs**.
2. **Type de projecteur** – choisissez-en un avec *Choisir un type...* (fabricant → appareil → mode, plus une recherche) ou l'un des génériques intégrés.
3. **Mode** – le mode DMX de l'appareil (il détermine le nombre de canaux).
4. **Nom** (facultatif) – par exemple « Tête » ; vide signifie le nom du type. Avec plusieurs projecteurs, OpenCue numérote les noms.
5. **Quantité** – combien de projecteurs identiques ajouter. Ils sont placés **les uns après les autres** sur des adresses consécutives.
6. **Univers** et **Canal de départ** – l'adresse du premier. Elle doit correspondre à l'adresse réglée sur l'appareil (afficheur ou commutateurs DIP).
7. Cliquez sur **Ajouter des projecteurs**.

La boîte de dialogue vous avertit si le dernier projecteur finirait au-delà du canal **512** d'un univers (« l'adresse de fin dépasse 512 … Réduisez la quantité ou l'adresse de départ »). Un univers contient 512 canaux ; utilisez l'univers suivant pour en avoir plus.

Chaque projecteur reçoit un **FID** stable (numéro de projecteur) utilisé par la ligne de commande (`Fixture 1 Thru 5`).

### Beaucoup de projecteurs d'un coup : une liste CSV ou Excel

La boîte de dialogue *Ajouter des projecteurs* comporte **Import avancé...** en bas (aussi dans le menu **Bibliothèque → Importer une liste de projecteurs**). Avec elle, vous créez tout un dispositif à partir d'un tableau :

1. **Choisir un fichier ...** – un fichier `.csv` ou Excel (`.xlsx`). La **première ligne** contient les titres des colonnes. Seul le **type** est nécessaire ; *nom*, *mode*, *univers*, *adresse*, *numéro* (FID) et *quantité* sont facultatifs. **Télécharger le patch actuel en CSV** vous donne un modèle.
2. OpenCue **devine les colonnes** (titres comme *Name*, *Type*, *Device*, *Universe*, *Address*, *Count* ...) ; vous pouvez modifier chaque assignation. Une adresse peut aussi s'écrire `2.045` ou `2/45` (univers 2, adresse 45). Si l'adresse manque, elle continue derrière l'appareil précédent du même univers.
3. L'**aperçu** montre chaque ligne – en rouge avec la raison quand quelque chose ne va pas (type inconnu ou ambigu, mode inconnu, ne tient pas dans l'univers, numéro déjà utilisé). **Type quand la cellule est vide** et **Univers si manquant** comblent les trous.
4. **Importer** crée les projecteurs. En cas de problèmes, cochez d'abord **Ignorer les lignes avec des problèmes**. Rien n'est créé avant cela.

### La liste des projecteurs et l'onglet Projecteurs

Deux endroits montrent vos projecteurs :

- Le panneau **Liste des projecteurs** est le tableau de patch : une ligne par projecteur avec FID, nom, type, univers, adresse et nombre de canaux, plus le bouton **Ajouter des projecteurs**.
- L'onglet **Projecteurs** du panneau **Contrôle des projecteurs** montre les mêmes projecteurs sous forme de grille de tuiles (comme sur une console d'éclairage) pour sélectionner rapidement.

| Action | Comment |
|---|---|
| Sélectionner | Cliquer / toucher une ligne ou une tuile |
| En sélectionner plusieurs | Dans la grille de tuiles, tracer un **lasso** sur les tuiles (souris et tactile) |
| Modifier un projecteur | Clic droit / appui long → **Modifier le projecteur…** |
| Supprimer | Sélectionner, appuyer sur `Suppr` ou utiliser le menu contextuel (demande confirmation) |

### Modifier le projecteur

Une seule boîte de dialogue change tout : **Nom**, **Univers**, **Canal de départ**, **Groupe** et un **Index de tri** libre.

- L'index de tri détermine où la tuile apparaît. Vide signifie le FID ; un nombre (décimales autorisées, par exemple 2,5) la place en conséquence.
- Un projecteur appartient à **un seul groupe** au plus.
- Avec **plusieurs projecteurs sélectionnés**, le menu propose aussi *Déplacer N projecteurs vers le groupe…*.

Changer l'adresse change l'endroit où OpenCue envoie les données – faites-le donc quand vous déplacez un appareil sur une autre adresse.

---

## 4. Groupes

Les groupes sont purement organisationnels : trier et sélectionner plusieurs projecteurs en un clic ou une commande. Ils sont enregistrés avec le show.

- **Créer :** dans l'onglet **Projecteurs** du panneau Contrôle des projecteurs, clic droit / appui long sur la zone vide → *Ajouter un nouveau groupe…* et saisissez un nom (les noms sont uniques, sans distinction de casse).
- **Remplir :** la liste déroulante *Groupe* dans *Modifier le projecteur…*, ou *Déplacer N projecteurs vers le groupe…* pour une sélection.
- **Sélectionner :** cliquez sur le groupe, ou utilisez la ligne de commande : `Group Front`, `Group 1 Thru 4`.
- **À partir d'une sélection :** `Store Group "Front"` enregistre la sélection actuelle comme groupe (voir *Référence des commandes*).

---

## 5. Piloter les projecteurs : le panneau Contrôle des projecteurs

Sélectionnez des projecteurs, puis utilisez le panneau **Contrôle des projecteurs** (souvent appelé « Programmeur » sur les consoles). Un panneau peut tout montrer (une barre latérale avec toutes les catégories) ou une seule catégorie (*Propriétés du panneau → Affichage*).

| Catégorie | Commandes |
|---|---|
| **Projecteurs** | La grille de tuiles pour sélectionner ; basculer **Liste / Disposition** (voir plus bas) |
| **Gradateur** | Fader et boutons rapides |
| **Position** | Basculer **Grossier / Fin**. *Grossier* : faders pan/tilt, **Centre / Position initiale / Inverser**, champs numériques en degrés. *Fin* : les canaux fins (16 bits) comme champs numériques ; balayez un champ numérique vers le haut ou le bas pour le modifier finement. Les projecteurs sans canaux fins agissent en 8 bits. |
| **Couleur** | **Fader** (TSV, CMJ ou RVB) ou **Sélecteur de couleur** (roue chromatique) |
| **Faisceau** | Sous-pages **Obturateur/Stroboscope** (ouvert, fermé, lent, rapide, stroboscope, pulsation …), **Gobo** (avec vignettes de la roue), **Prisme** |
| **Focus** | Focus et zoom |
| **DMX direct** | Chaque canal du mode comme fader à part (par numéro de canal, 0–255) |

Chaque canal décrit par le fichier GDTF reçoit une commande, de sorte que vous pouvez atteindre même des fonctions inhabituelles (frost, iris, roues de couleur, vitesses).

**Pointer vers un point (3D) :** si les projecteurs sont placés dans la **Simulation 3D**, le volet position propose *Définir le point dans la simulation 3D* : touchez une cible dans la vue 3D et les projecteurs asservis sélectionnés la visent. Dans le volet focus, *Focus automatique (3D)* et *Zoom automatique (3D)…* règlent le focus et le zoom d'après la distance à ce point.

### Ce que vous dit la couleur des commandes

Les commandes montrent toujours ce qui est actuellement envoyé (les mêmes valeurs que le moniteur DMX) – aussi pendant qu'un cue ou un effet tourne. Un fin trait coloré à côté d'un projecteur ou d'un onglet de catégorie montre ce qui a **changé par rapport au cue actif** – commandé à la main ou par un *Clear* qui a tout éteint. *Store Cue* enregistre toujours la différence avec le cue qui jouerait avant lui (aussi à l'insertion avec `2.5`). Après l'enregistrement, le nouveau cue est le cue actif et les traits disparaissent. Avec plusieurs listes de cues, c'est le cue actif de la liste utilisée en dernier qui compte.

---

### Projecteurs : liste ou disposition

En haut de l'onglet **Projecteurs**, vous basculez entre deux vues (comme *Couleur* entre Fader / Sélecteur / Roue) :

- **Liste :** les tuiles classées par groupes et numéros.
- **Disposition :** chaque projecteur est une **tuile carrée** sur une grille. Disposez les projecteurs comme ils sont accrochés sur scène et atteignez-les plus vite. Les tuiles montrent la même chose que dans la liste (numéro, luminosité, aperçu de la couleur et du faisceau).

Dans la disposition :

- **Sélectionner** comme dans la liste : un clic ou un **balayage** (lasso) sur la zone vide.
- **Zone illimitée :** elle continue dans **toutes les directions** (aussi à gauche et vers le haut ; les positions peuvent être négatives). Déplacez la vue avec la molette / les barres de défilement / un balayage, **glissez avec le bouton central**, ou allez au bord en faisant glisser une tuile. **Ctrl + molette** zoome.
- **Tout afficher :** le bouton en haut à droite zoome et centre de sorte que **tous les projecteurs** soient au milieu.
- **Vues (zones) :** *Enregistrer la vue…* (clic droit) enregistre le centre et le zoom actuels sous un nom, par exemple « Côté jardin ». Un bouton apparaît en haut ; un clic y saute, clic droit sur le bouton : écraser, renommer, supprimer. Avec beaucoup de projecteurs, vous n'avez pas à tout garder dans le champ à la fois.
- **Clic droit** (tactile : appui long) sur la zone libre ou sur une tuile ouvre le menu : *Mode construction*, *Tout afficher*, *Enregistrer la vue…*, *Grille* (tuile entière, demie ou quart), *Les tuiles peuvent se superposer*, *Réinitialiser le zoom*, *Réorganiser tous les projecteurs…*.
- **Mode construction :** glisser déplace une tuile ; à plusieurs sélectionnées, elles se déplacent ensemble. Les tuiles s'accrochent à la grille ; sans *Superposition*, elles ne se recouvrent jamais, avec *Superposition* vous pouvez les imbriquer (la dernière déplacée est au-dessus) et les décaler étroitement avec la grille fine (1/4). La zone vide sélectionne toujours par balayage. **Terminé** ou **Échap** termine le mode construction.
- **Enregistré dans le show :** les positions, la résolution de la grille, la *Superposition* et les vues enregistrées. **Sur votre appareil** (pas dans le show) : le zoom, le dernier centre affiché et la dernière sous-vue utilisée.

**Vues mémorisées :** partout où un panneau bascule entre des vues, votre appareil se souvient de la dernière et la restaure la fois suivante : dans Contrôle des projecteurs (Liste / Disposition, Fader / Sélecteur / Roue, Stroboscope / Gobo / Prisme, Grossier / Fin), dans *Variables et effets* (variables ou effets, filtre de type, tri), dans l'*Atelier d'effets* (aperçu activé / désactivé), dans la *Simulation 3D* (Vue / Construction / Projecteurs) et dans le sélecteur d'effets (catégorie et étiquettes comme *Basique*).

## 6. Variables et effets (presets)

Le panneau **Variables / Effets** contient des valeurs réutilisables : une couleur « Blanc chaud », une position « Face », un faisceau « Large ». Une variable est une **référence vivante** : appliquez-la à des projecteurs et ils la suivent ; changez la variable plus tard et tous les projecteurs qui l'utilisent changent avec elle – y compris les cues qui l'utilisent. Les effets sont de petits programmes qui modifient des valeurs au fil du temps ; voir le guide *Atelier d'effets*.

---

## 7. Projecteurs et fichier de show

- Un fichier de show enregistre les projecteurs **avec** leur type, mode, adresse et groupe, ainsi que les cues, effets, variables et presets.
- Les fichiers GDTF ne sont **pas** dans le show – mais quand vous **exportez un show** (gestionnaire de fichiers → exporter), les fichiers GDTF et les scripts d'effets que le show utilise sont placés dans le ZIP, de sorte que vous pouvez ouvrir le show sur un autre ordinateur sans rien installer. À l'import, un fichier local du même nom n'est jamais remplacé.
- **Imprimer / PDF** (menu Fichier) : documentation du show pour les techniciens – **liste de patch**, **carte des canaux DMX** (quel projecteur occupe quels canaux de chaque univers, chevauchements en rouge), **groupes**, **plan (vue de dessus)** des projecteurs (d'après la scène 3D, sinon d'après la vue en disposition) et **listes de cues**. La boîte de dialogue montre un **aperçu** du PDF à côté des choix (il suit chaque modification des choix et du format de papier ; sur les petits écrans, l'aperçu est omis). Les noms longs sont **renvoyés à la ligne** dans les tableaux et dans le plan (un très long nom sans espace est coupé). Dans le plan, chaque projecteur porte son numéro, et une liste sous le plan indique quel numéro correspond à quel projecteur ; les noms des objets de scène se trouvent à l'intérieur de leur forme. *Enregistrer en PDF* télécharge le fichier, *Ouvrir pour imprimer* l'affiche dans le lecteur PDF (imprimez-y avec Ctrl+P).
- **Fichier de show `.ocshow` :** *Fichier → Exporter le show* écrit un fichier `.ocshow` (un ZIP contenant le show et ses fichiers). Un **double-clic** l'ouvre dans OpenCue (l'installateur configure cela ; pour la version décompressée, utilisez *Paramètres → Général → Ouvrir les fichiers .ocshow avec OpenCue*). Si OpenCue tourne déjà, il reprend le fichier et demande d'abord ce qu'il faut faire des modifications non enregistrées. **Fichier → Ouvrir récent** liste les derniers shows.
- **Scène 3D en JSON :** dans le panneau 3D (mode *Construction* ou *Projecteurs*), faites passer la barre latérale de **Outils** à **JSON** (interrupteur sous le bouton Enregistrer ; il reste en haut de la barre latérale quand on fait défiler). Les outils (ajouter des corps, liste, propriétés) sont remplacés par le texte de la scène (pièce, objets, positions des projecteurs ; mètres, degrés, Z vers le haut ; projecteurs par leur numéro) ; le nom de la scène, l'annulation et **Enregistrer** restent identiques, **Outils** ramène la vue normale. **La largeur de la barre latérale peut être modifiée :** faites glisser son bord gauche (double-clic = largeur standard) ; la largeur est mémorisée comme proportion du panneau (trois quarts au maximum), de sorte qu'elle reste proportionnelle en plein écran. Les modifications sont vérifiées et **appliquées en direct** (une erreur de syntaxe nomme la ligne et ne change rien) ; ce que vous déplacez dans la vue 3D apparaît dans le texte. *Enregistrer* enregistre la scène, *Fermer JSON* ramène la barre latérale. Le même texte est disponible sous forme de boîte de dialogue dans *Bibliothèque → Modifier la scène 3D en JSON* (avec *Vérifier* et *Appliquer*).
- **Import MVR (scène et projecteurs) :** *Bibliothèque → Importer une scène MVR…* lit un fichier **.mvr** issu d'un logiciel de conception de scène ou de lumière (Vectorworks, Capture, Depence …). Choisissez le fichier (ou déposez-le sur la fenêtre) : OpenCue montre ce qu'il contient - éléments de scène, projecteurs et leurs types - et vous décidez : **scène 3D** *remplacer* (par défaut ; un fichier de scène enregistré auparavant reste intact sur le disque), *ajouter* ou *ne pas toucher*, et s'il faut **patcher les projecteurs**. Les projecteurs reçoivent type, mode, adresse DMX et numéro du fichier et sont placés dans la scène 3D avec leur position et leur rotation (un numéro déjà pris ou une adresse manquante est remplacé par un numéro libre - les remarques vous l'indiquent). Les fichiers GDTF vont dans la bibliothèque de projecteurs (rien n'est écrasé). Les éléments de scène (sol, structures, décors, écrans …) deviennent des **modèles 3D** (STL binaire, sous *Bibliothèque → Modèles 3D…*) et des objets de scène que vous pouvez déplacer, faire pivoter et redimensionner comme les autres ; un élément qui revient souvent (un symbole du fichier) partage un seul modèle. Une scène de plus de 200 éléments est regroupée par calque pour tenir sur une scène. La nouvelle scène n'est enregistrée que lorsque vous enregistrez le show. Les couleurs des matériaux sont conservées (par surface) et les éléments en miroir restent en miroir. Une barre de progression montre l'import - les gros fichiers de projecteurs LED demandent quelques secondes chacun, une fois par type, puis sont mémorisés. La fenêtre s'ouvre aussi via le petit bouton *Importer une scène MVR…* du panneau 3D (modes *Construction* et *Projecteurs*). Non repris : points de visée et textures d'image.
- Si un show utilise un type de projecteur dont le fichier manque, OpenCue utilise un substitut intégré pour que le show fonctionne quand même ; l'onglet *Dans ce show* l'indique comme *Substitut intégré* ou *Fichier manquant*.

---

## 8. Astuces rapides

- **Commencez par un générique :** ajoutez quelques projecteurs *Generic Dimmer* pour apprendre le programmeur, les cues et la ligne de commande avant de chercher de vrais fichiers GDTF.
- **Faites correspondre les adresses :** le canal de départ dans OpenCue doit être égal à l'adresse sur l'appareil. Les projecteurs asservis ont généralement besoin d'un bloc de canaux (par exemple 16 canaux), le projecteur suivant commence donc 16 canaux plus loin – OpenCue le calcule pour vous quand vous ajoutez une quantité.
- **Plusieurs modes :** beaucoup d'appareils proposent plusieurs modes (par exemple 8 bits et 16 bits). Choisissez le mode sur lequel l'appareil est réellement réglé.
- **Un appareil manque ?** Cherchez sur GDTF Share par fabricant ; si le modèle n'y est pas, partez du plus proche ou utilisez *Generic* et construisez vos propres cues.

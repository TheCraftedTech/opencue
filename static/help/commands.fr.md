# Ligne de commande – Référence des commandes

La **ligne de commande** pilote OpenCue en tapant, à la manière des consoles d'éclairage professionnelles. Elle complète l'utilisation à la souris et au tactile avec de courtes commandes que vous pouvez saisir, enchaîner et enregistrer dans des cues. Elle est disponible comme panneau **Ligne de commande** (*Modifier → Ajouter un panneau…*) ; les panneaux **Pavé numérique de commande** et **Boutons de commande** écrivent dans la même ligne de saisie pour l'utilisation tactile.

Chaque commande est exécutée sur le serveur et le résultat est signalé à **tous** les appareils connectés : la liste des projecteurs, la liste de cues et le programmeur se mettent à jour partout en même temps, pas seulement là où vous avez tapé.

> Les mots de commande sont en anglais – comme sur les consoles d'éclairage. Les majuscules et minuscules n'ont **pas** d'importance pour les commandes, attributs et noms.

---

## 1. L'idée en une minute

Chaque commande suit le même schéma : **quoi** – **lequel** – **valeur**.

| Action / objet | ID / plage | Propriété / cible |
|---|---|---|
| `Fixture` | `1` | – |
| `At` | – | `80` |
| `Store` | `Cue 1.5` | – |
| `Cue` | `1` | `Fade 3` |
| `Cuelist` | `Show` | `Go` |

- L'**action ou l'objet** vient toujours en premier (`Fixture`, `Group`, `At`, `Color`, `Pan`, `Zoom`, `Store`, `Cue`, `Go`, `Cuelist` …).
- L'**ID ou la plage** dit ce qui est concerné : un numéro de projecteur (FID), un nom, un numéro de cue, un nom de liste de cues, ou une plage (`1 Thru 10`).
- La **propriété ou la cible** est la valeur proprement dite : pourcentage, degrés, durée, nom, couleur.
- Les commandes **s'appuient les unes sur les autres**, comme sur une vraie console : on sélectionne d'abord (`Fixture 1 Thru 4`), puis une commande de valeur (`At 80`) agit exactement sur cette sélection. La sélection est **partagée par tous les appareils** : un clic dans la liste des projecteurs sur un écran et une commande `Fixture` sur un autre agissent sur la même sélection.
- Le texte avec des espaces (un nom de cue, un nom de liste) va entre guillemets doubles : `Label Cue 1 "Intro scene"`. Un mot entre guillemets est toujours un **nom**, jamais un mot de commande, de sorte qu'un groupe appelé « Color » peut aussi être adressé.
- La saisie est validée : des nombres invalides (`Zoom abc`), des attributs ou noms inconnus et des valeurs manquantes donnent un message d'erreur **sans rien modifier**.

```
Fixture 1 Thru 4 At 80
Fixture 1 Thru 4 Color Red
Store Cue 1 "Opening"
Go
```

---

## 2. Sélectionner des projecteurs et des groupes

| Commande | Effet |
|---|---|
| `Fixture 1` | Sélectionne le projecteur FID 1 (remplace la sélection actuelle). |
| `Fixture 1 Thru 10` | Sélectionne les FID 1 à 10. |
| `Fixture 1 + 3` | Sélectionne les FID 1 **et** 3 (combinez autant que vous voulez avec `+`). |
| `Fixture 1 Thru 5 + 10` | Sélectionne les FID 1–5 et aussi 10. |
| `Fixture 1 Thru 10 - 5` | Sélectionne les FID 1–10 **sans** 5 (un `-` avec espaces retire ; plusieurs possibles : `- 5 - 7 Thru 8`). |
| `Next` / `Previous` | Sélectionne le **projecteur suivant / précédent** par FID (boucle ; sans sélection, `Next` = le premier, `Previous` = le dernier). Parcourez les projecteurs un par un. |
| `Fixture "Head 2"` | Sélectionne le ou les projecteurs portant ce **nom** (combinable aussi avec `+`). |
| `Group 1` | Sélectionne le 1er groupe de la liste des groupes. |
| `Group 1 Thru 4` | Sélectionne les projecteurs des groupes 1 à 4. |
| `Group Front` | Sélectionne le groupe portant ce **nom** (`Group "Front Truss"` quand il contient des espaces). |

`Group N` désigne le **N-ième groupe créé**. Le nom est plus simple et plus robuste : `Group Front` fonctionne quel que soit l'ordre.

Un mot seul peut être écrit sans guillemets s'il n'est pas égal à un mot de commande et si le nom existe vraiment. Sinon, mettez entre `"…"` les noms avec espaces, virgules, points-virgules ou `+`, et les noms qui ressemblent à une commande ou à un nombre.

### Créer, renommer, supprimer des groupes

La **sélection actuelle** peut être enregistrée comme groupe :

| Commande | Effet |
|---|---|
| `Store Group "Front"` | Crée le groupe à partir de la sélection actuelle. |
| `Store Group "Front" Merge` | S'il existe : la sélection est **ajoutée**. |
| `Store Group "Front" Overwrite` | S'il existe : les membres sont **remplacés**. |
| `Label Group Front "Stage front"` | Renomme (`Set Group 2 Name "Stage front"` fonctionne aussi, également par numéro). |
| `Delete Group Front` | Supprime le groupe (`Delete Group 2` par numéro) – les projecteurs restent. |

Sans sélection, `Store Group` signale une erreur. Un nom existant (sans distinction de casse) n'est jamais écrasé en silence. Un projecteur appartient à un seul groupe au plus.

---

## 3. Régler des valeurs : At / Full

Agit sur les projecteurs **actuellement sélectionnés** (canal de gradateur).

| Commande | Effet |
|---|---|
| `At 80` | Gradateur à 80 % (`At 80%` fonctionne aussi). |
| `At Full` | Gradateur à 100 %. |
| `At At` | **Tout allumer** : gradateur à 100 % **et couleur blanche** (les projecteurs sans couleur ne reçoivent que le gradateur). **Sans sélection, cela concerne TOUS les projecteurs** (la sélection reste vide) – le contraire de `Clear Clear`. Avec une sélection, seule cette sélection est allumée. Possible aussi : `Fixture 5 At At`, `At At Color Red` (tout allumé, en rouge). |
| `Zero` | Sélection à 0 % (comme `At 0`). |
| `Full` | Forme courte sans « At » devant – aussi 100 %. |
| `At 0` | Gradateur à 0 % (éteint). |
| `At +10` / `At -10` | Augmente / diminue la valeur actuelle du gradateur de 10 points de pourcentage. |

Les valeurs sont limitées à 0–100 %. `At +` / `At -` se rapporte à la dernière valeur réglée dans le programmeur pour chaque projecteur (ou à la valeur DMX actuellement émise si rien n'a encore été programmé).

Les projecteurs concernés reçoivent un repère d'état rouge dans la liste des projecteurs – ils sont maintenant « dans le programmeur » et peuvent être enregistrés avec `Store Cue`.

### Master (luminosité globale)

`Master` (en abrégé `GrandMaster`) met à l'échelle la sortie de **tous** les canaux de gradateur en pourcentage. La valeur par défaut est 100 %. La valeur reste jusqu'à ce que vous la changiez et est enregistrée avec le fichier de show.

| Commande | Effet |
|---|---|
| `Master 80` / `Master At 80` | Luminosité globale 80 % (le mot `At` est facultatif). |
| `Master Full` | 100 %. |
| `Master -10` / `Master +10` | Diminue / augmente de 10 points de pourcentage. |

Le master ne met à l'échelle que les canaux de gradateur ; les couleurs et le pan/tilt restent inchangés. (Le **fader d'une liste de cues** est une autre chose – voir le chapitre 10.)

### Blackout

`Blackout` met la **luminosité de tous les projecteurs à 0** et la rétablit au `Blackout` suivant. C'est une bascule, indépendante du master.

| Commande | Effet |
|---|---|
| `Blackout` | Bascule. |
| `Blackout On` / `Blackout Off` | Active / désactive (`1`/`0`, `True`/`False` fonctionnent aussi). |

**Le blackout est prioritaire sur tout** – faders, commandes, cues, fondus et effets en cours : tant qu'il est actif, la luminosité de chaque projecteur reste à 0, dans la sortie DMX **et** dans la simulation 3D. Les valeurs sont conservées : vous pouvez changer la luminosité normalement pendant un blackout, et après `Blackout Off`, l'état **réglé en dernier** apparaît. Les projecteurs **sans** canal de gradateur (RVB pur) sont assombris par leur couleur. Un bouton d'ampoule qui pulse dans la barre d'outils indique un blackout actif ; un clic le bascule. L'état s'applique à tous les appareils mais n'est **pas** enregistré dans le show.

### Code temporel : `Timecode` / `TC`

Le code temporel global (l'horloge interne) peut aussi être piloté par commande – par exemple dans le champ **CMD** d'un cue (`Timecode Play` démarre l'horloge quand le cue se déclenche).

| Commande | Effet |
|---|---|
| `Timecode` | Affiche l'état (heure, en marche/arrêté, vitesse). |
| `Timecode At 4.3` | Saute à 4,3 s (aussi `00:00:04.300`, `1:04.300` ; 100 h au maximum). |
| `Timecode At 4.3 Play` | Saute et démarre (`Reverse` démarre à l'envers). |
| `Timecode +5` / `Timecode -2` | Relatif : 5 s en avant / 2 s en arrière. |
| `Timecode Play` / `Reverse` | Marche avant / arrière. |
| `Timecode Pause` | Pause. |
| `Timecode Stop` (`Reset`) | Arrête et remet à 00:00:00.000. |
| `Timecode Rate 2` | Vitesse (0,1 … 8 ; `0.5x` fonctionne aussi). |

Un saut ne déclenche pas les cues de timecode ; seule la marche avant le fait.

### Audio et tempo : `Tap` / `BPM` / `Audio`

Pilote le panneau *Audio* (voir le guide *Audio*) – utilisable aussi dans le champ **CMD** d'un cue.

| Commande | Signification |
|---|---|
| `Tap` | Taper le tempo : à partir du deuxième tap, le tempo est déterminé d'après vos taps (manuel) et le temps commence sur le tap. |
| `BPM` | Affiche le tempo et le mode. |
| `BPM 128` | Tempo fixe (30 … 300). |
| `BPM Auto` | Retour à la détection automatique. |
| `BPM Half` / `BPM Double` | Divise par deux / double le tempo (quand la détection a trouvé le double / la moitié). |
| `Audio Start` / `Audio Stop` | Ouvre la source choisie / la ferme. |
| `Audio Demo` | Démarre le battement de démonstration. |
| `Audio` (`Audio Status`) | Indique si l'audio tourne, le tempo et le niveau. |

### Envoyer de l'OSC : `Osc`

`Osc /address [value ...]` envoie un message OSC à la cible réglée sous **Contrôles → OSC ...** (*Envoyer à*) : `Osc /opencue/go`, `Osc /light/1 0.5 hello`. Les valeurs sont des nombres (les entiers partent comme entiers), `true` / `false` ou du texte. Sans cible, la commande le signale. Voir le guide *Planification, heure de la journée et OSC*.

### Envoyer du MIDI : `Midi`

Envoie du MIDI vers la sortie choisie (voir le guide *MIDI*) : `Midi Note 60 [velocity] [Ch 2] [Len 0.5]` joue une note et la coupe ensuite, `Midi On 60` / `Midi Off 60` séparément, `Midi CC 7 100` règle un contrôleur, `Midi PC 3` un changement de programme, `Midi Panic` coupe toutes les notes.

---

## 4. Couleur et position : Color / RGB / Pan / Tilt

Elles agissent aussi sur les projecteurs **actuellement sélectionnés**.

| Commande | Effet |
|---|---|
| `Color Red` | Règle la couleur sur rouge (couleur nommée, liste ci-dessous). |
| `Color #FF8000` | Couleur en hexadécimal (la forme courte `#F80` fonctionne aussi). |
| `Color 255 128 0` | Couleur en trois valeurs 0–255 (rouge / vert / bleu). |
| `RGB 255 0 0` | Pareil (notation console). |
| `Pan 180` | Déplace le pan à 180°. |
| `Tilt -45` | Déplace le tilt à -45°. |
| `Pan 50%` | Pan en pourcentage de la plage (0–100 % ; 50 % = centre). |
| `Pan +10%` / `Tilt -5%` | Relatif à la valeur actuelle, en pourcentage de la plage. |
| `Pan +15` / `Tilt -15` | Relatif en degrés (avec signe). |

**Couleurs nommées :** `Red`, `Green`, `Blue`, `White`, `Black`, `Yellow`, `Cyan`, `Magenta`, `Orange`, `Pink`, `Purple`, `Amber`, `Lime`, `Teal`, `Violet`, `LightBlue`, `Warm`, `Cool`.

**Degrés pour pan/tilt :** OpenCue lit la vraie plage de mouvement (plage physique) dans le profil GDTF du projecteur ; des projecteurs différents peuvent donc se placer légèrement différemment pour la même valeur en degrés. Si le profil n'a pas de plage, la valeur par défaut s'applique : **pan de -270° à +270°, tilt de -135° à +135°**.

---

## 5. Attributs de faisceau et canaux : Zoom, Gobo, CH …

Outre la luminosité, la couleur et la position, **chaque canal** d'un projecteur peut être réglé – de deux façons : par **nom d'attribut** (pourcentage, même logique que les faders du programmeur) ou directement par **numéro de canal** ou **nom** (comme « DMX direct »).

### Attributs en pourcentage

| Commande | Effet |
|---|---|
| `Zoom 50` | Zoom à 50 % (aussi `Zoom Full`, `Zoom Half`, `Zoom Min`, `Zoom 50%`). |
| `Focus 25` | Focus. |
| `Gobo 40` / `Gobo2 40` | Roue de gobos 1 / 2 (sélection ; nombre = pourcentage du canal). |
| `GoboSpin 30` / `Gobo2Spin 30` | Rotation / position de la roue de gobos. |
| `Prism 100` | Prisme. |
| `Strobe 0` (`Shutter 0`) | Obturateur / stroboscope. |
| `Zoom +10` / `Zoom -20` | Relatif à la valeur actuelle (points de pourcentage). |

Toutes les valeurs vont de 0 à 100 et sont enregistrées comme les faders : `Store Cue` les reprend. Si un projecteur n'a pas le canal (un gradateur pur n'a pas de zoom), il est ignoré et le retour l'indique : `OK: Zoom 50 applied to 3 fixtures (Zoom not available on 1 of 3 fixtures)`. Si **aucun** des projecteurs sélectionnés n'a le canal, c'est une erreur et rien ne change.

### Canaux par numéro : `CH` / `Channel`

| Commande | Effet |
|---|---|
| `CH6 128` | Canal 6 **du projecteur** (1 = premier canal) à la valeur DMX 128. |
| `Channel 6 128` | Pareil, écrit avec un espace (`CH 6 128` fonctionne aussi). |
| `CH6 50%` | Avec `%` : pourcentage au lieu de la valeur DMX (50 % = 128). |
| `CH6 +20` | Relatif : 20 pas DMX de plus (`-20` de moins). |
| `CH6 Full` | 255 (aussi `Half` = 50 %, `Min` = 0). |

Le numéro de canal se rapporte à l'**ordre dans le mode du projecteur** (visible dans l'onglet *DMX direct* du programmeur), pas à l'adresse DMX : `Fixture 5 Thru 8 CH6 255` règle le 6e canal de chaque projecteur sélectionné où qu'il soit patché. La valeur est **0–255** comme dans DMX direct.

### Canaux par nom

Chaque nom de canal GDTF du projecteur peut être utilisé directement comme clause (valeur en **pourcentage**) :

```
Fixture 1 Frost 50        Iris 30        Cyan 100
Channel Frost1 50         CH Frost 50
```

Le nom peut être abrégé tant qu'il reste sans ambiguïté (`Frost` pour `Frost1`) ; des noms courts usuels sont intégrés (`Cyan`, `Magenta`, `Yellow` pour les canaux CMJ, `Red`/`Green`/`Blue` pour les canaux RVB, `Intensity` pour le gradateur). L'autocomplétion montre quels noms possède un projecteur (chapitre 14).

Les canaux qui ont leur propre attribut (gradateur, pan, tilt, zoom, focus, roue de gobos, prisme, obturateur) sont enregistrés comme cet attribut ; tous les autres (frost, iris, roue de couleurs, canaux fins …) comme valeurs de canal brutes. `Store Cue` reprend les deux.

---

## 6. Variables, effets, manuel

Les variables (presets) et les effets peuvent être appliqués à la **sélection actuelle** – seuls ou comme clause derrière une sélection, comme n'importe quel autre attribut.

| Commande | Effet |
|---|---|
| `Variable "Warm White"` | Applique la variable **et la lie** : les projecteurs la suivent jusqu'à ce qu'une valeur, un effet ou un cue reprenne l'attribut (changez la variable et les projecteurs changent avec elle). Formes courtes : `Var`, `Preset`. |
| `Effect Rainbow` | Assigne l'effet (la catégorie découle de l'effet). Plusieurs projecteurs tournent avec un décalage de phase comme dans la liste déroulante. |
| `Effect Off` | Termine **tous** les effets de la sélection ; `Effect Off color position` seulement les catégories nommées. |
| `Manual` | Retour au **manuel** : libère le lien de variable **et** l'effet pour toutes les catégories ; les dernières valeurs de sortie restent. |
| `Manual color` | Seulement cette catégorie (`dimmer`, `color`, `position`, `zoom`, `focus`, `gobo`, plusieurs à la suite, ou `all`). |

Les noms de variables et d'effets sont uniques dans OpenCue et sans distinction de casse. Avec des espaces, soit entre `"…"`, soit simplement les uns après les autres (`Variable warm white`). Un nom inconnu donne une erreur avec la liste de ceux qui existent. L'autocomplétion propose des variables (avec leur type) et des effets (avec leur catégorie).

```
Fixture 1 Thru 4 Variable "Warm White" Variable Wide Effect Wave
Group Front Manual color
Effect Off
```

---

## 7. Commandes combinées

Les commandes de sélection et de valeur/attribut peuvent être combinées sur **une seule ligne** – équivalent à deux commandes à la suite, mais plus rapide à taper :

```
Fixture 1 At 80
Fixture 1 Thru 5 At Full
Fixture 1 + 3 At 50
Fixture 1 Thru 10 Color Blue
Fixture 1 Pan 90 Tilt 45
Fixture 1 Thru 4 At 80 Zoom 30 Gobo 40 Frost 0
Group Front At 100 Color Warm
Fixture "Head 2" CH6 128
```

Plusieurs clauses d'attribut peuvent se suivre directement (`Fixture 1 At 80 Color Red` règle le gradateur ET la couleur d'un coup). Si une clause contient une erreur (faute de frappe dans l'attribut, nombre invalide, canal qu'aucun projecteur n'a), **ni** la sélection **ni** aucune valeur ne change.

---

## 8. Commandes enchaînées (virgule ou point-virgule)

Plusieurs commandes complètes peuvent être enchaînées sur **une** ligne, séparées par une virgule ou un point-virgule. Elles s'exécutent l'une après l'autre :

```
Fixture 1 At 100, Fixture 2 At 50
Fixture 1 Color Red; Fixture 2 Color Blue; Fixture 3 At 0
```

Si une partie échoue, les autres s'exécutent quand même ; le journal montre tous les résultats partiels sur une ligne séparés par `|`. Les virgules et points-virgules **entre guillemets** (par exemple dans un nom de cue) sont correctement ignorés : `Label Cue 1 "Act 1, scene 2"` n'est pas découpé.

---

## 9. Clear : `Clear` contre `Clear Clear`

| Saisie | Effet |
|---|---|
| `Clear` | Libère seulement la sélection actuelle. Les valeurs programmées restent. |
| `Clear Clear` | **Réinitialisation complète :** remet **tous** les projecteurs entièrement à zéro – gradateur, couleur et pan/tilt (selon le réglage de *Paramètres → Valeurs par défaut → Clear Clear* : par défaut gradateur 0 %, couleur blanche, pan/tilt 0° ; les projecteurs sans canal de gradateur restent noirs), zoom, focus, roues de gobos 1 et 2 avec rotation, prisme, stroboscope **et tous les autres canaux du projecteur** (frost, iris, roue de couleurs, vitesse, canaux fins …) à 0. Termine tous les effets, vide le programmeur et libère la sélection. |
| `Clear` deux fois **en 1,0 seconde** | Pareil que `Clear Clear` – taper rapidement `Clear` deux fois déclenche la réinitialisation complète. |
| `Clear` … (plus de 1,0 s) … `Clear` | Deux actions indépendantes « libérer la sélection » – **pas** de réinitialisation. |

---

## 10. Listes de cues : sélectionner par nom, Go, fader, gérer

Les commandes de cue agissent sur la **liste de cues active** (liste déroulante dans le panneau de la liste de cues). Avec `Cuelist` (équivalent : `QList`, `Q-List`, `CL`, `List`, `Exec`), vous pouvez adresser n'importe quelle liste **par nom** – sans distinction de casse ; les noms sont uniques dans OpenCue, donc c'est toujours clair. Comme partout : **d'abord la catégorie, puis le nom** – un simple nom de liste (`Show Go`) n'est pas une commande.

| Commande | Effet |
|---|---|
| `Cuelist Show` | Fait de « Show » la liste **active**. |
| `Cuelist "Cue List 1"` | Nom avec espaces (sans guillemets aussi, si sans ambiguïté : `Cuelist Cue List 1`). |
| `Cuelist 2` | La 2e liste dans l'ordre de la liste déroulante (comme `Exec 2`). |
| `Cuelist Show Go` | Avance la liste « Show » d'un pas – **sans** changer la liste active. |
| `QList Show Go` | Pareil avec la catégorie `QList`. |

### Créer, renommer, dupliquer, supprimer des listes

| Commande | Effet |
|---|---|
| `Cuelist New "Act 1"` | Crée une nouvelle liste (les noms sont uniques ; sans nom : `Cue List 1`, `Cue List 2` …). S'il n'y en avait aucune, elle devient active. |
| `Cuelist Show Rename "Act 1"` | Renomme (un nom déjà utilisé est refusé). |
| `Cuelist Show Duplicate` | Copie avec tous les cues, nouveaux ID, nom `Show (copy)` ; avec un nom : `Duplicate "Backup"`. |
| `Cuelist Show Delete` | Supprime la liste (`Delete Cuelist Show` fonctionne aussi) – **sans** confirmation ; un fondu en cours se termine. |

Une liste appelée « New » s'atteint entre guillemets : `Cuelist "New" Go`. N'importe quelle commande de cue peut suivre le nom de la liste ; elle s'applique alors exactement à cette liste, et le retour la nomme entre crochets (`OK: Go Cue 1 [Show]`).

### Lecture

| Commande | Effet |
|---|---|
| `Go` | Cue suivant (à la fin de la liste, Go saute au premier cue, comme le bouton). |
| `Go Cue 3` / `Go 3` | Saute directement au cue 3 (fondu doux avec sa durée de fondu). |
| `Goto Cue 3` | Pareil que `Go Cue 3`. |
| `Back` / `Go Back` | Cue précédent. |
| `Pause` / `Resume` | Pause / reprise du fondu en cours. |
| `Stop` | Interrompt le fondu (les valeurs restent) ; termine aussi tous les effets en cours. |
| `Fader 50` | Le **fader** de la liste (mixage entre valeur manuelle et cue, comme le fader d'exécuteur) à 50 %. Aussi `Fader Full`, `Fader +10`, `Fader At 30`. |
| `Off` / `Off Exec 1` / `Off Cuelist Show` | Réinitialise l'état de cue actif de la liste active / de la 1re / de la liste nommée. (Les exécuteurs ne sont pas encore des objets séparés ; `Exec N` désigne la N-ième liste. `Off` ne fait pas disparaître en fondu les dernières valeurs DMX.) |

```
Cuelist Show Go                Go Cue 3
Cuelist "Encore" Goto Cue 1    QList "Encore" Fader 40
Cuelist Show Fader +10         Cuelist 2 Back
```

---

## 11. Gérer les cues

Toutes les commandes de cue agissent sur la **liste de cues active** – ou, avec un `Cuelist <name>` en tête, sur la liste nommée.

| Commande | Effet |
|---|---|
| `Store Cue 1` | Enregistre un nouveau cue avec **chaque changement par rapport au cue précédent** (voir plus bas) – y compris un *Clear* qui a tout éteint. Les valeurs que vous avez touchées explicitement sont toujours incluses. |
| `Store Cue 1.5` | Les nombres décimaux permettent d'insérer plus tard entre des cues existants. « Avant » est alors le cue 1 (le cue au numéro immédiatement inférieur), quel que soit le cue actif en ce moment. |
| `Store Cue 1.5 CueOnly` | Lors d'une insertion au milieu, le **cue suivant** garde son aspect précédent : les valeurs que le nouveau cue modifie et que le cue suivant ne règle pas lui-même y sont fixées avec l'ancien état. Sans `CueOnly`, le cue suivant les hérite par tracking. |
| `Store Cue 4 "Intro"` | Avec un nom (sinon le cue s'appelle « Cue 4 »). |
| `Store Cue 3 Merge` | Si le cue 3 existe : seul ce qui diffère dans l'image par rapport à **ce cue** y entre, le reste demeure. Sans `Merge`/`Overwrite`, `Store Cue 3` signale une erreur au lieu de créer un numéro en double. |
| `Store Cue 3 Overwrite` | Si le cue 3 existe : son contenu est entièrement remplacé par les changements par rapport au cue précédent (nom, durées, déclencheur restent). |
| `Store Cue 6 Absolute` | Le cue rejouera plus tard **exactement l'état que vous avez vu à l'enregistrement** (tous les projecteurs, tous les canaux). Fonctionne aussi avec un programmeur vide : l'état actuel est enregistré comme instantané. `Relative` (par défaut) ne rejoue que vos changements. |
| `Update` | Reprend dans le cue **actif** tout ce qui diffère dans l'image de ce cue (seulement les canaux modifiés). Sans complément, c'est le réglage par défaut de *Paramètres → Valeurs par défaut → Nouveaux cues → Update* qui s'applique (« Demander chaque fois » agit comme le tracking pour la commande). |
| `Update Tracking` | Les cues suivants qui ne règlent pas eux-mêmes ces valeurs les reprennent à la lecture. |
| `Update CueOnly` | Comme `Update Tracking`, mais le cue suivant garde son aspect précédent. |
| `Delete Cue 3` | Supprime le cue 3. Avec une plage : `Delete Cue 3 Thru 5`. |
| `Move Cue 1 At 5` | Renumérote le cue 1 en 5 (la liste se retrie). Si le numéro cible existe, une erreur est signalée. |
| `Label Cue 1 "Intro"` / `Set Cue 1 Name "Intro"` | Renomme le cue 1. |

**Comment un cue est enregistré.** Un cue ne contient que ce qu'il modifie par rapport au cue précédent (tracking). Lors de l'enregistrement, OpenCue cherche donc le cue qui jouerait **avant** le nouveau – celui au numéro immédiatement inférieur, aussi pour `1.5` au milieu de la liste –, lit son état et enregistre exactement les différences avec l'image que vous voyez maintenant. Cela inclut un *Clear* : il éteint tout et constitue donc un grand changement. S'il n'y a pas de cue avant (le premier de la liste), il ne reçoit que les valeurs que vous avez touchées explicitement. Si rien n'a changé, `Store Cue` le dit et ne crée pas de cue (sauf avec `Absolute`).

**L'affichage « modifié ».** Le repère rouge de la liste des projecteurs et les points sur les onglets montrent la même chose : ce qui diffère maintenant du **cue actif** (en plus de ce que vous avez commandé à la main). Avec plusieurs listes, c'est le cue actif de la liste **utilisée en dernier** qui compte (Go, Back, saut, sélection, enregistrement). Pendant que cette liste fait un fondu, l'affichage reste tel quel ; avec un fader d'exécuteur sous 100 %, il est vide (la sortie est mélangée exprès). Ce n'est qu'un affichage – ce qui est enregistré est toujours le changement par rapport au cue précédent.

**Après l'enregistrement**, le cue enregistré est le **cue actif** de la liste (l'image lui correspond) ; le prochain `Go` démarre donc le cue qui le suit. Le programmeur est vidé pour les projecteurs enregistrés (le repère rouge disparaît). Les nouveaux cues reçoivent par défaut `Fade = 0.0 s` (commutation franche).

**Relatif et absolu :** chaque cue **enregistre toujours les deux** dans le fichier de show : les *changements* (ce que vous avez touché) et l'*état complet* de tous les projecteurs au moment de l'enregistrement (gradateur, couleur, position, gobo, zoom, focus et tous les autres canaux ; les variables restent des références). La **lecture** décide de ce qui se passe au Go :

- **Relatif** (tracking, par défaut) : seuls les changements enregistrés sont réglés, tout le reste demeure comme le cue précédent l'a laissé.
- **Absolu** : chaque projecteur est réglé exactement sur l'état enregistré – le cue 6 a donc exactement l'aspect de l'enregistrement, même si vous avez d'abord traversé les cues 1-5. Les effets que le cue n'a pas se terminent aussi sur tous les projecteurs.

La valeur par défaut pour les nouveaux cues se règle sous *Paramètres → Valeurs par défaut → Nouveaux cues* (on y trouve aussi le déclencheur, le délai, la durée de fondu, l'entrée/sortie en fondu des effets, le MIB et ce que fait *Update*). `Store Cue 6` sans complément reprend toujours ces valeurs ; ce que vous indiquez explicitement (`Absolute`, `Relative`) l'emporte. Dans la boîte de dialogue d'enregistrement, vous pouvez le changer pour un seul cue, plus tard dans la boîte de dialogue de modification, par un double-clic sur la colonne **Lecture** ou par la commande `Cue 6 Mode Absolute` / `Cue 6 Mode Relative`. Comme l'état est toujours enregistré, tout cue peut être basculé à tout moment. Sous *Valeurs par défaut → Démarrage du programme*, vous réglez aussi l'état d'OpenCue après le lancement (grand master du show ou valeur fixe, blackout activé/désactivé) et le niveau du fader d'exécuteur pour les nouvelles listes. Les anciens cues sans état enregistré se comportent, en absolu, comme le tracking de la liste jusqu'à ce cue.

**Les effets** sont toujours un état complet : un cue mémorise tous les effets qui tournaient quand il a été enregistré. `Update` le reprend aussi – un effet que vous avez arrêté disparaît du cue.

### Modifier les cues dans la liste (souris et tactile)

- **Une seule cellule :** double-cliquez sur une cellule (nom, déclencheur, durées, MIB, CMD …) pour la modifier directement dans la liste. La boîte de dialogue de modification (clic droit → *Modifier*) reste pour tout à la fois.
- **Plusieurs cues à la fois :** tracez un **rectangle** sur les cellules à la souris (au tactile : appui bref, puis glissement). **Seules les cellules à l'intérieur du rectangle** sont sélectionnées, pas la ligne entière. Un **double-clic** sur une cellule sélectionnée modifie alors **toutes les cellules sélectionnées de cette colonne** d'un coup – par exemple régler la durée de fondu de plusieurs cues sur 1. Cela fonctionne aussi pour des lignes entières sélectionnées par `Ctrl`-clic ou `Maj`-clic. Un simple clic sélectionne de nouveau une ligne entière. Le numéro de cue se modifie toujours un par un (les numéros sont uniques).
- **Déclencheurs avec symboles :** Go, Follow, Code temporel, Audio, MIDI et Heure de la journée ont chacun un symbole – dans la liste et sous forme de rangée de boutons dans la boîte de dialogue de modification (avec une courte remarque sur le moment où le cue démarre).
- **Déplacer :** changez le numéro du cue – le cue se déplace à sa nouvelle place.
- **Copier :** sélectionnez des cues → **Copier** (ou clic droit → *Copier …*). Choisissez la liste et le numéro de la première copie ; les autres gardent l'espacement des originaux. Les numéros qui existent déjà ne sont jamais écrasés – dans ce cas rien n'est copié et OpenCue nomme les numéros pris.
- **Annuler :** `Ctrl+Z` / `Ctrl+Y` annulent et rétablissent les modifications de cues (voir *Raccourcis clavier*).

### Propriétés d'un cue : `Cue <number> <property> <value>`

Tout ce qui se trouve dans la boîte de dialogue de modification (et dans les colonnes de la liste de cues) peut se régler par commande. À la place d'un numéro, une plage fonctionne aussi : `Cue 1 Thru 5 Fade 2` modifie les cues 1 à 5.

| Commande | Effet |
|---|---|
| `Cue 1 Fade 3` / `Cue 1 Delay 1.5` | Durées générales (gradateur) en secondes. |
| `Cue 1 Color Fade 2` / `Color Delay` | Durée propre à la couleur (`Colour` fonctionne aussi). |
| `Cue 1 Pos Fade 4` / `Pos Delay` | Durée propre à la position (`Position Fade` fonctionne aussi). |
| `Cue 1 Beam Fade 0` / `Beam Delay` | Durée propre au faisceau (gobo, prisme, stroboscope, focus …). |
| `Cue 1 Zoom Fade 2` / `Zoom Delay 1` | Durée propre au zoom. |
| `Cue 1 Color Fade -` | Un `-` (ou `default`) remet le groupe sur la durée générale. |
| `Cue 1 FX In 2` / `FX Out 1` | Entrée / sortie en fondu des effets en secondes (`Effect In` / `Effect Out` fonctionnent aussi). |
| `Cue 1 Trigger Go` / `Follow` | Déclencheur du cue. |
| `Cue 1 Trigger Timecode 00:01:30` | Déclenchement par le code temporel global (heure comme avec `Timecode At`). |
| `Cue 2 Trigger Audio Beat 4` | Déclenchement par la musique : se déclenche à chaque 4e temps dès qu'il est le cue suivant (le panneau Audio doit tourner). Sources : `Beat`, `Kick`, `Snare`, `Hat` (le nombre = un sur n, par défaut 1) et `Level`, `Bass`, `Mid`, `High`, `B1` … `B8` (le nombre = seuil en %, par défaut 70). |
| `Cue 2 Trigger Audio Kick` | Se déclenche au prochain coup de grosse caisse. |
| `Cue 2 Trigger Audio Bass 80` | Se déclenche quand les basses atteignent 80 %. |
| `Cue 3 Trigger Midi Note 60` | Déclenchement par un signal MIDI : se déclenche quand cette touche est pressée, dès que le cue est le cue suivant d'une liste en cours. `Note` prend un nombre (0–127) ou un nom de note (`Note C4`), `CC <number> [threshold]` se déclenche quand un contrôleur atteint le seuil (par défaut 64), `PC <number>` sur un changement de programme. Ajoutez `Ch <1-16>` pour un seul canal (par défaut : tous). Exemples : `Cue 3 Trigger Midi Note C4 Ch 2`, `Cue 4 Trigger Midi CC 20 100`, `Cue 5 Trigger Midi PC 3`. Le MIDI doit être activé (guide *MIDI*, section 5c). |
| `Cue 3 Trigger Clock 19:30 Mon-Fri` | Déclenchement par l'**horloge** : dès que le cue est le cue suivant d'une liste en cours, il attend cette heure de la journée (et ces jours : `Mon-Fri`, `Sat,Sun`, `weekdays`, `weekend`, `daily` – sans jours : tous les jours ; secondes autorisées : `19:30:15`). Voir le guide *Planification, heure de la journée et OSC*. (`Trigger Time` reste le déclencheur de code temporel.) |
| `Cue 1 MIB Auto` (`Off` / `On`) | Move In Black. |
| `Cue 1 Mode Absolute` (`Relative`) | Lecture : exactement l'état enregistré ou seulement les changements (voir plus haut). |
| `Cue 1 Cmd "Fixture 1 At 0; Go"` | Commande(s) que le cue exécute quand il se déclenche (chapitre 12). |
| `Cue 1 Name "Intro"` | Nom. |

---

## 12. CMD : attacher des commandes à un cue

Chaque cue a un champ de texte facultatif **CMD** (clic droit → Modifier → section « MIB et CMD », double-clic dans la colonne de la liste de cues, ou par la commande `Cue 3 Cmd "…"`). S'il contient une commande, OpenCue l'exécute **automatiquement** quand le cue est déclenché (par `Go`, un `Follow` automatique ou le menu contextuel « Fondu ici ») – avant le début du fondu proprement dit.

Plusieurs commandes se séparent par une **virgule ou un point-virgule** :

```
Fixture 1 At 0
Fixture 3 Thru 6 Color Blue
Fixture 1 At 0; Fixture 2 Zoom 30; Cuelist Encore Go
```

Le résultat apparaît dans le même historique de commandes partagé qu'une commande tapée, de sorte qu'il reste visible qu'un cue a déclenché une action. Le champ accepte jusqu'à 200 caractères. CMD peut contenir **n'importe quelle** commande de cette référence, y compris enchaînée et combinée – un cue peut démarrer une autre liste avec `Cuelist Encore Go`. Les appels récursifs `Go Cue` sont possibles, mais OpenCue ne détecte pas les boucles infinies entre des cues CMD enchaînés.

---

## 13. Retour dans le journal

Chaque commande exécutée produit une ligne dans la zone de journal du panneau, avec un horodatage :

```
[20:45:01] OpenCue> Fixture 1 Thru 10
           OK: 10 fixtures selected
[20:45:07] OpenCue> At 80
           OK: At 80 applied to 10 fixtures
[20:45:12] OpenCue> Store Cue 1
           OK: Cue 1 stored
```

Les commandes erronées sont marquées en **rouge** :

```
[20:46:40] OpenCue> At 80
           At: no fixtures selected
[20:46:55] OpenCue> Go Cue 99
           Cue 99 not found
[20:47:02] OpenCue> Fixture 1 Colr Red
           Unknown attribute: Colr
```

Les commandes enchaînées donnent **une** ligne avec tous les résultats partiels séparés par `|`. Le journal est identique sur **tous** les appareils connectés – chaque commande, où qu'elle ait été tapée (ou exécutée par le CMD d'un cue), apparaît dans chaque panneau de ligne de commande ouvert. Le texte du journal peut être sélectionné et copié.

---

## 14. Clavier et autocomplétion

| Touche | Effet |
|---|---|
| `Entrée` | Exécute la commande et vide la saisie. |
| `Flèche haut` | Commande précédente (plus ancienne). |
| `Flèche bas` | Commande suivante (plus récente), ou retour au brouillon que vous aviez commencé. |
| `Tab` | Prend la première suggestion ; chaque `Tab` suivant passe à la suivante. |
| `Maj` + `Tab` | Comme `Tab`, à l'envers. |
| `Échap` | Ferme la liste des suggestions. |

**Autocomplétion :** pendant la saisie (et au clic dans le champ), une liste de suites possibles apparaît au-dessus de la saisie. Au début d'une ligne, elle montre **seulement les catégories** (`Fixture`, `Group`, `Cuelist`, `Cue`, `Go` …) – les noms et valeurs viennent ensuite. La liste connaît l'**état actuel**, pas seulement les mots de commande :

- après `Fixture ` les numéros (avec le nom de l'appareil) et les noms,
- après `Group ` les groupes ; après `Cuelist ` les listes de cues (les noms avec espaces sont automatiquement mis entre `"…"`),
- après une sélection de projecteurs les attributs et exactement les **canaux que ces projecteurs possèdent** (`Frost1`, `Iris`, `ColorSub_C` … avec le numéro de canal comme indication),
- après `Go `, `Cue `, `Delete Cue ` les cues de la liste (nommée) avec leurs noms, puis les propriétés (`Fade`, `Color Fade`, `FX In`, `Trigger` …),
- après `Color ` les noms de couleurs, après `Zoom ` des valeurs (`Full`, `Half`, `Min`),
- après `Variable ` / `Effect ` les variables (avec type) et les effets (avec catégorie) ; après `Manual ` les catégories ; après `Store ` / `Delete ` / `Label ` `Cue` et `Group` ; après `Cuelist ` d'abord `New` ; après `Blackout ` `On` / `Off`.

Les lignes en italique sont des **indications** sur la valeur attendue (`<0-100> | +<n> | -<n> (%)`, `<0-255> (DMX) | <0-100>%`) et ne peuvent pas être insérées. La liste se rapporte toujours à la **dernière commande partielle** (après la dernière virgule/point-virgule). Un clic sur une entrée l'insère aussi. Toute la grammaire se trouve dans le serveur ; l'interface n'affiche que ce que le serveur suggère, de sorte que les suggestions ne diffèrent jamais de l'analyseur réel.

Un petit **interrupteur** tout à droite de la ligne de saisie active et désactive les suggestions (enregistré dans la configuration de l'application, valable pour tous les appareils).

Dans *Propriétés du panneau → Paramètres du module*, vous pouvez aussi changer les couleurs du texte, du succès et de l'erreur du journal.

---

## 15. Aide-mémoire

```
Fixture 1                       Fixture 1 Thru 10          Fixture 1 + 3
Fixture "Head 2"                Group 1                    Group Front

At 80          At Full          At At          Full        At 0     At +10     At -10
Master 80      Master Full      Master -10

Color Red      Color #FF8000    Color 255 128 0            RGB 255 0 0
Pan 180   Tilt -45   Pan 50%    Pan +10%                   Pan +15

Zoom 50   Focus 25   Gobo 40   Gobo2 40   GoboSpin 30   Prism 100   Strobe 0
CH6 128   CH6 50%    Channel 6 +20   Frost 50   Channel Frost1 50   Cyan 100

Fixture 1 At 80 Color Red Zoom 30          Group Front At 100, Fixture 5 At 0

Blackout       Blackout On       Blackout Off

Variable "Warm White"   Effect Wave   Effect Off   Effect Off color   Manual   Manual color

Store Group "Front"   Store Group "Front" Merge   Delete Group Front   Label Group Front "New"

Clear          Clear Clear

Go    Back    Go Cue 3    Goto Cue 3    Pause    Resume    Stop    Fader 50
Cuelist New "Act 1"    Cuelist Show Rename "Act 2"    Cuelist Show Duplicate    Cuelist Show Delete
Cuelist Show    Cuelist Show Go    QList "Encore" Fader 40    Cuelist 2 Back    Off    Off Cuelist Show

Store Cue 1    Store Cue 1.5    Store Cue 4 "Intro"    Store Cue 3 Merge    Update    Update CueOnly
Delete Cue 3   Delete Cue 3 Thru 5    Move Cue 1 At 5    Label Cue 1 "Intro"
Cue 1 Fade 3   Cue 1 Delay 1.5   Cue 1 Thru 5 Fade 2   Cue 1 Color Fade 2   Cue 1 Pos Delay 1
Cue 1 FX In 2  Cue 1 Trigger Follow   Cue 1 Trigger Timecode 00:01:30   Cue 3 Trigger Midi Note 60   Cue 1 MIB Auto   Cue 1 Cmd "Fixture 1 At 0; Go"

Timecode Play    Timecode At 4.3    Timecode Stop
```

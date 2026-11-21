# Atelier d'effets – Guide

Un **effet** est un petit programme qui modifie la lumière au fil du temps : un gradateur qui pulse, une couleur qui parcourt l'arc-en-ciel, un projecteur asservi qui décrit un cercle. Vous écrivez les effets dans l'**Atelier d'effets** (panneau *Atelier d'effets*) dans un langage qui ressemble à du C++ ou à Arduino : avec des variables, `if`, `for`, `while` et vos propres fonctions. Pas besoin d'être programmeur – les modèles sous **Nouveau...** fonctionnent tout de suite et sont faits pour être lus et modifiés.

Ce guide est aussi disponible dans l'atelier avec le bouton **Aide**.

---

## 1. L'idée en une minute

- Un **script** est un fichier texte (`.fx`). Il décrit ce qui se passe en **un seul passage**. Ce passage s'appelle `loop()` et s'exécute **`#RATE` fois par seconde** (1 à 40, par défaut 40).
- À chaque passage, le script calcule de nouvelles **valeurs de sortie** : `dimmer`, ou `r`/`g`/`b`, ou `pan`/`tilt`. Lesquelles, c'est la **catégorie** (`#CATEGORY`) qui le décide.
- Entre deux passages, la **sortie reste où elle est**. À 10 passages par seconde, la valeur change donc dix fois par seconde – exprès, c'est ainsi qu'on construit des effets par paliers.
- Le script s'exécute **pour chaque projecteur séparément**. Chacun connaît son numéro (`index`) et le total (`count`) ; utilisez-les pour répartir des vagues et des chenillards sur plusieurs projecteurs.
- Les variables que vous créez en dehors de `loop()` **gardent leur valeur d'un passage à l'autre** : compteurs, états, minuteries.

```
#NAME Sine
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05

loop() {
  dimmer = 50 + 50 * sin(2 * PI * speed * elapsed);
}
```

C'est un effet complet : le gradateur oscille entre 0 et 100 % avec `speed` vagues par seconde.

---

## 2. Aperçu des commandes (aide-mémoire)

Toutes les commandes en un coup d'œil. Les chapitres suivants les expliquent avec des exemples.

| Domaine | Commandes |
|---|---|
| Lignes d'en-tête | `#NAME`, `#DESCRIPTION`, `#CATEGORY dimmer` / `color` / `position`, `#RATE 1` à `40`, `#VAR name Slider` / `NumberInput` / `ColorPicker` / `Internal ...` |
| Structure | `setup() { }` (une fois au début), `loop() { }` (`#RATE` fois par seconde) |
| Types | `float` (`double`), `int` (`long`, `short`, `byte`), `bool` (`boolean`), `void`, `const` |
| Affectation | `x = 1;`, `x += 1;` (aussi `-=` `*=` `/=` `%=`), `x++;`, `x--;` |
| Branchement | `if (...) { } else if (...) { } else { }`, `condition ? a : b` |
| Boucles | `for (int i = 0; i < n; i++) { }`, `while (...) { }`, `do { } while (...);`, `break;`, `continue;` |
| Fonctions | `float name(float x) { return x * 2; }`, `void name() { }`, `return value;` |
| Calcul | `+ - * / %`, `== != < <= > >=`, `&& \|\| !` |
| Commentaires | `// jusqu'à la fin de la ligne`, `/* sur plusieurs lignes */` |
| Sorties | Gradateur : `dimmer` · Couleur : `r`, `g`, `b` ou `hsv(h, s, v);` · Position : `pan`, `tilt` · Zoom : `zoom` · Focus : `focus` · Gobo : `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin` |
| Temps | `t` (temps système partagé), `elapsed` (depuis le début de l'effet), `dt`, `tick` (`loop_count`), `rate` |
| Projecteurs | `index`, `count`, `phase` (= `index / count`), `slots`, `slots2` (nombre de gobos sur la roue 1 et la roue 2) |
| Constantes | `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false` |
| Maths | `sin` `cos` `tan` `asin` `acos` `atan` `atan2` `sqrt` `pow` `exp` `log` `abs` `sign` `min` `max` `floor` `ceil` `round` `fract` `mod` |
| Utilitaires | `constrain(x, lo, hi)` `map(x, inMin, inMax, outMin, outMax)` `lerp(a, b, k)` `smoothstep(e0, e1, x)` `radians(d)` `degrees(r)` |
| Formes d'onde | `saw(x)` `tri(x)` `square(x)` `square(x, duty)` – chacune de 0 à 1 par période |
| Aléatoire, couleur, gobo | `random()` `random(max)` `random(min, max)` · `hsv(h, s, v)` · `slot(n)` `slot(n, wheel)` |

---

## 3. Utiliser l'atelier

| Zone | Ce qu'elle fait |
|---|---|
| **Ouvrir...** | Boîte de dialogue avec tous les effets, **favoris en premier** (recherche, catégorie, boucles par seconde, origine ; les effets fournis portent l'insigne **Par défaut**). La liste défile. Cliquez sur une ligne pour l'ouvrir, l'**étoile** fait d'un effet un favori (valable pour tous les appareils), la corbeille le supprime du dossier utilisateur. En bas : **Restaurer les effets par défaut**. |
| **Nouveau...** | Boîte de dialogue : d'abord la **catégorie** (gradateur, couleur, position, zoom, focus, gobo) ou **Fichier vide**, puis un **modèle** (*Vide* est présélectionné), puis les **boucles par seconde**. *Fichier vide* crée un éditeur entièrement vide sans lignes d'en-tête. **Créer** charge le résultat dans l'éditeur – rien n'est enregistré tant que vous ne le dites pas. |
| **Enregistrer** | Enregistre dans le fichier de l'effet. Un nouvel effet demande un nom de fichier. Un point à côté du nom indique des modifications non enregistrées. Clavier : **Ctrl+S** dans le texte (enregistre l'effet, pas le show). |
| **Enregistrer sous...** | Un nouveau nom de fichier. S'il existe déjà, l'atelier demande s'il faut l'écraser. |
| **Supprimer** | Supprime l'effet chargé (dossier utilisateur seulement ; on vous demande d'abord). Ensuite l'éditeur est vide. Si le bouton est gris, une indication dit pourquoi (pas encore enregistré, ou pas dans le dossier utilisateur). |
| **Aide** | Ouvre ce guide. L'aide-mémoire (chapitre 2) liste toutes les commandes. |
| **Aperçu** | Affiche ou masque l'aperçu à droite. |
| **Barre d'état** | Vert = tout va bien. Rouge = erreur avec numéro de ligne. À droite : ligne et colonne du curseur. |

L'éditeur **colorie** les mots-clés, types, nombres, commentaires, fonctions, variables système, sorties et vos curseurs (`#VAR`). **Entrée** conserve l'indentation de la ligne (deux espaces de plus après `{`), **Tab** insère deux espaces.

### L'aperçu

L'aperçu exécute votre script **sans aucun projecteur** pendant que vous tapez – exactement avec les boucles par seconde choisies par `#RATE` – et dessine le résultat :

- **Gradateur :** une courbe par projecteur, de 0 à 100 %.
- **Couleur :** R/V/B en courbes et une **bande de couleur** par projecteur en dessous.
- **Position :** pan et tilt en courbes et le **tracé** dans le champ pan/tilt.

Par défaut : **1 projecteur, 2 secondes**. En haut, vous réglez le nombre de projecteurs (1 à 16) et la durée (1 à 20 s) ; plusieurs projecteurs montrent comment `index`, `count` et `phase` décalent les vagues. En dessous se trouvent des **curseurs pour vos paramètres `#VAR`** – faites-en glisser un et la courbe suit aussitôt. À une cadence basse (jusqu'à 20 boucles par seconde), l'aperçu dessine des paliers, jusqu'à 10 en plus les points individuels.

Si le script contient une erreur, l'aperçu reste sur le **dernier bon état, estompé**, la ligne d'erreur est marquée en rouge et la barre d'état nomme la ligne et le message.

---

## 4. Votre premier effet

1. **Nouveau...** → catégorie **Gradateur** → modèle **Sine** → **Créer**.
2. L'aperçu montre deux vagues en deux secondes (`speed` vaut 1).
3. Passez `speed` à 2 : deux fois plus vite. Réglez 3 projecteurs dans l'aperçu et passez `spread` à 0,33 : les vagues sont décalées les unes par rapport aux autres.
4. Changez `0.5 + 0.5 * sin(...)` dans le texte et observez la courbe.
5. **Enregistrer** (Ctrl+S), saisissez un nom de fichier. L'effet apparaît maintenant dans la liste d'effets du programmeur.

---

## 5. Structure d'un script

Un script comporte trois parties :

```
#NAME My effect                            // 1. Header lines (start with #)
#CATEGORY dimmer
#RATE 25
#VAR speed Slider 1 0.1 8 0.1

float level = 0;                           // 2. Variables and functions (optional)

setup() {                                  //    setup(): once when the effect starts (optional)
  level = 50;
}

loop() {                                   // 3. loop(): required, runs #RATE times per second
  dimmer = level;
}
```

### Lignes d'en-tête

| Ligne | Signification |
|---|---|
| `#NAME text` | Nom affiché dans le programme. Sans elle, le nom du fichier est utilisé. |
| `#CATEGORY dimmer` / `color` / `position` | **Obligatoire.** Ce que l'effet pilote. |
| `#RATE n` | Combien de fois `loop()` s'exécute par seconde : un nombre entier de **1 à 40**. Par défaut 40 – la cadence de la sortie DMX. |
| `#DESCRIPTION text` | Une courte description (aussi `#DESCRIPTION en ...` et `#DESCRIPTION de ...` pour un texte par langue ; le programme affiche celui de la langue de l'interface). |
| `#INFO name en Label \| Hint` | Donne au curseur `name` une **étiquette** et une **info-bulle** dans une langue (`en` ou `de`), par exemple `#INFO speed de Tempo \| Wie schnell der Effekt läuft`. Sans `#INFO`, le programme utilise son glossaire intégré des noms usuels (`speed`, `size`, `low`, `high`, `strobe` ...) et enfin le nom de la variable elle-même. |
| `#TAGS a, b, c` | Mots-clés pour chercher et filtrer dans la boîte de dialogue du type d'effet (par exemple `strobe, flash, toggle` ; jusqu'à 8, en minuscules). Un script qui lit des variables audio reçoit automatiquement l'étiquette `audio` – vous ne l'écrivez pas. Les effets fournis portent `basic` (pour débutants, 19 d'entre eux) ou `advanced` (tous les autres) comme première étiquette ; la boîte de dialogue les affiche comme « Basique » / « Avancé » – utilisez-les aussi pour vos propres effets. |
| `#VAR ...` | Un **curseur** (voir la section 9) ou une variable interne. |

---

## 6. Temps et cadence

**La règle la plus importante :** `loop()` s'exécute exactement `#RATE` fois par seconde – quelle que soit la vitesse de l'ordinateur. Vous pouvez donc **penser en secondes exactes**.

| Nom | Signification |
|---|---|
| `elapsed` | **Secondes depuis le début de l'effet** sur ce projecteur. Commence à 0. Exactement `tick / rate`. C'est ainsi que vous programmez « à la seconde 3, ceci doit se produire ». |
| `t` | Temps système partagé en secondes. Le même pour **tous** les effets – les effets qui calculent avec `t` restent **synchronisés** entre eux même s'ils ont été démarrés à des moments différents. |
| `tick` | Numéro du passage, commence à 0. |
| `rate` | Passages par seconde (la valeur de `#RATE`). |
| `dt` | Temps entre deux passages en secondes (`1 / rate`). |

Quelle cadence choisir ?

- **40** (par défaut) : les courbes les plus fluides – pour les vagues, cercles, fondus enchaînés.
- **10 à 25** : suffisant pour les changements de couleur et les effets qui sont de toute façon par paliers.
- **1 à 5** : effets par pas (un pas par seconde, chenillards « clic-clic »), peu coûteux à calculer.

**La convention « speed » :** les effets fournis et tous les modèles ont un curseur `speed` avec la valeur par défaut **1** : c'est **une période par seconde**. `sin(2 * PI * speed * elapsed)` est une vague par seconde avec `speed = 1`.

### À la seconde X ...

```
#NAME Sequence
#CATEGORY dimmer
#RATE 20
#VAR length Slider 8 2 30 1       // length of the sequence in seconds

loop() {
  float s = elapsed % length;     // time within the sequence; jumps back to 0 after "length" seconds
  if (s < 2) {
    dimmer = map(s, 0, 2, 0, 100);                 // seconds 0 to 2: fade in
  } else if (s < 5) {
    dimmer = 100;                                  // seconds 2 to 5: full
  } else {
    dimmer = 100 * (1 - (s - 5) / (length - 5));   // then fade out
  }
}
```

---

## 7. Le langage

Tout est un **nombre**. Les types sont `float` (décimal, aussi `double`), `int` (entier, aussi `long`, `short`, `byte`) et `bool` (0 ou 1, aussi `boolean`). `true` et `false` valent 1 et 0.

### Variables

```
float x = 1.5;          // decimal number (dot, not comma)
int n = 3;              // whole number: assigning truncates (7.9 becomes 7)
bool on = true;         // 0 or 1: any value other than 0 becomes 1
const float K = 0.25;   // constant, cannot be changed
float a = 1, b2 = 2;    // several in one line
```

- Les variables créées **en dehors** des fonctions sont **globales** et **gardent leur valeur** d'un passage à l'autre. Leur valeur initiale s'applique au démarrage de l'effet (pour les réinitialiser plus tard, écrivez `setup()`).
- Les variables créées **à l'intérieur** de `{ }` sont **locales** : elles durent jusqu'à l'accolade fermante et repartent à neuf à chaque passage.
- Affecter une variable **non déclarée** (`counter = counter + 1;`) crée automatiquement un `float` global – c'est ainsi que fonctionnaient les anciens scripts. Mieux vaut la déclarer.
- Les noms `t`, `elapsed`, `dt`, `tick`, `rate`, `index`, `count`, `phase`, `dimmer`, `r`, `g`, `b`, `pan`, `tilt`, `PI` ainsi que tous les mots-clés et noms de fonctions sont pris.

### Calculer et comparer

| Symbole | Signification |
|---|---|
| `+ - * /` | Arithmétique de base. La division par 0 donne 0. |
| `%` | Reste (aussi pour les décimaux) : `5.5 % 2` vaut 1,5. |
| `== != < <= > >=` | Comparaisons ; résultat 1 (vrai) ou 0 (faux). |
| `&& \|\| !` | Et, ou, non. Les conditions sont vraies quand elles ne valent pas 0. |
| `condition ? a : b` | Choix : `a` si la condition est vraie, sinon `b`. |
| `= += -= *= /= %=` | Affectation ; `x += 2;` équivaut à `x = x + 2;`. |
| `x++;` `x--;` | Augmenter / diminuer de 1. |

### Branchement et répétition

```
if (x > 10) {                 // if ...
  dimmer = 100;
} else if (x > 5) {           // else if ...
  dimmer = 50;
} else {                      // else
  dimmer = 0;
}

for (int i = 0; i < 5; i++) { // count i from 0 to 4
  total += i;
}

while (n > 0) { n--; }        // as long as n is greater than 0

do { n++; } while (n < 3);    // run at least once

break;                        // leave the loop at once
continue;                     // jump to the next loop pass
```

Les accolades `{ }` sont facultatives pour une seule instruction (`if (a) b = 1;`), mais plus claires avec. Il n'y a pas de `switch` – utilisez `if` / `else if`.

### Vos propres fonctions

```
float wave(float x) {                     // return type, name, parameters
  return 0.5 + 0.5 * sin(2 * PI * x);     // return hands the value back
}

void setBright(float v) {                 // void: returns nothing
  dimmer = v;
}

loop() {
  setBright(100 * wave(speed * elapsed));
}
```

Les fonctions peuvent se trouver avant ou après l'endroit où elles sont appelées, et peuvent s'appeler elles-mêmes (récursivité, limitée). Les paramètres sont locaux ; les variables globales et les sorties (`dimmer` ...) sont accessibles partout.

### Commentaires

```
// rest of the line is a comment
/* several
   lines */
```

### Limites

- Un passage peut faire au plus **60 000 itérations de boucle et appels de fonction** ; une boucle infinie s'arrête avec le message « endless loop? ».
- Un effet qui **provoque une erreur ou a besoin de plus de 50 ms par passage** est désactivé (« mis au repos ») pour ne pas retarder les autres. Enregistrez de nouveau le script et il tourne de nouveau.
- Il n'y a que des nombres : pas de texte, de listes (tableaux) ni de pointeurs.

---

## 8. Sorties par catégorie

Le script écrit son résultat dans des variables adaptées à la catégorie :

| `#CATEGORY` | Sorties | Plage |
|---|---|---|
| `dimmer` | `dimmer` | 0 à 100 (%) |
| `color` | `r`, `g`, `b` | 0 à 255 |
| `position` | `pan`, `tilt` | 0 à 100 (%), 50 est le centre. Si le projecteur a des canaux fins (16 bits), les décimales sont utilisées : `pan = 33.3333;` est plus précis que `pan = 33;` |
| `zoom` | `zoom` | 0 à 100 (%) – les extrémités du canal de zoom (large/étroit, selon le projecteur) |
| `focus` | `focus` | 0 à 100 (%) – les extrémités du canal de focus (près/loin) |
| `gobo` | `gobo` | 0 à 100 (%) – la position du canal de gobo de la roue 1 ; choisissez les gobos de préférence avec `slot(n)` (voir plus bas) |
| `gobo` | `gobo_spin` | 0 à 100 (%) – rotation ou secousse de la roue 1 (la plage fixe le sens et la vitesse, selon le projecteur) |
| `gobo` | `gobo2` | 0 à 100 (%) – roue de gobos 2 (projecteurs avec une seconde roue seulement), choisissez les gobos avec `slot(n, 2)` |
| `gobo` | `gobo2_spin` | 0 à 100 (%) – rotation de la roue 2 |

Les valeurs hors plage sont ramenées dans la plage. **Un effet ne pilote que les sorties que son script affecte quelque part** (`hsv()` compte comme `r`, `g`, `b` ; pour la couleur toujours les trois). Si un script n'écrit que `pan`, `tilt` est laissé tranquille : le canal ne suit pas l'effet, et dans le programmeur seul le fader Pan est verrouillé – vous pouvez continuer à régler Tilt à la main. Si une sortie n'est pas atteinte pendant un passage (p. ex. l'affectation est dans un `if`), elle vaut 0 pour ce passage (`pan`/`tilt` : centre, 50). Si le projecteur n'a pas le canal, la sortie est ignorée sans bruit. Les sorties d'une autre catégorie sont ignorées. Avec `hsv(h, s, v);`, vous réglez `r`, `g`, `b` à partir de la teinte, de la saturation et de la valeur (chacune de 0 à 1) en une seule étape.

Remarque : les sorties ne s'appliquent qu'au **passage en cours** – pour mémoriser une valeur, créez votre propre variable (`float level = 0;` ... `dimmer = level;`).

---

## 9. Curseurs : `#VAR`

```
#VAR <name> <type> <default> [min max step]
```

| Type | Valeur par défaut | Commande |
|---|---|---|
| `Slider` | nombre, plus `min max step` | curseur |
| `NumberInput` | nombre, plus `min max step` | champ numérique |
| `ColorPicker` | couleur hexadécimale, p. ex. `#ff8800` | sélecteur de couleur ; dans le script sous la forme `name_r`, `name_g`, `name_b` (0 à 255) |
| `Internal` | nombre | pas de commande – une variable globale avec une valeur initiale (comme `float name = 0;`) |

```
#VAR speed Slider 1 0.05 8 0.05          // periods per second
#VAR size Slider 100 0 100 1             // strength in %
#VAR color ColorPicker #00aaff           // color_r, color_g, color_b
```

Les curseurs apparaissent dans la boîte de dialogue **Créer / Modifier un effet** et dans l'aperçu de l'atelier. Dans le script, ils sont en **lecture seule**.

---

## 10. Variables système

| Nom | Signification |
|---|---|
| `t` | Temps système partagé en secondes (garde les effets synchronisés). |
| `elapsed` | Secondes depuis le début de cet effet sur ce projecteur. |
| `dt` | Secondes entre deux passages (`1 / rate`). |
| `tick` | Numéro du passage (0, 1, 2 ...). Aussi `loop_count`. |
| `rate` | Passages par seconde. |
| `index` | Numéro de ce projecteur dans l'ordre de sélection du programmeur (0, 1, 2 ...). |
| `count` | Nombre de projecteurs sur lesquels l'effet tourne. |
| `phase` | `index / count` : décalage régulier sur la sélection (0 à presque 1). |
| `slots` | Nombre de gobos fixes sur la roue 1 (seulement dans la catégorie `gobo`, sinon 0). L'aperçu utilise 8 gobos. |
| `slots2` | Pareil pour la roue 2 (0 si le projecteur n'a qu'une roue). |

L'ordre de sélection est l'ordre dans lequel vous avez choisi les projecteurs.

### Variables audio (`a_...`)

Les effets peuvent réagir à la musique. Le panneau **Audio** analyse le son (voir le guide *Audio*) ; ces variables contiennent le résultat. Toutes commencent par `a_`, elles n'entrent donc jamais en conflit avec vos propres noms. Sans source audio en cours, elles valent toutes `0`. Un script qui en lit une est un **effet audio** (signalé dans la liste et dans l'atelier ; l'aperçu fait alors tourner un battement d'exemple à 120 BPM).

| Nom | Signification |
|---|---|
| `a_active` | `1` tant que du son arrive, sinon `0`. |
| `a_level` | Volume global de 0 à 1 (relatif aux parties les plus fortes des dernières secondes). |
| `a_bass`, `a_mid`, `a_high` | Basses (jusqu'à 150 Hz), médiums (150 Hz à 2,5 kHz) et aigus (au-dessus de 2,5 kHz), de 0 à 1. |
| `a_b1` ... `a_b8` | Les huit bandes une par une (20-60, 60-150, 150-400, 400-1k, 1k-2,5k, 2,5k-5k, 5k-10k, 10k-20k Hz), de 0 à 1. |
| `a_kick`, `a_snare`, `a_hat` | Coups de grosse caisse, de caisse claire (ou clap) et de charleston : saute à 0,45 - 1 à chaque coup et s'estompe en 0,15 s environ (charleston 0,07 s). |
| `a_beat` | Le même genre d'impulsion à chaque temps du tempo détecté. |
| `a_beat_phase` | Position dans le temps, de 0 à 1, croissant régulièrement d'un temps au suivant : idéal pour des vagues synchrones avec le tempo. |
| `a_beat_count` | Numéro du temps ; augmente de 1 à chaque temps. |
| `a_bpm` | Tempo détecté (ou réglé) en battements par minute ; `0` tant qu'il est inconnu. |
| `a_conf` | Fiabilité de la détection du tempo, de 0 à 1. |

```
#CATEGORY dimmer
#RATE 40
loop() {
  dimmer = lerp(5, 100, a_kick);                              // flash on every bass drum
}
```

Astuce : un passage ne voit que l'état à son propre instant. Lire une impulsion (`a_kick`) est toujours sûr parce qu'elle s'estompe ; pour réagir à l'*instant* d'un coup, mémorisez la dernière valeur dans une variable globale et comparez (voir l'effet *Audio : Hi-Hat Sparkle*). Utilisez `#RATE 40` pour les effets audio afin qu'ils restent nerveux.

---

## 11. Fonctions

| Fonction | Signification |
|---|---|
| `sin(x)`, `cos(x)`, `tan(x)` | Angle en radians (tour complet = `2 * PI`). |
| `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y, x)` | Fonctions inverses. |
| `sqrt(x)`, `pow(x, y)`, `exp(x)`, `log(x)` | Racine, puissance, fonction exponentielle, logarithme népérien. Une entrée invalide donne 0. |
| `abs(x)`, `sign(x)` | Valeur absolue ; signe (-1, 0, 1). |
| `min(a, b)`, `max(a, b)` | Valeur la plus petite / la plus grande. |
| `floor(x)`, `ceil(x)`, `round(x)` | Arrondir vers le bas, vers le haut, arrondir. |
| `fract(x)` | Partie fractionnaire : `fract(2.25)` vaut 0,25. Utile pour « position dans la période ». |
| `mod(a, b)` | Reste jamais négatif (contrairement à `%` pour les nombres négatifs). |
| `constrain(x, low, high)` | Limite `x` à la plage. |
| `map(x, inMin, inMax, outMin, outMax)` | Convertit `x` d'une plage à une autre (comme dans Arduino). |
| `lerp(a, b, k)` | Linéaire de `a` à `b` : `a + (b - a) * k`. |
| `smoothstep(e0, e1, x)` | Transition douce de 0 à 1 entre `e0` et `e1`. |
| `saw(x)`, `tri(x)`, `square(x)`, `square(x, duty)` | Formes d'onde de 0 à 1 par période de `x` : dent de scie, triangle, carré (`duty` = part « allumée », par défaut 0,5). |
| `radians(d)`, `degrees(r)` | Degrés ↔ radians. |
| `random()`, `random(max)`, `random(min, max)` | Nombre aléatoire (0 à 1, 0 à `max`, `min` à `max`). Chaque projecteur a sa propre séquence **reproductible**. |
| `hsv(h, s, v)` | Règle `r`, `g`, `b` à partir de la teinte `h` (0 à 1, cyclique), de la saturation `s` et de la valeur `v` (0 à 1). |
| `slot(n)` | La valeur (en %) du n-ième gobo de la roue 1 ; `slot(0)` est le premier (généralement ouvert). Seulement dans la catégorie `gobo` ; la liste vient du fichier du projecteur, sans données `slot()` renvoie 0. |
| `slot(n, wheel)` | Comme `slot(n)`, mais pour la roue `wheel` (1 ou 2) : `gobo2 = slot(3, 2);` |

Constantes : `PI`, `TWO_PI`, `HALF_PI`, `E`, `true`, `false`.

---

## 12. Exemples

### Pulse (gradateur)

Allumé et éteint net ; `duty` est la part de la période pendant laquelle la lumière est allumée.

```
#NAME Pulse
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR duty Slider 0.25 0.05 1 0.05
#VAR spread Slider 0 0 1 0.05

loop() {
  float p = fract(speed * elapsed + index * spread);
  dimmer = p < duty ? 100 : 0;
}
```

### Chase (gradateur)

Une lumière parcourt tous les projecteurs sélectionnés.

```
#NAME Chase
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1
#VAR width Slider 1 0.5 8 0.5

loop() {
  float pos = fract(speed * elapsed) * count;   // current step (decimal)
  float d = abs(index - pos);
  if (d > count / 2) d = count - d;             // distance on the circle
  dimmer = d < width ? 100 : 0;
}
```

### Couleur aléatoire (couleur)

Change `speed` fois par seconde vers une teinte aléatoire. La variable globale `hue` s'en souvient.

```
#NAME Random color
#CATEGORY color
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float hue = 0;

loop() {
  if (tick % max(1, round(rate / speed)) == 0) {
    hue = random();
  }
  hsv(hue, 1, 1);
}
```

### Quatre positions (position, machine à états)

La tête saute au coin suivant parmi quatre toutes les `interval` secondes. L'état est dans `step`.

```
#NAME Four positions
#CATEGORY position
#RATE 10
#VAR interval Slider 1 0.2 10 0.1

int step = 0;
float start = 0;

loop() {
  if (elapsed - start >= interval) {
    step = (step + 1) % 4;
    start = elapsed;
  }
  pan = (step == 0 || step == 3) ? 20 : 80;
  tilt = (step < 2) ? 20 : 80;
}
```

### Harmoniques (gradateur, boucle)

Additionne plusieurs vagues avec une boucle `for` (plus l'harmonique est haute, plus elle est faible).

```
#NAME Harmonics
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 4 0.1
#VAR harmonics Slider 3 1 8 1

loop() {
  float sum = 0;
  float norm = 0;
  for (int k = 1; k <= harmonics; k++) {
    sum += sin(2 * PI * k * speed * elapsed) / k;
    norm += 1.0 / k;
  }
  dimmer = 50 + 50 * sum / norm;
}
```

### Zoom qui respire (zoom)

Le zoom oscille entre `low` et `high` (0 et 100 sont les extrémités du canal de zoom).

```
#NAME Zoom breathing
#CATEGORY zoom
#RATE 40
#VAR speed Slider 1 0.05 8 0.05
#VAR low Slider 20 0 100 1
#VAR high Slider 80 0 100 1

loop() {
  float k = 0.5 + 0.5 * sin(2 * PI * speed * elapsed);
  zoom = lerp(low, high, k);
}
```

### Changement de gobo (gobo)

Parcourt tour à tour les gobos du projecteur. `slots` est leur nombre, `slot(n)` la valeur du n-ième (0 = le premier, généralement ouvert). Chaque projecteur a des gobos différents – l'effet interroge donc le projecteur au lieu de deviner des pourcentages.

```
#NAME Gobo change
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05
#VAR first Slider 0 0 20 1

loop() {
  float n = max(1, slots - first);
  gobo = slot(first + mod(floor(speed * elapsed), n));
}
```

### Gobo avec rotation et seconde roue (gobo)

Les sorties `gobo`, `gobo_spin`, `gobo2` et `gobo2_spin` peuvent être utilisées séparément. Cet exemple parcourt la roue 1, laisse la roue 2 suivre avec un décalage et fait tourner le gobo choisi :

```
#NAME Two wheels
#CATEGORY gobo
#RATE 20
#VAR speed Slider 0.5 0.05 8 0.05

loop() {
  float n  = max(1, slots);
  float n2 = max(1, slots2);
  gobo  = slot(mod(floor(speed * elapsed), n));
  gobo2 = slot(mod(floor(speed * elapsed) + 1, n2), 2);
  gobo_spin = 70;                    // rotation of wheel 1 (set only if wanted)
}
```

### Coureur bicolore (couleur)

Tous les projecteurs montrent la couleur A, un ou deux parcourent la rangée en couleur B (ordre de sélection). `direction` fixe le sens – c'est le *Color Runner* fourni en version courte :

```
#NAME Color runner
#CATEGORY color
#RATE 40
#VAR speed Slider 0.5 0.05 4 0.05
#VAR width Slider 1.5 0.5 8 0.5
#VAR direction Slider 1 0 1 1
#VAR color_a ColorPicker #ffcc00
#VAR color_b ColorPicker #ff0000

loop() {
  float run = fract(speed * t);
  if (direction < 0.5) run = 1 - run;
  float d = abs(index - run * count);
  if (d > count / 2) d = count - d;
  float k = d < width ? 1 : 0;
  r = lerp(color_a_r, color_b_r, k);
  g = lerp(color_a_g, color_b_g, k);
  b = lerp(color_a_b, color_b_b, k);
}
```

### Votre propre fonction (gradateur)

```
#NAME Triangle with function
#CATEGORY dimmer
#RATE 40
#VAR speed Slider 1 0.1 8 0.1

float triangle(float x) {
  return 1 - abs(2 * fract(x) - 1);
}

loop() {
  dimmer = 100 * triangle(speed * elapsed + phase);
}
```

---

## 13. Erreurs et vérification

L'atelier vérifie pendant que vous tapez. Messages typiques (toujours avec un numéro de ligne) :

| Message | Cause |
|---|---|
| `Unbekannte Variable 'x'` | Nom jamais déclaré ni affecté (faute de frappe ?). |
| `Unbekannte Funktion 'foo()'` | La fonction n'existe pas. |
| `sin() erwartet 1 Argument(e)` | Mauvais nombre d'arguments. |
| `';' erwartet, gefunden '}'` | Il manque un point-virgule (le message pointe souvent la ligne suivante). |
| `Ausdruck erwartet, gefunden ';'` | Il manque une valeur, p. ex. `dimmer = 1 +;`. |
| `'speed' ist ein Regler (#VAR) ...` | Les curseurs sont en lecture seule ; créez votre propre variable. |
| `'b' ist eine Ausgabe des Effekts ...` | `dimmer`, `r`, `g`, `b`, `pan`, `tilt` et les noms système sont pris. |
| `'break' ist nur in einer Schleife erlaubt` | `break` / `continue` en dehors de `for` / `while`. |
| `#RATE erwartet eine ganze Zahl von 1 bis 40` | Cadence invalide. |
| `#CATEGORY fehlt` | L'en-tête n'a pas de catégorie. |
| `loop() erwartet` | Le script n'a pas de fonction `loop()`. |
| `Zu viele Schritte in einem Durchlauf ... Endlosschleife?` | Une boucle ne se termine jamais (erreur d'exécution, apparaît dans l'aperçu). |

(Les messages sont affichés en allemand quelle que soit la langue de l'interface.)

**Enregistrer** enregistre aussi les scripts avec erreurs pour que vous puissiez continuer à travailler. Un script défectueux n'est pas exécuté ; les effets en cours gardent la **dernière bonne version**.

Si un script est enregistré pendant que des effets tournent, ils prennent le nouveau code au passage suivant. Leur **mémoire** (variables globales, compteurs, état) est conservée ; les variables nouvellement ajoutées démarrent avec leur valeur initiale.

---

## 14. Comment les effets fonctionnent dans le programme

- **Script et effet :** le script (`.fx`) est le fichier. Un **effet** (dans la liste d'effets du programmeur) est une **définition** : un nom, un script et des valeurs pour ses curseurs. Plusieurs effets peuvent utiliser le même script avec des valeurs de curseurs différentes. Quand vous en créez un, la boîte de dialogue montre la description du script et ses boucles par seconde.
- **Application :** dans le programmeur, vous assignez un effet par **catégorie** (gradateur, couleur, position, zoom, focus, gobo) aux projecteurs sélectionnés : la ligne **Variable:/Effet** dans la vue du programmeur correspondante (focus et zoom dans la vue focus, gobo dans l'onglet gobo de la zone faisceau ; pendant qu'un effet tourne, le fader correspondant est verrouillé). L'ordre de sélection détermine `index` et donc la répartition sur les projecteurs. Un effet ne pilote que les canaux de sa catégorie.
- **Dans les cues :** un cue enregistre les assignations d'effets (avec l'ordre de sélection) et les démarre à la lecture ; les durées d'**entrée en fondu** et de **sortie en fondu de l'effet** du cue enchaînent l'amplitude depuis / vers la valeur précédente. Si un cue fixe une valeur pour une catégorie, l'effet en cours s'arrête là et le cue fait un fondu depuis la dernière sortie de l'effet.
- **Synchronisation :** les effets qui utilisent `t` (ou `phase`/`index` avec `t`) tournent en phase entre eux. Avec `elapsed`, chaque effet repart du début quand il démarre – juste pour des séquences « à partir de maintenant ».
- **État :** chaque effet a sa **propre mémoire** par projecteur et catégorie. Elle repart à neuf quand l'effet est de nouveau assigné.
- **Fichiers :** les scripts se trouvent dans le dossier `effects/` du dossier de données. L'atelier, le **gestionnaire de fichiers** (genre *Effets* : renommer, dupliquer, télécharger, téléverser) et l'**export** du show (les scripts utilisés vont dans le paquet) travaillent avec les mêmes fichiers. Les effets fournis sont copiés au premier démarrage ; **Restaurer les effets par défaut** (dans la boîte de dialogue Ouvrir ou le gestionnaire de fichiers) recrée ceux qui manquent et n'écrase **jamais** rien.
- **Le show enregistre les définitions** (nom, nom du script, valeurs des curseurs), pas le texte du script. Si le script manque, les définitions perdent leur effet et refonctionnent à son retour ; un cue avec un effet manquant laisse le canal inchangé.

### Limites actuelles

- Il y a six catégories (gradateur, couleur, position, zoom, focus, gobo). D'autres (prisme, stroboscope, valeurs DMX brutes) sont préparées mais pas encore intégrées.
- Le zoom et le focus utilisent le canal propre du projecteur et celui-ci doit exister ; les gobos dépendent du fichier du projecteur. L'aperçu ne montre que les valeurs des gobos, pas l'image.
- Un effet pilote une catégorie par projecteur ; deux catégories à la fois demandent deux effets.
- La cadence est au plus de 40 par seconde car la sortie DMX n'envoie pas plus vite.

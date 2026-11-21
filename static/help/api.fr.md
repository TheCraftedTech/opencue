# API REST

Avec l'**API REST**, d'autres programmes peuvent **lire** l'état d'OpenCue et le **piloter et le modifier** – scripts, contrôleur de show, domotique, page web de régie, application pour tablette ou votre propre outil. Elle parle en **HTTP** simple et répond en **JSON**. Aucun logiciel supplémentaire n'est nécessaire, et elle fonctionne entièrement hors ligne dans votre réseau.

L'accès est protégé par des **jetons** que vous créez dans OpenCue. Chaque jeton a ses propres **autorisations** : une application de tablette peut ne faire que lire, un autre outil peut aussi déclencher des cues et un troisième peut construire des shows entiers.

---

## 1. L'idée en une minute

- L'API se trouve sous **`/api/v1/`**, à la même adresse et sur le même port qu'OpenCue lui-même (par exemple `http://127.0.0.1:8000/api/v1/`).
- Vous **créez un jeton** dans *Paramètres → API* et l'envoyez avec chaque requête.
- Les requêtes de **lecture** (`GET`) renvoient l'état : projecteurs, listes de cues, cues, variables, effets, signal DMX, code temporel, programmeur.
- Les requêtes d'**exploitation** (`POST` / `PUT`) font tourner le show : commandes, cues, code temporel, blackout, audio, programmeur.
- Les requêtes de **modification** changent le show lui-même : créer et modifier des listes de cues et des cues, des variables, des effets et des scripts d'effets, patcher des projecteurs, enregistrer et charger des fichiers de show, téléverser des médias.
- Les **boutons, faders et interrupteurs** propres de la console peuvent être pressés, déplacés et basculés de l'extérieur.
- Tout ce qu'un opérateur fait dans la fenêtre apparaît **aussitôt dans toutes les fenêtres ouvertes** – y compris ce que l'API modifie.
- Un **flux en direct** (`GET /events`) signale les changements au moment où ils se produisent, de sorte qu'un tableau de bord n'a pas à interroger sans cesse.
- Pour le **matériel** (un ESP32 avec joystick, potentiomètres, boutons, microphone), il y a un **WebSocket** (`/api/v1/ws`) : joystick relatif ou absolu, valeurs absolues ou relatives, DMX et valeurs en direct, envoi et réception du code temporel, valeurs audio et données audio dans les deux sens (section 10). Pour les appareils simples sans interface propre, il y a des **vues d'état** sous forme d'image ou de page web (section 11).
- Chaque fonction nécessite **une autorisation**. Un jeton qui ne l'a pas reçoit `403`. Les autorisations de modification sont **désactivées par défaut**.
- L'API est une interface propre et stable. Les routes internes qu'utilise la fenêtre du programme n'en font *pas* partie.

---

## 2. Démarrage rapide

1. Ouvrez **Paramètres → API REST** (possible aussi depuis un appareil distant connecté). Par défaut, il n'y a **aucun jeton** et l'API ne répond que sur **cet ordinateur**.
2. Cliquez sur **Nouveau jeton**, donnez-lui un nom, choisissez les autorisations (ou un préréglage) et cliquez sur **Créer le jeton**. Un **nouveau jeton est créé aussitôt** (sans *Enregistrer*) et affiché juste après.
3. **Copiez le jeton maintenant.** Il n'est affiché qu'une fois ; ensuite seuls ses premiers caractères sont visibles. S'il est perdu, créez-en un nouveau ou utilisez *Générer un nouveau jeton*.
4. Essayez :

```
curl -H "Authorization: Bearer oc_xxxxxxxx" http://127.0.0.1:8000/api/v1/status
```

La réponse est un objet JSON avec le nom du show, le blackout, le grand master, le code temporel et plus encore (voir la section 6).

L'adresse des exemples (`127.0.0.1:8000`) est celle de la console elle-même. Pour l'adresse depuis d'autres appareils, voir la section 8. Une page avec toutes les routes, consultable avec recherche et lisible hors ligne, se trouve à `/api/v1/docs`.

---

## 3. Jetons et autorisations

### Gérer les jetons

Dans **Paramètres → API REST**, vous pouvez :

| Action | Signification |
|---|---|
| **API REST activée/désactivée** | L'interrupteur principal. Désactivé, chaque requête reçoit la réponse `403 api_disabled`. |
| **Accessible depuis** | *Cet ordinateur seulement* (par défaut) ou *Le réseau*. Les autres appareils ont aussi besoin que l'**accès distant** soit activé ; sinon la page vous l'indique (avec un lien). De l'extérieur, l'API répond `403 api_local_only` quand le réglage est *Cet ordinateur seulement*. |
| **Autoriser les pages web d'autres adresses** | Les pages de navigateur ouvertes depuis une autre adresse peuvent appeler l'API (CORS, section 8). Activé par défaut. |
| **Vues d'état (image / web)** | Interrupteur pour les vues de la section 11. Activé par défaut (chacune nécessite un jeton). |
| **Connectés actuellement (WebSocket)** | Liste des appareils connectés par le WebSocket en ce moment (jeton, adresse, ce qu'ils reçoivent, joystick actif, messages par seconde) – en direct, avec **Déconnecter**. |
| **Nouveau jeton** | Crée un jeton. Une grande boîte de dialogue permet de choisir les autorisations en trois colonnes : *Lecture*, *Exploitation*, *Modifier le show*. |
| **Modifier** | Changer le nom et les autorisations. |
| **Interrupteur Actif** | Désactive puis réactive un jeton sans le supprimer (`403 token_disabled` tant qu'il est désactivé). |
| **Générer un nouveau jeton** (dans *Modifier*) | Remplace le secret. L'ancien jeton cesse de fonctionner dès que vous enregistrez. |
| **Supprimer** | Demande dans une boîte de dialogue à part (désactivable, voir *Valeurs par défaut → Suppression*) puis supprime le jeton **aussitôt**. |
| **Dernière utilisation** | Montre quand un jeton a été utilisé pour la dernière fois. |

Un **nouveau jeton** est créé et affiché aussitôt, une **suppression** s'applique aussitôt après la question. Tout le reste est un **brouillon** comme dans tous les paramètres (interrupteur, modification, régénération) : les lignes modifiées sont marquées et comptées, seul **Enregistrer** applique tout (la boîte de dialogue reste ouverte), *Fermer* abandonne après une question. Les jetons ne peuvent être gérés que sur l'ordinateur de la console lui-même, pas depuis des appareils distants.

Seul un **hachage** du jeton est enregistré sur le disque, jamais le jeton lui-même.

### Les autorisations

**Lecture**

| Autorisation | Permet | Par défaut |
|---|---|---|
| **Statut** | État : nom du show, blackout, grand master, code temporel, sélection, programmeur, analyse audio, sorties, le flux d'événements en direct | activée |
| **Données du show** | Projecteurs, types de projecteurs, groupes, variables, effets, scripts d'effets, fichiers de show, listes de cues et cues, médias, dispositions | activée |
| **Sortie DMX** | Valeurs DMX actuelles et état en direct de chaque projecteur | activée |

**Exploitation**

| Autorisation | Permet | Par défaut |
|---|---|---|
| **Commandes de la console** | Exécuter n'importe quelle commande de la ligne de commande (peut aussi modifier et supprimer des données du show) – *critique* | activée |
| **Listes de cues** | Go, Back, saut vers un cue, pause, reprise, arrêt, fader | activée |
| **Code temporel** | Démarrer, pause, arrêt, saut, vitesse | activée |
| **Blackout et master** | Activer le blackout, régler le grand master | activée |
| **Audio** | Ouvrir / fermer la source audio, modifier ses réglages, taper le tempo | activée |
| **Programmeur et sélection** | Sélectionner des projecteurs, régler des valeurs et variables en direct, vider le programmeur | activée |
| **Boutons, faders, interrupteurs de la console** | Presser, déplacer et basculer les panneaux Bouton, Fader et Interrupteur de la console (ils exécutent les commandes qui y sont configurées) | activée |
| **Régler le DMX directement** | Écrire des canaux DMX – prime sur le show en cours – *critique* | **désactivée** |

**Modifier le show**

| Autorisation | Permet | Par défaut |
|---|---|---|
| **Listes de cues et cues** | Créer, modifier, copier, renuméroter et supprimer des listes de cues et des cues ; enregistrer le programmeur comme cue | **désactivée** |
| **Variables** | Créer, modifier et supprimer des variables et des groupes de variables | **désactivée** |
| **Effets** | Créer, modifier et supprimer des effets et des groupes d'effets ; démarrer et arrêter des effets sur des projecteurs | **désactivée** |
| **Scripts d'effets** | Vérifier, enregistrer et supprimer des types d'effets (fichiers de script) | **désactivée** |
| **Patch et groupes de projecteurs** | Patcher, modifier et supprimer des projecteurs ; gérer les groupes de projecteurs ; installer et retirer des types de projecteurs GDTF – *critique* | **désactivée** |
| **Fichiers de show** | Nouveau, charger, enregistrer, renommer, copier et supprimer des fichiers de show – *critique* | **désactivée** |
| **Médias** | Téléverser, renommer et supprimer des fichiers vidéo et audio | **désactivée** |
| **Dispositions** | Afficher une disposition de panneaux enregistrée dans la fenêtre de la console | **désactivée** |
| **Sorties DMX et langue** | Activer Art-Net, sACN et DMX USB, changer les adresses, l'univers par défaut, la langue – *critique* | **désactivée** |

**Préréglages** dans la boîte de dialogue : *Lecture seule* (les trois autorisations de lecture), *Exploitation* (lecture plus listes de cues, code temporel, blackout/master, audio, programmeur et boutons / faders / interrupteurs de la console – pas de commandes, pas de DMX direct), *Modifier le show* (Exploitation plus listes de cues et cues, variables, effets), *Accès complet* et *Par défaut*.

---

## 4. Règles pour toutes les requêtes

- **Connexion :** envoyez le jeton sous la forme `Authorization: Bearer oc_…`. L'en-tête `X-API-Key: oc_…` fonctionne aussi.
- **Format :** les requêtes avec un corps utilisent le JSON et `Content-Type: application/json`. Les réponses sont toujours en JSON (sauf le flux d'événements et les téléchargements de fichiers).
- **Choisir des éléments :**
  - un *projecteur* par son **numéro (FID)**, son id ou un nom sans ambiguïté ; un *groupe* de projecteurs par son nom ;
  - une *liste de cues* par son **nom** ou son id ; un *cue* par son **numéro** (par exemple `1.5`) ou son id ;
  - une *variable*, un *effet* ou un *fichier de show* par son **nom** (majuscules / minuscules sans importance) ou son id.
  - Les noms avec espaces doivent être encodés en URL dans le chemin (`Par%20links`).
- **Choisir plusieurs projecteurs** dans un corps : `"fixtures": [1, 2, "Front"]`, `"fixture": 3` et / ou `"group": "Wash"`. Pour les appels du programmeur, `"selection": true` désigne les projecteurs sélectionnés sur la console, et un appel sans aucun de ces champs utilise la sélection.
- **Pourcentages et octets :** gradateur, position et similaires s'expriment en **pourcentage (0–100)**, les canaux DMX bruts en **0–255**, les couleurs sous la forme `"#rrggbb"`, `[r, g, b]` ou `{"r": …, "g": …, "b": …}` (0–255).
- **Durées** en secondes ; le code temporel en secondes ou en texte (`00:01:04.300`).
- **Contrôles de saisie rigoureux :** un champ qui n'existe pas est rejeté (`422`), une valeur ou un nom erroné donne `400`, un nom déjà pris donne `409 duplicate`. Rien n'est deviné ni ignoré en silence.
- **Vérifié avant toute modification :** un appel avec une valeur, un nom ou un projecteur erroné est refusé en bloc – un cue avec un projecteur erroné n'est pas enregistré à moitié.

### Erreurs

Les erreurs ont toujours le même aspect :

```json
{ "error": { "code": "not_found", "message": "No fixture '99' (use the fixture number, id or an unambiguous name)." } }
```

| HTTP | `code` | Signification |
|---|---|---|
| 400 | `bad_request` | La requête est erronée (valeur hors plage, attribut inconnu, commande vide …) |
| 401 | `unauthorized` | Jeton manquant ou invalide |
| 403 | `forbidden` | Le jeton n'a pas l'autorisation pour cette fonction |
| 403 | `token_disabled` / `api_disabled` | Le jeton ou toute l'API est désactivé |
| 404 | `not_found` | Le projecteur, la liste de cues, le cue, la variable, l'effet, le fichier de show … n'existe pas |
| 409 | `duplicate` | Le nom est pris (liste de cues, variable, effet, groupe …) |
| 409 | `cue_exists` | Un cue portant ce numéro existe – envoyez `on_conflict` (`merge` / `overwrite`) |
| 409 | `address_conflict` | Les adresses DMX chevauchent un autre projecteur – `allow_overlap: true` patche quand même |
| 409 | `unsaved_changes` | Le show a des modifications non enregistrées – enregistrez-le, ou envoyez `force: true` |
| 409 | `exists` / `in_use` / `never_saved` | Un fichier de show ou un script de ce nom existe / le fichier de show est celui qui est chargé / le show n'a pas encore de fichier |
| 409 | `no_active_cue` / `programmer_empty` | *Update* sans cue actif ou avec un programmeur vide |
| 409 | `audio_failed` | La source audio n'a pas pu être ouverte (la raison est dans le message) |
| 415 | `invalid_type` | Un téléversement de média qui n'est pas un fichier vidéo / audio pris en charge |
| 422 | `invalid` | Un champ manque, est inconnu ou a un mauvais type |
| 422 | `invalid_script` | Un script ne compile pas ou échoue à son essai (avec la ligne) |
| 429 | `rate_limited` | Trop de mauvais jetons depuis cette adresse – attendez le délai indiqué dans `Retry-After` |

Une **commande de console rejetée** (par exemple une faute de frappe) n'est *pas* une erreur HTTP : la réponse est `200` avec `"success": false` et le message de la ligne de commande.

---

## 5. Aperçu des points d'accès

Tous les chemins commencent par `/api/v1`. L'autorisation dans la colonne de droite est ce dont le jeton a besoin. Dans les chemins, `{list}` est une liste de cues, `{cue}` un cue, `{fixture}` un projecteur, `{ref}` une variable / un effet / un nom.

### Lecture

| Méthode | Chemin | Renvoie | Autorisation |
|---|---|---|---|
| GET | `/` | Index : version, liens, ce que ce jeton peut faire | Statut |
| GET | `/status` | État global : show, blackout, master, code temporel, sélection, liste de cues active, sorties DMX, nombres | Statut |
| GET | `/blackout` · `/master` · `/timecode` · `/selection` | Une partie de l'état | Statut |
| GET | `/system` | Version, langue, sorties DMX (Art-Net, sACN, USB), univers, accès distant, dossier de données | Statut |
| GET | `/showfile` | Nom du show chargé, s'il a des modifications non enregistrées et un fichier | Statut |
| GET | `/programmer` | Sélection, valeurs réglées à la main (pourcentage, couleur + hex, canaux bruts), variables qu'elles suivent, effets en cours | Statut |
| GET | `/audio` · `/audio/devices` | L'analyse audio en direct et les réglages / chaque entrée audio | Statut |
| GET | `/system/usb-ports` · `/command/suggest?text=` | Ports série pour le DMX USB / complétions pour une commande (comme Tab dans la ligne de commande) | Statut |
| GET | `/events` | **Flux en direct** des changements (Server-Sent Events, section 6) | Statut |
| GET | `/fixtures` | Tous les projecteurs. Facultatifs : `?universe=`, `?group=`, `?include_state=true` | Données du show |
| GET | `/fixtures/{fixture}` | Un projecteur avec chaque canal (adresse, valeur DMX actuelle) et son état | Données du show |
| GET | `/fixture-types` | La bibliothèque de projecteurs : id, nom, fabricant, modes avec nombre de canaux (`?q=` filtre) | Données du show |
| GET | `/groups` · `/variable-groups` · `/effect-groups` | Groupes de projecteurs, groupes de variables, groupes d'effets | Données du show |
| GET | `/variables` · `/variables/{ref}` | Toutes les variables / une (avec le nombre d'entrées de cues qui l'utilisent) | Données du show |
| GET | `/effects` · `/effects/{ref}` · `/effects/assignments` | Effets / un effet avec les infos de son type / quel effet tourne sur quel projecteur | Données du show |
| GET | `/effect-scripts` · `/effect-scripts/{name}` | Tous les types d'effets (catégorie, étiquettes, réglages) / le texte source d'un type | Données du show |
| GET | `/cuelists` · `/cuelists/{list}` | Toutes les listes de cues avec cue actif, fader et état de lecture / une liste avec tous ses cues | Données du show |
| GET | `/cuelists/{list}/cues` | Les cues d'une liste ; `?detail=true` ajoute **ce que chaque cue modifie** | Données du show |
| GET | `/cuelists/{list}/cues/{cue}` | Un cue en détail complet | Données du show |
| GET | `/showfiles` | Noms des fichiers de show enregistrés (et celui qui est chargé) | Données du show |
| GET | `/media` · `/media/{id}/file` | Les médias du show / en télécharger un | Données du show |
| GET | `/layouts` | Dispositions enregistrées de la console | Données du show |
| GET | `/widgets` | Les panneaux Bouton / Fader / Interrupteur de la console : commandes, limites et valeur du fader, état de l'interrupteur | Données du show |
| GET | `/dmx` · `/dmx/{universe}` | Les univers et leurs valeurs (`?first=&last=`, `?nonzero=true`) | Sortie DMX |
| GET | `/fixtures/state` | L'état en direct de **chaque** projecteur (ce que la console émet en ce moment) | Sortie DMX |

### Exploitation

| Méthode | Chemin | Corps | Autorisation |
|---|---|---|---|
| POST | `/command` | `{"command": "Fixture 1 At 80"}` | Commandes de la console |
| POST | `/commands` | `{"commands": ["…", "…"], "stop_on_error": false}` – jusqu'à 100 | Commandes de la console |
| POST | `/cuelists/{list}/go` | `{"cue": "2"}` facultatif (sans : le cue suivant) | Listes de cues |
| POST | `/cuelists/{list}/back` · `/pause` · `/resume` · `/stop` | – | Listes de cues |
| PUT | `/cuelists/{list}/fader` | `{"value": 70}` (pourcentage) | Listes de cues |
| PUT | `/timecode` | `{"action": "play" \| "pause" \| "stop" \| "seek" \| "rate", "position": …, "direction": 1, "rate": 1}` | Code temporel |
| PUT | `/blackout` | `{"enabled": true}` (sans valeur : bascule) | Blackout et master |
| PUT | `/master` | `{"value": 80}` (pourcentage) | Blackout et master |
| PUT | `/audio` | `{"running": true, "device": "demo", "settings": {"mode": "manual", "bpm": 128}}` – chaque champ facultatif | Audio |
| POST | `/audio/tap` | – (un tap du bouton de tempo) | Audio |
| PUT | `/selection` | `{"fixtures": [1, 2], "mode": "set" \| "add" \| "remove" \| "clear"}` (aussi `group`) | Programmeur et sélection |
| PUT | `/programmer/values` | `{"fixtures": [1, 2], "values": {"dimmer": 80, "color": "#ff0000"}}` | Programmeur et sélection |
| POST | `/programmer/variables` | `{"variable": "Warm white", "fixtures": [1, 2]}` – applique et lie une variable | Programmeur et sélection |
| POST | `/widgets/{id}/press` | – (exécute la commande d'un bouton) | Boutons, faders, interrupteurs de la console |
| PUT | `/widgets/{id}/value` | `{"value": 70}` (fader ; limité à son minimum / maximum, arrondi) | Boutons, faders, interrupteurs de la console |
| PUT | `/widgets/{id}/state` | `{"on": true}` (interrupteur ; sans valeur il bascule) | Boutons, faders, interrupteurs de la console |
| POST | `/programmer/clear` | `{"fixtures": [1]}` oublie leurs valeurs ; `{"all": true}` = *Clear Clear* : tout dans le noir | Programmeur et sélection |
| PUT | `/dmx/{universe}/{channel}` | `{"value": 255}` ou `{"percent": 100}` | Régler le DMX directement |
| PUT | `/dmx/{universe}` | `{"channels": {"1": 255, "2": 0}}` | Régler le DMX directement |
| PUT | `/fixtures/{fixture}/channels/{channel}` | `{"value": 128}` ou `{"percent": 50}` ; `{channel}` est le numéro de canal du projecteur (1 = premier) ou son nom (`Dimmer`) | Régler le DMX directement |

### Modifier : listes de cues et cues – autorisation *Listes de cues et cues*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/cuelists` | `{"name": "Act 1"}` | Crée une liste de cues (201) |
| PUT | `/cuelists/{list}` | `{"name": "…", "active": true}` | Renomme ; `active` en fait la liste affichée par les panneaux de listes de cues |
| PUT | `/cuelists/order` | `{"order": ["Act 2", "Act 1"]}` | Ordre des listes |
| POST | `/cuelists/{list}/duplicate` | `{"name": "Copy"}` | Copie avec tous les cues |
| DELETE | `/cuelists/{list}` | – | Supprime la liste |
| POST | `/cuelists/{list}/cues` | voir plus bas | Crée un cue (201) |
| PUT | `/cuelists/{list}/cues/{cue}` | voir plus bas | Modifie les propriétés et / ou le contenu, renumérote |
| DELETE | `/cuelists/{list}/cues/{cue}` | – | Supprime un cue |
| POST | `/cuelists/{list}/cues/delete` | `{"cues": ["1", "2.5"]}` | En supprime plusieurs (tous ou aucun) |
| POST | `/cuelists/{list}/cues/{cue}/duplicate` | `{"number": 9, "name": "…"}` | Copie un cue |
| POST | `/cuelists/{list}/update-active` | `{"mode": "normal" \| "only"}` | Reprend le programmeur dans le cue actif (comme *Update*) |

**Corps d'un cue** (création et modification ; chaque champ est facultatif lors d'une modification) :

| Champ | Signification |
|---|---|
| `number` | Numéro du cue, décimales autorisées. Omis à la création : le prochain numéro libre. |
| `name`, `fade`, `delay` | Nom et durées générales en secondes |
| `trigger` | `go` · `follow` · `timecode` · `audio` · `midi` · `clock` |
| `timecode` | Pour `timecode` : secondes ou `1:04.300` |
| `audio` | Pour `audio` : `{"source": "beat" \| "kick" \| "snare" \| "hat" \| "level" \| "bass" \| "mid" \| "high" \| "b1" … "b8", "value": 4}` (un coup sur n, ou un seuil en %) |
| `midi` | Pour `midi` : `{"type": "note" \| "cc" \| "pc", "number": 60, "channel": 0, "value": 64}` – le cue se déclenche à l'arrivée de ce signal lorsqu'il est le cue suivant d'une liste en cours ; `channel` 0 = tous (1–16 = un canal), `value` = le seuil d'un `cc` (1–127) |
| `clock` | Pour `clock` : `{"time": "19:30", "days": "Mon-Fri"}` (ou `"days": [0,1,2,3,4]`, lundi = 0 ; vide = tous les jours) – le cue attend, en tant que cue suivant d'une liste en cours, cette heure de l'horloge murale. |
| `mib`, `command` | Move in black (`Off` / `Auto` / `On`) ; commandes de console exécutées avec le cue |
| `times` | Durées propres par groupe : `{"color": {"fade": 2, "delay": 0}, "position": {…}, "beam": {…}, "zoom": {…}}` ; `null` = utiliser de nouveau la durée générale |
| `effect_fade` | `{"in": 1, "out": 2}` |
| `changes` | Ce que le cue modifie (ci-dessous) |
| `effects` | Les effets que le cue démarre : `[{"fixtures": [2, 3], "effects": {"dimmer": "Strobe"}}]` (catégorie → nom de l'effet) |
| `from_programmer` | *(création)* enregistre aussi ce qui est dans le programmeur **et chaque changement de l'image par rapport au cue précédent** (comme *Store Cue* ; si rien n'a changé : `409 nothing_changed`) ; `clear_programmer` le vide ensuite |
| `on_conflict` | *(création / renumérotation)* le numéro existe : `merge` (seuls les attributs envoyés rejoignent le cue existant) ou `overwrite` |
| `content` | *(modification)* `merge` (par défaut) ou `replace` : le contenu du cue est exactement ce qui est envoyé |

`changes` est une liste ; chaque entrée nomme des projecteurs et ce qu'ils reçoivent :

```json
{ "fixtures": [2, 3], "values": { "dimmer": 80, "color": "#00ff00", "pan": 40 }, "variables": { "color": "Warm white" } }
```

`values` : `dimmer`, `pan`, `tilt`, `strobe`, `gobo`, `gobo_spin`, `gobo2`, `gobo2_spin`, `prism`, `focus`, `zoom` en pourcentage, `color`, canaux bruts `ch<N>` (0–255). `variables` associe un type (`dimmer`, `position`, `color`, `focus`, `zoom`, `gobo`) à une variable : le cue **renvoie alors à la variable** (un marqueur, résolu en direct quand le cue s'exécute) au lieu d'enregistrer la valeur.

### Modifier : variables – autorisation *Variables*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/variables` | `{"name": "Warm white", "type": "color", "group": "Colours", "values": {"hex": "#ffb060"}}` | Crée |
| PUT | `/variables/{ref}` | `{"name": "…", "group": "…", "values": {…}}` | Modifie ; le type ne peut pas changer. Une nouvelle valeur atteint le programmeur, les cues en cours et **chaque cue qui utilise la variable** |
| DELETE | `/variables/{ref}` | – | Supprime (les liens du programmeur sont libérés) |
| POST · DELETE | `/variable-groups` · `/variable-groups/{name}` | `{"name": "Colours"}` | Crée / supprime un groupe (ses variables restent) |

`values` par type : `dimmer`, `focus`, `zoom` : `{"level": 0-100}` · `position` : `{"pan": 0-100, "tilt": 0-100}` · `color` : `{"r","g","b"}` ou `{"hex": "#ff8000"}` · `gobo` : `{"level", "spin", "gobo2", "gobo2_spin"}`.

### Modifier : effets – autorisation *Effets*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/effects` | `{"script": "strobe", "name": "Blink", "group": "…", "params": {"rate_hz": 8}}` | Crée un effet à partir d'un type d'effet (`GET /effect-scripts`) ; `params` sont vérifiés par rapport aux limites du type |
| PUT | `/effects/{ref}` | `{"name", "group", "params"}` | Modifie (le type ne peut pas changer) |
| DELETE | `/effects/{ref}` | – | Supprime ; il s'arrête partout |
| POST | `/effects/{ref}/assign` | `{"fixtures": [2, 3]}` (aussi `group`) | **Démarre** l'effet sur des projecteurs (l'ordre répartit les vagues) |
| POST | `/effects/release` | `{"fixtures": [2], "categories": ["dimmer"]}` | **Arrête** les effets sur des projecteurs (les valeurs restent) |
| POST · DELETE | `/effect-groups` · `/effect-groups/{name}` | `{"name": "…"}` | Crée / supprime un groupe |

### Modifier : scripts d'effets – autorisation *Scripts d'effets*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/effect-scripts/check` | `{"text": "…"}` | Compile et fait un essai d'un script sans l'enregistrer : `{ok, line, message}` |
| POST | `/effect-scripts/preview` | `{"text": "…", "count": 3, "duration": 4, "bpm": 120, "params": {…}}` | Simule les courbes sans projecteurs |
| PUT | `/effect-scripts/{name}` | `{"text": "…", "overwrite": false}` | Enregistre comme fichier dans le dossier d'effets de l'utilisateur – **seulement s'il compile et s'exécute** (`422 invalid_script` avec la ligne). Un nom existant demande `overwrite` |
| DELETE | `/effect-scripts/{name}` | – | Supprime un script du dossier utilisateur ; les effets de ce type s'arrêtent |

Le langage de script est décrit dans le guide *Atelier d'effets*.

### Modifier : patch et groupes de projecteurs – autorisation *Patch et groupes de projecteurs*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/fixtures` | `{"type": "Generic RGBW LED Par", "mode": "…", "name": "Par", "quantity": 4, "universe": 1, "address": 11, "group": "Wash"}` | Patche un ou plusieurs projecteurs les uns après les autres. Les adresses sont vérifiées (elles doivent tenir dans 512 et ne pas se chevaucher – `allow_overlap: true` force) |
| PUT | `/fixtures/{fixture}` | `{"name", "universe", "address", "sort_index", "group", "allow_overlap"}` | Modifie ; `"group": ""` le sort de son groupe |
| DELETE | `/fixtures/{fixture}` · POST `/fixtures/delete` | `{"fixtures": [1, 2]}` | Supprime (les cues gardent leurs entrées pour le projecteur manquant, comme dans la fenêtre) |
| POST | `/groups` | `{"name": "Wash", "fixtures": [2, 3]}` | Crée un groupe de projecteurs |
| POST | `/fixture-types` | le fichier `.gdtf` brut ; en-tête `X-Filename` (encodé en URL) | Installe un type de projecteur (jusqu'à 30 Mo ; vérifié avant l'installation) |
| DELETE | `/fixture-types/{id}` | – | Retire un type installé (`409 in_use` tant que le show l'utilise) |
| PUT · DELETE | `/groups/{name}` | `{"name": "…", "fixtures": […]}` | Renomme / définit les membres (remplace la liste) / supprime (les projecteurs restent) |

### Modifier : fichiers de show – autorisation *Fichiers de show*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/showfile/new` | `{"force": false}` | Démarre un nouveau show vide |
| POST | `/showfile/save` | – | Enregistre sous le nom actuel (`409 never_saved` s'il n'a pas encore de fichier) |
| POST | `/showfile/save-as` | `{"name": "Concert", "overwrite": false}` | Enregistre sous un nom (les caractères interdits dans les noms de fichiers sont retirés) |
| POST | `/showfile/load` | `{"name": "Concert", "force": false}` | Charge un show enregistré – remplace celui en cours |
| POST | `/showfiles/{name}/rename` | `{"new_name": "…", "overwrite": false}` | Renomme un fichier enregistré |
| POST | `/showfiles/{name}/duplicate` | – | Copie un fichier enregistré |
| DELETE | `/showfiles/{name}` | `?force=true` pour celui qui est chargé | Supprime un fichier enregistré |

**Nouveau** et **Charger** remplacent le show en cours. Avec des modifications non enregistrées, ils sont refusés avec `409 unsaved_changes` jusqu'à ce que vous enregistriez d'abord ou envoyiez `"force": true`.

### Modifier : médias – autorisation *Médias*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/media` | le fichier brut ; en-tête `X-Filename` (encodé en URL) | Téléverse un fichier vidéo / audio (jusqu'à 1 Go ; le même fichier deux fois ne fait qu'une entrée) |
| PUT | `/media/{id}` | `{"name": "…"}` | Renomme |
| DELETE | `/media/{id}` | – | Retire du show et supprime la copie |

### Modifier : dispositions et paramètres – autorisations *Dispositions* et *Sorties DMX et langue*

| Méthode | Chemin | Corps | Ce que cela fait |
|---|---|---|---|
| POST | `/layouts/{filename}/load` | – | Affiche une disposition enregistrée (`Name.json` comme dans `GET /layouts`) dans la fenêtre de la console ; les modifications de disposition non enregistrées y sont perdues |
| PUT | `/system` | `{"artnet": {"enabled": true, "ip": "2.255.255.255", "bind_ip": ""}, "sacn": {"enabled": true}, "enttec": {"enabled": false, "port": "COM3", "universe": 1}, "default_universe": 1, "language": "de"}` – chaque champ facultatif | Active les sorties DMX et change la langue / l'univers par défaut ; la réponse est `GET /system` |
| POST | `/system/dmx/reinitialize` | – | Redémarre les sorties DMX sans redémarrer le programme |

### Documentation (sans jeton)

| Méthode | Chemin | Renvoie |
|---|---|---|
| GET | `/docs` | Un aperçu lisible et consultable de toutes les routes (fonctionne hors ligne) |
| GET | `/openapi.json` | La description lisible par machine (OpenAPI 3.1) ; chaque route indique son autorisation sous `x-capability` |

---

## 6. Exemples avec de vraies réponses

### État

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

### Quels projecteurs sont dans le show, et de quelle couleur sont-ils ?

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

`state` contient exactement ce que la console émet actuellement, lu dans le tampon DMX : `dimmer`, `pan`, `tilt`, `zoom`, `focus` … en pourcentage et `color` en r/g/b. Les attributs qu'un projecteur n'a pas sont absents. (À un grand master de 0 ou en blackout, le gradateur ne peut pas être reconstitué et est omis.)

### Un projecteur avec tous ses canaux

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

### Que modifie un cue ?

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

- `fade` / `delay` sont les durées générales ; `times` contient les durées facultatives par groupe d'attributs (`null` = utilise la durée générale).
- `changes[].values` sont les valeurs fixes enregistrées dans le cue. `variables` liste les variables (marqueurs) auxquelles le cue renvoie, par type et nom – une variable est résolue en direct quand le cue s'exécute.
- `effects` liste les effets que le cue démarre, par projecteur.
- Tous les cues d'une liste d'un coup avec leurs détails : `GET /api/v1/cuelists/Show/cues?detail=true`.

### Le signal DMX

```
GET /api/v1/dmx/1?first=1&last=14
GET /api/v1/dmx/1?nonzero=true
```

```json
{ "universe": 1, "first": 1, "last": 14, "values": [0,0,0,0,0,0,0,0,0,0,255,0,0,0] }
{ "universe": 1, "first": 1, "last": 512, "channels": { "11": 255 } }
```

### Exécuter une commande de console

```
POST /api/v1/command
{ "command": "Fixture 1 Thru 4 At 80" }
```

```json
{ "command": "Fixture 1 Thru 4 At 80", "success": true, "message": "OK: 4 fixtures selected; At 80 applied" }
```

Toutes les commandes de la ligne de commande fonctionnent, aussi enchaînées avec `;` (voir le guide *Référence des commandes*).

### Déclencher un cue

```
POST /api/v1/cuelists/Show/go            { "cue": "2" }
```

```json
{ "cuelist": { "id": "7e5d274f-…", "name": "Show" }, "command": "Cuelist \"Show\" Go Cue 2", "success": true, "message": "OK: Go Cue 2 [Show]" }
```

Sans corps, `go` démarre le cue suivant. Remarque : une liste de cues dont le **nom contient un guillemet** ne peut pas être adressée ainsi ; renommez-la.

### Code temporel

```
PUT /api/v1/timecode   { "action": "seek", "position": "1:04.300" }
PUT /api/v1/timecode   { "action": "play", "position": 10 }
GET /api/v1/timecode
```

```json
{ "running": false, "direction": 1, "rate": 1.0, "position_ms": 64300.0, "position": "00:01:04.300" }
```

`position` est un nombre en **secondes** ou un texte comme `1:04.300` ou `00:00:04.300`. `play` peut démarrer depuis une `position` et tourner à l'envers avec `"direction": -1` ; `rate` est la vitesse entre 0,1 et 8. Un saut avec `seek` ne déclenche pas les cues de code temporel.

### Régler des canaux DMX

```
PUT /api/v1/dmx/1/200                      { "value": 255 }
PUT /api/v1/dmx/1                          { "channels": { "201": 10, "202": 20 } }
PUT /api/v1/fixtures/Front/channels/Dimmer { "percent": 50 }
```

```json
{ "universe": 1, "channel": 1, "value": 128, "fixture": { "fid": 1, "name": "Front" }, "channel_of_fixture": 1 }
```

Un canal qui appartient à un **projecteur** est réglé comme le fader *DMX direct* du programmeur : il devient une valeur manuelle que les cues en cours ne mélangent plus. Les autres canaux sont écrits directement dans la sortie. Cette autorisation est **désactivée par défaut**.

### Audio : lire et piloter

```
GET  /api/v1/audio/devices                    -> { "devices": [ { "id": "demo", "kind": "demo", "name": "Demo beat" }, ... ] }
PUT  /api/v1/audio    { "device": "demo" }    open that source (`running` false closes it)
PUT  /api/v1/audio    { "settings": { "mode": "manual", "bpm": 128, "sensitivity": 0.7 } }
POST /api/v1/audio/tap                        tap the tempo (about 4 taps in a row set it, the tempo switches to manual)
GET  /api/v1/audio                            level, bands, kick / snare / hat, bpm, beat_phase ... and the settings
```

`PUT /audio` applique d'abord les `settings`, puis ouvre (`running: true`, ou un `device`) ou ferme (`running: false`) la source, et répond comme `GET /audio`. Si la source ne peut pas être ouverte, la réponse est `409 audio_failed` avec la raison. Réglages : `gain`, `auto_gain`, `sensitivity`, `smoothing`, `latency_ms`, `mode` (`auto` | `manual`), `bpm` (tempo manuel), `phase_follow`, `demo_bpm`, `autostart` ; les clés inconnues sont ignorées et les nombres sont limités à leur plage.

### Construire un cue

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

La réponse est le cue entier tel que `GET …/cues/3` le montrerait. Si le cue 3 existe, vous obtenez `409 cue_exists` ; envoyez `"on_conflict": "merge"` pour y ajouter les attributs envoyés, ou `"overwrite"` pour remplacer son contenu (statut `merged` / `overwritten`).

La même chose depuis le programmeur, comme *Store Cue* :

```
PUT  /api/v1/programmer/values   { "fixtures": [2, 3], "values": { "color": "#ff8000", "dimmer": 100 } }
POST /api/v1/cuelists/Show/cues  { "number": 4, "name": "Orange", "from_programmer": true, "clear_programmer": true }
```

### Modifier et supprimer des cues

```
PUT    /api/v1/cuelists/Show/cues/3   { "name": "Deep blue", "fade": 5, "times": { "color": { "fade": 8 } } }
PUT    /api/v1/cuelists/Show/cues/3   { "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] }                       (adds to the content)
PUT    /api/v1/cuelists/Show/cues/3   { "content": "replace", "changes": [ { "fixtures": [1], "values": { "dimmer": 0 } } ] } (content = exactly this)
PUT    /api/v1/cuelists/Show/cues/3   { "number": 2.5 }                                                                          (renumber)
DELETE /api/v1/cuelists/Show/cues/3
```

Seul ce que vous envoyez change. Une modification d'un cue en cours de lecture prend effet à son prochain *Go*.

### Variables et effets

```
POST /api/v1/variables  { "name": "Warm white", "type": "color", "values": { "hex": "#ffb060" } }
PUT  /api/v1/variables/Warm white   { "values": { "hex": "#ffa040" } }      -> every cue that uses it is warmer now
POST /api/v1/effects    { "script": "strobe", "name": "Blink", "params": { "rate_hz": 8 } }
POST /api/v1/effects/Blink/assign   { "fixtures": [2, 3] }                  -> it runs now
POST /api/v1/effects/release        { "fixtures": [2, 3] }                  -> stop it
```

`GET /api/v1/effect-scripts` liste les types d'effets avec leurs réglages (`variables` : nom, genre, limites, valeur par défaut, étiquettes dans les deux langues).

### Écrire votre propre type d'effet

```
POST /api/v1/effect-scripts/check   { "text": "…" }                  -> { "ok": false, "line": 3, "message": "…" }
PUT  /api/v1/effect-scripts/my_wave { "text": "…", "overwrite": true }
POST /api/v1/effects                { "script": "my_wave" }
```

Un script n'est enregistré que s'il compile et s'exécute. Le langage est documenté dans le guide *Atelier d'effets*.

### Patcher des projecteurs

```
GET  /api/v1/fixture-types?q=par
POST /api/v1/fixtures  { "type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "universe": 1, "address": 11, "group": "Wash" }
```

```json
{ "created": [ { "fid": 4, "name": "Par 1", "universe": 1, "start_channel": 11, "end_channel": 14, … },
               { "fid": 5, "name": "Par 2", "universe": 1, "start_channel": 15, … }, … ] }
```

Les adresses qui chevauchent d'autres projecteurs sont refusées (`409 address_conflict`) ; `"allow_overlap": true` patche quand même.

### Le programmeur

```
GET  /api/v1/programmer
PUT  /api/v1/selection            { "group": "Wash" }
PUT  /api/v1/programmer/values    { "values": { "dimmer": 100, "color": [255, 0, 0] } }       (without fixtures: the selection)
POST /api/v1/programmer/variables { "variable": "Warm white" }
POST /api/v1/programmer/clear     { "fixtures": [2] }          forget their values (the output stays)
POST /api/v1/programmer/clear     { "all": true }              Clear Clear: every fixture dark, effects end
```

Les valeurs réglées ainsi se comportent comme les faders de la fenêtre du programmeur : la sortie change aussitôt, elles comptent comme touchées, et le prochain *Store Cue* les reprend.

### Valeurs relatives (pousser au lieu de régler)

```
curl -X PUT -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/json" \
  -d '{"group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}' \
  http://127.0.0.1:8000/api/v1/programmer/values
```

Avec `"mode": "relative"`, les nombres sont des **changements en points de pourcentage** (−100 à 100) ; chaque projecteur part de sa propre valeur et est limité à 0 / 100 %. Les couleurs et les canaux bruts n'existent qu'en valeurs absolues. Pour des séquences rapides de changements (potentiomètres, joystick), le WebSocket (section 10) est préférable.

### Fichiers de show

```
POST /api/v1/showfile/save-as  { "name": "Concert" }
POST /api/v1/showfile/load     { "name": "Concert", "force": false }
POST /api/v1/showfile/new      { "force": true }
```

Sans `force`, *load* et *new* s'arrêtent avec `409 unsaved_changes` quand le show en cours a des modifications non enregistrées. `GET /api/v1/showfile` indique s'il en a.

### Boutons, faders et interrupteurs de la console

```
GET /api/v1/widgets
POST /api/v1/widgets/b1/press
PUT  /api/v1/widgets/f1/value   { "value": 70 }
PUT  /api/v1/widgets/t1/state   { "on": true }
```

`GET /widgets` liste les panneaux avec leur `id`, `label`, commande et la valeur actuelle (faders) ou l'état (interrupteurs). Presser, déplacer ou basculer exécute la commande configurée dans le panneau – la même qu'un opérateur déclenche – et les panneaux de tous les appareils suivent (un bouton pressé pulse, les faders et interrupteurs avec la même commande bougent aussi). La valeur d'un fader est limitée à son minimum / maximum. Un panneau sans commande répond `409 no_command` (un interrupteur sans commandes ne fait que basculer). Les panneaux sont ceux de la disposition de la **console** ; les appareils distants ont leurs propres dispositions.

### Sorties et dispositions

```
PUT  /api/v1/system   { "artnet": { "ip": "192.168.1.255" }, "sacn": { "enabled": false } }
POST /api/v1/layouts/Concert.json/load
POST /api/v1/fixture-types   (raw .gdtf file, header X-Filename: my_fixture.gdtf)
```

### Téléverser un média

```
curl -X POST -H "Authorization: Bearer oc_xxxxxxxx" -H "Content-Type: application/octet-stream" \
     -H "X-Filename: intro.mp4" --data-binary @intro.mp4 http://127.0.0.1:8000/api/v1/media
```

### Événements en direct (flux)

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

La connexion reste ouverte. Arrivent d'abord `hello` et un message par genre avec l'**état actuel**, puis chaque changement. Genres : `cue` (le cue actif d'une liste a changé), `cuelists` (des listes / cues ont été ajoutés, retirés, renommés), `blackout`, `master`, `timecode` (démarré, arrêté, vitesse), `selection`, `effects`, `fixtures`, `variables`, `show` (nom / modifications non enregistrées), `command` (une commande de console a été exécutée, d'où que ce soit), `audio` (source ouverte / fermée, tempo, signal présent). Seulement sur demande (`?events=beat,hit`) : `beat` (chaque temps, avec le tempo) et `hit` (chaque coup de grosse caisse / caisse claire / charleston : `{"drum": "kick", "strength": 0.9}`). `?events=` limite le flux. Les changements sont détectés en 0,1 s environ. Une ligne de commentaire (`: keep-alive`) arrive toutes les 15 s ; 20 flux au plus tournent en même temps. Nécessite l'autorisation *Statut*.

Dans un navigateur, `EventSource` ne peut pas envoyer d'en-têtes : utilisez plutôt `?access_token=<token>`, ou `fetch()` avec un en-tête et lisez le flux. Le jeton apparaît alors dans l'adresse ; donnez donc à une telle page son propre jeton avec seulement *Statut*.

---

## 7. Petits programmes

Python, avec la bibliothèque `requests` (n'importe quelle bibliothèque HTTP convient) :

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

Construire un petit show (nécessite les autorisations de modification) :

```python
requests.post(f"{BASE}/fixtures", headers=HEAD, json={"type": "Generic RGBW LED Par", "quantity": 4, "name": "Par", "address": 1, "group": "Wash"})
requests.post(f"{BASE}/variables", headers=HEAD, json={"name": "Warm", "type": "color", "values": {"hex": "#ffb060"}})
requests.post(f"{BASE}/cuelists", headers=HEAD, json={"name": "Show"})
requests.post(f"{BASE}/cuelists/Show/cues", headers=HEAD, json={
    "number": 1, "name": "Warm", "fade": 3,
    "changes": [{"group": "Wash", "values": {"dimmer": 80}, "variables": {"color": "Warm"}}]})
requests.post(f"{BASE}/showfile/save-as", headers=HEAD, json={"name": "From the API"})
```

Une page web qui montre le cue actif en direct (JavaScript dans le navigateur ; la page peut provenir de n'importe quelle adresse, voir la section 8) :

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

## 8. Autres appareils et sécurité

- **Depuis un autre ordinateur ou une tablette**, l'API est joignable dès que **Autoriser l'accès par HTTP** (Paramètres → Accès distant) est activé. Utilisez l'adresse de la console (affichée sur cette page) à la place de `127.0.0.1`, par exemple `http://192.168.1.20:8000/api/v1/status`. Avec l'accès distant désactivé, le port est fermé au réseau. Le **jeton remplace le mot de passe** dans ce cas – aucune connexion n'est nécessaire.
- Les jetons donnent un vrai contrôle sur les lumières. Donnez à chaque programme **son propre jeton avec seulement les autorisations dont il a besoin** et supprimez les jetons que vous n'utilisez plus.
- Les **autorisations de modification sont désactivées par défaut** et peuvent changer ou détruire les données du show : *Patch*, *Fichiers de show* et *Commandes de la console* sont marqués **critiques**. *Charger* et *Nouveau* refusent de jeter des modifications non enregistrées sans `force`.
- Le trafic est du HTTP simple à l'intérieur de votre réseau. N'exposez pas le port sur Internet.
- Les **pages web d'autres adresses** (votre propre tableau de bord, un outil web dans le navigateur) peuvent appeler directement l'API : les réponses portent les en-têtes d'accès inter-origines (CORS) et la requête préliminaire du navigateur (`OPTIONS`, qui ne peut pas porter de jeton) reçoit une réponse. La page a toujours besoin d'un jeton dans l'en-tête `Authorization`, et elle doit garder ce jeton pour elle (ne mettez pas de jeton puissant dans une page web publique). Désactivez cela dans *Paramètres → API → Autoriser les pages web d'autres adresses* si vous n'en avez pas besoin ; les navigateurs bloquent alors de nouveau ces pages (les programmes et scripts ne sont pas concernés).
- L'API modifie le show **en mémoire**, comme la fenêtre. Rien n'est écrit sur le disque tant que le show n'est pas enregistré (`POST /showfile/save`, ou *Enregistrer* dans la fenêtre).

---

## 9. Quand quelque chose ne marche pas

| Problème | À vérifier |
|---|---|
| `401 unauthorized` | En-tête écrit `Authorization: Bearer oc_…` avec le jeton complet ? Jeton supprimé ou régénéré ? |
| `403 forbidden` | Le jeton n'a pas cette autorisation – ouvrez le jeton dans *Paramètres → API* et activez-la (le message la nomme). |
| `403 api_disabled` | L'interrupteur principal de *Paramètres → API* est désactivé. |
| `403 remote access disabled` | Vous appelez depuis un autre appareil alors que *Autoriser l'accès par HTTP* est désactivé. |
| `404 not_found` | Vérifiez le numéro de projecteur, le nom de la liste de cues (exactement) et le numéro de cue. |
| `409 duplicate` | Le nom est pris (majuscules / minuscules sans importance). Choisissez un autre nom ou modifiez l'existant avec `PUT`. |
| `409 cue_exists` | Un cue avec ce numéro est dans la liste : `on_conflict` ou `PUT`. |
| `409 unsaved_changes` | Enregistrez d'abord (`POST /showfile/save`) ou envoyez `force: true`. |
| `409 no_command` / `409 wrong_type` | Un panneau n'a pas de commande / vous avez pressé un fader, déplacé un bouton … (voir `GET /widgets` pour le type). |
| `422` | Un champ qui n'existe pas (faute de frappe ?) ou un mauvais type – le message nomme le champ. |
| `422 invalid_script` | Le script contient une erreur – le message nomme la ligne. `POST /effect-scripts/check` teste sans enregistrer. |
| `200` mais `"success": false` | La commande a été rejetée – lisez `message`. |
| `429` | Trop de mauvais jetons depuis cette adresse. Attendez `Retry-After` secondes. |
| Page de navigateur : « bloqué par CORS » | *Paramètres → API → Autoriser les pages web d'autres adresses* est désactivé, ou la requête n'a pas de jeton (la réponse d'erreur de l'API porte les en-têtes, de sorte que la vraie raison est visible). |
| Aucune réponse du tout | OpenCue tourne-t-il, et le port est-il le bon (Paramètres → Accès distant l'indique) ? |

---

## 10. Matériel et pilotage rapide : le flux WebSocket

Pour le **matériel** (ESP32, Arduino, Raspberry Pi, une console maison) et toute application qui envoie ou reçoit **beaucoup de petites valeurs rapidement**, il existe un **WebSocket** à côté des routes HTTP : `ws://<console>:8000/api/v1/ws`. Une connexion reste ouverte et les deux côtés envoient de petits **messages JSON** (trames texte) – sans le coût d'une nouvelle requête HTTP par valeur. Il ne demande aucune autorisation supplémentaire : chaque message nécessite **la même autorisation que la route HTTP correspondante** (tableau ci-dessous). Avec le préréglage *Exploitation*, tout fonctionne sauf le DMX brut.

### Se connecter et s'identifier

Le jeton peut être envoyé de trois façons (les microcontrôleurs trouvent l'adresse le plus facilement) :

1. dans l'adresse : `ws://opencue.local:8000/api/v1/ws?access_token=oc_xxxxxxxx`
2. dans l'en-tête : `Authorization: Bearer oc_xxxxxxxx` (ou `X-API-Key`)
3. comme **premier message** dans les 5 s : `{"op": "auth", "token": "oc_xxxxxxxx"}`

OpenCue envoie ensuite `{"op": "hello", ...}` avec les autorisations, opérations, sujets et limites permis. Les erreurs ferment la connexion avec un code : `4401` (jeton manquant / erroné), `4403` (API désactivée, ce PC seulement, accès distant désactivé, jeton désactivé), `4429` (trop de tentatives échouées / trop de connexions). Les mêmes règles que pour HTTP s'appliquent : *API REST activée*, *Accessible depuis*, blocage après des tentatives échouées. 10 connexions au plus sont ouvertes en même temps.

Chaque message est un objet JSON avec `"op"`. Un **`"id"`** facultatif (n'importe quel nombre ou texte) revient dans la réponse : `{"op": "ack", "id": 7, ...}` en cas de succès, `{"op": "error", "id": 7, "code": "...", "message": "..."}` en cas d'erreur. Sans `id`, seules les erreurs reçoivent une réponse. Un message défectueux ne termine jamais la connexion.

### Messages du matériel

| `op` | Autorisation | Ce que cela fait |
|---|---|---|
| `joystick` | Programmeur | Un joystick – voir plus bas |
| `set` | Programmeur | Régler des valeurs, **absolues** ou **relatives** – voir plus bas |
| `select` | Programmeur | Changer la sélection : `{"op":"select","mode":"set","fixtures":[1,2]}` (`mode` : `set`, `add`, `remove`, `clear`) |
| `cmd` | Commandes | Commande de console : `{"op":"cmd","line":"Cuelist Main Go"}` (réponse : `success`, `message`) |
| `cue` | Cues | `{"op":"cue","list":"Main","action":"go"}` ; `action` : `go` (avec `"cue": 5` il saute), `back`, `pause`, `resume`, `stop`, `fader` (avec `"value"`) |
| `master`, `blackout` | Blackout / Master | `{"op":"master","value":70}`, `{"op":"blackout","on":true}` |
| `dmx` | Canaux DMX | `{"op":"dmx","universe":1,"channels":{"1":255,"2":0}}` – valeurs de canaux brutes comme `PUT /dmx/{universe}` |
| `tap` | Audio | Taper le tempo (un bouton sur l'ESP32) |
| `timecode` | Code temporel | Piloter le code temporel : `{"op":"timecode","action":"play"}` (aussi `pause`, `stop`, `seek`, `rate`) – ou `{"op":"timecode","action":"sync","position":12345,"running":true}` : OpenCue **suit** une horloge extérieure (position en ms ou `"0:12.345"` ; les écarts inférieurs à 60 ms ne sont pas corrigés pour que l'horloge ne tremble pas ; un saut la déplace sans déclencher de cues) |
| `audio_in` | Audio | Audio **entrant** – voir plus bas |
| `subscribe`, `unsubscribe` | selon le sujet | **S'abonner** à des valeurs en direct – voir plus bas |
| `ping` | – | Réponse `{"op":"pong","t":<votre t>,"server_ms":...}` : mesurer l'aller-retour, comparer les horloges |

Les cibles (`set`, `joystick`, `select`) sont nommées comme dans les routes HTTP : `"fixtures": [1, 2, "Front 3"]`, `"fixture": 5`, `"group": "Front"` et / ou `"selection": true` (la sélection de la console). Sans aucune d'elles, la sélection est utilisée.

### Régler des valeurs : absolu et relatif

```json
{"op": "set", "fixtures": [1, 2], "values": {"dimmer": 80, "pan": 25, "color": "#ff8800"}}
{"op": "set", "group": "Front", "mode": "relative", "values": {"pan": 2.5, "dimmer": -10}}
```

- **absolu** (par défaut) : les valeurs sont les nouvelles valeurs – pourcentage 0–100, couleur sous la forme `#rrggbb` / `[r,g,b]`, canaux bruts sous la forme `ch<N>` (0–255).
- **relatif** (`"mode": "relative"`) : les nombres sont des **changements en points de pourcentage** (−100 à 100) ; chaque projecteur part de **sa propre** valeur et est limité à 0 / 100 %. C'est ce qu'il faut pour les potentiomètres rotatifs et les boutons « un peu plus loin ». Les couleurs et les canaux bruts ne peuvent pas être relatifs.

HTTP a la même chose : `PUT /programmer/values` avec `"mode": "relative"`. Pan et tilt sont réglés avec la pleine **résolution 16 bits** (grossier et fin).

### Joystick

```json
{"op": "joystick", "selection": true, "x": 0.35, "y": -0.8}
```

`x` et `y` vont de −1 à 1 (droite / haut positif). Par défaut, il pilote le pan (`x`) et le tilt (`y`) des projecteurs sélectionnés ; `"axes": {"x": "pan", "y": "zoom"}` assigne n'importe quel attribut (`dimmer`, `zoom`, `focus`, `strobe`, `gobo`, `prism` ...). Deux modes (`"mode"`) :

- **`rate`** (par défaut, **relatif**) : la déflexion fixe la **vitesse**, pas la position – comme le joystick du programmeur. Les petites déflexions sont très précises (près du centre environ 1° par seconde), les grandes rapides (tout à l'extérieur, toute la plage défile en quelques secondes) ; la courbe est exponentielle. OpenCue intègre le mouvement **lui-même à 40 Hz** à partir de la dernière déflexion signalée – l'appareil n'a qu'à envoyer les changements et la valeur actuelle toutes les 20–50 ms ; la gigue du WLAN ne rend pas le mouvement saccadé. Plusieurs projecteurs sélectionnés bougent de la même quantité à partir de **leur** valeur de départ ; en fin de plage, ils s'arrêtent. Avec `x = y = 0` (ou dans la zone morte), le manche est relâché : **les projecteurs restent où ils sont**.
- **`position`** (**absolu**) : la déflexion est la position – `x = −1` est pan 0 %, `x = 1` pan 100 %. Peu utile pour un manche à rappel par ressort, mais pour un encodeur ou un curseur.

Autres champs : `stick` (un nom quand un appareil a plusieurs manches ; par défaut `main`, jusqu'à 4), `speed` (facteur 0,05–4 pour la vitesse, par défaut 1), `deadzone` (0–0,5, par défaut 0,04), `timeout_ms` (100–5000, par défaut 500), `invert_y`, `release: true` (relâcher aussitôt). Les cibles sont fixées au premier contact avec le manche et conservées jusqu'à son relâchement.

**Homme mort :** si aucun message n'arrive pendant plus de `timeout_ms` (câble débranché, WLAN disparu, appareil planté), le manche s'arrête et OpenCue signale `{"op":"joystick","stick":"main","state":"timeout"}`. Si la connexion tombe, tous les projecteurs restent où ils sont.

### S'abonner aux valeurs en direct

`{"op":"subscribe","topic":"<topic>","hz":30}` – `hz` est la cadence la plus élevée (1–60, par défaut 30). OpenCue n'envoie que ce qui a **changé**. `unsubscribe` avec `"topic"` termine l'abonnement.

| `topic` | Autorisation | Messages |
|---|---|---|
| `audio` | Statut | `{"op":"audio","t":ms,"running":true,"v":{"a_level":0.62,"a_bass":0.9,"a_bpm":124,...}}` – les variables audio de l'analyse audio ; `"keys": ["a_level","a_bass"]` les limite |
| `dmx` | DMX | `"universes": [1]` (jusqu'à 8) : d'abord `{"op":"dmx","universe":1,"full":true,"values":[512 numbers]}`, ensuite seulement `{"op":"dmx","universe":1,"changes":{"17":255}}` (canal → valeur) |
| `fixtures` | DMX | `{"op":"fixtures","values":{"3":{"pan":12.5,"tilt":50,"dimmer":100,"color":{...}}}}` – valeurs en direct par **numéro** de projecteur, seulement celles qui ont changé |
| `timecode` | Statut | `{"op":"timecode","ms":83400,"text":"00:01:23.400","running":true,"direction":1,"rate":1}` – pendant que l'horloge tourne à chaque tick (jusqu'à 60 Hz), sinon seulement à un changement (démarrage, arrêt, saut, vitesse) |
| `events` | Statut | comme `GET /events` : `{"op":"event","event":"cue","data":{...}}` ; `"events": ["cue","blackout"]` choisit (par défaut : les genres standard ; `beat` et `hit` seulement sur demande). L'état actuel vient en premier |

### Audio entrant : un microphone sur l'ESP32

Avec la source audio **« Réseau (flux API) »**, OpenCue analyse l'audio qu'un appareil envoie – niveau, bandes, grosse caisse / caisse claire / charleston, tempo et temps existent alors comme variables `a_` pour les **effets, les déclencheurs de cues et le panneau Audio** comme d'habitude.

1. Ouvrez la source : choisissez *Réseau (flux API)* dans le panneau Audio, ou `PUT /audio` avec `{"device": "network"}`, ou faites-le avec le message de l'étape 2 (`"open": true`).
2. `{"op":"audio_in","rate":16000,"open":true}` – annonce du PCM (`rate` 8000–48000 Hz, **16 bits signé little endian, mono**).
3. Envoyez ensuite des **trames binaires** (WebSocket binaire) avec les échantillons, p. ex. 20 ms à la fois (640 octets à 16 kHz). 64 Ko au plus par trame.

Si la source n'est pas ouverte, OpenCue répond (au plus une fois par seconde) avec l'erreur `audio_source`. Sans données, l'analyse continue sur le silence.

### Limites et protection

**La sortie DMX a toujours la priorité** : elle tourne dans son propre thread (priorité légèrement supérieure) et le flux est limité – le matériel ne peut donc jamais ralentir la console. 300 messages par seconde au plus par connexion (rafales jusqu'à 600) et 1200 au total – les suivants reçoivent `rate_limited` et sont abandonnés ; messages texte jusqu'à 8 Ko, trames binaires jusqu'à 64 Ko ; 10 connexions ; un joystick change au plus à 40 Hz. Une connexion qui ne s'identifie pas est fermée après 5 s.

### Exemple : ESP32 avec un joystick (Arduino)

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

L'appareil continue d'envoyer `x = 0, y = 0` au repos – cela ne fait aucun mal (le manche compte comme relâché). La sélection sur la console décide de ce qui bouge ; avec `"fixtures": [1, 2]` ou `"group"` à la place de `"selection": true`, la cible est fixe.

### Exemple : Python

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

Une référence de tous les messages se trouve aussi sur la page `/api/v1/docs`.

---

## 11. Vues d'état : images et pages web pour appareils simples

Pour les appareils qui ne savent que **récupérer une image** ou afficher une **page simple** – un ESP32 avec un écran, une vieille tablette comme affichage mural, un onglet de navigateur sur le moniteur du foyer – il existe des **vues d'état**. Elles sont **en lecture seule** (aucune commande), ne nécessitent **aucune bibliothèque** sur l'appareil et OpenCue les génère lui-même : le contenu est le même, sous forme d'image ou de page.

| Vue | Montre | Autorisation |
|---|---|---|
| `status` | show, blackout, master, code temporel, le cue actif de chaque liste, tempo | Statut |
| `timecode` | l'horloge, en grand, « en marche / arrêtée » | Statut |
| `dmx` | les 512 canaux d'un univers sous forme de grille (`?universe=1`), luminosité = valeur | DMX |
| `cue` | le cue actif d'une liste (`?list=Main`) et le suivant | Statut |
| `audio` | niveau, les huit bandes, tempo | Statut |

Chaque vue existe sous plusieurs formes (`GET /api/v1/views/<name>…`) :

| Adresse | Résultat |
|---|---|
| `/views/status` | **page web** qui s'actualise toute seule (`?refresh=2` secondes) ; sans JavaScript par meta refresh |
| `/views/status.png` | **image PNG** (`?w=320&h=240&theme=dark` ; taille de 64×48 à 800×600 ; `theme` : `dark` ou `light`) |
| `/views/status.bmp` | **BMP** 24 bits – tout petit décodeur le comprend |
| `/views/status.rgb565` | **pixels bruts**, 16 bits chacun (5-6-5, octet de poids fort d'abord) ; la taille figure dans les en-têtes `X-Width` / `X-Height` : donnez-les directement à un TFT (aucun décodeur nécessaire) |
| `/views/status.json` | le modèle d'affichage (parties : titre, lignes, barres, grille) – pour ceux qui veulent dessiner eux-mêmes |
| `/views` | liste de toutes les vues avec leurs paramètres |

Connectez-vous comme d'habitude. Un navigateur ou un appareil qui ne peut pas envoyer d'en-tête ajoute le jeton (`access_token`, `token` fonctionne aussi ; les espaces et guillemets emportés lors d'un copier-coller n'ont pas d'importance). Le message indique si le jeton est **manquant** ou **invalide / supprimé** ; la console journalise chaque connexion rejetée. Si le premier chargement de `opencue.local` traîne (Windows résout parfois lentement les noms `.local` la première fois), utilisez l'**adresse IP** – elle figure dans *Paramètres → API REST* (à copier) : `…/views/status?access_token=oc_xxxxxxxx` (le jeton fait alors partie de l'adresse – créez pour cela un jeton séparé **avec seulement « Statut » et « DMX »**). L'interrupteur **Vues d'état** dans *Paramètres → API REST* désactive tout (réponse `403 views_disabled`).

**Couleur :** `?color=green` (ou `amber`, `red`, `blue`, `cyan`, `white`, `magenta`, `violet`, `orange`, `yellow`, ou `#rrggbb`) change la couleur de mise en valeur ; le moniteur DMX est **vert** par défaut.

**Les erreurs sont visibles :** si quelque chose ne va pas (mauvais jeton, vues désactivées, pas d'autorisation), une **image** (`.png` / `.bmp` / `.rgb565`) revient avec le bon code d'état (401, 403 ...) **sous forme d'image avec le message** – un écran l'affiche simplement (« TOKEN MISSING OR WRONG », « STATUS VIEWS ARE OFF » ...) ; la **page web** affiche une page avec le message et se recharge toutes les 5 s. Si OpenCue n'est plus joignable après l'ouverture de la page, la page affiche **« Pas de connexion à OpenCue »** en haut et assombrit la dernière image jusqu'au retour. `.json` conserve le message d'erreur JSON.

**La sortie DMX a toujours la priorité :** les images sont recalculées au plus toutes les 0,4 s par vue et par taille (de nombreux appareils partagent une même image), dans un thread d'arrière-plan, et jamais plus de quatre en même temps. Une image 320×240 coûte environ 6 ms. Le thread de sortie DMX tourne en outre avec une priorité légèrement supérieure.

### ESP32 avec un TFT : une image toutes les deux secondes

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

Pour les appareils à peu de mémoire : choisissez une taille plus petite (`w=160&h=120`) ou transmettez le flux à l'écran ligne par ligne.

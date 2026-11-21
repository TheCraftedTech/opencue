# Accès distant (tablette et téléphone)

Avec l'**accès distant**, vous utilisez OpenCue depuis un iPad, une tablette, un téléphone ou n'importe quel autre ordinateur du **même réseau** – pendant que l'ordinateur console continue de jouer le show et d'envoyer le DMX. Parcourez la salle et ajustez les lumières, lancez des cues depuis la scène, ou utilisez une tablette comme second écran.

L'accès distant est **désactivé par défaut**. Tant qu'il est désactivé, OpenCue n'est pas du tout joignable depuis le réseau (le port est réellement fermé, pas seulement protégé par un mot de passe).

---

## 1. L'idée en une minute

- La **console** est l'ordinateur où OpenCue est installé et fonctionne. Il fait tout le travail : il contient le show, calcule les cues et envoie le DMX.
- Un **appareil distant** n'est qu'un navigateur. Il ouvre une adresse web de la console, se connecte avec le mot de passe et affiche **la même interface OpenCue** – même barre d'outils, mêmes panneaux, mêmes droits.
- Tout reste synchronisé en direct : quand vous sélectionnez un projecteur, déplacez un fader ou appuyez sur *Go* sur un appareil, tous les autres l'affichent aussitôt.
- Aucun Internet n'est nécessaire. Tout se passe dans votre réseau local.

---

## 2. L'activer

1. Sur la console, ouvrez **Paramètres** (barre d'outils) → catégorie **Accès distant**.
2. Activez l'**interrupteur principal de l'accès distant** en haut. **Il n'y a pas de mot de passe par défaut :** la première fois, OpenCue vous demande le vôtre – **« Choisir un mot de passe »**, saisi deux fois (au moins 4 caractères ; *Annuler* désactive à nouveau l'accès distant). **HTTP** est ensuite activé.
3. Le **mot de passe** se définit et se change sous **Paramètres → Sécurité** (bouton *Définir ou changer le mot de passe ...* dans la section Accès distant) ; cela fonctionne aussi depuis un appareil distant (sa propre connexion est conservée ; tous les autres appareils doivent se reconnecter). Utilisez *Afficher* pour vérifier ce que vous avez tapé. Le même mot de passe protège l'écran verrouillé (section 8). Tout mot de passe est permis (au moins 4 caractères) – le choix vous appartient.
4. Vous pouvez modifier le **port HTTP** (1024–65535, 8000 par défaut). Un port modifié prend effet après le redémarrage d'OpenCue.
   **HTTPS** est une section à part ci-dessous avec son propre interrupteur et son propre **port HTTPS** (8001 par défaut, effet immédiat) : certaines fonctions du navigateur exigent une **page sécurisée (https)** : **garder l'écran de l'iPad allumé** (Paramètres → Options suppl. → *Garder l'écran allumé*), le mode VR de la simulation 3D, et le microphone et la caméra dans le navigateur. Ouvrez donc l'**adresse https://** sur l'iPad (confirmez le certificat une fois) ; avec `http://`, seul le réglage de l'appareil « Verrouillage automatique : Jamais » fonctionne. OpenCue crée lui-même le certificat ; le navigateur demande de le confirmer une fois à la première visite. HTTP et HTTPS s'activent et se désactivent indépendamment et ont chacun leur adresse et leur code QR.
   **Nom réseau :** la console est aussi joignable sous `opencue.local` (il vient automatiquement avec l'accès distant ; un petit interrupteur sous *Avancé*), par exemple `http://opencue.local:8000` – l'adresse reste la même dans tous les réseaux. Si le nom est déjà pris (par exemple par une seconde console), OpenCue utilise `opencue-2.local` et ainsi de suite ; les paramètres indiquent lequel s'applique. iPad, iPhone, Mac et Windows 10/11 comprennent le nom d'eux-mêmes. Une web-app installée est liée à son adresse : si vous passez au nom, installez-la encore une fois.
5. Cliquez sur **Enregistrer** (la fenêtre reste ouverte). Aucun redémarrage n'est nécessaire. La première fois, Windows pose une question de pare-feu – autorisez les **réseaux privés**.

OpenCue écoute maintenant sur chaque adresse réseau de la console. La page affiche :

| Élément | Signification |
|---|---|
| **État** | « Joignable sur le réseau » ou « Local seulement ». |
| **Adresses** | Chaque adresse sous laquelle la console est joignable, chacune avec un bouton **Copier**. |
| **Code QR** | Pour l'adresse sélectionnée – scannez-le avec la caméra d'un iPad ou d'un téléphone. Le mot de passe est demandé à la connexion. |
| **Détecter à nouveau les adresses** | Après avoir changé de Wi-Fi ou branché un câble. |

Quand vous le désactivez, les écouteurs sont refermés immédiatement.

> **Pare-feu Windows :** à la première activation de l'accès distant, Windows peut demander si OpenCue peut communiquer sur le réseau. Autorisez-le pour votre réseau **privé** ; sinon les autres appareils ne peuvent pas se connecter.

---

## 3. Connecter un appareil

1. Assurez-vous que l'appareil est dans le **même réseau** (même Wi-Fi ou LAN) que la console.
2. Ouvrez l'adresse de la page des paramètres dans le navigateur de l'appareil – par exemple `http://192.168.1.20:8000/` – ou scannez le code QR. L'adresse redirige vers la page distante `/remote/`.
3. Saisissez le mot de passe et appuyez sur **Se connecter**.

**Enregistrer le mot de passe** (case sur la page de connexion) mémorise le mot de passe dans le navigateur de **cet appareil seulement** et préremplit le champ la fois suivante. Il n'y a pas de connexion automatique – vous appuyez toujours sur *Se connecter*. Décochez la case pour supprimer aussitôt le mot de passe mémorisé.

**Mauvais mot de passe :** des essais erronés répétés bloquent l'appareil pendant un moment (protection contre la force brute).

**Se déconnecter :** *Fichier → Se déconnecter* (affiché seulement sur les appareils distants).

Si rien ne se connecte : vérifiez que les deux appareils sont dans le même réseau (les Wi-Fi invités séparent souvent les appareils les uns des autres), que l'adresse correspond à celle de la page des paramètres, et le pare-feu (voir ci-dessus).

---

## 4. Ce que peut faire un appareil distant

- **Tout ce que peut la console.** Après connexion, un appareil distant a les mêmes droits : programmation, cues, effets, fichiers, paramètres, paramètres DMX et paramètres d'accès distant. Cela inclut des choses aux conséquences – désactiver l'accès distant (ce qui exclut cet appareil) ou **quitter OpenCue**, ce qui arrête le programme pour tout le monde. Utilisez un mot de passe que seules des personnes de confiance connaissent.
- **Mise en page propre à chaque appareil.** Chaque appareil retient la mise en page qu'il a utilisée et peut en montrer une autre que la console. Construisez pour la tablette une mise en page avec de gros boutons (voir plus bas). Si un appareil enregistre une mise en page qu'un autre affiche actuellement, l'autre la reprend – ou, s'il a ses propres modifications non enregistrées, propose *Appliquer* ou *Garder ma version*.
- **Accès complet à tous les paramètres, aussi depuis l'iPad.** C'est important quand OpenCue tourne sans fenêtre (*serveur seulement*, icône de la zone de notification) : tous les paramètres – sortie, sécurité et mode verrouillage, API REST, assistant IA, commande vocale, sauvegardes, démarrage avec Windows, valeurs par défaut, entrées / sorties ... – se modifient sur l'iPad et s'appliquent **au serveur**. L'interrupteur du microphone de la commande vocale est aussi présent sur l'iPad. **Dossiers :** là où l'ordinateur principal ouvrirait l'Explorateur Windows, un appareil distant obtient l'**Explorateur OpenCue** – une grande fenêtre pour le dossier de données d'OpenCue (shows, sauvegardes, journaux, projecteurs ...) : parcourir, télécharger (un dossier en ZIP), téléverser, nouveau dossier, renommer, dupliquer, supprimer. Il ne peut pas sortir du dossier de données. La même fenêtre (*Choisir un dossier...*) permet de choisir un nouvel emplacement de stockage. L'**apprentissage / la surveillance MIDI**, l'**entrée DMX** et la **règle de pare-feu** (Windows demande l'autorisation sur l'ordinateur principal) fonctionnent aussi depuis l'iPad. Seules quelques choses tiennent **physiquement à l'ordinateur principal** : sa fenêtre (plein écran), l'**écran verrouillé** de la console (à déverrouiller là), l'enregistrement de la touche d'un **clavier précis**, le **microphone pendant la dictée** et le véritable Explorateur Windows.
- **Propre à chaque appareil :** seulement le **mode plein écran** (celui de chaque navigateur) et l'**échelle de l'interface**.
- **Les données restent sur la console.** Enregistrer et charger passent toujours par la console ; shows, mises en page et projecteurs vivent sur l'ordinateur console.

### Qui est connecté ?

Une icône de la barre d'outils indique **combien d'appareils distants sont connectés**. Cliquez dessus pour voir l'adresse IP, l'appareil et la durée de connexion de chacun – et pour **déconnecter** (*Expulser*) un appareil. Un appareil déconnecté voit un avis et doit recharger la page pour se reconnecter.

---

## 5. Installer comme application (iPad / iPhone / Android)

La page distante est une **web-app**. Sur l'appareil, vous pouvez l'ajouter à l'écran d'accueil :

- **iPad / iPhone (Safari) :** bouton Partager → **Sur l'écran d'accueil**.
- **Android (Chrome) :** menu → **Installer l'application** / **Ajouter à l'écran d'accueil**.

Elle s'ouvre ensuite en plein écran sans barres de navigateur, avec les couleurs de votre thème actuel.

**Icône :** l'application reçoit l'icône OpenCue et le nom « OpenCue » – aussi en HTTPS. (L'icône est intégrée à la page ; sinon iOS ne la récupère pas avec un certificat auto-créé et n'affiche qu'une lettre grise.) Si l'icône ne change toujours pas, supprimez l'application de l'écran d'accueil et ajoutez-la de nouveau – iOS se souvient de l'ancienne icône.

**Page hors ligne et choix du serveur (page sécurisée, HTTPS) :** quand le serveur est injoignable, l'application affiche « **Serveur injoignable** » au lieu d'une page d'erreur. Vous pouvez y **Recharger**, ou saisir une nouvelle **adresse ou IP**, le **port** et **HTTPS** activé / désactivé sous **Autre serveur** et **Se connecter** – si l'ordinateur a une nouvelle adresse IP, il n'est pas nécessaire de réinstaller l'application. Les adresses récemment utilisées sont listées dessous pour être touchées. Si la connexion tombe (Wi-Fi disparu, OpenCue fermé), l'avis « Rétablissement de la connexion » apparaît ; après 3 secondes avec le bouton « **Choisir un autre serveur (7 s)** » dont le nombre **décompte** ; à 0, la page hors ligne s'ouvre d'elle-même et recharge OpenCue dès que le serveur répond. Cela vaut aussi quand le Wi-Fi est là mais que l'ordinateur ne répond pas – la page hors ligne apparaît alors après **environ 1,5 seconde** au lieu d'un écran blanc et disparaît immédiatement quand le serveur répond. Si vous l'ouvrez volontairement avec le bouton, elle reste. Astuce : le nom `opencue.local` trouve l'ordinateur même quand l'IP change.

**Important sur l'iPad – installer le certificat une fois :** avec un certificat auto-créé, iOS ne connaît l'exception « continuer malgré l'avertissement » que **dans l'onglet Safari**. Une application de l'écran d'accueil reste alors **blanche**, et le service worker (page hors ligne) n'est pas autorisé. OpenCue crée donc sa propre autorité de certification (« OpenCue Local CA ») qui signe le certificat https. Vous l'installez **une fois** sur l'appareil :

Les étapes sont une **page de guide** sur le serveur : *Paramètres → Accès distant → Certificat pour iPad et navigateurs* en montre l'adresse et un code QR (scannez-le avec la caméra de l'iPad). La page s'ouvre en **http://** sans connexion et suit la langue de l'appareil. En haut, vous choisissez entre **iPad / iPhone** et **Android · Windows · macOS**. Pour l'iPad, il y a quatre étapes avec un rappel : **Télécharger → Installer → Faire confiance → Ouvrir https** ; vous pouvez cocher les étapes terminées (la page s'en souvient). **Important : ouvrez la page dans Safari** – le profil ne peut pas être installé depuis l'application de l'écran d'accueil, depuis Chrome ni depuis le navigateur intégré à une autre application. « Réglages » désigne l'**application Réglages de l'iPad**, pas un réglage de Safari. À la fin de chaque page, il est indiqué comment **supprimer à nouveau le certificat** (iPad : Réglages → Général → VPN et gestion d'appareils → « OpenCue » → Supprimer le profil). Dans OpenCue, la même chose se trouve sous *Paramètres → Accès distant → Certificat pour iPad et navigateurs* (version courte pour installer et supprimer). (L'accès en HTTP doit être activé pour cela.)

À partir de là, https fonctionne sans avertissement, l'application s'ouvre, le service worker et la page hors ligne fonctionnent – aussi quand l'ordinateur reçoit une **nouvelle adresse IP** (OpenCue ne réémet que le certificat du serveur, l'autorité reste). L'autorité ne peut se porter garante que de noms locaux (`.local`, `localhost`) et d'adresses privées. Android / Windows / macOS : installez le fichier de certificat (`opencue-ca.crt`) et configurez-le comme autorité de confiance. Si vous supprimez le dossier `https` du dossier de données, une nouvelle autorité est créée – réinstallez le profil sur les appareils.

**Limite :** les web-apps installables et la page hors ligne nécessitent une connexion sécurisée (HTTPS, sur l'iPad avec le certificat installé). En simple `http://`, l'application de l'écran d'accueil fonctionne, mais il n'y a pas de page hors ligne et l'appareil doit joindre la console pour afficher quoi que ce soit.

---

## 6. Conseils pour une bonne mise en page de tablette

- Créez une **mise en page séparée** pour la tablette (*Édition → Gérer les mises en page…*) : un grand **Exécuteur**, la **Liste de cues**, quelques panneaux **Bouton** ou **Fader** et la catégorie du **Contrôle des projecteurs** dont vous avez le plus besoin. Les appareils distants chargent leur propre mise en page, la mise en page de la console reste donc telle quelle.
- Pour le tactile, utilisez les panneaux **Pavé numérique de commande** et **Boutons de commande** plutôt que de taper sur le clavier à l'écran.
- Augmentez l'**échelle de l'interface** sur la tablette (`Ctrl +` ou *Affichage → Échelle de l'interface…*) – elle ne s'applique qu'à cet appareil.
- On peut changer de mise en page par **balayage** horizontal si *Paramètres → Général → Changer de mise en page par balayage* est activé (par appareil).
- Les listes de cues avec déclencheurs timecode continuent de tourner sur la console même si un appareil se déconnecte – le show ne dépend pas de la tablette.

---

## 7. Sécurité et bonnes pratiques

- N'utilisez l'accès distant que dans des réseaux de confiance (votre propre routeur, un réseau de show dédié). La connexion n'est **pas chiffrée** (HTTP simple) ; toute personne du réseau pourrait lire le trafic.
- Choisissez un mot de passe que vous n'utilisez pas ailleurs – il est stocké dans la configuration de l'application sur la console et, si vous cochez *Enregistrer le mot de passe*, dans le navigateur de cet appareil.
- Désactivez l'accès distant quand vous n'en avez pas besoin.
- La sortie DMX tourne toujours sur la console – même si tous les appareils distants se déconnectent, les lumières restent comme elles sont.

## 8. Verrouillage : écran verrouillé et déconnexion

**Paramètres → Sécurité** contient le **mode verrouillage** (désactivé par défaut, demande le mot de passe) :

- **À la console :** le **cadenas** de la barre du haut, **Ctrl+L** (modifiable sous *Contrôles → Raccourcis clavier*) ou **Contrôles → Verrouiller** verrouille OpenCue. Une console verrouillée n'affiche qu'une fenêtre sombre de mot de passe – le reste de l'interface est masqué, le clavier ne fait rien, et la console n'accepte plus de modifications de cette fenêtre (pas même en contournant l'interface). Un rechargement ne déverrouille **pas**. **Le show continue :** cues, effets, MIDI, OSC, planification et appareils distants fonctionnent comme avant. Cinq mots de passe erronés de suite suspendent le déverrouillage pendant une minute. Le mot de passe ne quitte jamais la console tant qu'elle est verrouillée. Redémarrer OpenCue déverrouille.
- **Sur un appareil distant :** le cadenas **déconnecte l'appareil** : la session se termine, le *mot de passe enregistré* de cet appareil est effacé, et la page affiche de nouveau la connexion avec un champ de mot de passe vide. Les appareils distants ne peuvent pas changer le mot de passe ni le mode verrouillage.
- **Verrouiller automatiquement après ...** (1 à 60 minutes sans aucune saisie ; désactivé par défaut) : la console se verrouille d'elle-même, les appareils distants se déconnectent. Attention avec une tablette qui ne fait qu'afficher : laissez le réglage désactivé pour celles-ci.

## 9. Commande simple et mode opérateur (pour confier la console à quelqu'un d'autre)

- Le **panneau « Commande simple »** (*Édition → Ajouter un panneau → Saisie*) est le petit frère du panneau *Contrôle des projecteurs* et utilise **tout le panneau** avec des champs fixes en pourcentage : à gauche (38 %) **chaque projecteur a sa propre tuile** (numéro, nom, couleur et luminosité en direct), triée par **groupes** (toucher le nom du groupe = sélectionner tout le groupe ; le reste trié par type ; *Tous* / *Aucun* en haut) ; à droite la **luminosité** (grand fader, *Off* / *Full*), la **couleur** (champ de couleur – teinte de gauche à droite, plus de blanc vers le haut – plus des boutons de couleur), le **mouvement** (**joystick** à ressort : poussez – plus loin, plus vite ; lâchez = arrêt ; *Centre*), le **zoom**, les **gobos** en images, un grand bouton **Blackout** et les **looks** : *Arc-en-ciel*, *Cercle* (pan / tilt), *Pulsation*, *Stroboscope* – des effets standard tout prêts sans aucun réglage (toucher à nouveau = désactivé, *Looks off* retire tout ; l'effet est ajouté automatiquement au show la première fois). Une commande que les lumières sélectionnées n'ont pas reste à sa place mais est atténuée. Sur un **panneau étroit** (moins d'environ 720 px), il passe en **mode compact** avec un onglet par domaine (*Lumières | Luminosité | Couleur | Mouvement | Faisceau | Looks* ; Blackout reste visible). Rien ici ne modifie les groupes ni le show ; sélection, valeurs et effets sont ceux de tout le programme (programmeur, cues, atelier d'effets). Créez une mise en page avec seulement ce panneau (ou quelques autres) pour la personne qui doit utiliser.
- Le **mode opérateur** (*Affichage → Mode opérateur ...* ou le bouton joystick de la barre du haut ; demande le mot de passe, *Paramètres → Sécurité*) : cet appareil peut **seulement utiliser** ce qui est à l'écran – pas de menus, pas de barre du haut, pas de paramètres ni d'autres fenêtres, pas de raccourcis clavier (la saisie dans un champ de texte fonctionne encore), pas de déplacement ni de reconstruction des panneaux, pas de changement de mise en page ni de show. On en sort avec le petit **cadenas en bas à droite** et le mot de passe, ou avec **Ctrl+L**. Il ne se lance que depuis le menu ou le bouton (pas de raccourci clavier). Les **commandes** (ligne de commande, touches, widgets) ne sont exécutées par le serveur en mode opérateur que si elles **servent à utiliser** ; tout ce qui modifie le show (*Store, Update, Delete, Move, Label, Set*, temps de cue, création / renommage / suppression de listes de cues) est refusé – y compris dans une chaîne de commandes. **À la console, la commande vocale est désactivée en mode opérateur** (le microphone reste fermé) et revient ensuite si elle est activée. Le **serveur l'impose** : d'un appareil en mode opérateur, seuls les messages d'utilisation sont acceptés (sélectionner, régler des valeurs, cues, presets, timecode, ligne de commande ...) ; les messages de programmation, de mise en page, de show et de paramètres sont rejetés et les requêtes d'écriture reçoivent la réponse `423`. Un rechargement ne quitte pas le mode. Il fonctionne à la console et sur chaque appareil distant indépendamment (confiez un iPad avec l'application en mode opérateur) ; redémarrer OpenCue y met fin. Cinq mots de passe erronés de suite suspendent la sortie pendant une minute.
- **Bon à savoir :** la ligne de commande, si vous la mettez dans cette mise en page, peut exécuter n'importe quelle commande – laissez-la hors d'une mise en page pour des invités. Les touches d'un clavier supplémentaire dédié (*Raccourcis clavier personnalisés*, propres à l'appareil) et les contrôleurs MIDI / OSC continuent de fonctionner : ils appartiennent au show, pas à l'écran.

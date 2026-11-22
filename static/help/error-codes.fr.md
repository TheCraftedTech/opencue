# Codes d'erreur et dépannage

Quand quelque chose ne va pas, OpenCue ne disparaît pas simplement : il affiche une petite **fenêtre d'erreur** avec une courte explication et un **code d'erreur** du type `OC-1002`. Le même code est écrit dans le **fichier journal**. Cette page explique chaque code : ce qu'il signifie et comment y remédier.

Si vous ne parvenez pas à résoudre un problème, copiez les détails (voir la section 1) et envoyez-les avec votre question – le code nous indique aussitôt où chercher.

---

## 1. La fenêtre d'erreur

La fenêtre comporte un titre, une courte explication, le **CODE D'ERREUR**, parfois un cadre avec des détails techniques, et ces boutons :

| Bouton | Ce qu'il fait |
|---|---|
| **Copier les détails** | Place dans le presse-papiers tout ce qu'il faut pour un rapport de bogue : code d'erreur, version d'OpenCue, versions de Windows et de Python, le texte de l'erreur et les **40 dernières lignes du journal**. Collez-le dans un e-mail, un ticket GitHub ou une conversation avec un assistant. (Raccourci : **Ctrl+C**) |
| **Ouvrir le dossier des journaux** | Ouvre dans l'Explorateur le dossier contenant les fichiers journaux. |
| **Ouvrir le fichier journal** | Ouvre le journal actuel (`opencue.log`) dans votre éditeur de texte. |
| **Fermer** | Ferme la fenêtre (aussi **Échap** ou la **×**). Si l'erreur a arrêté OpenCue, le programme se termine après la fermeture de la fenêtre. |

Vous pouvez déplacer la fenêtre par sa barre de titre. La fenêtre d'erreur apparaît dans la langue d'OpenCue (en anglais si elle ne peut pas être déterminée) ; le texte copié avec *Copier les détails* est toujours en anglais, afin qu'un rapport puisse être lu par tout le monde.

---

## 2. Où se trouvent les fichiers journaux

Chaque démarrage d'OpenCue écrit un journal :

| Fichier | Contenu |
|---|---|
| `opencue.log` | Le démarrage **actuel** : tout ce qu'OpenCue signale – messages, avertissements, erreurs avec leurs codes et traces de plantage. |
| `opencue.previous.log` | Le journal du démarrage **précédent**. Après un plantage et un redémarrage, la cause s'y trouve encore. |

Ils se trouvent dans le dossier `logs` du dossier de données d'OpenCue – normalement `%LOCALAPPDATA%\OpenCue\logs` (tapez-le dans la barre d'adresse de l'Explorateur). La fenêtre d'erreur l'ouvre pour vous.

**Chercher dans le journal :** les codes s'écrivent `OC-1234`. Cherchez `OC-` pour les trouver tous, ou `OC-3` pour les petits problèmes d'une fonction isolée (section 5).

---

## 3. Problèmes de démarrage (OC-1xxx)

OpenCue vérifie ces points **avant** que quoi que ce soit d'autre démarre. La fenêtre vous dit ce qui ne va pas ; OpenCue se ferme ensuite.

### OC-1001 – OpenCue est déjà en cours d'exécution

**Signification :** Un seul OpenCue peut tourner à la fois par dossier de données. Un second se disputerait les mêmes paramètres, le même port et la même sortie DMX.

**Ce qui se passe :** La fenêtre de l'OpenCue en cours est amenée au premier plan et cette fenêtre apparaît. (Si l'OpenCue en cours est un **serveur sans fenêtre**, voir le guide *Options de démarrage et mode serveur* : aucune erreur n'apparaît, votre navigateur s'ouvre alors sur la console en cours.)

**Que faire :**
- Utilisez la fenêtre qui est passée au premier plan. Si vous ne la voyez pas, regardez sur vos **autres écrans** et dans la **barre des tâches**.
- Vous venez de fermer OpenCue et vous obtenez quand même ce message ? Il lui faut peut-être quelques secondes pour s'arrêter. Attendez un instant et redémarrez.
- Rien de visible du tout ? Ouvrez le **Gestionnaire des tâches**, cherchez `OpenCue` (ou `python`/`pythonw` si lancé depuis les sources) et terminez le processus résiduel.
- Avancé : pour un second OpenCue séparé (par exemple pour des tests), réglez la variable d'environnement `OPENCUE_DATA_DIR` sur un autre dossier **et** donnez-lui un autre port dans son `app_config.json` (voir OC-1002).
- **Redémarrage juste après la fermeture :** OpenCue attend maintenant (jusqu'à environ 25 secondes) que l'ancien ait fini de se fermer, puis démarre tout seul. Vous ne voyez ce message que si l'ancien ne se termine pas.

### OC-1002 – Le port réseau est déjà utilisé

**Signification :** OpenCue possède un petit serveur intégré avec lequel sa fenêtre communique. Il lui faut un port réseau libre (par défaut **8000**). Un autre programme utilise ce port. Sans cette vérification, la fenêtre d'OpenCue afficherait la page de l'*autre* programme.

**Que faire :**
1. Fermez l'autre programme. Causes fréquentes : un autre serveur web ou outil de développement, ou un processus OpenCue résiduel (voir OC-1001, Gestionnaire des tâches).
2. Pour savoir qui utilise le port, ouvrez une invite de commandes et tapez `netstat -ano | findstr :8000` (avec votre numéro de port). La dernière colonne est l'identifiant du processus ; cherchez-le dans le Gestionnaire des tâches (onglet *Détails*).
3. Ou laissez OpenCue utiliser un autre port : fermez OpenCue, ouvrez dans un éditeur de texte le fichier de paramètres indiqué dans la fenêtre (normalement `%LOCALAPPDATA%\OpenCue\config\app_config.json`) et remplacez `"server_port": 8000` par un nombre libre entre **1024 et 65535**, par exemple `8010`. Si la ligne manque, ajoutez-la. Enregistrez et redémarrez OpenCue. (Quand OpenCue tourne, vous pouvez le changer dans **Paramètres → Accès distant → Port HTTP**.)

### OC-1003 – Microsoft Edge WebView2 Runtime introuvable

**Signification :** OpenCue affiche sa fenêtre avec le **Microsoft Edge WebView2 Runtime** gratuit. Windows 11 l'a ; Windows 10 l'a généralement via Edge ou Office, mais pas toujours.

**Que faire :** Cliquez sur **Ouvrir la page de téléchargement**, installez le runtime *Evergreen* de Microsoft et redémarrez OpenCue. Si vous êtes sûr que le runtime est installé, cliquez sur **Démarrer quand même**. L'installateur d'OpenCue télécharge le runtime automatiquement s'il manque et qu'il y a Internet.

### OC-1004 – Le dossier de données est inutilisable

**Signification :** OpenCue enregistre ses paramètres, shows, dispositions et journaux dans son **dossier de données** (normalement `%LOCALAPPDATA%\OpenCue`) et ne peut ni le créer ni y écrire. La ligne sous l'explication indique la raison technique.

**Que faire :** Vérifiez que le dossier existe et que votre compte Windows peut y écrire ; que le disque n'est pas plein, n'est pas en lecture seule et (pour un lecteur réseau ou USB) est connecté ; qu'aucun antivirus ni « accès contrôlé aux dossiers » ne bloque OpenCue. Si un dossier de données personnalisé a été choisi lors de l'installation, assurez-vous que ce lecteur est disponible. Un nom de dossier qui est en réalité un **fichier** existant provoque aussi cette erreur.

---

## 4. Erreurs inattendues (OC-2xxx)

Ce sont des erreurs qu'OpenCue n'attendait pas – en général un bogue. **Veuillez copier les détails et les signaler.** Le texte de l'erreur et le journal montrent où cela s'est produit.

### OC-2001 – OpenCue n'a pas pu démarrer

Une erreur inattendue a arrêté OpenCue pendant son démarrage. Redémarrez une fois. Si cela revient : copiez les détails et signalez-le. Comme solution de contournement, un fichier de paramètres endommagé peut en être la cause : fermez OpenCue, renommez `config\app_config.json` dans le dossier de données en `app_config.old.json` et redémarrez (OpenCue démarre alors avec les paramètres par défaut ; vos shows et dispositions sont des fichiers séparés et restent).

### OC-2002 – Une tâche en arrière-plan a échoué

Quelque chose s'est mal passé dans une tâche en arrière-plan, par exemple l'analyse audio, le MIDI ou le réseau. **OpenCue continue de tourner.** La fenêtre n'apparaît que pour la *première* erreur de ce type par démarrage (toutes figurent dans le journal). Si quoi que ce soit se comporte bizarrement, enregistrez votre show et redémarrez OpenCue. Merci de le signaler avec les détails copiés.

### OC-2003 – Le serveur d'OpenCue s'est arrêté

Le serveur intégré s'est arrêté de façon inattendue ou n'a pas pu démarrer, la fenêtre ne peut donc pas fonctionner. OpenCue se ferme après la fenêtre et libère d'abord la sortie DMX et les caméras. Redémarrez OpenCue. Si cela se reproduit, signalez-le ; vérifiez aussi OC-1002 (un problème de port peut aussi aboutir ici).

### OC-2004 – OpenCue s'est arrêté de façon inattendue

Une erreur inattendue s'est produite pendant que OpenCue tournait et le programme doit se fermer. **Les modifications non enregistrées peuvent être perdues.** Redémarrez OpenCue et signalez l'erreur avec les détails copiés. Astuce : enregistrez régulièrement votre show (**Ctrl+S**) pendant les longues sessions.

---

## 5. Problèmes d'une fonction isolée (OC-3xxx, journal seulement)

Ceux-ci **n'ouvrent pas** de fenêtre et OpenCue continue de tourner. Ils apparaissent en tout début d'une **ligne du journal** (par exemple `... [DMX] OC-3103 USB DMX: COM3 ...`) et souvent comme message dans la page de paramètres correspondante. Cherchez `OC-3` dans le journal.

| Code | Signification | Que faire |
|---|---|---|
| **OC-3001** | Le fichier de paramètres `app_config.json` n'a pas pu être lu. OpenCue a utilisé la sauvegarde automatique (`.bak`) ou, si elle était aussi endommagée, les paramètres par défaut. Le fichier endommagé est conservé à côté sous le nom `.corrupt`. | Vérifiez vos paramètres. Pour garder d'anciens paramètres, copiez des valeurs du fichier `.corrupt` dans le nouveau `app_config.json` (fermez d'abord OpenCue). |
| **OC-3101** | Une erreur s'est produite dans le thread de sortie DMX. | Vérifiez les paramètres DMX (Paramètres → Sortie DMX) et la connexion réseau ou USB. Signalez-le si cela se répète. |
| **OC-3102** | La sortie Art-Net n'a pas pu être (re)configurée avec les paramètres actuels. | Vérifiez la cible et l'adresse IP de liaison dans les paramètres DMX. La carte réseau doit exister et être connectée. |
| **OC-3103** | L'interface DMX USB a été débranchée ou a signalé une erreur d'envoi. | Rebranchez-la et appuyez sur *Actualiser les ports* dans les paramètres DMX. Essayez un autre port USB ou un autre câble ; vérifiez qu'aucun autre programme n'utilise le port. |
| **OC-3104** | Une erreur s'est produite dans l'horloge de la sortie DMX (elle envoie les images à Art-Net, sACN et USB). | OpenCue continue de tourner et l'horloge reprend à l'image suivante. Signalez-le si cela se répète (Aide → Signaler un problème). |
| **OC-3105** | Le **processus de sortie DMX séparé** (un second processus OpenCue dans le Gestionnaire des tâches) s'est terminé ou n'a pas pu démarrer. | OpenCue le redémarre automatiquement (la sortie revient en moins d'une seconde). S'il meurt cinq fois en une minute ou ne démarre pas du tout, la sortie continue à l'intérieur du programme principal – sans la séparation, mais sans coupure. Vérifiez votre antivirus (il doit autoriser `OpenCue.exe` à lancer un second processus) ; signalez-le si cela se répète. |
| **OC-3201** | L'analyse audio n'a pas pu ouvrir son entrée ou sa source (périphérique occupé, retiré ou bloqué par les paramètres de confidentialité de Windows). | Choisissez une autre source dans le panneau Audio. Fermez les programmes qui utilisent le périphérique en exclusivité. Pour un microphone, autorisez l'accès dans *Paramètres Windows → Confidentialité → Microphone*. |
| **OC-3202** | La commande vocale n'a pas pu ouvrir le microphone sélectionné (OpenCue essaie plusieurs fois). | Choisissez à nouveau le microphone dans Paramètres → Mot de réveil ; fermez les autres programmes qui l'utilisent ; vérifiez le paramètre de confidentialité du microphone de Windows. |
| **OC-3301** | Un périphérique MIDI n'a pas pu être ouvert. Sous Windows, la plupart des périphériques ne peuvent être utilisés que par **un seul programme** à la fois. | Fermez l'autre programme (logiciel de musique, station audio) ou désactivez-y le périphérique. Débranchez puis rebranchez le périphérique. |
| **OC-3401** | Le nom `opencue.local` n'a pas pu être annoncé sur le réseau (mDNS). Les appareils distants peuvent toujours utiliser l'adresse IP. | Utilisez l'adresse avec le numéro IP indiquée dans les paramètres d'Accès distant. Vérifiez que le réseau autorise le multicast et que le pare-feu Windows autorise OpenCue sur les réseaux privés. |
| **OC-3402** | OpenCue n'a pas pu écouter sur une adresse réseau pour les appareils distants. | Un autre programme utilise peut-être ce port, ou l'adresse a disparu (Wi-Fi changé). Désactivez puis réactivez l'accès distant dans Paramètres → Accès distant, ou choisissez un autre port. |
| **OC-3501** | La mise à jour n'a pas pu être téléchargée ou sa somme de contrôle ne correspondait pas. | Vérifiez la connexion Internet et réessayez plus tard, ou téléchargez l'installateur depuis la page des versions. |
| **OC-3502** | L'installateur de mise à jour téléchargé n'a pas pu être lancé. | Téléchargez l'installateur depuis la page des versions et lancez-le vous-même. |
| **OC-3601** | L'interface utilisateur a signalé une erreur JavaScript. La ligne du journal indique le message, le fichier et la ligne, et sur quel appareil cela s'est produit (la console ou un appareil distant). Souvent rien n'est visible ; parfois un panneau reste vide. | Rechargez la fenêtre (ou la page sur l'appareil distant). Si cela se reproduit, signalez-le avec *Aide → Signaler un problème* – la ligne fait partie des détails. |
| **OC-3701** | Une sauvegarde en arrière-plan du show n'a pas pu être écrite (disque plein, dossier non accessible en écriture ou protégé par un antivirus). Le show lui-même n'est pas affecté. | Libérez de l'espace disque ou choisissez un autre dossier de données (*Paramètres → Général → Dossier de données et gestion des fichiers*). *Fichier → Restaurer une sauvegarde* montre quelles sauvegardes existent ; le dossier est `backups` dans le dossier de données. |
| **OC-3801** | OSC n'a pas pu écouter sur son port UDP (un autre programme l'utilise). | Choisissez un autre port dans **Contrôles → OSC ...** ou fermez l'autre programme. |

---

## 6. Signaler un problème

1. Le plus simple : **Aide → Signaler un problème...** copie les détails dans le presse-papiers et ouvre la page de signalement. (Dans la fenêtre d'erreur : **Copier les détails**.) **Aide → Ouvrir le dossier des journaux** ouvre le dossier contenant `opencue.log`.
2. Sur la page **Issues** du projet OpenCue sur GitHub, décrivez ce que vous avez fait avant l'erreur.
3. Collez le texte copié. Il ne contient aucune donnée de show, seulement les informations techniques décrites dans la section 1.

Merci de ne pas envoyer de mots de passe ni de clés d'accès ; si vous avez collé des lignes du journal provenant d'un écran de paramètres, retirez-les d'abord.

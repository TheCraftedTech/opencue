# Options de démarrage et mode serveur

OpenCue peut être lancé avec des options – dans un raccourci, un fichier batch, le Planificateur de tâches ou un terminal. Ce guide les énumère, explique le **mode serveur sans fenêtre** (`--no-ui`), le **démarrage avec Windows**, ce que les **droits d'administrateur** changent (et ne changent pas) et la règle du **pare-feu Windows**.

---

## 1. Les options

Placez-les derrière le programme : `OpenCue.exe --no-ui --open-browser` (depuis les sources : `python main.py ...`). Dans un raccourci : *Propriétés → Cible*, après les guillemets fermants du chemin.

| Option | Effet |
|---|---|
| `--no-ui` ou `--server-only` | Démarrer **sans fenêtre de programme** (section 2). Implique `--no-splash`. |
| `--open-browser` | Avec `--no-ui` : ouvre au démarrage le navigateur par défaut sur la console. |
| `SHOWFILE` ou `--show FICHIER` | Charge ce show au lieu du dernier. Un fichier de show en premier paramètre fonctionne comme un démarrage par double-clic ; cela inclut un fichier `.ocshow` (paquet d'export). Si OpenCue tourne déjà, le programme en cours reprend le fichier (et demande d'abord ce qu'il faut faire des modifications non enregistrées). |
| `--new-show` | Démarre avec un **show vide** au lieu du dernier. Rien n'est supprimé ; le show « utilisé en dernier » reste tel quel. |
| `--port N` | Port du serveur **pour cette exécution seulement** (1–65535). Le réglage enregistré ne change pas. |
| `--remote` | Active l'**accès réseau** (comme dans *Paramètres → Accès distant*) – ce réglage-ci est **enregistré**. |
| `--data-dir DOSSIER` | Utilise un autre **dossier de données** pour cette exécution (usage portable, tests). Identique à la variable `OPENCUE_DATA_DIR`. |
| `--fullscreen` | Démarre la fenêtre du programme en plein écran. |
| `--priority normal`, `above` ou `high` | Priorité du processus ; par défaut `above` (supérieure à la normale), voir la section 5. |
| `--no-splash` | Pas d'écran de démarrage (aussi : `OPENCUE_NO_SPLASH=1`). |
| `--version`, `--help` | Affiche la version ou la liste des options. |

Le programme compilé n'a pas de console propre : `--help` et `--version` écrivent dans la console depuis laquelle il a été lancé (cmd, PowerShell).

---

## 2. Mode serveur sans fenêtre (`--no-ui`)

OpenCue démarre comme d'habitude – sortie DMX, cues, effets, MIDI, accès distant, API REST – mais **aucune fenêtre de programme ne s'ouvre**. Vous le pilotez depuis

- **un navigateur sur cet ordinateur :** `http://127.0.0.1:8000` (le port des *Paramètres → Accès distant*, ou `--port`) – exactement la même console que dans la fenêtre, ou
- **une tablette ou un téléphone** via le réseau (activez l'**Accès distant** dans les paramètres ou démarrez une fois avec `--remote`).

Une **icône dans la zone de notification** de la barre des tâches montre qu'OpenCue tourne : un **clic** ouvre la console dans votre navigateur ; un **clic droit** ouvre le menu *Ouvrir OpenCue dans le navigateur*, *Ouvrir le dossier des journaux* et *Quitter OpenCue*. Si le show a des modifications non enregistrées, la fermeture demande confirmation une fois (une copie de sauvegarde est de toute façon enregistrée).

Le menu affiche en haut le **nom du show**, l'avertissement **⚠ Modifications non enregistrées** lorsqu'il y en a (l'info-bulle de l'icône aussi) et les **adresses** auxquelles la console est joignable (avec l'accès distant activé, aussi celles du réseau) – un clic en ouvre une dans le navigateur.

Autres façons de quitter : **Fichier → Quitter** dans le navigateur, **Ctrl+C** si le programme a été lancé depuis un terminal, ainsi que la fermeture de session ou l'arrêt de Windows (OpenCue essaie alors de se fermer proprement, avec la sauvegarde habituelle).

**Lancer OpenCue une seconde fois** pendant que le serveur tourne n'affiche pas d'erreur : cela ouvre simplement votre navigateur sur la console en cours.

Ce qui **peut ne pas fonctionner** sans la fenêtre : ce qui nécessite la fenêtre native du programme elle-même – par exemple le sélecteur de fichiers pour *lier* un fichier vidéo ou audio, ou le basculement en plein écran de la fenêtre. Tout le reste est disponible dans le navigateur.

Astuce : pour un PC de scène qui ne fait que sortir du DMX, activez *Démarrer OpenCue quand je me connecte à Windows* + *Démarrer sans fenêtre* (section 3).

---

## 3. Démarrer avec Windows

**Paramètres → Général → Comportement :**

- **Démarrer OpenCue quand je me connecte à Windows** – une entrée pour **votre utilisateur Windows** (aucun droit d'administrateur nécessaire ; supprimez-la en la désactivant).
- **Démarrer sans fenêtre (serveur uniquement)** – démarre avec `--no-ui`.

Cette option existe dans le **programme installé**, pas lorsqu'on démarre depuis le code source. (Un show exporté avec l'extension `.ocshow` s'ouvre toujours dans OpenCue par double-clic – il n'y a pas d'interrupteur pour cela.) L'entrée pointe vers le fichier du programme : si vous déplacez ou réinstallez OpenCue ailleurs, désactivez puis réactivez l'option.

---

## 4. Droits d'administrateur et pare-feu

**OpenCue tourne-t-il en administrateur ?** Le journal (`opencue.log`, premières lignes) et les détails d'un rapport d'erreur indiquent *« Administrator: yes »* ou *« no »*. Si c'est le cas, OpenCue écrit aussi une remarque dans le journal.

**Vous n'en avez pas besoin – et ne devriez pas l'utiliser :** Windows bloque le **glisser-déposer de fichiers depuis l'Explorateur** vers un programme exécuté en administrateur, et un serveur web avec des droits d'administrateur est une cible plus grosse. Les droits d'administrateur n'aident que pour **une** chose : créer la **règle du pare-feu Windows**.

**Règle de pare-feu :** sans elle, Windows pose la question la première fois qu'OpenCue utilise le réseau ; une question restée sans réponse ou refusée bloque les tablettes, le sACN et le nom réseau `opencue.local`. **Paramètres → Accès distant → Pare-feu Windows → Autoriser OpenCue dans le pare-feu** crée une règle pour ce programme précis, **entrante, uniquement dans les réseaux privés et de domaine** (jamais dans les réseaux publics). Windows demande l'autorisation **une seule fois** (invite d'administrateur) – seule cette petite commande est lancée avec des droits élevés, OpenCue lui-même continue de tourner normalement. *Supprimer la règle de pare-feu* la supprime de nouveau. La ligne d'état indique si la règle existe.

---

## 5. Priorité et précision du temps

Au démarrage, OpenCue règle la **priorité du processus** sur *supérieure à la normale* et la **résolution du minuteur sur 1 ms** (Windows bat normalement toutes les 15,6 ms). Les deux maintiennent la fluidité des boucles à 40 Hz des cues, des effets et du DMX quand l'ordinateur est occupé – aucun droit d'administrateur nécessaire. `--priority high` l'augmente encore (pour un PC qui ne fait rien d'autre), `--priority normal` la désactive.

---

## 6. Exemples

- Serveur sur un PC de scène, le navigateur s'ouvre : `OpenCue.exe --no-ui --open-browser`
- Ouvrir un show depuis *Ouvrir avec* de l'Explorateur : `OpenCue.exe "D:\Shows\Concert.json"`
- Démarrer vide sans toucher au dernier show : `OpenCue.exe --new-show`
- Tester sur un autre port avec ses propres données : `OpenCue.exe --port 8080 --data-dir D:\OpenCueTest`

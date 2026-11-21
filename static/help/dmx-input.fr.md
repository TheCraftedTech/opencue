# Entrée DMX (recevoir Art-Net et sACN)

OpenCue peut non seulement envoyer du DMX mais aussi le **recevoir par le réseau** – depuis une console d'éclairage, un programme (par exemple un visualiseur ou un contrôleur de show) ou un appareil. Les valeurs reçues peuvent être **transmises et mélangées** à la sortie ou servir de **déclencheurs**.

Ouvrez-la avec **Contrôles → Entrée DMX…** (elle peut aussi être modifiée depuis une tablette).

---

## 1. L'activer

- Activez **Recevoir le DMX** (désactivé par défaut – le DMX n'a pas de mot de passe, n'importe qui dans le réseau peut envoyer).
- **Protocoles :** Art-Net (UDP 6454) et/ou sACN / E1.31 (UDP 5568, multicast). Univers Art-Net = *adresse de port* (exactement comme OpenCue l'envoie : univers 1 = adresse de port 1).
- **Émetteurs autorisés :** vide = tout le monde ; sinon des adresses IP ou leurs débuts (p. ex. `192.168.1.`).
- **Carte réseau :** seulement nécessaire si l'ordinateur en a plusieurs et que l'entrée doit écouter sur une carte précise.
- **Source disparue après :** après ce délai sans paquet, OpenCue libère les valeurs de la source (sACN : immédiatement avec « flux terminé »).

**Sources vues** montre en direct tout ce qui est envoyé : protocole, univers, émetteur, paquets par seconde et combien de canaux ne sont pas à zéro. **Voir** affiche les 512 canaux sous forme de grille ; **Transmettre** crée aussitôt une assignation.

---

## 2. Transmettre / mélanger (source → sortie)

Une **assignation** mélange un *univers d'entrée* dans un *univers de sortie* d'OpenCue :

| Mode | Signification |
|---|---|
| **Le plus haut gagne** (HTP) | Par canal, la plus grande valeur entre OpenCue et l'entrée compte. Le mode par défaut, sûr pour mélanger. |
| **Remplacer** | L'entrée compte tant que la source est là (zéros inclus). Éventuellement seulement pour une plage de canaux. |

- Plusieurs sources pour le même univers : **le plus haut gagne**. Avec sACN, seules comptent les sources de plus haute **priorité**.
- Si l'univers de sortie n'a **aucun projecteur**, il est tout de même émis – cela donne une **transmission pure** (p. ex. Art-Net → sACN ou → un adaptateur USB).
- L'entrée se place **au-dessus de tout** (programmeur, cues, effets). Les valeurs dans OpenCue restent inchangées ; le mélange n'a lieu que dans la **sortie**.
- Les paquets propres sont reconnus et ignorés – une transmission ne crée pas de boucle de rétroaction.
- Elle tourne dans le **processus de sortie DMX** : la transmission continue sans changement même si le programme principal se bloque. Si ce processus échoue et que la sortie tourne dans le programme principal en secours, les déclencheurs et l'affichage continuent de fonctionner mais pas le mélange (la fenêtre l'indique).

---

## 3. Déclencheurs (canal → commande)

Un **déclencheur** exécute une commande de la ligne de commande quand un canal change :

- **Bouton :** quand la valeur passe au-dessus du **seuil**, la première commande s'exécute (p. ex. `Go`) ; quand elle repasse en dessous, la seconde (facultative, p. ex. `Blackout Off`).
- **Fader :** chaque nouvelle valeur s'exécute comme une commande ; `{value}` représente la valeur ramenée à la **plage** (0–100 par défaut), p. ex. `Master {value}`.
- **Apprendre :** cliquez sur **Apprendre** et bougez un canal sur la console – protocole, univers et canal sont remplis.
- La première valeur vue est seulement mémorisée, rien n'est déclenché (pas de saut à la connexion). Les commandes de fader s'exécutent au plus 20 fois par seconde ; la dernière valeur arrive toujours.

Exemples : canal 1 = `Go` (bouton), canal 2 = `Blackout` (bouton), canal 3 = `Master {value}` (fader), canal 10 = `Goto Cue 5`.

**Derniers déclencheurs** montre ce qui a été déclenché.

---

## 4. Bon à savoir

- L'entrée appartient à la **configuration de l'application** (pas au show) et s'applique à cet ordinateur.
- Pour qu'une console atteigne OpenCue, elle doit envoyer à l'adresse IP de l'ordinateur ou en diffusion (broadcast) ; le pare-feu Windows doit autoriser UDP 6454 / 5568 pour OpenCue – la fenêtre indique si la règle existe et la crée en un clic (Windows demande l'autorisation sur l'ordinateur principal).
- **Se signaler comme appareil Art-Net :** OpenCue répond à la recherche (ArtPoll) des autres appareils et apparaît dans leur liste d'appareils Art-Net – une console peut le choisir comme cible sans saisir l'adresse IP.
- Une vue d'ensemble de toutes les entrées et sorties se trouve dans **Paramètres → Vue d'ensemble**.

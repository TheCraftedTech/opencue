# Commandes vocales

Avec les **commandes vocales**, vous pilotez OpenCue à la voix : vous dites le **mot de réveil** (par défaut « OpenCue ») et juste après une **commande de la ligne de commande** – OpenCue la transcrit, la convertit dans la notation de la ligne de commande et l'**exécute aussitôt**, exactement comme une commande saisie au clavier (elle apparaît aussi dans l'historique des commandes, toutes les fenêtres suivent). Tout fonctionne **hors ligne** sur l'ordinateur de la console (après le téléchargement unique des modèles), aucune IA n'est nécessaire.

Vous parlez **anglais** : les commandes de la ligne de commande (`Fixture`, `At`, `Color`, `Blackout`, `Go` …) sont en anglais, et la reconnaissance vocale est réglée pour écrire des mots anglais.

---

## 1. L'activer

1. Le **symbole du microphone** en haut à droite de la barre d'outils est un **interrupteur marche/arrêt** :
   - **vert** = la commande vocale écoute le mot de réveil,
   - **rouge et barré** = désactivée,
   - **jaune** = erreur (microphone inaccessible, modèle manquant …; l'indication se trouve dans l'info-bulle).
2. Une fois, deux modèles sont téléchargés (chacun une seule fois, ensuite tout fonctionne sans Internet) : le petit **modèle du mot de réveil** (41 Mo : *Paramètres → Mot de réveil → Télécharger le modèle vocal*, ou déjà dans l'installateur) et le **modèle de parole** pour les commandes (*Paramètres → Dictée → Charger maintenant* ; c'est le même que pour la dictée). Le modèle de parole *Précis* (small) comprend bien mieux que *Rapide* (base).
3. Le microphone, le mot de réveil et la sensibilité se règlent sous *Paramètres → Mot de réveil*.

Le symbole existe sur l'ordinateur de la console et aussi sur les appareils distants (iPad) : l'interrupteur active ou désactive la commande vocale du serveur ; le microphone lui-même reste toujours branché sur l'ordinateur principal.

---

## 2. Comment parler

```
"OpenCue … Blackout on."
"OpenCue … Fixture five at seventy nine, color green."
"OpenCue … Fixtures one through five at full."
```

- D'abord le **mot de réveil**, puis – dans le même souffle ou après une courte pause (jusqu'à environ 2 secondes) – la **commande**.
- Quand la commande est terminée, **attendez environ une seconde** : une courte pause termine l'enregistrement (10 secondes au maximum).
- En bas au centre de l'écran, une bulle montre la progression : **Écoute …** → **Compréhension …** → **la commande** avec son résultat (vert = faite, rouge = erreur ou rien compris). Si OpenCue a corrigé un mot, cela s'affiche derrière (« corrigé : add → At »).
- Parlez par commandes courtes et claires. Les mots de remplissage (« uh », « please », « now », « set ») et les bégaiements sont supprimés.

---

## 3. Ce que vous pouvez dire

Vous dites les commandes telles qu'elles s'écrivent dans la ligne de commande (voir le guide *Ligne de commande*). Les nombres peuvent être dits en mots (« seventy nine ») ou en chiffres. Plusieurs commandes dans un même souffle sont séparées par **« then »**.

### Sélectionner des projecteurs et la luminosité

| Vous dites | Ce qui s'exécute |
|---|---|
| Fixture five | `Fixture 5` |
| Fixtures one through ten | `Fixture 1 Thru 10` |
| Fixture three and seven | `Fixture 3 + 7` |
| Fixture five at seventy nine | `Fixture 5 At 79` |
| Fixture five brightness fifty percent | `Fixture 5 At 50%` (aussi *dimmer, intensity, level*) |
| Fixtures one through five at full / at half | `Fixture 1 Thru 5 At Full` / `… At Half` |
| Fixture five on / full | `Fixture 5 At Full` |
| Fixture five off / out | `Fixture 5 At 0` |
| Fixture five at seventy nine point five | `Fixture 5 At 79.5` |
| At at / Everything on / All lights on | `At At` – **tout allumer** (100 % + blanc) : sans sélection tous les projecteurs, avec une sélection seulement cette sélection. Dites d'abord « Clear » pour être sûr que ce soit tout. |
| Fixtures one through ten minus five (aussi *except / without*) | `Fixture 1 Thru 10 - 5` (sans le n° 5) |
| Next fixture / Previous fixture | `Next` / `Previous` (sélectionne le projecteur suivant / précédent) |
| Group front at full | `Group front At Full` |
| Group front truss at forty | `Group "front truss" At 40` (plusieurs mots de nom vont ensemble entre guillemets) |
| Light / lamp / spot five | `Fixture 5` |

### Couleurs

| Vous dites | Ce qui s'exécute |
|---|---|
| Fixture five color green | `Fixture 5 Color Green` |
| Fixture five green | `Fixture 5 Color Green` (le mot « color » est ajouté) |
| Fixture five warm white / cool white / light blue | `Fixture 5 Color Warm` / `Cool` / `Lightblue` |
| RGB two fifty five zero zero | `RGB 255 0 0` |
| Color two fifty five one twenty eight zero | `Color 255 128 0` (« one twenty eight » = 128 après *color / rgb / bpm*) |

Les couleurs comme dans la ligne de commande : red, green, blue, white, black, yellow, cyan, magenta, orange, pink, purple, amber, lime, teal, violet, light blue, warm, cool.

### Position et faisceau

| Vous dites | Ce qui s'exécute |
|---|---|
| Pan ninety / Pan fifty percent | `Pan 90` / `Pan 50%` |
| Tilt minus forty five / Pan plus fifteen | `Tilt -45` / `Pan +15` (un signe = relatif) |
| Fixture five home / center | `Fixture 5 Pan 50% Tilt 50%` |
| Zoom half / full / minimum / fifty | `Zoom Half` / `Zoom Full` / `Zoom Min` / `Zoom 50` |
| Focus twenty five | `Focus 25` |
| Gobo forty / gobo spin thirty | `Gobo 40` / `GoboSpin 30` |
| Prism one hundred | `Prism 100` |
| Strobe zero / shutter ten | `Strobe 0` / `Strobe 10` |
| Channel six one hundred twenty eight | `Channel 6 128` (canal 6 du projecteur sur DMX 128) |

### Master et blackout

| Vous dites | Ce qui s'exécute |
|---|---|
| Blackout | `Blackout` (bascule) |
| Blackout on / Blackout off | `Blackout On` / `Blackout Off` |
| Master eighty / Master full / Master minus ten | `Master 80` / `Master Full` / `Master -10` |

### Listes de cues

| Vous dites | Ce qui s'exécute |
|---|---|
| Go / Next cue | `Go` |
| Back / Go back / Previous cue | `Back` |
| Pause / Resume / Stop | `Pause` / `Resume` / `Stop` |
| Go to cue five | `Go Cue 5` (aussi *goto cue five*) |
| Cue list main go | `Cuelist main Go` |
| Cue list front of house back | `Cuelist "front of house" Back` |
| Cuelist two go | `Cuelist 2 Go` |
| Cuelist main fader eighty / Fader fifty | `Cuelist main Fader 80` / `Fader 50` |
| Cue five fade three / Cue five delay one point five | `Cue 5 Fade 3` / `Cue 5 Delay 1.5` |
| Store cue five (merge) | `Store Cue 5` (`Merge`) |
| Update / Clear | `Update` / `Clear` |

### Timecode et audio

| Vous dites | Ce qui s'exécute |
|---|---|
| Timecode play / pause / stop / reset / reverse | `Timecode Play` / `Pause` / `Stop` / `Reset` / `Reverse` |
| Timecode rate two | `Timecode Rate 2` |
| Tap | `Tap` (taper le tempo) |
| BPM one twenty eight / BPM auto / BPM half | `BPM 128` / `BPM Auto` / `BPM Half` (aussi *beats per minute*) |
| Audio start / stop / demo | `Audio Start` / `Stop` / `Demo` |

### Effets, variables, programmeur

| Vous dites | Ce qui s'exécute |
|---|---|
| Effect rainbow / Effect off | `Effect rainbow` / `Effect Off` |
| Variable warm white | `Variable "warm white"` |
| Manual / Manual color | `Manual` / `Manual Color` |

### Plusieurs commandes

« Fixture one at full **then** fixture two at zero » → `Fixture 1 At Full; Fixture 2 At 0`.

---

## 4. Ce qui est corrigé automatiquement

Whisper écrit parfois des mots qui sonnent pareil mais n'ont aucun sens dans la commande (« add » au lieu de « at », « true » au lieu de « thru »). OpenCue vérifie **à quelle place de la commande** se trouve le mot et met le mot de commande qui convient – seulement là où il convient :

| Entendu / écrit | Devient | Quand |
|---|---|---|
| add, ad, it, app | At | après un nombre, avant un nombre (« fixture 5 **add** 70 ») |
| true, threw, till, through, until, to, too, drew, grew, crew, throw … | Thru | entre deux nombres (« fixtures 1 **true** 5 ») |
| **2** (Whisper entend « thru » comme le nombre *two*) | Thru | dans une sélection exactement entre deux nombres (« fixtures one **two** five » = `Fixture 1 Thru 5` ; aussi « fixture 1-5 » et « 1, 2, 5 ») |
| eight (8) | At | dans une sélection entre deux nombres (« fixture 5 **eight** 70 ») |
| halve, calf | Half | toujours ; « fixture 3 half » = `Fixture 3 At Half` |
| chanel, clair, stroke, pawn, tell, fate, delight … | Channel, Clear, Strobe, Pan, Tilt, Fade, Delay | selon la position (avant un nombre, ou toujours) |
| oh | 0 | là où un nombre doit se trouver (« at oh », « master oh ») |
| picture, pitcher, fix sure, fixer | Fixture | toujours (« **picture** one to four ») |
| for, to, too, won, ate, tree | 4, 2, 2, 1, 8, 3 | seulement là où un nombre doit se trouver (« fixture **for** at fifty » → Fixture 4 At 50) |
| collar, caller | Color | toujours |
| pen, ban, pun | Pan | avant un nombre |
| till, tilted | Tilt | avant un nombre (« **till** minus ten ») |
| queue, q, cute, cube, key | Cue | avant un nombre (« go **key** five ») |
| fool | Full | toujours |
| of, own | Off, On | après Blackout |
| prison, prisms | Prism | toujours |
| strove | Strobe | toujours |
| paws, pours | Pause | toujours |
| affect, effects | Effect | toujours |
| tab | Tap | toujours |
| read, grin, grain, blew, wait … | Red, Green, Blue, White | après « color » ou comme nom de couleur |
| black out, black art, blackouts | Blackout | toujours |
| time code, cue list, grand master, go bo, b p m | Timecode, Cuelist, Master, Gobo, BPM | expressions de plusieurs mots |

De plus :

- **Les nombres en mots** → chiffres (« twenty one », « one hundred and five », « two point five », « minus ten percent »).
- **Comparaison phonétique :** un mot inconnu qui se trouve là où un mot de commande précis doit se trouver et qui sonne pareil devient ce mot.
- **Petites fautes d'orthographe** des mots-clés → le mot de commande le plus proche (« blakout » → Blackout).
- **Variantes du mot de réveil** (« open queue », « open Q », « OpenCue ») sont supprimées au début, ainsi que tout ce qui a été dit avant le mot de réveil.
- **Les noms** (après *group, cuelist, effect, variable*) restent tels que prononcés.
- **Le pourcentage** après Master, Fader, BPM et les numéros de cue est supprimé (« master eighty percent » → `Master 80`), car la ligne de commande ne connaît pas de pourcentage à cet endroit.
- Le bavardage introductif avant la commande (« set », « please », tout ce qui n'est pas compris) est supprimé ; la commande doit commencer par un mot de commande.

---

## 5. Ce qui ne fonctionne pas à la voix

En **mode opérateur** sur la console (*Affichage → Mode opérateur ...*), la commande vocale est **désactivée**, de sorte que sur ce PC seul ce que propose la surface de contrôle est possible ; après être sorti de ce mode, elle refonctionne si elle était activée.

Par sécurité, la commande vocale **n'exécute jamais rien qui supprime ou écrase** : `Delete …`, `Clear Clear`, `Overwrite`. La bulle indique alors « Pas par la voix ». Saisissez ces commandes au clavier ou utilisez l'interface.

---

## 6. Quand ça ne marche pas

| Affichage | Que faire |
|---|---|
| Microphone jaune | Lire l'info-bulle ; *Paramètres → Mot de réveil* (bon microphone ?) |
| « Modèle de parole manquant » | *Paramètres → Dictée → Charger maintenant* (et pour le mot de réveil : *Paramètres → Mot de réveil → Télécharger le modèle vocal*) |
| « Rien compris » | Se rapprocher du microphone, parler plus clairement, dire la commande tout de suite après le mot de réveil |
| « Aucune commande reconnue » | Le texte ne commence pas par un mot de commande – la bulle montre ce qui a été compris ; parlez exactement comme dans la ligne de commande |
| Commande rouge (✗) | La ligne de commande dit ce qui ne va pas (par exemple le projecteur n'existe pas, « cette liste de cues n'a pas de cues ») |
| Le mot de réveil n'est pas reconnu | Augmenter *Paramètres → Mot de réveil → Sensibilité* |
| Un mot est toujours mal écrit | Noter ce que Whisper écrit (le texte figure dans le journal) – le tableau des corrections est facile à compléter |

Le mot de réveil est reconnu par un petit modèle hors ligne, la commande qui suit est transcrite par Whisper (environ 1 à 3 secondes sur un ordinateur normal). Une musique forte ou du bruit dans la pièce dégrade la reconnaissance – un microphone près de la bouche aide plus que tout.

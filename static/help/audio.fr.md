# Audio : des lumières qui réagissent à la musique

OpenCue peut **écouter** la musique et faire réagir les lumières : plus lumineuses avec les basses, un flash à chaque grosse caisse, des couleurs qui changent sur le temps, un chenillard qui court en rythme. L'analyse tourne en direct sur la console, ne nécessite pas Internet et n'utilise que quelques pour cent d'un cœur de processeur.

---

## 1. L'idée en une minute

- Le **panneau Audio** prend une source sonore et l'analyse : volume, spectre, coups de **grosse caisse, caisse claire et charleston**, **tempo (BPM)** et position dans le temps.
- Les résultats sont disponibles pour les effets sous forme de **variables** (`a_level`, `a_bass`, `a_kick`, `a_beat_phase` ...). Un **effet audio** est un script d'effet normal qui les lit. Il fonctionne comme tout autre effet : assignez-le à des projecteurs dans le programmeur, enregistrez-le dans des cues, faites-le apparaître et disparaître en fondu.
- 33 effets audio prêts à l'emploi sont fournis avec le programme. Ils portent l'étiquette **Audio** (posée automatiquement dès qu'un effet lit des valeurs audio) – choisissez l'étiquette dans la boîte de dialogue du type d'effet pour les lister.
- Sans source en cours, toutes les valeurs audio valent `0` : un effet audio reste simplement sombre ou à sa valeur de repos.
- Les cues peuvent aussi démarrer **sur la musique** : le déclencheur de cue *Audio* (section 8).
- Les boutons, faders et interrupteurs propres de la console peuvent suivre la musique (section 9), et l'API REST peut lire et piloter l'audio (section 10).

---

## 2. Démarrage rapide

1. Ajoutez le panneau : **Modifier → Ajouter un panneau…** → catégorie *Médias et temps* → **Audio**.
2. Choisissez **Battement de démonstration** dans la liste des sources et appuyez sur **Démarrer**. Une boucle de batterie à 120 BPM est analysée – vous voyez le spectre, les voyants *Grosse caisse / Caisse claire / Charleston / Battement* clignoter et le tempo apparaître.
3. Dans le programmeur, sélectionnez quelques projecteurs, ouvrez l'onglet **Effets** et cliquez sur **Ajouter un effet**, choisissez le type d'effet **Kick Flash** (ou *Bass Dimmer*, *Beat Chase* ... – astuce : filtrez par l'étiquette *Audio*) et créez-le. Les projecteurs clignotent maintenant avec le battement de démonstration.
4. Passez la source à votre vraie musique (section suivante).

Les installations existantes obtiennent les nouveaux effets via le **Gestionnaire de fichiers** (liste *Effets*) avec **Restaurer les effets par défaut**. Cela ne crée que les fichiers *manquants* et n'écrase jamais : si vous avez déjà restauré une version plus ancienne, supprimez d'abord les anciens fichiers `audio_*.fx` dans le gestionnaire de fichiers, puis restaurez à nouveau.

---

## 3. Choisir la source

La liste montre tout ce que Windows connaît :

| Groupe | Ce que c'est | Usage typique |
|---|---|---|
| **Son du système** | Ce que cet ordinateur joue sur un haut-parleur ou un casque (« loopback »). Une entrée par périphérique de sortie. | Musique du même ordinateur (logiciel de DJ, Spotify, navigateur). Pas de câble, pas de microphone. |
| **Entrées** | Microphones, prises ligne et interfaces audio USB. | Musique d'une table de mixage ou d'un téléphone : branchez le câble sur l'**entrée ligne** ou l'interface. Un portable avec une seule prise casque combinée la traite comme un *microphone* : le signal est plus faible, augmentez le **gain d'entrée**. Un microphone dans la salle fonctionne aussi, mais la musique doit être forte et claire. |
| **Test** | Le battement de démonstration. | Essayer des effets sans musique. |

Les entrées marquées *(par défaut)* sont celles que Windows utilise par défaut. **Rechercher à nouveau** (le bouton aux flèches) recherche les périphériques après un branchement.

Appuyez sur **Démarrer**. La source reste ouverte jusqu'à ce que vous appuyiez sur **Arrêter** ; le prochain démarrage du programme la rouvre tout seul. Si une source ne peut pas être ouverte, le panneau dit pourquoi (utilisée par un autre programme, bloquée dans les paramètres de confidentialité Windows *Microphone*, débranchée).

---

## 4. Ce que montre le panneau

- **Spectre :** 32 barres de 30 Hz à 16 kHz (les sons graves à gauche). Le cadre brille à chaque temps.
- **Voyants :** *Grosse caisse*, *Caisse claire*, *Charleston* s'allument à chaque coup ; *Battement* à chaque temps du tempo.
- **Niveau** avec un repère *Surcharge* : s'allume quand le signal est écrêté (trop fort à l'entrée ; baissez le volume ou le gain).
- **Tempo :** les BPM en grands chiffres, une LED de temps, une barre montrant la position dans le temps et une fine barre indiquant la fiabilité de la détection.

---

## 5. Tempo : automatique, tapé ou fixe

- **Auto** détecte le tempo d'après la musique (70 – 180 BPM). Il lui faut quelques secondes et un rythme régulier ; il suit les changements de tempo.
- **Taper :** tapez sur le bouton en rythme avec la musique (aussi la commande `Tap`). À partir du deuxième tap, le tempo est déterminé d'après vos taps et le temps commence exactement sur le tap. Le tempo est alors *Manuel*.
- **÷2 / ×2 :** quand la détection a trouvé la moitié ou le double de la vitesse (typique pour une musique très lente ou très rapide).
- **Manuel :** le tempo est fixe ; saisissez-le dans le champ. Avec *Tempo manuel : le temps suit la musique*, la position du temps s'ajuste encore doucement aux coups. Sans aucune musique, un tempo fixe tourne comme un **métronome** – les effets avec `a_beat_phase` continuent de tourner en rythme.
- **Auto** revient à la détection.

Commandes : `Tap`, `BPM 128`, `BPM Auto`, `BPM Half`, `BPM Double`, `Audio Start`, `Audio Stop`, `Audio Demo`, `Audio Status`.

---

## 6. Paramètres

| Paramètre | Ce qu'il fait |
|---|---|
| **Gain d'entrée** | Amplifie (×0,1 à ×10) un signal faible, p. ex. un microphone. |
| **Gain automatique** | L'analyse se mesure aux parties les plus fortes des dernières secondes, de sorte qu'un morceau calme fonctionne comme un morceau fort. Désactivez-le pour une échelle fixe (le gain agit alors directement). |
| **Sensibilité du battement** | Plus haut : même les coups doux comptent (risque : faux coups). Plus bas : seuls les coups nets comptent. |
| **Lissage** | La lenteur avec laquelle les niveaux et les bandes redescendent. |
| **Décalage temporel** | −100 à +200 ms. Positif : les lumières réagissent **plus tôt** – à utiliser quand les lumières ou les haut-parleurs sont en retard. |

Les paramètres appartiennent à la console (pas à un show ni à un panneau) et sont enregistrés automatiquement. Chaque appareil ayant un panneau Audio montre et pilote la même source.

---

## 7. Les effets audio prêts à l'emploi

| Effet | Catégorie | Ce qu'il fait |
|---|---|---|
| Band Bars | Gradateur | Chaque projecteur montre une bande de fréquences : le premier les graves, le dernier les aigus (se répète au-delà de 8 projecteurs). |
| Bass Dimmer | Gradateur | La luminosité suit les basses de la musique. |
| Beat Chase | Gradateur | Un chenillard qui avance à chaque temps (ou un temps sur n). |
| Beat Pulse | Gradateur | La luminosité pulse en rythme avec la musique : vive sur le temps, puis qui s'estompe doucement. |
| Beat Strobe | Gradateur | Stroboscope en rythme avec la musique : plusieurs flashs par temps, calés sur le tempo. |
| Beat Toggle | Gradateur | Bascule entre deux groupes à chaque temps (ou un temps sur n), net ou en fondu enchaîné (doux). |
| Hi-Hat Sparkle | Gradateur | À chaque coup de charleston, des projecteurs choisis au hasard scintillent. |
| Kick Chase | Gradateur | Un chenillard qui avance à chaque coup de grosse caisse (au lieu du temps). |
| Kick Flash | Gradateur | Chaque coup de grosse caisse fait flasher les lumières, qui s'estompent ensuite. |
| Level Dimmer | Gradateur | La luminosité suit le volume global. |
| Snare Flash | Gradateur | Chaque coup de caisse claire (ou clap) fait flasher les lumières, qui s'estompent ensuite. |
| Beat Color | Couleur | La couleur change à chaque temps (ou un temps sur n) et est la plus lumineuse sur le temps. |
| Beat Color Chase | Couleur | Une lumière colorée (A) parcourt une couleur de fond (B), un pas par temps (ou un temps sur n). |
| Beat Color Fade | Couleur | Fondu entre deux couleurs en rythme avec la musique. |
| Beat Color Strobe | Couleur | Un stroboscope coloré en rythme avec la musique : plusieurs flashs par temps, en alternance entre les couleurs A et B. |
| Color Blend | Couleur | Fond de la couleur A (calme) vers la couleur B (fort). |
| Color Hit | Couleur | La couleur de base flashe vers la couleur de flash à chaque coup de la percussion choisie. |
| Hi-Hat Color Sparkle | Couleur | À chaque coup de charleston, des projecteurs choisis au hasard flashent d'une couleur aléatoire (dans la plage de couleurs). |
| Hue Drift | Couleur | Les couleurs dérivent à travers la plage de couleurs, un cycle complet dure `beats` temps. |
| Kick Color Flash | Couleur | La couleur de base flashe vers la couleur de flash à chaque coup de grosse caisse. |
| Spectrum Color | Couleur | La couleur se mélange d'après la musique : basses = rouge, médiums = vert, aigus = bleu. |
| Spectrum Hue | Couleur | La couleur suit le son : une musique riche en basses montre le début de la plage de couleurs, les sons brillants sa fin. |
| Bass Tilt | Position | Le tilt suit les basses : calme = bas, basses fortes = haut (autour de la position de base). |
| Beat Circle | Position | Les têtes décrivent un cercle en rythme avec la musique : un tour dure `beats` temps. |
| Beat Fan | Position | Les projecteurs s'ouvrent en éventail et se referment en rythme avec la musique. |
| Kick Tilt Punch | Position | À chaque coup de grosse caisse, les têtes donnent un coup de tilt et reviennent à la position de base. |
| Level Spread | Position | Plus la musique est forte, plus les projecteurs s'écartent en éventail (symétriquement autour de la position de base). |
| Pan/Tilt Sway | Position | Les têtes bougent en rythme avec la musique. |
| Snare Pan Snap | Position | À chaque coup de caisse claire, chaque tête saute à la suivante de quatre positions de pan. |
| Beat Zoom Pulse | Zoom | Le zoom pulse à chaque temps : haut sur le temps, puis retombe vers le bas. |
| Kick Zoom Punch | Zoom | Le zoom passe de bas à haut à chaque coup de grosse caisse puis retombe. |
| Bass Focus | Focus | La mise au point suit les basses de la musique. |
| Beat Gobo Change | Gobo | Le gobo change à chaque temps (ou un temps sur n). |

Presque chaque effet a des options pour **activer des animations** et ajouter un **stroboscope** : *strobe* (flashs par seconde, 0 = désactivé), *mode* (par exemple tous ensemble / pair-impair en alternance / aléatoire), *direction* (chenillard avant, arrière, aller-retour, aléatoire), *every* (changer un temps sur n), *soft* (commutation nette ou fondu enchaîné). Ce sont des effets normaux : enregistrez-les dans des cues, variez-les, copiez-les.

---

## 8. Déclencheur de cue : Audio

Outre *Go*, *Follow*, *Code temporel* et *MIDI* (guide *MIDI*), un cue peut avoir le déclencheur **Audio** : il se déclenche alors tout seul **sur la musique**. Dans la boîte de dialogue du cue, choisissez le déclencheur *Audio*, sélectionnez **une source** et, au besoin, une valeur – dans la liste de cues, vous pouvez aussi la saisir (`audio kick`, `audio beat 4`, `audio bass 70`) ou utiliser la commande `Cue 2 Trigger Audio Beat 4`.

| Source | Valeur | Le cue se déclenche … |
|---|---|---|
| **Battement (tempo)**, **Grosse caisse**, **Caisse claire**, **Charleston** | un sur n (1 à 64, par défaut 1) | … à chaque n-ième temps / coup. |
| **Niveau global**, **Basses**, **Médiums**, **Aigus** ou l'une des **huit bandes** (avec leur plage en Hz dans la liste) | seuil en % (par défaut 70) | … quand cette partie du son **atteint** le seuil par le bas. |

Fonctionnement :
- Le cue se déclenche lorsqu'il est le **cue suivant** d'une liste en cours : démarrez d'abord la liste avec *Go*, puis le cue audio suivant attend son événement. Après son déclenchement, le cue qui le suit (s'il a aussi le déclencheur *Audio*) attend à son tour – vous pouvez ainsi enchaîner toute une séquence sur la musique.
- Le compteur (*un sur n*) repart à 0 chaque fois qu'un nouveau cue devient actif.
- Avec un seuil, le cue se déclenche une fois quand le niveau l'atteint ; il n'est réarmé qu'après que le niveau est nettement retombé en dessous (environ 80 % du seuil). Si le niveau est déjà au-dessus quand le cue devient suivant, il attend la prochaine montée.
- Après un déclenchement, il y a une courte pause (0,25 s), de sorte qu'un coup ne démarre jamais deux cues.
- Le **panneau Audio doit tourner** (une source démarrée) ; sans son, rien ne se déclenche. Le déclencheur fonctionne pour chaque liste de cues indépendamment.

---

## 9. Boutons, faders et interrupteurs qui réagissent à la musique

Les panneaux **Bouton**, **Fader** et **Interrupteur** de la console peuvent utiliser la musique comme *signal* – dans *Suit l'état de* (un fader bouge avec la musique, un interrupteur bascule avec le signal) et dans les **conditions des règles** (couleur, texte ou commande quand …). Les signaux sont dans le groupe **Audio** :

| Signal | Signification |
|---|---|
| **Signal audio présent** | actif tant qu'une source est ouverte et que quelque chose est joué |
| **Niveau global**, **basses**, **médiums**, **aigus** | 0–100 % |
| **Grosse caisse**, **caisse claire**, **charleston**, **temps** (impulsion) | saute à 100 % à chaque coup puis s'estompe |
| **Tempo (BPM)** | le tempo détecté ou réglé |

Exemples : un fader qui suit les basses comme un indicateur de niveau ; un bouton qui s'allume en rouge quand le tempo est compris entre 120 et 130 BPM ; un interrupteur qui indique si de la musique arrive. La source audio tourne sur la console ; un panneau n'a besoin que d'être à l'écran d'un appareil quelconque – les mesures sont envoyées à un appareil exactement tant qu'un tel panneau (ou le panneau *Audio*) y est ouvert.

## 10. L'audio via l'API

L'API REST peut lire l'analyse (`GET /api/v1/audio`), ouvrir et fermer la source, modifier les paramètres et taper le tempo (`PUT /api/v1/audio`, `POST /api/v1/audio/tap`, autorisation *Audio*), et le **flux d'événements en direct** (`GET /api/v1/events?events=audio,beat,hit`) signale la source, chaque temps et chaque coup de percussion au moment où ils se produisent. Voir le guide *API REST*.

## 11. Écrire votre propre effet audio

Ouvrez l'**Atelier d'effets**, créez un effet et lisez les variables audio – voir le guide *Atelier d'effets*, section *Variables audio*. Un premier exemple :

```
#NAME My Flash
#CATEGORY dimmer
#RATE 40
#VAR peak Slider 100 0 100 1

loop() {
  dimmer = peak * a_kick;
}
```

L'aperçu de l'atelier joue un battement d'exemple (120 BPM) pour que vous voyiez tout de suite comment se comporte la courbe.

---

## 12. Quand quelque chose ne marche pas

| Problème | À vérifier |
|---|---|
| La source ne peut pas être ouverte | Un autre programme l'utilise en exclusivité ; le microphone est bloqué dans les paramètres de confidentialité Windows (*Paramètres → Confidentialité → Microphone*) ; le périphérique est débranché. |
| Le panneau n'affiche rien / tout est plat | La source est-elle *démarrée* ? L'indicateur de volume de Windows bouge-t-il ? Augmentez le **gain d'entrée**. Pour *Son du système*, le programme doit réellement jouer sur ce périphérique de sortie. |
| *Surcharge* est allumé | Le signal est trop fort : baissez le volume à la source ou le gain d'entrée. |
| Les BPM sautent ou sont la moitié / le double | Appuyez sur **÷2 / ×2**, tapez le tempo ou fixez-le avec *Manuel*. Une musique sans rythme régulier (classique, parole) n'a pas de tempo détectable. |
| Les lumières réagissent trop tard | Utilisez le **Décalage temporel** (valeurs positives). |
| Un effet audio reste sombre | Aucune source en cours, ou la sensibilité est trop faible pour la musique ; augmentez le curseur *gain* de l'effet. |

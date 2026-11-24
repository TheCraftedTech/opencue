# Simulation 3D

Le panneau **Simulation 3D** montre votre scène en 3D ; chaque projecteur s'allume en direct selon ses valeurs DMX. Ajoutez-le avec **Ajouter un panneau**. Ce guide explique les boutons, les réglages de **Salle et lumière** et ce qu'il faut vérifier quand l'image n'est pas celle attendue (tous les projecteurs n'éclairent pas la scène, cônes ou ombres manquants, lenteur).

---

## 1. Le panneau

- Trois modes en haut à gauche : **Affichage**, **Construction** (objets et modèles 3D) et **Projecteurs** (placer les projecteurs, pointer les lyres).
- Boutons en haut à droite : casque VR (seulement si le navigateur en propose un), partager la caméra entre appareils, **Salle et lumière** (engrenage), **Arrêter / Démarrer la simulation 3D**, **Blackout** (ampoule), **Réinitialiser la vue**, **Plein écran**.
- En bas à gauche : le bouton de qualité indique la cadence et la résolution ; un clic bascule Auto → Basse → Moyenne → Élevée.

## 2. Arrêter et démarrer la simulation 3D

Le bouton pause arrête complètement la simulation : la scène, le contexte graphique et les modèles sont supprimés, rien n'est calculé ni dessiné et le reste d'OpenCue n'est pas ralenti. Le panneau reste dans votre layout et affiche un bouton lecture ; **Démarrer** reconstruit tout. Le choix est mémorisé **par appareil** et vaut pour tous les panneaux 3D de cet appareil. Si un panneau 3D est vide et indique qu'il est arrêté, appuyez sur le bouton lecture.

Après le démarrage, le chargement d'un grand show ou la modification des limites de lumière, le panneau affiche brièvement *Préparation de l'éclairage …* : la carte graphique prépare ses programmes en arrière-plan et le reste d'OpenCue reste utilisable.

## 3. Salle et lumière

Ouvrez la boîte de dialogue avec l'engrenage. Elle comporte deux parties.

**Pour tous les appareils** – valable pour chaque appareil connecté au show (console, iPad, accès à distance) : *Éclairage* (lumière de travail en mode Construction, lumière de salle), *Lumière réfléchie* (lumière de salle, réflexion des murs, rayonnement des couleurs), *Image* (réflexion des objets, exposition, **Brume**) et *Grille et axes dans la vue*. **Brume à 0 %** désactive complètement la brume : ni cônes de lumière ni calcul de brume – c'est ce qui économise le plus de performances.

**Cet appareil uniquement** – performance et qualité. Ces réglages ne valent que sur cet appareil, chaque appareil peut choisir les siens :

| Réglage | Signification |
|---|---|
| **Qualité** | Auto (s'adapte à la cadence), Basse, Moyenne, Élevée : résolution et détail des ombres. |
| **Lumières max.** | Combien de projecteurs reçoivent en même temps leur propre lumière sur les surfaces (par défaut 32). Les plus lumineux l'emportent. |
| **Ombres max.** | Combien de ces lumières projettent des ombres. 0 = autant que la carte graphique le permet. |
| **Faisceaux miroir max.** | Reflets sur le métal et les miroirs. |
| **Cônes de lumière simples max.** | Combien de cônes simples sont dessinés. 0 = tous. Avec une limite, chaque projecteur garde d'abord son premier cône, puis les plus lumineux. |
| **Cadence max.** | Limite le nombre de rafraîchissements par seconde (par ex. 30). 0 = illimitée. |
| **Les projecteurs projettent des ombres** | Les boîtiers des projecteurs projettent des ombres dans les cônes de lumière (activé par défaut). |

La ligne sous les réglages indique ce qui s'applique en ce moment (lumières, ombres, projecteurs placés) et ce que la carte graphique autorise. **Réinitialiser les limites** rétablit les valeurs par défaut.

## 4. Quand l'image n'est pas celle attendue

- **Tous les projecteurs n'éclairent pas la scène, certains n'ont pas d'ombre, seuls quelques-uns montrent un gobo.** Cela vient des limites de cet appareil. Seuls les *Lumières max.* projecteurs les plus lumineux (par défaut 32) éclairent les surfaces, seules *Ombres max.* de ces lumières projettent des ombres (la carte graphique fixe une limite supérieure, indiquée dans la ligne d'information) et un motif de gobo ou de prisme n'apparaît que sur les **3** premières lumières de ce type ; les autres montrent une lumière ouverte. Augmentez *Lumières max.* et *Ombres max.* (0 = autant que possible) pour tout afficher – avec beaucoup de projecteurs, l'image devient plus lente ou un peu en retard.
- **Un projecteur est allumé mais son cône manque.** Vérifiez la **Brume** (0 % = pas de cônes), *Cônes de lumière simples max.*, le Blackout, le Grand Master, le dimmer du projecteur et que la simulation 3D n'est pas arrêtée.
- **L'image est sombre.** La lumière de travail n'existe qu'en mode Construction ; vérifiez le réglage *Exposition*, le Blackout et le Grand Master.
- **La simulation 3D est lente.** Essayez dans cet ordre : Brume 0 % (si vous n'en avez pas besoin), moins de *Lumières max.* / *Ombres max.*, *Cônes de lumière simples max.* (par ex. 200), désactiver *Les projecteurs projettent des ombres*, qualité Basse ou Auto, une *Cadence max.* de 30, ou arrêter la simulation 3D tant que vous n'en avez pas besoin. Les scènes avec 100 projecteurs allumés ou plus sont exigeantes ; jusqu'à environ 16 projecteurs allumés en même temps, les valeurs par défaut suffisent.
- **Un projecteur ne bouge pas en 3D.** Son type a besoin d'un modèle 3D avec lyre / tête mobile et de canaux Pan / Tilt ; les types sans cela (panneaux LED, barres, blinders) restent immobiles. Le projecteur doit aussi être placé sur la scène (mode Projecteurs → *Tout placer*).
- **Un cône de lumière pointe dans le mauvais sens.** OpenCue retourne la direction automatiquement quand un fichier GDTF fait pointer le faisceau dans le boîtier. Si un type reste faux, notez son nom et signalez-le au développeur.

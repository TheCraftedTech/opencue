# Projecteurs perso (éditeur)

L'éditeur crée des appareils pour lesquels il n'existe pas de fichier GDTF adapté – une machine à fumée, un simple gradateur, un par RVB, un projecteur asservi. Le résultat est un **vrai fichier GDTF** (format GDTF 1.2, construit comme les fichiers de GDTF Share). Vous n'avez **pas** besoin d'un compte GDTF Share pour cela.

---

## 1. L'ouvrir

**Bibliothèque → Bibliothèque de projecteurs… → « Projecteur perso… ».** La fenêtre a la taille de la bibliothèque et comporte trois onglets : **Général**, **Modes et canaux**, **Image et 3D**.

- Modifier plus tard un type perso : cliquez sur **Modifier** dans la liste des types installés (uniquement pour les types créés avec l'éditeur, marqués « Perso · non vérifié »).
- Partir d'un type existant (**charger depuis un autre projecteur**) : dans l'éditeur, sur l'onglet *Général*, tout en haut, le choix **« Partir d'un projecteur existant »**, ou sur la carte dans la bibliothèque **Plus → Modifier une copie**. Sont repris : les données de base, les modes, les canaux, les noms de fonctions, les plages et l'image de profil. **Ne sont pas** repris : les roues (gobos, roues de couleur), la géométrie et les pièces 3D ; l'éditeur vous indique ce qui a été laissé de côté.

---

## 2. Général

| Champ | Signification |
|---|---|
| Fabricant, Nom | Obligatoires. Le nom de fichier devient `Fabricant@Nom@Eigen.gdtf`. Si le type existe déjà, l'éditeur vous le signale. |
| Nom court | Facultatif, 8 caractères au maximum. |
| Catégorie | Projecteur asservi, barre LED, par, gradateur, stroboscope, effet, autre – ou « Automatique » (détectée d'après les canaux). Vous pouvez filtrer la bibliothèque par catégorie. |
| Poids, Description | Facultatifs. |
| Étiquettes | Saisissez et appuyez sur **Entrée**. La bibliothèque les recherche aussi (p. ex. « fumée », « extérieur », « 12 V »). |
| Modèle | Pour les nouveaux types seulement : machine à fumée, gradateur, RVB, RVB + gradateur, projecteur asservi. |

---

## 3. Modes et canaux

Un **mode** est une disposition de canaux (beaucoup d'appareils en ont plusieurs, p. ex. « 3 canaux » et « 8 canaux »). **+ Mode (copie)** ajoute un autre mode comme copie du mode sélectionné ; changez son nom en haut à droite.

Pour chaque **canal** :

- **Attribut** – ce que fait le canal. La liste est classée en intensité, couleur, position, faisceau, effets (fumée, brouillard, ventilateur) et contrôle. Tout en bas, séparé : **Nom perso …** pour tout ce qui n'est pas dans la liste (p. ex. « Bulles »).
- **Libellé** – texte libre, p. ex. « Sortie de fumée ». Il apparaît dans le panneau de détail DMX direct.
- **8 / 16 bits** – un canal 16 bits utilise deux adresses DMX (poids fort + poids faible).
- **Valeur par défaut** (0–255) – la valeur de l'appareil lorsqu'il n'est pas piloté.
- **Plages** – des paliers nommés, p. ex. à partir de 0 « Arrêt », à partir de 10 « Fumée ». La première plage commence toujours à 0 ; chacune des autres se termine juste avant le début de la suivante. Pour le pan, le tilt et le zoom, vous saisissez en plus la plage d'angle en degrés.

Les flèches changent l'ordre ; les adresses DMX en sont déduites (à gauche de chaque ligne).

### Import CSV

**Importer un CSV…** lit une liste de canaux : une ligne par canal, avec une ligne d'en-tête. Colonnes (dans n'importe quel ordre, séparées par `;`, `,` ou tabulation) : `Attribute`, `Label`, `Bit`, `Default`, `Ranges`. Écrivez les plages sous la forme `0 Off; 10 Fog` ou `0-9 Off; 10-255 Fog` – si la cellule contient le séparateur, mettez-la entre guillemets :

```
Attribute;Label;Bit;Default;Ranges
Fog1;Fog output;8;0;"0 Off; 10 Fog"
Control1;Fan;8;0;"0-9 Off; 10-255 On"
```

---

## 4. Image et 3D

- **Image de profil** – n'importe quelle image ; elle est écrite dans le fichier au format PNG (512 pixels au maximum) et apparaît dans la bibliothèque.
- **Modèle 3D** – éventuellement un fichier `.glb`, `.3ds`, `.stl` ou `.obj` (25 Mo et 250 000 triangles au maximum ; STL et OBJ sont convertis en GLB) pour les appareils **fixes** ; la taille en mètres détermine la taille à laquelle il apparaît sur la scène 3D. Les projecteurs asservis (pan/tilt) reçoivent socle, lyre et tête comme pièces standard.

---

## 5. Transmettre le fichier

Chaque carte de la bibliothèque propose **Plus → Exporter le fichier (.gdtf)** et **Afficher dans le dossier** (uniquement sur l'ordinateur où tourne le programme). Le fichier peut être copié et ajouté sur un autre ordinateur avec **Importer un fichier GDTF…** – ou ouvert dans n'importe quel autre logiciel GDTF. La description de l'éditeur y est enregistrée comme fichier supplémentaire ; les autres programmes l'ignorent.

---

## 6. Bon à savoir

- Les types perso sont **non vérifiés** : contrôlez la disposition des canaux sur l'appareil réel.
- Si vous modifiez un type utilisé par le show, les changements s'appliquent immédiatement. Si le **nombre de canaux d'un mode utilisé** change (ou si un tel mode est supprimé ou renommé), l'éditeur affiche une **remarque** – elle n'empêche rien ; vérifiez ensuite les adresses DMX.
- **Annuler demande d'abord confirmation :** si vous avez modifié quelque chose, *Annuler*, la croix × et Échap ouvrent la boîte « Modifications non enregistrées » (*Continuer l'édition*, *Abandonner les modifications* ou *Enregistrer*). Sans modification, l'éditeur se ferme aussitôt.
- **Supprimer demande d'abord confirmation :** un mode, un canal, une plage, une image de profil ou un modèle 3D n'est supprimé qu'après confirmation.
- Le grand master et le blackout n'agissent que sur le **gradateur** (ou sur la couleur s'il n'y a pas de canal de gradateur) – un canal de fumée continue de tourner sans être affecté.
- Vous commandez la fumée, le brouillard et autres dans le contrôle du projecteur, sur l'onglet **DMX direct**. Survoler le libellé, cliquer dessus ou faire un clic droit sur un fader affiche les noms de fonctions et les plages du canal.

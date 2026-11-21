# Sauvegardes, verrous et fermeture sûre

Vous avez programmé le show avant l'événement et vous **n'enregistrez volontairement pas** pendant qu'il tourne – rien ne doit être écrasé par erreur. OpenCue vous protège de quatre façons : des **sauvegardes en arrière-plan**, la **restauration** après un plantage, un **verrou** pour les shows terminés et une **fenêtre de fermeture prudente**. Ce guide explique les quatre, et comment signaler un problème.

---

## 1. Sauvegardes en arrière-plan

OpenCue écrit régulièrement l'**état actuel de votre show** – y compris les modifications que vous n'avez *pas* enregistrées – dans un dossier caché. Vous ne le voyez que quand vous en avez besoin. Une sauvegarde **ne remplace jamais votre fichier de show**.

- **Quand :** toutes les **15 minutes** par défaut, mais **seulement si** le show a des modifications non enregistrées et que quelque chose a changé depuis la dernière sauvegarde. Rien n'a changé = rien n'est écrit.
- **Aussi :** quand vous quittez sans enregistrer, quand l'enregistrement a échoué (par exemple parce que le show est verrouillé), et juste avant d'ouvrir ou de démarrer un autre show alors que celui-ci a encore des modifications non enregistrées.
- **Combien :** les **10** plus récentes par show sont conservées, 100 au maximum au total ; les plus anciennes sont supprimées automatiquement.
- **Où :** le dossier `backups` dans le dossier de données (`%LOCALAPPDATA%\OpenCue\backups`). Une sauvegarde est un fichier de show ordinaire.

### Paramètres

**Paramètres → Général → Sauvegardes du show** :

| Paramètre | Signification |
|---|---|
| **Sauvegarder le show en arrière-plan** | Active ou désactive toute la fonction (par défaut : activée). |
| **Toutes les (minutes)** | L'intervalle, de 1 à 240 (par défaut 15). |
| **Conserver par show** | Combien de sauvegardes d'un même show sont conservées, de 1 à 50 (par défaut 10). |
| **Restaurer une sauvegarde...** / **Ouvrir le dossier** | Ouvre la fenêtre de restauration (section 2) ou le dossier dans l'Explorateur. |

Les paramètres s'appliquent à tout le programme et peuvent être modifiés depuis n'importe quel appareil, aussi depuis un appareil distant.

---

## 2. Restaurer une sauvegarde

**Fichier → Restaurer une sauvegarde...** (ou le bouton dans les paramètres) liste toutes les sauvegardes, les plus récentes d'abord : nom du show, heure, raison (automatique, à la fermeture, manuelle, avant une restauration, échec de l'enregistrement) et taille.

- **Restaurer** charge la sauvegarde comme un **show non enregistré**. Le fichier de show sur le disque reste exactement tel quel, même s'il est verrouillé. Puis **Enregistrer** (ou **Enregistrer le show sous...**) quand vous êtes satisfait.
- L'état que vous aviez avant est d'abord sauvegardé – une restauration ne peut donc rien faire perdre non plus.
- **Sauvegarder maintenant** fait une sauvegarde immédiate ; **Supprimer** en retire une. Tout cela fonctionne aussi depuis un appareil distant (*Ouvrir le dossier* y affiche l'Explorateur OpenCue).
- Shows, mises en page, scènes et paramètres sont écrits **en sécurité** : d'abord dans un fichier voisin, puis échangés – un plantage ou une coupure de courant en plein enregistrement ne peut pas détruire le fichier existant.

### Après un plantage

Si OpenCue n'a pas été fermé correctement (plantage, coupure de courant, tâche arrêtée), il **propose la dernière sauvegarde de cette session** au prochain démarrage : *« OpenCue n'a pas été fermé correctement … La restaurer ? »* – **Restaurer**, **Afficher toutes les sauvegardes** ou **Pas maintenant** (les sauvegardes restent disponibles sous *Fichier → Restaurer une sauvegarde...*).

---

## 3. Verrouiller un show

Un show terminé peut être **verrouillé** pour que personne ne le modifie par erreur. Dans le **gestionnaire de fichiers** (*Fichier → Gestionnaire de fichiers...*, type *Shows*), cliquez sur le **symbole de verrou** dans la ligne du show ; cliquez à nouveau pour déverrouiller.

Un show verrouillé :

- est marqué **Verrouillé** dans la liste et montre un petit **verrou** à côté du nom du show dans la barre du haut tant qu'il est chargé,
- **ne peut pas être écrasé, renommé ni supprimé** – l'enregistrement affiche *« Non enregistré : … est verrouillé »*,
- peut toujours être **chargé**, **dupliqué** (la copie n'est pas verrouillée) et enregistré sous **un autre nom** avec *Enregistrer le show sous...*.

Le verrou protège contre les faux pas, pas contre la copie : le fichier lui-même peut encore être modifié avec n'importe quel autre programme.

---

## 4. Quitter en sécurité

**Fichier → Quitter** (ou le bouton de fermeture) demande : **Enregistrer et quitter**, **Quitter sans enregistrer** ou **Annuler**.

Si le show **ne peut pas être enregistré** mais a des modifications – il est verrouillé, le fichier est protégé en écriture, le dossier n'est pas accessible en écriture ou le dernier enregistrement a échoué – la fenêtre change :

- Un **cadre orange** en haut dit *« Ce show ne peut pas être enregistré »* et nomme les raisons. Il indique aussi si une copie de sauvegarde de vos modifications est conservée.
- **Enregistrer une copie et quitter...** remplace *Enregistrer et quitter* : vous choisissez un nouveau nom, le show y est enregistré, puis OpenCue se ferme.
- **Quitter sans enregistrer** demande **deux clics** : le premier rend le bouton rouge (*« Cliquez encore : quitter et perdre les modifications »*), seul le second quitte.

Même alors, une sauvegarde de vos modifications est écrite à la fermeture (si les sauvegardes sont activées), de sorte que *Fichier → Restaurer une sauvegarde...* peut encore les ramener.

---

## 5. Signaler un problème

- **Aide → Ouvrir le dossier des journaux** ouvre le dossier contenant `opencue.log`.
- **Aide → Signaler un problème...** copie les **diagnostics** (version, système, dernières lignes du journal – sans jetons d'accès ni mots de passe) dans le presse-papiers et ouvre la page de signalement du projet dans votre navigateur. Décrivez ce que vous avez fait, collez les diagnostics.
- Les erreurs de l'interface utilisateur sont écrites dans le journal sous **OC-3601** ; une sauvegarde qui n'a pas pu être écrite sous **OC-3701** (voir le guide *Codes d'erreur*).

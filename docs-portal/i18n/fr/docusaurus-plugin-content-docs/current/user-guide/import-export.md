---
title: Import et export
sidebar_position: 7
---

# Import et export

Les prompts peuvent être exportés dans un fichier puis réimportés plus tard, que ce soit comme sauvegarde portable de votre propre bibliothèque ou pour déplacer des prompts entre instances.

## Formats d'export

Les prompts s'exportent en **CSV**, **Markdown** ou **JSON**. L'export JSON produit le format d'enveloppe propre à PromptVault, qui est aussi le format que l'importeur reconnaît automatiquement lors d'une réimportation.

## Modes d'import

Lors de l'import d'un fichier, vous choisissez comment il interagit avec vos prompts existants :

- **Ajout** — chaque prompt du fichier est ajouté, même si un prompt portant le même titre existe déjà (peut créer des doublons).
- **Fusion** — un prompt du fichier n'est ajouté que si aucun prompt existant ne porte déjà exactement ce titre ; sinon il est ignoré.
- **Remplacement** — toute votre bibliothèque de prompts existante est d'abord vidée, puis chaque prompt du fichier est ajouté. PromptVault crée automatiquement une sauvegarde avant l'exécution d'un import en remplacement, afin que l'état précédent ne soit pas perdu.

## L'état de partage n'est pas portable

L'import/export n'inclut jamais les droits de partage des prompts — voir [Partage](./sharing.md#exportimport-et-partage) pour comprendre pourquoi, et pour l'alternative recommandée quand cet état doit être préservé.

## Statistiques d'import et d'export

Une vue de statistiques d'import/export indique les chiffres d'utilisation actuels des deux opérations, utile pour confirmer qu'un import ou export volumineux s'est bien terminé comme prévu.

---
title: Import et export
sidebar_position: 7
---

# Import et export

Exportez des prompts pour déplacer leur contenu entre instances ou conserver une copie portable de votre bibliothèque. Un export n'est pas une sauvegarde complète : il ne conserve pas les droits de partage. Utilisez une sauvegarde complète lorsque vous devez préserver l'état de contrôle d'accès.

## Formats d'export

Les prompts s'exportent en **CSV**, **Markdown** ou **JSON**. L'export JSON produit le format d'enveloppe propre à PromptVault, qui est aussi le format que l'importeur reconnaît automatiquement lors d'une réimportation.

## Modes d'import

Avant l'import, identifiez le mode correspondant au résultat attendu. Choisissez **Remplacement** uniquement si vous voulez remplacer toute la bibliothèque.

- **Ajout** — chaque prompt du fichier est ajouté, même si un prompt portant le même titre existe déjà (peut créer des doublons).
- **Fusion** — un prompt du fichier n'est ajouté que si aucun prompt existant ne porte déjà exactement ce titre ; sinon il est ignoré.
- **Remplacement** — toute votre bibliothèque de prompts existante est d'abord vidée, puis chaque prompt du fichier est ajouté. PromptVault crée une sauvegarde avant l'import. Vérifiez que cette sauvegarde est terminée avant de compter sur elle pour récupérer la bibliothèque précédente.

## L'état de partage n'est pas portable

L'import/export n'inclut jamais les droits de partage des prompts — voir [Partage](./sharing.md#exportimport-et-partage) pour comprendre pourquoi, et pour l'alternative recommandée quand cet état doit être préservé.

## Statistiques d'import et d'export

Une vue de statistiques d'import/export indique les chiffres d'utilisation actuels des deux opérations, utile pour confirmer qu'un import ou export volumineux s'est bien terminé comme prévu.

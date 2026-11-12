---
title: Sauvegardes
sidebar_position: 2
---

# Sauvegardes

PromptVault inclut des fonctions de sauvegarde et de restauration pour les copies planifiées, la vérification d'intégrité, le chiffrement et le stockage cloud optionnel. Une sauvegarde aide à récupérer des données ; un export ne la remplace pas lorsque vous devez préserver les droits de partage.

## Sauvegardes planifiées

Les administrateurs configurent les sauvegardes automatiques depuis la page de gestion des sauvegardes. Choisissez une fréquence quotidienne, hebdomadaire ou mensuelle, ainsi qu'une heure, puis activez la planification. Si une sauvegarde planifiée doit démarrer alors qu'une autre est déjà en cours, PromptVault ignore la nouvelle exécution et enregistre cette décision.

La première sauvegarde d'une installation (ou la première après qu'une sauvegarde précédente devienne inutilisable) est toujours une sauvegarde complète ; les sauvegardes planifiées suivantes sont incrémentales, ne stockant que ce qui a changé depuis la dernière sauvegarde complète afin de limiter l'espace de stockage utilisé.

## Vérification d'intégrité

Le contenu de chaque sauvegarde est validé après sa création, et le résultat est enregistré. Une somme de contrôle est stockée avec les métadonnées de chaque sauvegarde afin de pouvoir revérifier son intégrité ultérieurement. Vous pouvez aussi déclencher manuellement un test d'intégrité sur une sauvegarde existante à tout moment depuis la page de gestion des sauvegardes — utile avant d'en avoir réellement besoin pour une restauration.

## Chiffrement

Les sauvegardes peuvent être chiffrées avec une clé que vous fournissez avant leur écriture sur le stockage ; PromptVault ne stocke jamais les clés de chiffrement en clair. La rotation des clés est prise en charge — les sauvegardes déjà chiffrées avec une clé précédente restent accessibles pendant la transition vers une nouvelle clé.

## Stockage cloud

Depuis la page de gestion des sauvegardes, configurez un fournisseur compatible S3, Google Drive ou Dropbox comme destination. PromptVault conserve une copie locale même lorsque l'envoi vers le cloud est configuré, et vous pouvez restaurer directement depuis le stockage cloud.

Les identifiants du fournisseur cloud (clé d'accès / clé secrète) sont chiffrés au repos à l'aide de `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` — voir [Configuration](../configuration/index.md#sauvegardes). Cette variable est requise avant de pouvoir ajouter un fournisseur cloud.

## Aperçu de restauration et restauration sélective

Avant d'appliquer une restauration, consultez l'aperçu : il liste les prompts qui seront ajoutés, modifiés ou supprimés. Sélectionnez uniquement les prompts à restaurer, ou restaurez la sauvegarde complète. N'appliquez pas la restauration avant de comprendre les changements listés.

## Rétention

Une période de rétention configurable (en jours) détermine quand les sauvegardes plus anciennes deviennent éligibles au nettoyage, afin que l'espace de stockage des sauvegardes ne croisse pas indéfiniment.

## Remarques pratiques

- Gardez `PROMPTVAULT_DATA_DIR` distinct par environnement (dev/staging/prod) — partager un répertoire de données entre environnements peut faire entrer en collision les sauvegardes et restaurations planifiées, puisqu'elles sont stockées relativement à ce répertoire.
- Testez occasionnellement une restauration, pas uniquement une sauvegarde. La vérification d'intégrité confirme que le fichier de sauvegarde est lisible ; un aperçu de restauration confirme qu'il contient les données attendues.

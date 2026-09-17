---
title: Sauvegardes
sidebar_position: 2
---

# Sauvegardes

PromptVault inclut un système de sauvegarde et de restauration couvrant la planification, la vérification d'intégrité, le chiffrement et le stockage cloud optionnel.

## Sauvegardes planifiées

Les administrateurs peuvent configurer des sauvegardes automatiques selon une fréquence quotidienne, hebdomadaire ou mensuelle, à une heure choisie. La planification peut être activée ou désactivée à tout moment. Si une sauvegarde planifiée devait démarrer alors qu'une autre est déjà en cours, le nouveau déclenchement est ignoré plutôt qu'exécuté en parallèle, et cet abandon est journalisé.

La première sauvegarde d'une installation (ou la première après qu'une sauvegarde précédente devienne inutilisable) est toujours une sauvegarde complète ; les sauvegardes planifiées suivantes sont incrémentales, ne stockant que ce qui a changé depuis la dernière sauvegarde complète afin de limiter l'espace de stockage utilisé.

## Vérification d'intégrité

Le contenu de chaque sauvegarde est validé après sa création, et le résultat est enregistré. Une somme de contrôle est stockée avec les métadonnées de chaque sauvegarde afin de pouvoir revérifier son intégrité ultérieurement. Vous pouvez aussi déclencher manuellement un test d'intégrité sur une sauvegarde existante à tout moment depuis la page de gestion des sauvegardes — utile avant d'en avoir réellement besoin pour une restauration.

## Chiffrement

Les sauvegardes peuvent être chiffrées avec une clé que vous fournissez avant leur écriture sur le stockage ; PromptVault ne stocke jamais les clés de chiffrement en clair. La rotation des clés est prise en charge — les sauvegardes déjà chiffrées avec une clé précédente restent accessibles pendant la transition vers une nouvelle clé.

## Stockage cloud

Vous pouvez configurer un fournisseur compatible S3, Google Drive ou Dropbox comme destination de sauvegarde depuis l'interface d'administration. Une copie locale est toujours conservée même lorsque l'envoi vers le cloud est configuré, et vous pouvez restaurer directement depuis le stockage cloud, pas uniquement depuis des sauvegardes locales.

Les identifiants du fournisseur cloud (clé d'accès / clé secrète) sont chiffrés au repos à l'aide de `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` — voir [Configuration](../configuration/index.md#sauvegardes). Cette variable est requise avant de pouvoir ajouter un fournisseur cloud.

## Aperçu de restauration et restauration sélective

Avant qu'une restauration ne soit appliquée, PromptVault affiche un aperçu détaillé de ce qui va exactement changer — prompts ajoutés, modifiés ou supprimés — plutôt que de restaurer à l'aveugle. Depuis cet aperçu, vous pouvez également sélectionner un sous-ensemble de prompts à restaurer plutôt que de restaurer l'intégralité de la sauvegarde.

## Rétention

Une période de rétention configurable (en jours) détermine quand les sauvegardes plus anciennes deviennent éligibles au nettoyage, afin que l'espace de stockage des sauvegardes ne croisse pas indéfiniment.

## Remarques pratiques

- Gardez `PROMPTVAULT_DATA_DIR` distinct par environnement (dev/staging/prod) — partager un répertoire de données entre environnements peut faire entrer en collision les sauvegardes et restaurations planifiées, puisqu'elles sont stockées relativement à ce répertoire.
- Testez occasionnellement une restauration, pas seulement une sauvegarde — la vérification d'intégrité confirme que le fichier de sauvegarde est lisible, mais un aperçu de restauration complet confirme que les données qu'il contient sont réellement celles attendues.

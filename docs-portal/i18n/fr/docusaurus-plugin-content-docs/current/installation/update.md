---
title: Mettre à jour PromptVault
description: Mettre à jour en toute sécurité une installation PromptVault auto-hébergée.
---

# Mettre à jour PromptVault

Suivez ces étapes pour mettre à jour l'installation Docker Compose décrite dans [Installation](index.md). La base de données conserve ses données pendant la reconstruction des services `web` et `docs`.

## Avant de commencer

1. Consultez les [notes de version](../release-notes/index.md) pour repérer les changements qui concernent votre installation.
2. Vérifiez que le serveur dispose d'assez d'espace pour une sauvegarde de la base et les nouvelles images.
3. Prévoyez une courte fenêtre de maintenance. Les utilisateurs pourraient ne pas pouvoir se connecter pendant le redémarrage de l'application.
4. Vérifiez que vous avez accès au dossier du projet PromptVault et au conteneur de base de données.

## 1. Sauvegarder la base de données

Créez et vérifiez une sauvegarde compressée avant de télécharger ou de démarrer la mise à jour. Exécutez ces commandes depuis le dossier du projet PromptVault :

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

La dernière commande doit se terminer sans erreur. Vérifiez que le fichier de sauvegarde n'est pas vide. Gardez-le dans `data/backups` pour une éventuelle restauration et copiez-en une seconde version dans un emplacement sûr en dehors du serveur. Ne continuez pas si la sauvegarde a échoué.

## 2. Télécharger et reconstruire

Depuis le dossier du projet PromptVault, choisissez la version à installer. Une étiquette de version (tag) identifie une version publiée. Choisissez-en une indiquée dans les notes de version :

```bash
git fetch --tags
git checkout <ETIQUETTE_VERSION>
```

Reconstruisez et démarrez les services de l'application et de la documentation :

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

La configuration du projet démarre `web` uniquement lorsque la base de données et Redis indiquent qu'ils sont prêts.

## 3. Mettre à jour la base de données

Une migration met à jour la structure de la base de données pour la nouvelle version de PromptVault. Exécutez la migration, puis vérifiez quelle version de migration est active :

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

La seconde commande doit afficher la version de migration active. Si la migration échoue, arrêtez-vous et consultez la page [Dépannage](../troubleshooting/index.md).

## 4. Vérifier la mise à jour

```bash
curl --fail http://localhost:8001/api/health
```

Le contrôle de santé doit répondre avec succès. Ouvrez PromptVault dans un navigateur, connectez-vous et vérifiez que vos prompts sont présents. Si vous utilisez le service de documentation, ouvrez-le aussi (adresse par défaut : `http://localhost:7876`).

## En cas de problème

Consultez les journaux des services pour repérer un message d'erreur :

```bash
docker compose logs --tail=100 web docs
```

Si une reconstruction sans cache échoue avec `No module named 'psycopg'`, utilisez PromptVault 1.13.1 ou une version ultérieure : cette version corrige le problème de dépendance décrit dans le [ticket #94](https://codeberg.org/medenor/promptvault/issues/94). Pour les autres erreurs, consultez la page [Dépannage](../troubleshooting/index.md).

### Revenir à la version précédente

Ces étapes restaurent la sauvegarde de la base créée avant la mise à jour et rétablissent la version précédente de l'application et de la documentation. La restauration remplace la base actuelle par la sauvegarde antérieure. Les prompts et autres changements effectués depuis cette sauvegarde seront perdus si vous ne sauvegardez pas d'abord la base actuelle.

Si vous avez créé ou modifié des prompts après la mise à jour, sauvegardez la base actuelle avant de la restaurer :

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Arrêtez ensuite l'application, choisissez dans les notes de version l'étiquette de la version précédente, puis reconstruisez ses images :

```bash
docker compose stop web
git fetch --tags
git checkout <ETIQUETTE_VERSION_PRECEDENTE>
docker compose build web docs
```

Restaurez la sauvegarde vérifiée d'avant la mise à jour. Remplacez `<NOM_FICHIER_SAUVEGARDE>` par le nom du fichier créé à l'étape 1. La première commande supprime le contenu actuel de la base avant de charger la sauvegarde :

```bash
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
set -euo pipefail
gzip -dc "data/backups/<NOM_FICHIER_SAUVEGARDE>" \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Redémarrez la version précédente et vérifiez que PromptVault fonctionne :

```bash
docker compose up -d web docs
curl --fail http://localhost:8001/api/health
```

Connectez-vous et vérifiez que vos prompts sont présents. Si la restauration ou le démarrage échoue, arrêtez-vous et consultez la page [Dépannage](../troubleshooting/index.md).

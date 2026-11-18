---
title: Mettre à jour PromptVault
description: Mettre à jour en toute sécurité une installation PromptVault auto-hébergée.
---

# Mettre à jour PromptVault

Suivez ces étapes pour mettre à jour l'installation Docker Compose décrite dans [Installation](index.md). La base de données conserve ses données pendant la reconstruction des services `web` et `docs`.

## Avant de commencer {#before-you-start}

1. Consultez les [notes de version](../release-notes/index.md) et `CHANGELOG.md` pour repérer les changements incompatibles et les notes de migration.
2. Vérifiez que le serveur dispose d'assez d'espace pour une sauvegarde de la base et les nouvelles images.
3. Testez d'abord la mise à jour sur une installation de test, si vous en avez une.
4. Prévoyez une courte fenêtre de maintenance. Les utilisateurs pourraient ne pas pouvoir se connecter pendant le redémarrage de l'application.
5. Vérifiez que vous avez accès au dossier du projet PromptVault et au conteneur de base de données.

## 1. Sauvegarder la base de données {#1-back-up-the-database}

Créez et vérifiez une sauvegarde compressée avant de télécharger ou de démarrer la mise à jour. Exécutez ces commandes depuis le dossier du projet PromptVault :

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

La dernière commande doit se terminer sans erreur. Vérifiez que le fichier de sauvegarde n'est pas vide. Gardez-le dans `data/backups` pour une éventuelle restauration et copiez-en une seconde version dans un emplacement sûr en dehors du serveur. Ne continuez pas si la sauvegarde a échoué.

## 2. Télécharger et reconstruire {#2-download-and-rebuild}

Depuis le dossier du projet PromptVault, récupérez la dernière version de la branche `main`. Pour installer une version stable précise, utilisez plutôt son étiquette de version.

```bash
git checkout main
git pull origin main
```

Pour installer une version publiée précise, récupérez et choisissez son étiquette :

```bash
git fetch --tags
git checkout <ETIQUETTE_VERSION>
```

Reconstruisez les services sans utiliser les couches en cache, puis remplacez le conteneur web. Laissez la base de données et Redis démarrés :

```bash
docker-compose build --no-cache
docker-compose stop web
docker-compose rm web
docker-compose up -d db redis
sleep 15
docker-compose up -d web docs
```

Après le démarrage de la base de données et de Redis, attendez 15 secondes pour laisser la base terminer son initialisation. Le projet attend également que les contrôles de santé de la base et de Redis réussissent avant de démarrer `web`.

## 3. Mettre à jour la base de données {#3-apply-database-updates}

Une migration met à jour la structure de la base de données pour la nouvelle version de PromptVault. Exécutez la migration, puis vérifiez quelle version de migration est active :

```bash
docker-compose exec -T web alembic upgrade head
docker-compose exec -T web alembic current
```

Exécutez cette migration uniquement après le démarrage de `web`. La seconde commande doit afficher la version de migration active. Si la migration échoue, arrêtez-vous et consultez la page [Dépannage](../troubleshooting/index.md).

## 4. Vérifier la mise à jour {#4-check-the-update}

```bash
docker-compose logs web | head -50
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Le contrôle de santé doit répondre avec succès. Ouvrez PromptVault dans un navigateur, connectez-vous et vérifiez que vos prompts sont présents. Si vous utilisez le service de documentation, ouvrez-le aussi (adresse par défaut : `http://localhost:7876`).

## En cas de problème {#if-something-goes-wrong}

Consultez les journaux des services pour repérer un message d'erreur :

```bash
docker-compose logs --tail=100 web docs
```

Si une reconstruction sans cache échoue avec `No module named 'psycopg'`, utilisez PromptVault 1.13.1 ou une version ultérieure : cette version corrige le problème de dépendance décrit dans le [ticket #94](https://github.com/Medenor/PromptVault/issues/94). Pour les autres erreurs, consultez la page [Dépannage](../troubleshooting/index.md).

### Revenir à la version précédente {#return-to-the-previous-version}

Ces étapes restaurent la sauvegarde de la base créée avant la mise à jour et rétablissent la version précédente de l'application et de la documentation. La restauration remplace la base actuelle par la sauvegarde antérieure. Les prompts et autres changements effectués depuis cette sauvegarde seront perdus si vous ne sauvegardez pas d'abord la base actuelle.

Arrêtez l’application avant de continuer :

```bash
docker-compose stop web
```

Si vous avez créé ou modifié des prompts après la mise à jour, sauvegardez la base actuelle avant de la restaurer :

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Restaurez la sauvegarde vérifiée d'avant la mise à jour. Remplacez `<NOM_FICHIER_SAUVEGARDE>` par le nom du fichier créé à l'étape 1, sans le préfixe de dossier `data/backups/`. Ces commandes suppriment et recréent la base avant de charger la sauvegarde :

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<NOM_FICHIER_SAUVEGARDE>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

Choisissez ensuite la version précédente et reconstruisez ses images sans utiliser les couches en cache :

```bash
git fetch --tags
git checkout <ETIQUETTE_VERSION_PRECEDENTE>
docker-compose build --no-cache
```

Redémarrez la version précédente et vérifiez les journaux ainsi que le point de santé :

```bash
docker-compose up -d web docs
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Connectez-vous et vérifiez que vos prompts sont présents. Si la restauration ou le démarrage échoue, arrêtez-vous et consultez la page [Dépannage](../troubleshooting/index.md).

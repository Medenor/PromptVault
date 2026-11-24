---
title: Mettre à jour PromptVault
description: Mettre à jour en toute sécurité une installation PromptVault auto-hébergée.
---

# Mettre à jour PromptVault

Suivez ces étapes pour mettre à jour l'installation Docker Compose décrite dans [Installation](index.md). La base de données conserve ses données pendant la reconstruction des services `web` et `docs`.

Si vos paramètres de production sont dans un fichier `.env.production` distinct (recommandé, voir [Configurer un environnement de production](production-setup.md)), indiquez-le une fois à Docker Compose avant de commencer. Toutes les commandes `docker-compose` de la même fenêtre de terminal l'utilisent ensuite :

```bash
export COMPOSE_ENV_FILES=.env.production
```

Exécutez les commandes de cette page dans cette fenêtre de terminal. Sans ce réglage, Docker Compose lit `.env` et vos valeurs de développement remplacent celles de production. Cela demande Docker Compose 2.24 ou une version ultérieure ; avec une version plus ancienne, voir [Configurer un environnement de production](production-setup.md#use-a-separate-environment-file).

## Avant de commencer {#before-you-start}

1. Consultez les [notes de version](../release-notes/index.md) et `CHANGELOG.md` pour repérer les changements incompatibles et les notes de migration.
2. Vérifiez que le serveur dispose d'assez d'espace pour une sauvegarde de la base et les nouvelles images.
3. Testez d'abord la mise à jour sur une installation de test, si vous en avez une.
4. Prévoyez une courte fenêtre de maintenance. Les utilisateurs pourraient ne pas pouvoir se connecter pendant le redémarrage de l'application.
5. Vérifiez que vous avez accès au dossier du projet PromptVault et au conteneur de base de données.

## 1. Sauvegarder la base de données {#1-back-up-the-database}

Créez une sauvegarde compressée de la base de données et vérifiez que l'archive est intacte avant de télécharger ou de démarrer la mise à jour. Exécutez ces commandes depuis le dossier du projet PromptVault :

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

La dernière commande doit se terminer sans erreur. Vérifiez que le fichier de sauvegarde n'est pas vide. Gardez-le dans `data/backups` pour une éventuelle restauration et copiez-en une seconde version dans un emplacement sûr en dehors du serveur. Ne continuez pas si la sauvegarde a échoué. La commande `gzip -t` montre que le fichier n'est pas endommagé ; elle ne teste pas une restauration.

Étiquetez ensuite l'image que votre conteneur de production exécute actuellement, afin de pouvoir y revenir sans reconstruire. L'*image* est la copie empaquetée de PromptVault que le conteneur exécute. Utilisez l'identifiant d'image du conteneur plutôt que `:latest` : l'étiquette `:latest` de votre machine peut déjà pointer vers une version plus récente.

```bash
docker tag "$(docker inspect promptvault-web --format '{{.Image}}')" promptvault-web:pre-update
docker run --rm --entrypoint python promptvault-web:pre-update -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

La seconde commande doit afficher la version que vous exécutez actuellement. Si elle affiche une autre version, ne continuez pas : vérifiez le nom du conteneur avec `docker-compose ps`, puis relancez la première commande.

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
# Dernières lignes du journal : cherchez des erreurs
docker-compose logs web | head -50
# Contrôle de santé : doit réussir
curl --fail http://localhost:8001/api/health
# Nombre de prompts : doit correspondre à ce que vous attendez
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
# Version en cours d'exécution : doit être la nouvelle version
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
# Paramètres utilisés : la production exige ENVIRONMENT=production et DISABLE_RATE_LIMITING=false
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

La réponse du contrôle de santé n'indique pas la version : utilisez la commande de version pour confirmer la mise à jour. Ouvrez PromptVault dans un navigateur, connectez-vous et vérifiez que vos prompts sont présents. Si vous utilisez le service de documentation, ouvrez-le aussi (adresse par défaut : `http://localhost:7876`).

## En cas de problème {#if-something-goes-wrong}

Consultez les journaux des services pour repérer un message d'erreur :

```bash
docker-compose logs --tail=100 web docs
```

Si le conteneur `web` redémarre en boucle avec `No module named 'psycopg'` sur PostgreSQL, consultez [Dépannage](../troubleshooting/index.md#psycopg-missing). Pour les autres erreurs, consultez la page [Dépannage](../troubleshooting/index.md).

### Revenir à la version précédente {#return-to-the-previous-version}

Revenez à l'image que vous avez étiquetée à l'étape 1 (`promptvault-web:pre-update`). Suivez ces étapes dans l'ordre.

**1. Démarrez l'image précédente.**

```bash
docker tag promptvault-web:pre-update promptvault-web:latest
docker-compose up -d --no-build web
docker-compose logs web --tail=20
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

La dernière commande doit afficher la version précédente. Vérifiez le point de santé (`curl --fail http://localhost:8001/api/health`), connectez-vous et vérifiez que vos prompts sont présents. Si tout fonctionne et que la mise à jour n'a exécuté aucune migration de base de données, c'est terminé. La ligne « Mise à jour » des [notes de version](../release-notes/index.md) de la version installée indique si elle a exécuté des migrations ; beaucoup de versions n'en ont aucune. Si c'est le cas, passez à l'étape 2.

**2. Arrêtez l'application.** Faites-le uniquement si vous restaurez la base de données.

```bash
docker-compose stop web
```

**3. Sauvegardez la base actuelle (facultatif).**

Si vous avez créé ou modifié des prompts après la mise à jour, sauvegardez la base actuelle avant de la restaurer :

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

**4. Restaurez la sauvegarde.** La restauration remplace la base actuelle : les prompts et autres changements effectués depuis la sauvegarde sont perdus si vous ne les avez pas sauvegardés à l'étape 3.

Restaurez la sauvegarde vérifiée d'avant la mise à jour. Remplacez `<NOM_FICHIER_SAUVEGARDE>` par le nom du fichier créé à l'étape 1, sans le préfixe de dossier `data/backups/`. Ces commandes suppriment et recréent la base avant de charger la sauvegarde :

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<NOM_FICHIER_SAUVEGARDE>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

**5. Redémarrez l'image précédente et vérifiez-la.**

```bash
docker-compose up -d --no-build web
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Connectez-vous et vérifiez que vos prompts sont présents. Si la restauration ou le démarrage échoue, arrêtez-vous et consultez la page [Dépannage](../troubleshooting/index.md).

**Si vous n'avez pas étiqueté d'image à l'étape 1,** extrayez l'étiquette de la version précédente (`git fetch --tags`, puis `git checkout <ETIQUETTE_VERSION_PRECEDENTE>`) et exécutez `docker-compose build` sans `--no-cache`. Docker peut réutiliser les couches de dépendances en cache, mais rien ne le garantit : vérifiez la version et le démarrage de l'application avant de vous y fier.

Ne revenez pas en arrière en extrayant l'ancienne version et en reconstruisant avec `--no-cache`. La construction réinstalle ses dépendances : le résultat peut donc différer de l'image que vous utilisiez, et certaines versions ne peuvent plus être reconstruites. Une image construite à partir du code source de la version 1.16.0, par exemple, plante avec PostgreSQL.

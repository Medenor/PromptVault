---
title: Configurer un environnement de production
description: Séparer les paramètres de production de ceux de développement et remplacer le mot de passe de base de données par défaut.
---

# Configurer un environnement de production

Suivez ces étapes sur le serveur qui exécute PromptVault avec Docker Compose. Docker Compose lit le fichier `.env` situé à côté de `docker-compose.yml`, le même que vous utilisez pour le développement : un paramètre de développement comme `ENVIRONMENT=development` ou `DISABLE_RATE_LIMITING=true` peut donc atteindre vos conteneurs de production. Ces étapes placent les paramètres de production dans un fichier distinct.

## Utiliser un fichier d'environnement distinct {#use-a-separate-environment-file}

Exécutez ces commandes depuis le dossier du projet PromptVault. Vérifiez que Git ignore le nouveau fichier avant qu'il ne contienne des secrets :

```bash
echo '.env.production' >> .gitignore
cp .env .env.production

sed -i.bak \
  -e 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' \
  -e 's/^LOG_LEVEL=.*/LOG_LEVEL=WARNING/' \
  -e 's/^DISABLE_RATE_LIMITING=.*/DISABLE_RATE_LIMITING=false/' \
  .env.production && rm .env.production.bak
grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)=' .env.production
```

La dernière commande doit afficher `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` et `DISABLE_RATE_LIMITING=false`. Si une variable manque dans le résultat, ajoutez-la à `.env.production`.

Indiquez à Docker Compose d'utiliser le nouveau fichier. Faites-le une fois dans chaque fenêtre de terminal utilisée pour la production : toutes les commandes `docker-compose` de cette fenêtre l'utilisent ensuite :

```bash
export COMPOSE_ENV_FILES=.env.production
docker-compose up -d
```

`COMPOSE_ENV_FILES` demande Docker Compose 2.24 ou une version ultérieure (vérifiez avec `docker-compose version`). Avec une version plus ancienne, ajoutez plutôt `--env-file .env.production` à chaque commande `docker-compose`.

Docker Compose ne transmet que ces variables du fichier aux conteneurs :

- `ENVIRONMENT`, `LOG_LEVEL`, `DISABLE_RATE_LIMITING` et `POSTGRES_PASSWORD`
- `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` et `JWT_REFRESH_TOKEN_EXPIRE_SECONDS`
- `DOCS_APP_URL` et `VITE_DOCS_PORTAL_URL`

Les autres valeurs de `.env` (comme `DATABASE_URL`) ne servent que lorsque vous exécutez PromptVault directement sur un ordinateur, pas avec Docker Compose. La page [Configuration](../configuration/index.md) décrit chaque variable.

`ENVIRONMENT=production` peut appliquer un comportement plus strict qu'en développement. Après le changement, lisez `docker-compose logs --tail 30 web` et corrigez ce qui y est signalé.

## Vérifier les paramètres utilisés {#check-the-settings-in-use}

Affichez les paramètres que le conteneur en cours d'exécution utilise :

```bash
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

Le résultat doit afficher `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` et `DISABLE_RATE_LIMITING=false`. S'il affiche des valeurs de développement, le conteneur a été démarré sans le fichier de production : définissez `COMPOSE_ENV_FILES` comme ci-dessus, puis relancez `docker-compose up -d`.

`docker-compose config` affiche `POSTGRES_PASSWORD` en clair : ne collez donc sa sortie nulle part.

## Remplacer le mot de passe de base de données par défaut {#replace-the-default-database-password}

Si `POSTGRES_PASSWORD` n'est pas défini, Docker Compose utilise silencieusement `changeme`. Seuls les conteneurs du même réseau Docker peuvent atteindre la base de données, mais remplacez quand même cette valeur par défaut.

PostgreSQL ne lit `POSTGRES_PASSWORD` qu'à la première création du volume de données : modifier la variable seule ne change **pas** le mot de passe d'une base existante. Changez-le d'abord dans la base, puis dans Compose :

```bash
# 1. Générez un mot de passe sans caractères spéciaux (il fait partie d'une URL de connexion)
NEWPW=$(openssl rand -hex 24)

# 2. Changez-le dans la base de données
docker exec promptvault-db psql -U promptvault -d promptvault -c "ALTER USER promptvault PASSWORD '$NEWPW'"

# 3. Enregistrez-le pour Compose et recréez immédiatement les conteneurs
echo "POSTGRES_PASSWORD=$NEWPW" >> .env.production
docker-compose up -d
```

Faites-le à un moment calme : entre les étapes 2 et 3, le conteneur web conserve l'ancien mot de passe et les nouvelles connexions échouent pendant quelques secondes. Faites une nouvelle sauvegarde ensuite.

Vérifiez le résultat depuis le conteneur web, et non depuis le conteneur de base de données : l'image de la base fait confiance aux connexions établies depuis l'intérieur de son propre conteneur, donc un test à cet endroit accepte n'importe quel mot de passe. Exécutez les deux commandes :

```bash
# L'ancien mot de passe doit être rejeté
docker exec promptvault-web python -c "import psycopg; psycopg.connect(host='db', user='promptvault', password='changeme', dbname='promptvault', connect_timeout=5)" >/dev/null 2>&1 && echo "old password: ACCEPTED" || echo "old password: rejected"

# Le mot de passe actuel doit fonctionner
docker exec promptvault-web python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)" >/dev/null 2>&1 && echo "current password: works" || echo "current password: FAILED"
```

Résultat attendu : `old password: rejected`, puis `current password: works`. Si le mot de passe remplacé n'était pas `changeme`, indiquez-le à la place dans la première commande.

Conservez `.env.production` en lieu sûr, par exemple dans un gestionnaire de mots de passe : il contient la seule copie du mot de passe en dehors de la base.

---
title: Installation
sidebar_position: 1
---

# Installation

PromptVault est une application auto-hébergée : vous l'exécutez sur une infrastructure que vous contrôlez. Choisissez l'assistant de configuration s'il doit créer les éléments requis de manière interactive. Choisissez le parcours manuel uniquement si vous savez modifier des variables d'environnement et exécuter des commandes Docker.

## Prérequis {#prerequisites}

- Python 3.14+
- PostgreSQL 15+ (recommandé en production) ou SQLite (suffisant pour le développement/usage mono-utilisateur)
- Docker et Docker Compose (méthode de déploiement recommandée)
- Git

## Démarrage rapide avec l'assistant de configuration {#quick-start-with-the-setup-wizard}

Le moyen le plus rapide d'obtenir une instance fonctionnelle est l'assistant de configuration intégré. Il crée les clés de signature JSON Web Token (JWT), configure l'environnement, initialise la base de données et crée un compte administrateur.

```bash
git clone https://github.com/Medenor/PromptVault.git
cd PromptVault
pip install -e ".[setup]"
python scripts/setup/setup.py
```

Suivez les instructions. Une fois terminé, ouvrez l'adresse affichée et connectez-vous avec les identifiants administrateur créés.

## Configuration manuelle avec Docker Compose {#manual-docker-compose-setup}

Utilisez ce parcours uniquement si vous devez contrôler chaque paramètre. Exécutez les commandes dans l'ordre : les suivantes utilisent les fichiers et services créés par les précédentes.

```bash
# Cloner le dépôt
git clone https://github.com/Medenor/PromptVault.git
cd PromptVault

# Configurer l'environnement
cp .env.example .env
# Modifiez .env selon vos besoins et définissez un mot de passe de base de données robuste.
# Sans POSTGRES_PASSWORD, Docker Compose utilise silencieusement « changeme ».
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)" >> .env

# Générer les clés de signature JWT pour l'authentification
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem

# Faire pointer .env vers les clés générées
echo "JWT_PRIVATE_KEY_PATH=$(pwd)/es256-private.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=$(pwd)/es256-public.pem" >> .env

# Démarrer les services (PostgreSQL + PromptVault)
docker-compose up -d

# Exécuter les migrations de base de données
docker-compose exec web alembic upgrade head

# Créer l'utilisateur administrateur par défaut
docker-compose exec web python scripts/create_admin_user.py

# (Optionnel) Migrer des données JSON existantes
docker-compose exec web python scripts/migrate_json_to_db.py
```

`.env.example` est un modèle de développement (`ENVIRONMENT=development`), et Docker Compose transmet certaines de ses valeurs aux conteneurs. Pour un serveur de production, créez plutôt un fichier `.env.production` distinct : voir [Fichier d'environnement de production](production-setup.md).

Une fois les conteneurs démarrés, ouvrez `http://localhost:8001` et connectez-vous avec les identifiants administrateur créés. Si la page ne s'ouvre pas, consultez [Dépannage](../troubleshooting/index.md) avant de modifier des données ou des volumes Docker.

## Compiler depuis les sources {#building-from-source}

Si vous développez en local plutôt que de déployer via Docker, le `Makefile` du dépôt encapsule l'ensemble du flux de compilation/test/lint :

```bash
make install   # dépendances backend (.venv) + frontend (npm)
make dev       # backend sur le port :8003, serveur de développement frontend sur :5173
make build     # ressources frontend de production + image Docker
```

Consultez le `docs/DEVELOPMENT.md` du projet pour la liste complète des cibles, les variables d'environnement et les problèmes courants si une étape ne se comporte pas comme prévu.

## Créer l'utilisateur administrateur {#creating-the-admin-user}

Chaque nouvelle installation nécessite au moins un compte administrateur :

```bash
# Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# En local
python scripts/create_admin_user.py
```

Le script demande un nom d'utilisateur, une adresse e-mail et un mot de passe. Il vérifie que le mot de passe respecte la politique configurée, puis crée un utilisateur avec tous les droits administrateur. Conservez ces identifiants en lieu sûr.

- Pour mettre à jour une installation existante, suivez le guide [Mettre à jour PromptVault](update.md).
## Étapes suivantes {#next-steps}

- Consultez la [Référence de configuration](../configuration/index.md) pour les variables d'environnement que vous voudrez probablement ajuster (limites de débit, expiration des sessions, stockage des sauvegardes).
- Si quelque chose ne se comporte pas comme attendu, consultez le [Dépannage](../troubleshooting/index.md).

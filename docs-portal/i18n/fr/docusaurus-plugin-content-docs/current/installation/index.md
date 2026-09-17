---
title: Installation
sidebar_position: 1
---

# Installation

PromptVault est une application auto-hébergée. Cette page couvre les deux méthodes prises en charge pour la mettre en route : l'assistant de configuration automatisé et un déploiement manuel via Docker Compose.

## Prérequis

- Python 3.14+
- PostgreSQL 15+ (recommandé en production) ou SQLite (suffisant pour le développement/usage mono-utilisateur)
- Docker et Docker Compose (méthode de déploiement recommandée)
- Git

## Démarrage rapide avec l'assistant de configuration

Le moyen le plus rapide d'obtenir une instance fonctionnelle est l'assistant de configuration intégré, qui gère de façon interactive la génération des clés JWT, la configuration de l'environnement, la mise en place de la base de données et la création de l'utilisateur administrateur.

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
python scripts/setup/setup.py
```

Suivez les instructions. Une fois terminé, PromptVault est déployé et prêt à l'emploi.

## Configuration manuelle avec Docker Compose

Si vous préférez configurer chaque étape vous-même :

```bash
# Cloner le dépôt
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault

# Configurer l'environnement
cp .env.example .env
# Modifiez .env et définissez POSTGRES_PASSWORD (et d'autres valeurs si besoin)

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

Une fois les conteneurs démarrés, ouvrez `http://localhost:8001` et connectez-vous avec les identifiants administrateur que vous venez de créer.

## Compiler depuis les sources

Si vous développez en local plutôt que de déployer via Docker, le `Makefile` du dépôt encapsule l'ensemble du flux de compilation/test/lint :

```bash
make install   # dépendances backend (.venv) + frontend (npm)
make dev       # backend sur le port :8003, serveur de développement frontend sur :5173
make build     # ressources frontend de production + image Docker
```

Consultez le `docs/DEVELOPMENT.md` du projet pour la liste complète des cibles, les variables d'environnement et les problèmes courants si une étape ne se comporte pas comme prévu.

## Créer l'utilisateur administrateur

Chaque nouvelle installation nécessite au moins un compte administrateur :

```bash
# Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# En local
python scripts/create_admin_user.py
```

Le script demande un nom d'utilisateur, une adresse e-mail et un mot de passe, vérifie que le mot de passe respecte la politique configurée, puis crée un utilisateur avec tous les droits administrateur. Conservez ces identifiants en lieu sûr.

## Étapes suivantes

- Consultez la [Référence de configuration](../configuration/index.md) pour les variables d'environnement que vous voudrez probablement ajuster (limites de débit, expiration des sessions, stockage des sauvegardes).
- Si quelque chose ne se comporte pas comme attendu, consultez le [Dépannage](../troubleshooting/index.md).

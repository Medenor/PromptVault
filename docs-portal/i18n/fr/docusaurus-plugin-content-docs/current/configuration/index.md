---
title: Configuration
sidebar_position: 2
---

# Référence de configuration

PromptVault se configure par des variables d'environnement, généralement définies dans le fichier `.env` à la racine du dépôt. Commencez par copier `.env.example`. Cette page est une référence pour les administrateurs : modifiez une valeur seulement si vous connaissez le résultat recherché, puis redémarrez le service concerné et vérifiez qu'il démarre correctement.

Termes utilisés ci-dessous : une URL est une adresse permettant de joindre un service ; SQL est le langage de requête de la base de données ; Redis est le service qui applique les limites de débit ; SMTP est le protocole d'envoi d'e-mails.

## Base de données

| Variable | Valeur par défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data-dev/promptvault.db` | Chaîne de connexion. Utilisez une URL `postgresql://` en production. |
| `DB_POOL_SIZE` | `20` | Taille du pool de connexions (ignoré pour SQLite). |
| `DB_POOL_TIMEOUT` | `30` | Délai d'attente pour obtenir une connexion du pool, en secondes. |
| `DB_POOL_RECYCLE` | `3600` | Secondes avant qu'une connexion du pool ne soit recyclée. |
| `DB_ECHO` | `false` | Journalise chaque instruction SQL — utile pour le débogage, bruyant en production. |

## Application

| Variable | Valeur par défaut | Rôle |
|---|---|---|
| `ENVIRONMENT` | `development` | L'une des valeurs `development`, `testing`, `production`. |
| `PROMPTVAULT_DATA_DIR` | `./data-dev` | Répertoire des fichiers de données, sauvegardes et journaux. **Utilisez un chemin distinct par environnement** (dev/staging/prod), même s'ils partagent un système de fichiers — partager un répertoire de données entre environnements peut faire entrer en collision les sauvegardes et restaurations planifiées. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`. |
| `AUDIT_LOG_LEVEL` | `INFO` | Niveau de journalisation spécifique aux événements d'audit de contrôle de version et de sauvegarde. |

## Authentification

| Variable | Valeur par défaut | Rôle |
|---|---|---|
| `AUTH_ENABLED` | `true` | À définir sur `false` uniquement pour un déploiement mono-utilisateur de confiance et non exposé au réseau — cela désactive la connexion et rend chaque point de terminaison public. |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | — | Chemins vers la paire de clés ES256 utilisée pour signer et vérifier les JSON Web Tokens (JWT). Générez-la avec les commandes indiquées dans l'[Installation](../installation/index.md). |
| `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `900` (15 min) | Durée de vie du jeton d'accès. |
| `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `604800` (7 jours) | Durée de vie du jeton de rafraîchissement. |
| `TOTP_ENCRYPTION_KEY` | — | Secret côté serveur qui chiffre au repos les secrets de deux facteurs (TOTP). Obligatoire dès qu'un utilisateur active la 2FA. Générez-la avec `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Ne la changez jamais sans plan de migration : la changer invalide les configurations 2FA existantes. |
| `MAX_LOGIN_ATTEMPTS` | `5` | Nombre de tentatives échouées avant verrouillage du compte. |
| `ACCOUNT_LOCKOUT_DURATION_SECONDS` | `900` | Durée du verrouillage. |
| `MAX_SESSIONS_PER_USER` | `5` | Nombre maximal de sessions simultanées (`0` = illimité). |
| `SESSION_INACTIVE_TIMEOUT_SECONDS` | `2592000` (30 jours) | Expiration d'une session inactive. |

Les variables de politique de mot de passe `PASSWORD_MIN_LENGTH`, `PASSWORD_REQUIRE_UPPERCASE`, `PASSWORD_REQUIRE_LOWERCASE`, `PASSWORD_REQUIRE_DIGIT` et `PASSWORD_REQUIRE_SPECIAL` sont également configurables. Par défaut, elles exigent au moins 12 caractères et les quatre classes de caractères.

## Limitation de débit

Les limites de débit sont appliquées par utilisateur (avec repli par IP pour les requêtes anonymes) et regroupées en catégories, chacune réglable indépendamment :

| Catégorie | Valeur par défaut | Préfixe des variables |
|---|---|---|
| Lecture (requêtes GET) | 300/min | `RATE_LIMIT_READ_*` |
| Écriture (création/mise à jour/suppression/restauration) | 60/min | `RATE_LIMIT_WRITE_*` |
| Coûteuses (import/export, création/restauration/vérification de sauvegarde) | 10/min | `RATE_LIMIT_EXPENSIVE_*` |
| En masse (suppression en masse, suppression de toutes les sauvegardes, compression) | 5/min | `RATE_LIMIT_BULK_*` |

Chaque catégorie possède des variables `_ATTEMPTS` et `_WINDOW_SECONDS`, par exemple `RATE_LIMIT_WRITE_ATTEMPTS=60` et `RATE_LIMIT_WRITE_WINDOW_SECONDS=60`. Les points de terminaison d'authentification (connexion, inscription et réinitialisation de mot de passe) ont des limites distinctes : `RATE_LIMIT_LOGIN_*`, `RATE_LIMIT_REGISTER_*` et `RATE_LIMIT_PASSWORD_RESET_*`. La limitation de débit fonctionne uniquement si le service Redis indiqué par `REDIS_URL` est accessible. Si vous n'exécutez pas Redis, ne supposez pas que ces limites sont actives.

## E-mail (réinitialisation du mot de passe)

| Variable | Rôle |
|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS` | Connexion au serveur SMTP. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Identifiants SMTP. |
| `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` | Identité de l'expéditeur des e-mails sortants. |
| `PASSWORD_RESET_TOKEN_EXPIRE_SECONDS` | `3600` par défaut — durée de validité d'un lien de réinitialisation. |
| `APP_BASE_URL` | URL de base utilisée pour construire le lien de réinitialisation envoyé par e-mail. |

## Sauvegardes

| Variable | Rôle |
|---|---|
| `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` | Requis uniquement si vous configurez un stockage de sauvegarde dans le cloud — chiffre au repos les identifiants du fournisseur stockés (clés d'accès/secrètes). Générez-en une avec `python -c "import secrets; print(secrets.token_hex(32))"` et ne la validez jamais dans le contrôle de version. |

Voir [Sauvegardes](../user-guide/backups.md) pour comprendre comment planification, chiffrement et stockage cloud s'articulent.

## Ressources frontend

| Variable | Valeur par défaut | Rôle |
|---|---|---|
| `USE_VITE_ASSETS` | `false` | À définir sur `true` pour servir le CSS/JS depuis les artefacts compilés par Vite plutôt que depuis les sources. |

## Exemple : production PostgreSQL

```bash
DATABASE_URL=postgresql://promptvault_user:secure_password@localhost:5432/promptvault_prod
DB_POOL_SIZE=30
DB_POOL_TIMEOUT=60
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

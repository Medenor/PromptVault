---
title: Dépannage
sidebar_position: 4
---

# Dépannage

Cette page couvre les problèmes les plus fréquemment rencontrés lors de l'installation ou de l'exécution de PromptVault. Pour une couverture exhaustive, consultez `docs/TROUBLESHOOTING.md` dans le dépôt.

## Port déjà utilisé

Si le port `8001` (web), `5432` (PostgreSQL) ou `6379` (Redis) est déjà occupé par un autre processus, `docker-compose up` échouera à démarrer ce service. Arrêtez le processus en conflit, ou modifiez le port associé dans votre `.env`/`docker-compose.yml` avant de réessayer.

## Le démon Docker n'est pas en cours d'exécution

Les commandes `docker-compose` échouent avec une erreur de connexion si Docker lui-même n'est pas en cours d'exécution. Démarrez Docker Desktop (ou le service `docker` sous Linux) puis réessayez.

## Échec de connexion à la base de données

Si PromptVault ne parvient pas à joindre PostgreSQL au démarrage :

- Vérifiez que le conteneur/service est bien en cours d'exécution (`docker-compose ps`).
- Vérifiez que `DATABASE_URL` dans `.env` correspond bien aux identifiants et à l'hôte/port sur lesquels PostgreSQL écoute réellement.
- Si vous venez de changer `POSTGRES_PASSWORD`, notez que les conteneurs existants avec un volume de données déjà initialisé ne prendront pas automatiquement en compte le nouveau mot de passe — il peut être nécessaire de recréer le volume pour une installation propre, ou de mettre à jour le mot de passe directement dans la base existante.

## Échecs de migration

Si `alembic upgrade head` échoue en cours de route :

- Relancez-la — la plupart des migrations sont conçues pour être idempotentes.
- Si une migration échoue spécifiquement sur une base SQLite neuve avec une erreur SQL propre à PostgreSQL, vous utilisez probablement une version obsolète — des versions récentes ont corrigé des migrations utilisant du SQL spécifique à un dialecte non portable, assurez-vous donc de ne pas exécuter un commit plus ancien.
- Ne modifiez jamais le schéma de la base de données à la main pour contourner un échec de migration — ouvrez plutôt un ticket avec l'erreur exacte, car des modifications manuelles du schéma rendent les migrations futures imprévisibles.

## Erreurs de clé JWT

Si l'application échoue au démarrage en signalant des clés JWT manquantes ou invalides, vérifiez que `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` pointent vers une paire de clés ES256 valide générée avec :

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Des clés générées avec une autre courbe ou un autre algorithme ne fonctionneront pas — PromptVault attend spécifiquement du ES256 (P-256/prime256v1).

## Verrouillage après échecs de connexion

Des tentatives de connexion échouées répétées déclenchent un verrouillage temporaire du compte (`MAX_LOGIN_ATTEMPTS`, 5 tentatives par défaut, `ACCOUNT_LOCKOUT_DURATION_SECONDS`, 15 minutes par défaut). Attendez la fin de la période de verrouillage, ou demandez à un administrateur de la réinitialiser, plutôt que de réessayer sans cesse — réessayer pendant un verrouillage ne réinitialise pas le minuteur plus tôt.

## Erreurs de limitation de débit (429)

Si des opérations en masse, des imports/exports ou des actions de sauvegarde renvoient `429 Too Many Requests`, vous avez atteint l'une des catégories de limitation de débit par utilisateur décrites dans [Configuration](../configuration/index.md#limitation-de-débit). La réponse inclut un en-tête `Retry-After` ; attendez ce délai, ou demandez à un administrateur d'augmenter la variable `RATE_LIMIT_*` correspondante si la valeur par défaut est réellement trop basse pour votre usage.

## L'import/export ne restaure pas le partage

Si vous importez un fichier précédemment exporté et que les prompts partagés redeviennent privés sans aucune autorisation, c'est normal — l'export/import ne conserve volontairement pas l'état de partage (voir [Partage de prompts](../user-guide/sharing.md#exportimport-et-partage)). Utilisez plutôt une sauvegarde/restauration complète si vous avez besoin de conserver le partage.

## Toujours bloqué ?

Consultez le `docs/TROUBLESHOOTING.md` complet dans le dépôt, ou ouvrez un ticket sur [Codeberg](https://codeberg.org/medenor/promptvault) avec le message d'erreur exact et la commande exécutée.

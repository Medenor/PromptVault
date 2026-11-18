---
title: Dépannage
sidebar_position: 4
---

# Dépannage

Utilisez cette page pour identifier le symptôme, effectuer le plus petit changement sûr, puis réessayer. Ne supprimez pas une base de données ou un volume Docker lors du dépannage d'une installation existante. Pour une couverture exhaustive, consultez `docs/TROUBLESHOOTING.md` dans le dépôt.

## Port déjà utilisé {#port-already-in-use}

Si le port `8001` (web), `5432` (PostgreSQL) ou `6379` (Redis) est déjà occupé par un autre processus, `docker-compose up` échouera à démarrer ce service. Arrêtez le processus en conflit, ou modifiez le port associé dans votre `.env`/`docker-compose.yml` avant de réessayer.

## Le démon Docker n'est pas en cours d'exécution {#docker-daemon-not-running}

Les commandes `docker-compose` échouent avec une erreur de connexion si Docker lui-même n'est pas en cours d'exécution. Démarrez Docker Desktop (ou le service `docker` sous Linux) puis réessayez.

## Échec de connexion à la base de données {#database-connection-failed}

Si PromptVault ne parvient pas à joindre PostgreSQL au démarrage :

- Vérifiez que le conteneur ou le service est en cours d'exécution avec `docker-compose ps`.
- Vérifiez que `DATABASE_URL` dans `.env` correspond bien aux identifiants et à l'hôte/port sur lesquels PostgreSQL écoute réellement.
- Si vous avez modifié `POSTGRES_PASSWORD`, un volume de données existant déjà initialisé ne change pas automatiquement de mot de passe. Pour une installation existante, mettez à jour le mot de passe dans la base de données selon votre procédure établie. Recréez un volume uniquement pour une nouvelle installation sans données à conserver.

## Échecs de migration {#migration-failures}

Si `alembic upgrade head` échoue en cours de route :

- Relancez-la — la plupart des migrations sont conçues pour être idempotentes.
- Si une migration sur une base SQLite neuve renvoie une erreur SQL propre à PostgreSQL, vérifiez que vous utilisez une version récente avant d'essayer une autre solution.
- Ne modifiez jamais le schéma de la base de données à la main pour contourner un échec de migration — ouvrez plutôt un ticket avec l'erreur exacte, car des modifications manuelles du schéma rendent les migrations futures imprévisibles.

## Erreurs de clé JWT {#jwt-key-errors}

Si l'application échoue au démarrage en signalant des clés JWT manquantes ou invalides, vérifiez que `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` pointent vers une paire de clés ES256 valide générée avec :

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Des clés générées avec une autre courbe ou un autre algorithme ne fonctionneront pas — PromptVault attend spécifiquement du ES256 (P-256/prime256v1).

## Verrouillage après échecs de connexion {#locked-out-after-failed-logins}

Des tentatives de connexion échouées répétées verrouillent temporairement votre compte. Par défaut, cela se produit après cinq tentatives (`MAX_LOGIN_ATTEMPTS`) et dure 15 minutes (`ACCOUNT_LOCKOUT_DURATION_SECONDS`). Attendez la fin du verrouillage. Si vous êtes le seul administrateur, attendez plutôt que d'essayer d'autres mots de passe : les nouvelles tentatives ne raccourcissent pas le délai.

## Erreurs de limitation de débit (429) {#rate-limit-errors-429}

Si des opérations en masse, des imports, des exports ou des actions de sauvegarde renvoient `429 Too Many Requests`, vous avez atteint une limite de débit par utilisateur. La réponse fournit une valeur `Retry-After`. Attendez ce délai, puis réessayez une fois. Si cette limite bloque régulièrement un usage légitime, un administrateur peut ajuster le paramètre `RATE_LIMIT_*` correspondant décrit dans [Configuration](../configuration/index.md#rate-limiting).

## L'import/export ne restaure pas le partage {#importexport-doesnt-restore-sharing}

Si vous importez un fichier précédemment exporté et que les prompts partagés redeviennent privés sans aucune autorisation, c'est normal — l'export/import ne conserve volontairement pas l'état de partage (voir [Partage de prompts](../user-guide/sharing.md#exportimport-and-sharing)). Utilisez plutôt une sauvegarde/restauration complète si vous avez besoin de conserver le partage.

Pour une mise à jour planifiée, suivez le guide [Mettre à jour PromptVault](../installation/update.md).

## Toujours bloqué ? {#still-stuck}

Consultez le `docs/TROUBLESHOOTING.md` complet dans le dépôt, ou ouvrez un ticket sur [GitHub](https://github.com/Medenor/PromptVault) avec le message d'erreur exact et la commande exécutée.

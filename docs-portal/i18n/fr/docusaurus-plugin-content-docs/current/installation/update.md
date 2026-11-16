---
title: Mettre à jour PromptVault
description: Mettre à jour en toute sécurité une installation PromptVault auto-hébergée.
---

# Mettre à jour PromptVault

Ces étapes concernent l'installation Docker Compose décrite dans [Installation](index.md). Elles mettent à jour les services `web` et `docs` sans supprimer la base de données ni son volume nommé.

## Avant de commencer

1. Consultez les [notes de version](../release-notes/index.md) pour repérer les changements qui concernent votre installation.
2. Vérifiez que le serveur dispose d'assez d'espace pour la sauvegarde de la base et les nouvelles images.
3. Prévoyez une courte fenêtre de maintenance. Les utilisateurs pourraient ne pas pouvoir se connecter pendant le redémarrage.
4. Vérifiez que vous avez accès au dossier du projet sur le serveur et au conteneur de base de données.

## 1. Sauvegarder la base de données

Créez et vérifiez une sauvegarde compressée avant de télécharger ou démarrer la mise à jour :

```bash
mkdir -p data/backups
docker compose exec -T db pg_dump -U promptvault -d promptvault \
  | gzip > "data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
gzip -t data/backups/*.sql.gz
```

Vérifiez que le fichier le plus récent n'est pas vide et que `gzip -t` se termine sans erreur. Conservez la sauvegarde dans un endroit sûr. Ne continuez pas si la sauvegarde a échoué.

## 2. Télécharger et reconstruire

Depuis le dossier du projet PromptVault, récupérez la version souhaitée. Utilisez l'étiquette de version indiquée dans les notes de version si vous ne souhaitez pas la dernière version de développement :

```bash
git fetch --tags
git checkout <release-tag>
```

Reconstruisez et redémarrez les services de l'application et de la documentation :

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

La base de données et Redis doivent être en bon état avant le démarrage de l'application. Compose attend les contrôles de santé configurés dans le fichier du projet.

## 3. Appliquer les migrations

Exécutez les migrations avec l'image web mise à jour :

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

La seconde commande affiche la révision active. Si la migration échoue, arrêtez-vous et consultez la page [Dépannage](../troubleshooting/index.md).

## 4. Vérifier la mise à jour

```bash
curl --fail http://localhost:8001/api/health
```

Le point de santé doit répondre avec succès. Ouvrez PromptVault dans un navigateur, connectez-vous et vérifiez que vos prompts sont présents. Ouvrez aussi le service de documentation si vous l'utilisez (adresse par défaut : `http://localhost:7876`).

## En cas de problème

Consultez d'abord les journaux des services :

```bash
docker compose logs --tail=100 web docs
```

Une reconstruction sans cache peut révéler une dépendance Python manquante si sa version n'est pas correctement verrouillée. Par exemple, la contrainte de version SQLAlchemy corrigée dans les notes de version liées au [ticket #94](https://codeberg.org/medenor/promptvault/issues/94) évite un problème connu d'installation de `psycopg`. Pour les autres symptômes, consultez [Dépannage](../troubleshooting/index.md).

### Restaurer la sauvegarde

Si la nouvelle version ne fonctionne pas, revenez à la version précédente de l'application et restaurez la sauvegarde vérifiée. La restauration remplace le contenu actuel de la base : conservez d'abord une copie de son état si elle contient de nouvelles données.

```bash
docker compose stop web
# Copiez la sauvegarde sur le serveur si nécessaire, puis :
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
gzip -dc data/backups/<fichier-sauvegarde>.sql.gz \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Redémarrez les services `web` et `docs` de la version précédente après la restauration. En cas de problème, consultez [Dépannage](../troubleshooting/index.md).

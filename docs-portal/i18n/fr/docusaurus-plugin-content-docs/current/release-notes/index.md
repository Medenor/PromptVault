---
title: Notes de version
sidebar_position: 1
---

# Notes de version

Points forts des versions récentes de PromptVault. Pour l'historique complet et intégral, consultez `docs/CHANGELOG.md` dans le dépôt.

Pour les étapes de mise à jour, consultez [Mettre à jour PromptVault](../installation/update.md).

## À venir

Le portail propose désormais un guide pour sauvegarder, mettre à jour, vérifier et restaurer une installation Docker Compose. Chaque page comporte aussi un lien « Retour à PromptVault » ; définissez `DOCS_APP_URL` lors de la construction de l’image de documentation pour pointer vers votre instance. Consultez [Mettre à jour PromptVault](../installation/update.md).

## 1.14.1

- **Correctif** : les fenêtres d'import et de modification de skill respectent désormais le mode nuit au lieu de s'afficher sur fond blanc.

## 1.14.0

- **Skills** : PromptVault stocke désormais des skills (un fichier `SKILL.md` avec scripts, références et autres fichiers) à côté de vos prompts. Importez un skill depuis un `.zip` avec **Nouveau ▾ → Importer un skill**, parcourez ses instructions rendues et son arborescence, modifiez ses détails, remplacez ses fichiers, téléchargez-le en `.zip` ou supprimez-le. Les skills sont recherchables, filtrables par type et inclus dans les sauvegardes de la base. L'historique des versions, le partage, les placeholders et l'import/export en masse ne s'appliquent pas encore aux skills. Consultez la nouvelle page Skills du guide utilisateur.
- **Menus de l'en-tête** : « Nouveau prompt » et « Importer un skill » partagent désormais un menu **Nouveau ▾**, et les liens secondaires passent dans un menu **Plus ▾** sur les écrans de largeur moyenne, pour que la navigation tienne sur une ligne.
- **Correctif de sécurité** : la mise à jour groupée des tags vérifie désormais que vous êtes propriétaire (ou administrateur) de chaque élément sélectionné.
- **Mise à jour** : appliquez la migration de la base et reconstruisez les images. Un rechargement de la page peut être nécessaire une fois pour obtenir les nouvelles traductions.

## 1.13.1

- **Correction** : la reconstruction de l'image Docker sans cache n'échoue plus avec `No module named 'psycopg'` (la dépendance SQLAlchemy est désormais limitée à une version inférieure à 2.1).
- **Correction** : le lien Documentation du menu de l'application fonctionne désormais dans les déploiements Docker. La pile Docker inclut un service `docs` qui sert le portail sur le port 7876. Après la mise à jour, reconstruisez les deux images : `docker-compose build web docs && docker-compose up -d docs web`.

## 1.13.0

- **Authentification à deux facteurs (mot de passe à usage unique temporel, TOTP), facultative** : les utilisateurs peuvent activer une application d'authentification depuis leur profil et recevoir des codes de récupération à usage unique. Les administrateurs peuvent imposer le 2FA par rôle.
- **Lien vers le portail documentaire** : le menu de l’application pointe désormais vers le portail documentaire. L’URL de déploiement est configurée avec `VITE_DOCS_PORTAL_URL` ; le développement local utilise `http://localhost:7876`.
- **Recherche en texte intégral avec classement par pertinence** : la recherche s'appuie désormais sur un véritable index de texte intégral plutôt que sur un simple balayage de sous-chaîne, avec des résultats classés par pertinence et des extraits de correspondance mis en évidence.
- **Version de l'application affichée dans le pied de page**.
- Diverses corrections de fiabilité backend (plantage du rapport de couverture sur les templates, portabilité des migrations, nettoyage de code mort).

## 1.12.0

- **Partage de prompts et collaboration d'équipe** : les propriétaires de prompts peuvent accorder à des collègues un accès en lecture ou en édition sur des prompts individuels, avec un filtre « Partagés avec moi » et un badge distinct entre un partage explicite et un prompt visible par héritage. L'état de partage n'est volontairement pas inclus dans l'export/import — utilisez une sauvegarde/restauration complète si vous avez besoin de le conserver.
- **Changement de visibilité** : les nouveaux prompts sont désormais privés par défaut ; les prompts existant avant cette version ont été considérés « Public (hérité) » et peuvent être rendus privés (de façon irréversible) par leur propriétaire ou un administrateur.
- Refonte interne importante des templates surdimensionnés et des modules TypeScript — aucun changement de comportement visible pour l'utilisateur.
- **Sécurité** : la limitation de débit a été étendue des points de terminaison d'authentification à toutes les actions modifiant l'état et coûteuses (import/export, sauvegardes, actions en masse), désormais réellement par utilisateur plutôt qu'accidentellement globale. Plusieurs risques de XSS stockées liés à un usage non sécurisé d'`innerHTML` ont été corrigés.

## 1.11.0

- Correctifs de sécurité des dépendances (Jinja2, python-multipart, et d'autres) fermant 24 CVE connues.
- Nouvelle tâche CI d'audit de sécurité exécutant des analyses de vulnérabilités des dépendances à chaque push/PR.
- **Espaces réservés dynamiques dans les prompts** : le contenu d'un prompt peut désormais contenir des jetons de type `[NOM]`/`{NOM}`, remplis au moment de la copie.

## 1.10.0

- Pagination côté serveur pour la liste des prompts, afin que les bibliothèques volumineuses se chargent page par page plutôt que la totalité du jeu de données.
- **Système de sauvegarde et restauration amélioré** : chiffrement, stockage cloud (compatible S3, Google Drive, Dropbox), planification et journalisation d'audit pour les sauvegardes, ainsi que plusieurs correctifs de sécurité liés aux sauvegardes (traversée de chemin, XSS stockée, points de terminaison non authentifiés).
- Sélecteur de langue global ajouté à l'en-tête de chaque page.
- Nouveau Makefile de flux de développement (`make install`, `make dev`, `make test`, `make lint`, `make build`) comme point d'entrée unique pour les tâches courantes.
- Améliorations de l'interface adaptée au mobile : navigation optimisée au toucher, prise en charge hors ligne, et possibilité d'installation en tant qu'application web progressive.

## 1.9.0

- **Versionnage sémantique des prompts** : les prompts peuvent désormais se voir attribuer un numéro de version sémantique optionnel (`MAJEUR.MINEUR.CORRECTIF`) à la création ou à l'édition.

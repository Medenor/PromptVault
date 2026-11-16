---
title: Utiliser l’API existante
sidebar_position: 1
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Utiliser l’API existante

L’interface de programmation (API) permet de relier vos scripts et outils à PromptVault. Cet espace s’adresse aux personnes qui utilisent un terminal et des requêtes HTTP. Pour les tâches dans l’application, consultez le [guide utilisateur](../user-guide/prompt-management.md). Pour déployer ou configurer le serveur, suivez [Installation](../installation/index.md) et [Configuration](../configuration/index.md).

## Choisir un parcours

- [Effectuer vos premiers appels API](getting-started.md) : lire, créer et rechercher un prompt de test.
- [Référence de l’API](reference.md) : retrouver les opérations, formats, droits et solutions aux erreurs.

## Ouvrir la référence de votre instance

Le portail documentaire et l’application PromptVault peuvent avoir des adresses différentes. À l’adresse de **l’application**, ouvrez :

| Chemin          | Utilité                                         |
| --------------- | ----------------------------------------------- |
| `/docs`         | Référence interactive de l’API                  |
| `/redoc`        | Autre présentation de la référence              |
| `/openapi.json` | Description de l’API exploitable par des outils |

Pour une application à `http://localhost:8001`, ouvrez `http://localhost:8001/docs`. Conservez tout préfixe d’adresse fourni pour votre déploiement.

Vous pouvez lire ces guides sans instance démarrée. Pour exécuter une requête, il faut une application disponible et les identifiants qu’elle exige. **Try it out** dans la référence envoie de vraies requêtes. Utilisez des prompts de test pour les modifications et suppressions.

## Identifier le périmètre actuel

Les routes actuelles commencent par `/api/...`, sans `/v1`. Authentifiez vos scripts avec le jeton de session présenté dans le tutoriel.

La référence de l’instance liste les routes activées. Les routes d’authentification et d’administration sont absentes quand l’authentification est désactivée. Certaines descriptions conservent une ancienne formulation sur la visibilité : consultez les droits dans la [référence](reference.md). Retrouvez la version installée dans le pied de page de l’application et consultez les [notes de version](../release-notes/index.md).

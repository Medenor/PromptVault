---
title: Référence de l’API
sidebar_position: 3
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Référence de l’API

Retrouvez ici les familles de routes existantes. Ouvrez `/docs` sur votre **application**, pas sur le portail documentaire, pour le schéma complet de l’instance. Pour un parcours guidé, commencez par [vos premiers appels API](getting-started.md).

## Authentification et droits {#authentication-and-access}

Dans vos scripts, envoyez `Authorization: Bearer <ACCESS_TOKEN>`. La connexion et le renouvellement attendent du JSON. La création et la modification d’un prompt attendent des champs de formulaire.

Un jeton d’accès expire après 15 minutes par défaut. Envoyez le dernier jeton de renouvellement à `POST /api/auth/refresh` sous la forme `{"refresh_token":"<REFRESH_TOKEN>"}`. Remplacez les **deux** jetons après chaque renouvellement. Réutiliser un ancien jeton peut révoquer la session ; ne lancez pas plusieurs renouvellements en parallèle. `POST /api/auth/logout` accepte le jeton de renouvellement actuel au format JSON pour terminer cette session.

Avec l’authentification active, la liste et la recherche ne renvoient que les éléments visibles pour vous. Sans identifiants, ou avec un jeton invalide ou expiré, elles peuvent renvoyer une page vide plutôt qu’une erreur 401. Une page vide ne confirme donc pas que la connexion a réussi. La propriété, le rôle administrateur, les partages et la visibilité héritée déterminent les droits. Un partage en modification autorise les modifications et restaurations, pas la suppression ou la gestion des partages. Voir [Partage](../user-guide/sharing.md). Les skills suivent leurs propres règles ; voir [Skills](../user-guide/skills.md).

## Retrouver une opération {#find-an-operation}

Remplacez `{id}` par l’identifiant du prompt et `{version_id}` par un identifiant issu de son historique. Ce tableau donne des repères, pas une liste exhaustive des opérations d’administration.

| Opération                                     | Route                                                                                                          |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Lister / rechercher                           | `GET /api/prompts` · `GET /api/prompts/search`                                                                 |
| Créer / lire / modifier / supprimer           | `POST /api/prompts` · `GET /api/prompts/{id}` · `PUT /api/prompts/{id}` · `DELETE /api/prompts/{id}`           |
| Lire l’historique / une version               | `GET /api/prompts/{id}/versions` · `GET /api/prompts/{id}/versions/{version_id}`                               |
| Restaurer une version                         | `POST /api/prompts/{id}/versions/{version_id}/revert`                                                          |
| Gérer les partages d’un prompt                | `POST /api/prompts/{id}/shares` · `GET /api/prompts/{id}/shares` · `DELETE /api/prompts/{id}/shares/{user_id}` |
| Importer / consulter / télécharger des skills | `POST /api/skills/import` · `GET /api/skills/{id}` · `GET /api/skills/{id}/download`                           |
| Lire les catégories / tags                    | `GET /api/categories` · `GET /api/tags`                                                                        |
| Importer / exporter des prompts               | `POST /api/import` · `POST /api/export`                                                                        |
| Gérer les sauvegardes                         | `GET /api/backups` · `POST /api/backups`                                                                       |
| Gérer les comptes / sessions / planifications | `/api/admin/users` · `/api/admin/sessions` · `/api/admin/scheduler/...`                                        |

Consultez la référence de l’instance pour les droits et formats des opérations d’administration.

Les champs de formulaire de création et modification sont `title`, `prompt`, `category`, `tags`, `commit_message` et, facultativement, `semantic_version`. `title` et `prompt` sont requis dans les deux cas. Séparez les tags par des virgules. Une restauration accepte le champ de formulaire facultatif `commit_message` et crée une entrée d’historique. Une suppression retire des données : réservez-la aux éléments que vous souhaitez supprimer.

## Parcourir les résultats {#read-paginated-results}

La liste et la recherche utilisent par défaut `page=1` et `limit=50`, avec un maximum de 100 éléments par page. Continuez tant que `has_next` vaut `true`. L’objet `prompts` utilise les identifiants comme clés. `item_type` accepte `all`, `prompt` ou `skill` ; un skill n’a pas de corps `prompt`. `filter=shared-with-me` limite les résultats aux partages explicites.

La recherche accepte `search`, `category`, `tag`, `favorites`, `case_sensitive` et `ranked`. N’affichez jamais les extraits renvoyés comme du HTML brut. Voir le [guide de recherche](../user-guide/search.md) pour les correspondances.

## Résoudre un échec {#resolve-a-failed-call}

Examinez le statut HTTP et la réponse. Selon l’opération, l’erreur utilise `detail`, `error` ou un message structuré. Un prompt introuvable peut par exemple renvoyer `{"detail":"Prompt with ID 123 not found"}`.

| Statut | Cause à vérifier                                               | Action                                                                                             |
| ------ | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 401    | Identifiants absents, invalides ou expirés                     | Reconnectez-vous ou renouvelez une fois avec le dernier jeton.                                     |
| 403    | Droits insuffisants ou configuration 2FA exigée mais inachevée | Vérifiez vos droits et terminez la configuration dans l’application.                               |
| 404    | Route incorrecte ou désactivée, élément absent ou privé        | Vérifiez l’adresse, l’identifiant et vos droits ; ne supposez pas que l’élément existe.            |
| 409    | Opération incompatible avec le type d’élément                  | Utilisez les routes skills pour les skills et les routes propres aux prompts pour leurs fonctions. |
| 422    | Champs manquants, encodage ou valeurs incorrects               | Lisez les erreurs de champs ; utilisez un formulaire pour créer ou modifier un prompt.             |
| 429    | Limite de requêtes atteinte                                    | Attendez le nombre de secondes indiqué par `Retry-After`.                                          |

Les limites dépendent de l’opération et du serveur ; voir [Configuration](../configuration/index.md). Après une interruption réseau, vérifiez si une modification a abouti avant de la renvoyer. Pour les problèmes de connexion ou de serveur, consultez [Dépannage](../troubleshooting/index.md).

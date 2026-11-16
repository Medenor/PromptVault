---
title: Effectuer vos premiers appels API
sidebar_position: 2
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Effectuer vos premiers appels API

Lisez une page de prompts, puis créez et retrouvez un prompt de test sur votre instance.

## Préparer votre essai {#before-you-start}

Prévoyez une instance de test, Bash et `curl` avec `--json` (7.82 ou ultérieur). Si l’authentification est active, il vous faut un compte actif et, le cas échéant, votre application d’authentification. Remplacez localement les valeurs entre chevrons. Ne partagez ni mots de passe, ni jetons, ni réponses de connexion. Utilisez HTTPS pour une instance distante.

## Définir l’adresse de l’application {#set-the-application-address}

Utilisez l’adresse de votre application, pas celle du portail. L’exemple correspond à un déploiement local. Conservez tout préfixe, sans barre oblique finale.

```bash
BASE_URL='http://localhost:8001'
```

## Vous connecter {#sign-in}

Sautez cette étape uniquement si votre instance isolée est déjà configurée avec `AUTH_ENABLED=false` ; omettez alors l’en-tête d’autorisation dans la suite. Ne désactivez pas l’authentification pour faire fonctionner une intégration. Voir [Configuration](../configuration/index.md).

Envoyez vos identifiants au format JSON :

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login" \
  --json '{"username_or_email":"<USERNAME>","password":"<PASSWORD>"}'
```

Une connexion terminée renvoie `access_token` et `refresh_token`. Si vous recevez plutôt `challenge_token`, effectuez la requête suivante avec ce jeton et un code actuel de votre application d’authentification ou un code de récupération inutilisé. Ce jeton de vérification n’est pas un jeton d’accès. Si une configuration 2FA est exigée, terminez-la d’abord dans l’application ; voir [authentification à deux facteurs](../user-guide/two-factor-auth.md).

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login/2fa" \
  --json '{"challenge_token":"<CHALLENGE_TOKEN>","code":"<CODE>"}'
```

Copiez le `access_token` obtenu. Exécutez la commande suivante, collez le jeton, puis appuyez sur Entrée. Bash masque la saisie et ne place pas le jeton lui-même dans l’historique des commandes :

```bash
read -r -s TOKEN
```

## Lire une page de prompts {#read-a-page-of-prompts}

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts?page=1&limit=10&item_type=prompt"
```

La réponse attendue est HTTP 200 avec `prompts`, `page`, `limit`, `total_count`, `total_pages`, `has_next` et `has_previous`. `prompts` est un objet dont les clés sont les identifiants, pas une liste. Une page vide est possible. Avec l’authentification active, les résultats dépendent de votre identité et de vos droits.

## Créer un prompt de test {#create-a-disposable-prompt}

Cette requête crée des données. Utilisez un compte de test et un contenu fictif. La création attend des champs de formulaire, pas du JSON :

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts" \
  --data-urlencode 'title=API tutorial' \
  --data-urlencode 'prompt=Summarize this sample text.' \
  --data-urlencode 'tags=api-tutorial'
```

La réponse attendue est HTTP 201 avec `{"success":true,"prompt_id":...}`. Reportez ce `prompt_id` dans la commande suivante :

```bash
PROMPT_ID='<PROMPT_ID>'
```

## Rechercher et consulter les versions {#search-and-inspect-versions}

La recherche utilise `search`, pas `q`. Avec `item_type=prompt`, vous excluez les skills des résultats de liste et de recherche.

```bash
curl --silent --show-error --fail-with-body --get \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/search" \
  --data-urlencode 'search=API tutorial' \
  --data-urlencode 'item_type=prompt'
```

```bash
curl --silent --show-error --fail-with-body \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/$PROMPT_ID/versions"
```

La réponse d’historique contient `versions`. Retrouvez les routes de modification, restauration et suppression dans la [référence](reference.md). Ne supprimez que votre prompt de test. Retirez le jeton local avec `unset TOKEN` à la fin ; cela ne révoque pas la session sur le serveur. En cas d’échec, consultez les [solutions aux erreurs](reference.md#resolve-a-failed-call) avant de réessayer.

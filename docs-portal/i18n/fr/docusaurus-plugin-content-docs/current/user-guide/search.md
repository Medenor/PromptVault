---
title: Recherche
sidebar_position: 4
---

# Recherche

La recherche de PromptVault s'appuie sur un véritable index de texte intégral plutôt que sur un simple balayage de sous-chaîne, si bien que les résultats sont classés par pertinence et restent rapides même quand votre bibliothèque de prompts grandit.

## Fonctionnement du classement {#how-ranking-works}

Les correspondances dans le **titre** d'un prompt ont le poids le plus élevé, puis dans son **contenu**, puis dans sa **note** — un prompt dont le titre correspond à votre requête remonte donc au-dessus d'un prompt qui ne mentionne le terme qu'en passant. Les requêtes simples à plusieurs mots sont combinées avec un OU logique : les prompts ne correspondant qu'à certains des mots apparaissent quand même, mais classés en dessous de ceux correspondant à tous les mots.

Si vous choisissez explicitement une option de tri (par exemple par date), celle-ci prévaut sur le classement par pertinence, puisque vous avez demandé un ordre spécifique.

## Mise en évidence des termes correspondants {#matched-term-highlighting}

Les résultats de recherche incluent un extrait mettant en évidence le ou les termes correspondants en contexte, afin de voir en un coup d'œil pourquoi un prompt donné correspond, sans avoir à l'ouvrir.

## Correspondance exacte et par expression {#exact-and-phrase-matching}

- Les recherches avec `case_sensitive=true` préservent la correspondance exacte de la casse.
- Mettre une requête entre guillemets (`"expression exacte"`) recherche cette expression exacte plutôt que de traiter les mots séparément avec un OU.

## Fiabilité {#reliability}

Toute requête que PromptVault ne peut pas analyser comme une recherche structurée (par exemple, composée uniquement d'opérateurs de recherche sans terme de recherche réel) retombe automatiquement sur une simple recherche de sous-chaîne plutôt que de renvoyer une erreur — une recherche ne devrait jamais échouer simplement à cause de sa formulation.

## Performance {#performance}

La recherche reste rapide à mesure que votre bibliothèque grandit : la latence des requêtes reste globalement stable plutôt que de se dégrader linéairement avec le nombre de prompts stockés, car c'est l'index sous-jacent — et non un balayage complet — qui effectue le travail de correspondance.

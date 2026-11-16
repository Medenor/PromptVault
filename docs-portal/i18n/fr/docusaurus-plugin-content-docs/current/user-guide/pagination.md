---
title: Pagination
sidebar_position: 8
---

# Pagination

La grille principale des prompts charge les résultats page par page plutôt que de récupérer toute votre bibliothèque d'un coup, ce qui garde le chargement initial rapide même avec une grande collection.

## Charger plus {#loading-more}

Lorsque plus de prompts sont disponibles que ce que la page actuelle affiche, un bouton « Charger plus » récupère la page suivante et l'ajoute à ce qui est déjà affiché, sans perdre votre position. Une fois tous les prompts chargés, le bouton disparaît.

## Taille de page {#page-size}

Vous pouvez choisir une taille de page de 25, 50 ou 100 prompts ; si vous n'en choisissez pas, PromptVault charge 50 prompts à la fois par défaut. Demander une taille de page supérieure à 100 est ramenée à 100 plutôt que rejetée.

## Pagination et filtres {#pagination-and-filters}

Appliquer un filtre de [catégorie](./categories.md) ou de [tag](./tags.md), ou une requête de [recherche](./search.md), pagine l'ensemble de résultats filtré, pas votre bibliothèque complète — et modifier un filtre vous ramène toujours à la première page.

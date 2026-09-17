---
title: Tags
sidebar_position: 3
---

# Tags

Contrairement aux catégories, un prompt peut porter plusieurs tags à la fois, ce qui rend les tags plus adaptés aux étiquettes transversales — comme `client` ou `à-relire` — que le regroupement unique offert par une catégorie.

## Créer et attribuer des tags

Un tag possède un nom, une description facultative, une couleur facultative, et peut éventuellement avoir un tag parent, permettant de construire une hiérarchie simple de tags (un tag ne peut pas être son propre parent, et les cycles sont rejetés). Les tags sont attribués à un prompt lors de sa création ou de sa modification ; saisir un nom de tag qui n'existe pas encore le crée.

## Filtrer par tag

La grille principale des prompts peut être filtrée par tag pour réduire l'affichage aux prompts portant cette étiquette.

## Maintenance groupée des tags

La page Gérer les tags propose plusieurs opérations groupées pour garder votre liste de tags bien rangée :

- **Fusion** — regrouper un ou plusieurs tags sources dans un seul tag cible, en réattribuant tous les prompts qui portaient un tag source.
- **Suppression groupée** — retirer plusieurs tags à la fois ; supprimer un tag encore utilisé sur des prompts nécessite une confirmation explicite « forcée ».
- **Rechercher-remplacer** — renommer un tag partout à la fois, en le fusionnant avec le remplaçant s'il existe déjà sous ce nom.
- **Nettoyage des orphelins** — lister les tags sans aucun prompt associé (tags inutilisés) et les prompts sans aucun tag associé (prompts non étiquetés), pour nettoyer les deux côtés.

La fusion, la suppression groupée et le rechercher-remplacer peuvent tous être annulés immédiatement après leur exécution.

## Statistiques des tags

Une vue de statistiques des tags montre vos tags les plus et les moins utilisés, ainsi que les paires de tags qui apparaissent le plus souvent ensemble sur le même prompt, utile pour repérer des tags redondants ou trop spécifiques.

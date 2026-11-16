---
title: Gérer les prompts
sidebar_position: 1
---

# Gérer les prompts

La page principale de PromptVault est une grille de cartes : chaque prompt visible apparaît sous forme de carte, et le travail quotidien — création, modification, suppression et mise en favori — se fait directement depuis cette grille.

## Créer un prompt {#creating-a-prompt}

La création d'un prompt nécessite un titre et le contenu du prompt lui-même ; la catégorie et les tags sont facultatifs. Le premier enregistrement crée aussi la version initiale du prompt, associée à un message de commit (par défaut « Initial commit » si vous n'en fournissez pas), afin qu'elle apparaisse dès le départ dans l'[historique des versions](./versioning.md) de ce prompt.

## Modifier un prompt {#editing-a-prompt}

Modifier le titre, le contenu, la catégorie ou les tags d'un prompt crée une nouvelle version au lieu d'écraser silencieusement l'ancienne — chaque enregistrement est tracé, et vous pouvez toujours consulter (ou revenir à) une version antérieure. Vous choisissez le message de commit pour chaque modification, de la même manière que pour la création initiale.

## Supprimer un prompt {#deleting-a-prompt}

Supprimer un prompt effectue une suppression douce : le prompt disparaît de la grille, mais ses données et l'intégralité de son historique de versions sont conservées plutôt que détruites, ce qui rend une récupération toujours possible. Seul le propriétaire du prompt ou un administrateur peut le supprimer.

## Mise en favori {#favoriting}

N'importe quel prompt peut être marqué comme favori depuis sa carte, ce qui permet de filtrer la grille pour n'afficher que les prompts que vous utilisez le plus. Seul le propriétaire du prompt peut basculer son statut de favori — la mise en favori est un marqueur personnel, pas un marqueur partagé.

## Filtrer et parcourir {#filtering-and-browsing}

Au-delà des favoris, la grille peut être filtrée par [catégorie](./categories.md), par [tag](./tags.md), ou par requête de [recherche](./search.md), et les résultats sont paginés — voir [Pagination](./pagination.md) pour le fonctionnement du bouton « Charger plus » sur les grandes bibliothèques.

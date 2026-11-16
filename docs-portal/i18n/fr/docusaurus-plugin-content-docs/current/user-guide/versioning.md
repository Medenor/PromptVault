---
title: Versionnage des prompts
sidebar_position: 1
---

# Versionnage des prompts

PromptVault conserve un historique complet, façon Git, de chaque prompt, afin que vous ne perdiez jamais la trace de son évolution et puissiez toujours revenir à une version antérieure.

## Versionnage automatique {#automatic-versioning}

À chaque enregistrement d'une modification sur un prompt, PromptVault crée automatiquement une nouvelle version enregistrant :

- Un identifiant de version unique
- Un horodatage
- L'auteur de la modification
- Un message décrivant ce qui a changé
- Un instantané complet du prompt à ce moment précis

Vous n'avez rien à faire pour activer cela — c'est automatique à chaque mise à jour.

## Consulter l'historique des versions {#viewing-version-history}

Ouvrez l'historique des versions d'un prompt via :

- Le raccourci clavier `Cmd+H` (Mac) ou `Ctrl+H` (Windows/Linux)
- Le bouton « Historique des versions » dans l'éditeur de prompt

La fenêtre d'historique liste chaque version de la plus récente à la plus ancienne, avec son message et ses métadonnées, un champ de recherche pour retrouver une version précise, et des actions rapides de comparaison ou de restauration.

## Comparer des versions {#comparing-versions}

Depuis la fenêtre d'historique, sélectionnez deux versions pour voir un diff détaillé sur tous les champs du prompt (titre, contenu, catégorie, tags, notes).

Les champs texte utilisent une mise en évidence des différences au niveau du caractère plutôt qu'au niveau de la ligne, afin que les petites modifications — une correction de faute de frappe, un changement de ponctuation, un mot ajouté — soient faciles à repérer sans être noyées dans un mur de « ligne modifiée ». Les ajouts apparaissent surlignés en vert, les suppressions barrées en rouge, et le texte inchangé reste neutre.

## Revenir à une version antérieure {#reverting-to-a-previous-version}

Depuis la vue de comparaison ou d'historique, vous pouvez restaurer un prompt à une version antérieure. La restauration crée une **nouvelle** version contenant l'ancien contenu — elle ne supprime pas l'historique, donc la restauration elle-même est aussi tracée et peut être annulée en restaurant à nouveau.

## Pourquoi c'est important {#why-this-matters}

Si vous itérez sur un prompt et qu'une nouvelle variante fonctionne moins bien, vous pouvez toujours retrouver ce qui marchait sans avoir à vous souvenir ni à retaper manuellement la formulation précédente.

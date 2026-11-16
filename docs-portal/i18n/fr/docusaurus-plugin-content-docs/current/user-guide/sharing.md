---
title: Partage de prompts
sidebar_position: 3
---

# Partage de prompts

PromptVault permet de partager des prompts individuels avec des collègues spécifiques, avec un contrôle d'accès fin en lecture/édition.

## Accorder un accès {#granting-access}

Depuis la fenêtre de partage d'un prompt, vous pouvez accorder à un collègue l'un des deux niveaux d'accès suivants :

- **Lecture** : consulter le prompt et son historique de versions.
- **Édition** : tout ce que permet la lecture, plus la modification du contenu, de la catégorie et des tags du prompt, ainsi que la restauration vers une version antérieure.

Aucun des deux niveaux ne permet de supprimer le prompt, de le repartager avec d'autres, de basculer son statut favori, ou de transférer sa propriété — ces actions restent réservées au propriétaire. Le sélecteur de destinataire recherche les utilisateurs actifs par préfixe de nom d'utilisateur ou d'e-mail, mais n'affiche ni n'expose jamais les adresses e-mail dans les résultats.

## Révoquer un accès {#revoking-access}

L'accès peut être révoqué par le propriétaire du prompt à tout moment depuis la même fenêtre de partage.

## Retrouver les prompts partagés {#finding-shared-prompts}

Un filtre « Partagés avec moi » affiche les prompts que d'autres personnes ont partagés avec vous. Les prompts partagés portent un badge « Partagé » distinct afin de différencier un partage explicite d'un prompt simplement visible par défaut.

## Prompts publics hérités {#legacy-public-prompts}

Les prompts créés avant l'introduction du partage sont considérés « Public (hérité) » — visibles par tout utilisateur authentifié, pas seulement par les personnes ayant reçu un accès explicite — et sont badgés différemment d'un partage explicite. Un propriétaire ou un administrateur peut rendre privé un prompt public hérité via une action « Rendre privé » ; cette transition est irréversible et ne permet pas de repasser le prompt en public hérité par la suite, à traiter donc comme une décision délibérée plutôt qu'un simple bouton d'affichage.

Les prompts créés après l'introduction du partage sont **privés** par défaut : visibles uniquement par leur propriétaire, les administrateurs, et toute personne ayant reçu un accès explicite.

## Export/Import et partage {#exportimport-and-sharing}

Les autorisations de partage et l'indicateur public hérité ne sont **pas** inclus dans les prompts exportés (CSV/Markdown/JSON) — il s'agit d'un état de contrôle d'accès propre à cette instance et lié aux comptes utilisateurs, pas d'un contenu de prompt portable. La réimportation d'un fichier exporté crée des prompts privés simples, sans aucune autorisation restaurée. Si vous avez besoin de conserver l'état de partage, utilisez une sauvegarde/restauration complète de la base de données plutôt que l'export/import.

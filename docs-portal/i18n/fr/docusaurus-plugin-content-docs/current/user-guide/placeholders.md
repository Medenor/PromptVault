---
title: Espaces réservés
sidebar_position: 4
---

# Espaces réservés

Les espaces réservés transforment un prompt statique en modèle réutilisable : écrivez un jeton entre crochets comme `[DURATION]` ou entre accolades comme `{DURATION}` n'importe où dans le contenu d'un prompt, et PromptVault vous demandera de le remplir lors de la copie du prompt.

## Syntaxe reconnue

Un nom d'espace réservé doit comporter au moins 2 caractères composés de lettres majuscules, de chiffres, de tirets bas ou d'espaces — par exemple `[DURATION]`, `[TYPE OF PRESENTATION]` ou `{MAX_RETRIES}`. Les jetons en minuscules, en casse mixte ou avec des traits d'union (comme `[Duration]` ou `[YYYY-MM-DD]`) ne sont **pas** reconnus comme des espaces réservés et restent du texte brut, tout comme les crochets isolés qui ne forment pas une paire correctement fermée.

`[DURATION]` et `{DURATION}` sont traités comme deux espaces réservés distincts, même s'ils partagent un nom — les syntaxes crochets et accolades ne se fusionnent pas.

## Remplir les valeurs à la copie

Cliquer sur Copier pour un prompt contenant des espaces réservés ouvre un formulaire avec un champ de saisie par espace réservé distinct, au lieu de copier immédiatement. Si le même espace réservé apparaît plusieurs fois dans le prompt, il ne reçoit qu'un seul champ — la valeur saisie remplace chaque occurrence. Valider en laissant certains ou tous les champs vides copie tout de même avec succès ; le jeton d'un champ resté vide est copié inchangé, sous sa forme d'origine.

Les prompts sans espace réservé se copient instantanément, exactement comme avant — le formulaire n'apparaît que lorsqu'il y a réellement quelque chose à remplir.

## Les espaces réservés ailleurs dans PromptVault

En dehors du flux de copie, un jeton d'espace réservé est traité comme du texte ordinaire partout ailleurs : l'[historique des versions](./versioning.md) conserve le contenu brut de chaque version avec les jetons intacts, la [recherche](./search.md) et le filtrage par catégorie/tag traitent le texte des espaces réservés comme n'importe quel autre texte, et le contenu [exporté](./import-export.md) contient les jetons originaux, non substitués. Les vues d'historique des versions et de comparaison sont en lecture seule et n'affichent jamais le formulaire de remplissage — pour copier une ancienne version avec des valeurs remplies, revenez d'abord à cette version, puis utilisez l'action Copier habituelle.

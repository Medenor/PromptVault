---
title: Skills
sidebar_position: 4
---

# Skills

Un skill est un dossier d'instructions et de fichiers d'appoint qu'un agent d'IA peut charger pour accomplir une tâche. Il contient toujours un fichier `SKILL.md`, et peut aussi contenir des scripts, des références et d'autres fichiers. PromptVault conserve les skills à côté de vos prompts, pour que vous puissiez organiser, rechercher, sauvegarder et exporter les deux au même endroit.

## Ce qu'est un skill

Un skill est stocké sous forme d'archive `.zip`. Le fichier `SKILL.md` commence par un court en-tête (le nom et une description), suivi des instructions. PromptVault suit le format ouvert Agent Skills.

Dans la liste du coffre, un skill porte un badge **Skill** et une courte description à la place du corps d'un prompt. Utilisez le filtre **Type** au-dessus de la liste pour n'afficher que les prompts ou que les skills.

## Importer un skill

1. Choisissez **Importer un skill** dans l'en-tête.
2. Sélectionnez un fichier `.zip`. Le `SKILL.md` peut se trouver à la racine de l'archive ou dans un seul dossier de premier niveau.
3. Ajoutez au besoin une catégorie et des tags, puis choisissez **Importer**.

Le skill est enregistré en une seule étape : si l'archive pose le moindre problème, rien n'est stocké. Quand l'import réussit, le skill s'ouvre aussitôt.

## Avertissements de format

PromptVault accepte les skills même s'ils ne respectent pas exactement le format. Vous voyez alors un avis qui liste chaque règle enfreinte, par exemple un nom manquant, un nom qui n'est pas en minuscules avec des tirets, une description de plus de 1 024 caractères, ou un `SKILL.md` placé à la racine de l'archive au lieu d'être dans un dossier. Les avertissements restent visibles dans la vue détaillée du skill. Ils ne bloquent jamais un import.

## Limites et archives refusées

Une archive est refusée, et rien n'est stocké, lorsqu'elle :

- n'est pas un fichier zip valide, ou est chiffrée ;
- n'a pas de `SKILL.md` à sa racine ni dans un seul dossier de premier niveau ;
- contient un chemin qui sort du dossier du skill, un lien symbolique, un chemin en double, ou un nom de fichier invalide sur les systèmes courants ;
- dépasse une limite de taille de téléversement (10 Mo par défaut), de taille décompressée (50 Mo), de nombre de fichiers (500), de profondeur de dossiers (10 niveaux) ou de taille d'un fichier (10 Mo).

Le message indique quelle règle n'est pas respectée et, le cas échéant, quelle entrée en est la cause. Les administrateurs peuvent modifier ces limites avec les paramètres `SKILL_*` du guide de déploiement.

## Parcourir un skill

La vue détaillée affiche la description, les instructions mises en forme et la liste des fichiers sous forme d'arbre. Les dossiers viennent en premier. Vous pouvez parcourir l'arbre avec les touches fléchées, ouvrir un dossier avec la flèche droite et choisir un fichier avec Entrée.

Les fichiers texte s'affichent en lecture seule. Les fichiers binaires indiquent leur taille et un lien de téléchargement. Rien dans un skill n'est jamais exécuté ni affiché comme une page web, et des marqueurs comme `${CLAUDE_SKILL_DIR}` restent du texte brut.

## Télécharger un skill

**Télécharger le skill** vous donne `<nom-du-skill>.zip` avec un seul dossier à l'intérieur, selon la disposition standard. Chaque fichier est identique à celui que vous avez importé. Le nom de l'archive reprend l'identifiant du skill, donc renommer le titre ne le change pas. Vous pouvez aussi télécharger un seul fichier depuis le visualiseur.

## Modifier, remplacer et supprimer

- **Modifier les détails** change le titre, la catégorie, les tags, la note et le favori. Les fichiers ne sont pas touchés et aucun historique de versions n'est créé.
- **Remplacer les fichiers** téléverse une nouvelle archive. Le titre, la note, les tags, la catégorie et le favori sont conservés ; la description et l'identifiant viennent du nouveau `SKILL.md`. Si la nouvelle archive est refusée, le skill reste exactement tel qu'il était.
- **Supprimer le skill** retire définitivement le skill et tous ses fichiers. Cette action est irréversible : une confirmation vous est demandée.

## Recherche, sauvegardes et limites des skills

La recherche trouve un skill par son titre, sa note et le texte de son `SKILL.md`. Elle ne regarde pas à l'intérieur des scripts ni des autres fichiers joints. Les skills sont inclus dans les sauvegardes complètes de la base et reviennent à l'identique après une restauration.

Les skills sont privés pour la personne qui les a importés. Ils n'ont ni historique de versions, ni partage, ni placeholders, et l'export en masse des prompts ne les inclut pas : exportez un skill depuis sa propre vue.

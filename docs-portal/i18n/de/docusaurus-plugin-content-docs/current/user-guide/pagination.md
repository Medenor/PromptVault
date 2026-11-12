---
title: Pagination
sidebar_position: 8
---

# Pagination

Das Haupt-Prompt-Raster lädt Ergebnisse seitenweise, statt Ihre gesamte Bibliothek auf einmal abzurufen, wodurch der anfängliche Ladevorgang auch bei einer großen Sammlung schnell bleibt.

## Mehr laden

Wenn mehr Prompts verfügbar sind, als die aktuelle Seite anzeigt, ruft ein „Mehr laden"-Steuerelement die nächste Seite ab und hängt sie an das bereits Angezeigte an, ohne Ihre Position zu verlieren. Sobald alle Prompts geladen sind, verschwindet das Steuerelement.

## Seitengröße

Sie können eine Seitengröße von 25, 50 oder 100 Prompts wählen; wenn Sie keine wählen, lädt PromptVault standardmäßig 50 auf einmal. Eine angeforderte Seitengröße über 100 wird auf 100 begrenzt, statt abgelehnt zu werden.

## Pagination und Filter

Das Anwenden eines [Kategorie](./categories.md)- oder [Tag](./tags.md)-Filters oder einer [Such](./search.md)-Anfrage paginiert die gefilterte Ergebnismenge, nicht Ihre gesamte Bibliothek — und das Ändern eines Filters setzt Sie stets auf die erste Seite zurück.

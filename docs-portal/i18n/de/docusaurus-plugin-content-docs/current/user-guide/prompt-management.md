---
title: Prompts verwalten
sidebar_position: 1
---

# Prompts verwalten

Die Hauptseite von PromptVault ist ein Karten-Raster: Jeder sichtbare Prompt wird als Karte angezeigt, und die tägliche Arbeit — Erstellen, Bearbeiten, Löschen und Favorisieren — erfolgt direkt aus diesem Raster.

## Einen Prompt erstellen

Das Erstellen eines Prompts erfordert einen Titel und den eigentlichen Prompt-Inhalt; Kategorie und Tags sind optional. Das erste Speichern erzeugt außerdem die erste Version des Prompts mit einer Commit-Nachricht (standardmäßig „Initial commit", falls keine angegeben wird), sodass sie von Anfang an im [Versionsverlauf](./versioning.md) dieses Prompts erscheint.

## Einen Prompt bearbeiten

Das Bearbeiten von Titel, Inhalt, Kategorie oder Tags eines Prompts erzeugt eine neue Version, statt die alte stillschweigend zu überschreiben — jedes Speichern wird nachverfolgt, und Sie können jederzeit eine frühere Version einsehen (oder zu ihr zurückkehren). Sie wählen die Commit-Nachricht für jede Bearbeitung, genauso wie bei der ursprünglichen Erstellung.

## Einen Prompt löschen

Das Löschen eines Prompts ist ein weiches Löschen: Der Prompt wird aus dem Raster ausgeblendet, aber seine Daten und der vollständige Versionsverlauf bleiben erhalten, statt endgültig zerstört zu werden, sodass eine Wiederherstellung weiterhin möglich bleibt. Nur der Eigentümer des Prompts oder ein Administrator kann ihn löschen.

## Favorisieren

Jeder Prompt kann über seine Karte als Favorit markiert werden, wodurch Sie das Raster auf die von Ihnen am häufigsten genutzten Prompts filtern können. Nur der Eigentümer des Prompts kann dessen Favoritenstatus umschalten — Favorisieren ist eine persönliche Markierung, keine geteilte.

## Filtern und Durchsuchen

Neben Favoriten kann das Raster nach [Kategorie](./categories.md), nach [Tag](./tags.md) oder nach einer [Such](./search.md)-Anfrage gefiltert werden, und die Ergebnisse werden paginiert — siehe [Pagination](./pagination.md) für die Funktionsweise von „Mehr laden" bei großen Bibliotheken.

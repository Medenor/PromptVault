---
title: Platzhalter
sidebar_position: 4
---

# Platzhalter

Platzhalter verwandeln einen statischen Prompt in eine wiederverwendbare Vorlage: Schreiben Sie ein Token in eckigen Klammern wie `[DURATION]` oder in geschweiften Klammern wie `{DURATION}` irgendwo im Inhalt eines Prompts, und PromptVault fordert Sie beim Kopieren des Prompts auf, es auszufüllen.

## Erkannte Syntax {#recognized-syntax}

Ein Platzhaltername muss aus 2 oder mehr Zeichen bestehen — Großbuchstaben, Ziffern, Unterstriche oder Leerzeichen — zum Beispiel `[DURATION]`, `[TYPE OF PRESENTATION]` oder `{MAX_RETRIES}`. Kleinbuchstaben, gemischte Groß-/Kleinschreibung und Bindestrich-Tokens (wie `[Duration]` oder `[YYYY-MM-DD]`) werden **nicht** als Platzhalter erkannt und bleiben als reiner Text stehen, ebenso wie einzelne Klammern, die kein passendes Paar bilden.

`[DURATION]` und `{DURATION}` werden als zwei unterschiedliche Platzhalter behandelt, obwohl sie sich einen Namen teilen — die Klammer- und Geschweifte-Klammer-Syntax verschmelzen nicht.

## Werte beim Kopieren ausfüllen {#filling-in-values-on-copy}

Ein Klick auf Kopieren bei einem Prompt mit Platzhaltern öffnet ein Formular mit einem Eingabefeld pro eindeutigem Platzhalter, statt sofort zu kopieren. Kommt derselbe Platzhalter mehrfach im Prompt vor, erhält er trotzdem nur ein einziges Feld — der eingegebene Wert ersetzt jedes Vorkommen. Ein Bestätigen mit teilweise oder ganz leeren Feldern kopiert weiterhin erfolgreich; das Token eines leer gelassenen Feldes wird unverändert in seiner ursprünglichen Form kopiert.

Prompts ohne Platzhalter werden sofort kopiert, genau wie zuvor — das Formular erscheint nur, wenn tatsächlich etwas auszufüllen ist.

## Platzhalter an anderer Stelle in PromptVault {#placeholders-elsewhere-in-promptvault}

Außerhalb des Kopiervorgangs wird ein Platzhalter-Token überall sonst als gewöhnlicher Text behandelt: Der [Versionsverlauf](./versioning.md) speichert den Rohinhalt jeder Version mit unveränderten Tokens, die [Suche](./search.md) sowie die Kategorie-/Tag-Filterung behandeln Platzhaltertext wie jeden anderen Text, und [exportierter](./import-export.md) Inhalt enthält die ursprünglichen, nicht ersetzten Tokens. Die Versionsverlaufs- und Vergleichsansichten sind schreibgeschützt und zeigen niemals das Platzhalter-Ausfüllformular — um eine ältere Version mit ausgefüllten Werten zu kopieren, stellen Sie diese zuerst wieder her und verwenden dann die normale Kopieren-Aktion.

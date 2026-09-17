---
title: Suche
sidebar_position: 4
---

# Suche

Die Suche von PromptVault läuft gegen einen echten Volltextindex statt gegen einen einfachen Teilstring-Scan, sodass Ergebnisse nach Relevanz sortiert werden und auch bei wachsender Prompt-Bibliothek schnell bleiben.

## Wie die Rangfolge funktioniert

Übereinstimmungen im **Titel** eines Prompts werden am höchsten gewichtet, dann im **Inhalt**, dann in der **Notiz** — ein Prompt, dessen Titel Ihrer Anfrage entspricht, erscheint also über einem, der den Begriff nur beiläufig erwähnt. Einfache mehrwortige Anfragen werden per OR verknüpft: Prompts, die nur einige der Wörter enthalten, erscheinen weiterhin, jedoch niedriger eingestuft als Prompts, die alle Wörter enthalten.

Wenn Sie explizit eine Sortieroption wählen (z. B. nach Datum sortieren), überschreibt dies die Relevanzsortierung, da Sie eine bestimmte Reihenfolge angefordert haben.

## Hervorhebung passender Begriffe

Suchergebnisse enthalten einen hervorgehobenen Ausschnitt, der die passenden Begriffe im Kontext zeigt, sodass Sie auf einen Blick erkennen, warum ein Prompt getroffen wurde, ohne ihn zu öffnen.

## Exakte und Phrasen-Übereinstimmung

- `case_sensitive=true`-Suchen behalten die exakte Groß-/Kleinschreibung bei.
- Das Setzen einer Anfrage in Anführungszeichen (`"exakte Phrase"`) sucht nach genau dieser Phrase, statt sie als separate, per OR verknüpfte Wörter zu behandeln.

## Zuverlässigkeit

Jede Anfrage, die PromptVault nicht als strukturierte Suche parsen kann (zum Beispiel eine, die ausschließlich aus Suchoperatoren ohne tatsächliche Suchbegriffe besteht), fällt transparent auf eine einfache Teilstring-Suche zurück, statt einen Fehler zurückzugeben — eine Suche sollte niemals allein aufgrund ihrer Formulierung fehlschlagen.

## Leistung

Die Suche bleibt schnell, auch wenn Ihre Bibliothek wächst: Die Abfragelatenz bleibt weitgehend konstant, statt linear mit der Anzahl gespeicherter Prompts zuzunehmen, da der zugrunde liegende Index — nicht ein vollständiger Scan — die Übereinstimmungsarbeit übernimmt.

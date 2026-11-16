---
title: Prompt-Versionierung
sidebar_position: 1
---

# Prompt-Versionierung

PromptVault führt einen vollständigen, Git-ähnlichen Verlauf jedes Prompts, sodass Sie nie den Überblick über dessen Entwicklung verlieren und jederzeit zu einer früheren Version zurückkehren können.

## Automatische Versionierung {#automatic-versioning}

Jedes Mal, wenn Sie eine Änderung an einem Prompt speichern, erstellt PromptVault automatisch eine neue Version mit:

- Einer eindeutigen Versions-ID
- Einem Zeitstempel
- Dem Autor der Änderung
- Einer Commit-Nachricht, die beschreibt, was geändert wurde
- Einem vollständigen Snapshot des Prompts zu diesem Zeitpunkt

Sie müssen nichts aktivieren — dies geschieht bei jeder Aktualisierung automatisch.

## Versionsverlauf anzeigen {#viewing-version-history}

Öffnen Sie den Versionsverlauf eines beliebigen Prompts über:

- Die Tastenkombination `Cmd+H` (Mac) oder `Ctrl+H` (Windows/Linux)
- Die Schaltfläche „Versionsverlauf" im Prompt-Editor

Das Verlaufsfenster listet jede Version von der neuesten bis zur ältesten mit Commit-Nachricht und Metadaten auf, bietet ein Suchfeld zum Auffinden einer bestimmten Version sowie Schnellaktionen zum Vergleichen oder Wiederherstellen.

## Versionen vergleichen {#comparing-versions}

Wählen Sie im Versionsverlauf-Fenster zwei beliebige Versionen aus, um einen detaillierten Diff über alle Prompt-Felder (Titel, Inhalt, Kategorie, Tags, Notizen) zu sehen.

Textfelder verwenden eine zeichengenaue statt zeilenweise Hervorhebung von Unterschieden, sodass kleine Änderungen — eine Tippfehlerkorrektur, eine Interpunktionsänderung, ein einzelnes hinzugefügtes Wort — leicht zu erkennen sind, statt in einer Flut „geänderter Zeilen" unterzugehen. Einfügungen erscheinen grün hervorgehoben, Löschungen rot durchgestrichen, und unveränderter Text bleibt neutral.

## Zu einer früheren Version zurückkehren {#reverting-to-a-previous-version}

Aus der Vergleichs- oder Verlaufsansicht können Sie einen Prompt auf eine beliebige frühere Version zurücksetzen. Das Zurücksetzen erstellt eine **neue** Version mit dem alten Inhalt — der Verlauf wird nicht gelöscht, sodass auch das Zurücksetzen selbst protokolliert wird und durch erneutes Zurücksetzen rückgängig gemacht werden kann.

## Warum das wichtig ist {#why-this-matters}

Wenn Sie an einem Prompt experimentieren und eine neue Variante schlechter abschneidet, können Sie jederzeit zu dem zurückkehren, was funktioniert hat, ohne sich die vorherige Formulierung merken oder manuell erneut eingeben zu müssen.

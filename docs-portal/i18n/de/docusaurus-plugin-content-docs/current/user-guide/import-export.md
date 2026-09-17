---
title: Import & Export
sidebar_position: 7
---

# Import & Export

Prompts können in eine Datei exportiert und später wieder importiert werden — entweder als portables Backup Ihrer eigenen Bibliothek oder um Prompts zwischen Instanzen zu verschieben.

## Exportformate

Prompts werden als **CSV**, **Markdown** oder **JSON** exportiert. Der JSON-Export erzeugt PromptVaults eigenes Hüllenformat, welches auch das Format ist, das der Importer beim erneuten Import automatisch erkennt.

## Importmodi

Beim Importieren einer Datei wählen Sie, wie sie mit Ihren vorhandenen Prompts interagiert:

- **Anhängen** — jeder Prompt aus der Datei wird hinzugefügt, auch wenn bereits ein Prompt mit demselben Titel existiert (kann Duplikate erzeugen).
- **Zusammenführen** — ein Prompt aus der Datei wird nur hinzugefügt, wenn kein vorhandener Prompt bereits genau diesen Titel trägt; andernfalls wird er übersprungen.
- **Ersetzen** — Ihre gesamte vorhandene Prompt-Bibliothek wird zuerst geleert, dann wird jeder Prompt aus der Datei hinzugefügt. PromptVault erstellt vor einem Ersetzen-Import automatisch ein Backup, damit der vorherige Zustand nicht verloren geht.

## Freigabestatus ist nicht portabel

Import/Export enthält niemals Freigabeberechtigungen von Prompts — siehe [Freigabe](./sharing.md#exportimport-und-freigabe) für die Begründung und die empfohlene Alternative, wenn dieser Zustand erhalten bleiben muss.

## Import-/Export-Statistiken

Eine Import-/Export-Statistikansicht zeigt aktuelle Nutzungszahlen für beide Vorgänge an — nützlich, um zu bestätigen, dass ein umfangreicher Import oder Export tatsächlich wie erwartet abgeschlossen wurde.

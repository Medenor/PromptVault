---
title: Import & Export
sidebar_position: 7
---

# Import & Export

Exportieren Sie Prompts, um Prompt-Inhalte zwischen Instanzen zu verschieben oder eine portable Kopie Ihrer Bibliothek zu behalten. Ein Export ist kein vollständiges Backup: Er enthält keine Freigabeberechtigungen. Verwenden Sie ein vollständiges Backup, wenn der Zugriffszustand erhalten bleiben muss.

## Exportformate {#export-formats}

Prompts werden als **CSV**, **Markdown** oder **JSON** exportiert. Der JSON-Export erzeugt PromptVaults eigenes Hüllenformat, welches auch das Format ist, das der Importer beim erneuten Import automatisch erkennt.

## Importmodi {#import-modes}

Bestimmen Sie vor dem Import den Modus, der dem gewünschten Ergebnis entspricht. Wählen Sie **Ersetzen** nur, wenn Sie die gesamte Bibliothek ersetzen möchten.

- **Anhängen** — jeder Prompt aus der Datei wird hinzugefügt, auch wenn bereits ein Prompt mit demselben Titel existiert (kann Duplikate erzeugen).
- **Zusammenführen** — ein Prompt aus der Datei wird nur hinzugefügt, wenn kein vorhandener Prompt bereits genau diesen Titel trägt; andernfalls wird er übersprungen.
- **Ersetzen** — Ihre gesamte vorhandene Prompt-Bibliothek wird zuerst geleert, dann wird jeder Prompt aus der Datei hinzugefügt. PromptVault erstellt vor dem Import ein Backup. Prüfen Sie, dass dieses Backup abgeschlossen ist, bevor Sie sich darauf verlassen, die vorherige Bibliothek wiederherstellen zu können.

## Freigabestatus ist nicht portabel {#sharing-state-is-not-portable}

Import/Export enthält niemals Freigabeberechtigungen von Prompts — siehe [Freigabe](./sharing.md#exportimport-and-sharing) für die Begründung und die empfohlene Alternative, wenn dieser Zustand erhalten bleiben muss.

## Import-/Export-Statistiken {#importexport-statistics}

Eine Import-/Export-Statistikansicht zeigt aktuelle Nutzungszahlen für beide Vorgänge an — nützlich, um zu bestätigen, dass ein umfangreicher Import oder Export tatsächlich wie erwartet abgeschlossen wurde.

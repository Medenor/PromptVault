---
title: Prompts teilen
sidebar_position: 3
---

# Prompts teilen

PromptVault unterstützt das Teilen einzelner Prompts mit bestimmten Teammitgliedern, mit feingranularer Lese-/Bearbeitungs-Zugriffskontrolle.

## Zugriff gewähren {#granting-access}

Über das Freigabe-Modal eines Prompts können Sie einem Teammitglied eine von zwei Zugriffsstufen gewähren:

- **Lesen**: den Prompt und dessen Versionsverlauf ansehen.
- **Bearbeiten**: alles, was Lesen erlaubt, zusätzlich das Bearbeiten von Inhalt, Kategorie und Tags des Prompts sowie das Zurücksetzen auf eine frühere Version.

Keine der beiden Stufen erlaubt das Löschen des Prompts, das Weitergeben an andere, das Umschalten des Favoritenstatus oder die Übertragung des Eigentums — diese bleiben ausschließlich dem Eigentümer vorbehalten. Die Empfängersuche durchsucht aktive Benutzer nach Benutzername- oder E-Mail-Präfix, zeigt jedoch niemals E-Mail-Adressen in den Ergebnissen an.

## Zugriff widerrufen {#revoking-access}

Der Zugriff kann vom Prompt-Eigentümer jederzeit über dasselbe Freigabe-Modal widerrufen werden.

## Geteilte Prompts finden {#finding-shared-prompts}

Ein Filter „Mit mir geteilt" zeigt Prompts, die andere Personen mit Ihnen geteilt haben. Geteilte Prompts tragen ein eigenes „Geteilt"-Abzeichen, damit Sie eine explizite Freigabe von einem standardmäßig sichtbaren Prompt unterscheiden können.

## Legacy-öffentliche Prompts {#legacy-public-prompts}

Prompts, die vor der Einführung der Freigabefunktion erstellt wurden, sind als **„Öffentlich (Legacy)"** eingestuft — sichtbar für jeden authentifizierten Benutzer, nicht nur für explizit berechtigte Personen — und werden anders gekennzeichnet als eine explizite Freigabe. Ein Eigentümer oder Administrator kann einen Legacy-öffentlichen Prompt über die Aktion „Privat machen" privat setzen; dies ist ein einseitiger Übergang ohne Möglichkeit, ihn anschließend wieder als Legacy-öffentlich zu veröffentlichen — behandeln Sie dies daher als bewusste Entscheidung, nicht als Anzeigeoption.

Prompts, die nach der Einführung der Freigabefunktion erstellt wurden, sind standardmäßig **privat**: sichtbar nur für ihren Eigentümer, Administratoren und explizit berechtigte Personen.

## Export/Import und Freigabe {#exportimport-and-sharing}

Freigabeberechtigungen und das Legacy-öffentlich-Flag sind **nicht** in exportierten Prompts (CSV/Markdown/JSON) enthalten — sie sind Zugriffskontrollzustand, der an die Benutzerkonten dieser spezifischen Instanz gebunden ist, kein portabler Prompt-Inhalt. Das erneute Importieren einer exportierten Datei erstellt einfache private Prompts ohne wiederhergestellte Berechtigungen. Wenn der Freigabezustand erhalten bleiben soll, verwenden Sie stattdessen ein vollständiges Datenbank-Backup/eine Wiederherstellung statt Export/Import.

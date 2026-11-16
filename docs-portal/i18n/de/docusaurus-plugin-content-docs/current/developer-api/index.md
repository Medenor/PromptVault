---
title: Die vorhandene API nutzen
sidebar_position: 1
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Die vorhandene API nutzen

Über die Programmierschnittstelle (API) verbinden Sie Skripte und andere Werkzeuge mit PromptVault. Dieser Bereich richtet sich an Personen, die HTTP-Anfragen und ein Terminal verwenden. Für Aufgaben in der Anwendung lesen Sie das [Benutzerhandbuch](../user-guide/prompt-management.md). Hinweise zum Server finden Sie unter [Installation](../installation/index.md) und [Konfiguration](../configuration/index.md).

## Einen Einstieg wählen

- [Erste API-Aufrufe ausführen](getting-started.md): Prompts lesen und einen Test-Prompt erstellen und suchen.
- [API-Referenz](reference.md): Routen, Formate, Zugriffsregeln und Fehler nachschlagen.

## Die Referenz Ihrer Instanz öffnen

Dokumentation und PromptVault-Anwendung können unterschiedliche Adressen haben. Öffnen Sie diese Pfade an der Adresse der **Anwendung**:

| Pfad            | Zweck                             |
| --------------- | --------------------------------- |
| `/docs`         | Interaktive API-Referenz          |
| `/redoc`        | Alternative Ansicht der Referenz  |
| `/openapi.json` | Maschinenlesbare API-Beschreibung |

Läuft die Anwendung unter `http://localhost:8001`, öffnen Sie `http://localhost:8001/docs`. Behalten Sie einen vom Betreiber vorgegebenen URL-Präfix bei.

Zum Lesen dieser Anleitungen brauchen Sie keine laufende Instanz. Zum Ausführen einer Anfrage brauchen Sie die Anwendung und die dort verlangten Zugangsdaten. **Try it out** sendet echte Anfragen. Verwenden Sie zum Ändern und Löschen ausschließlich Test-Prompts.

## Den aktuellen Umfang kennen

Die vorhandenen Routen beginnen mit `/api/...`, ohne `/v1`. Authentifizieren Sie Skriptanfragen mit dem im Tutorial beschriebenen Sitzungstoken.

Die Live-Referenz zeigt die aktivierten Routen Ihrer Instanz. Bei deaktivierter Authentifizierung fehlen die Authentifizierungs- und Administrationsrouten. Manche Beschreibungen enthalten noch ältere Aussagen zur Sichtbarkeit; beachten Sie die Zugriffsregeln in der [Referenz](reference.md). Die installierte Anwendungsversion steht in der Fußzeile. Änderungen finden Sie in den [Versionshinweisen](../release-notes/index.md).

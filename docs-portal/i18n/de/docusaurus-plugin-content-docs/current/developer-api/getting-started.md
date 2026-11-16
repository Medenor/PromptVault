---
title: Erste API-Aufrufe ausführen
sidebar_position: 2
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Erste API-Aufrufe ausführen

Lesen Sie eine Seite mit Prompts. Erstellen und suchen Sie anschließend einen Test-Prompt auf Ihrer Instanz.

## Den Versuch vorbereiten

Sie benötigen eine Testinstanz, Bash und `curl` mit `--json` (ab Version 7.82). Bei aktiver Authentifizierung brauchen Sie ein aktives Konto und gegebenenfalls Ihre Authenticator-App. Ersetzen Sie Platzhalter in spitzen Klammern lokal. Geben Sie Passwörter, Tokens und Anmeldeantworten nicht weiter. Verwenden Sie HTTPS für entfernte Instanzen.

## Die Anwendungsadresse festlegen

Tragen Sie die Adresse Ihrer Anwendung ein, nicht die der Dokumentation. Das Beispiel gilt für eine lokale Installation. Behalten Sie einen vorhandenen URL-Präfix bei, ohne abschließenden Schrägstrich.

```bash
BASE_URL='http://localhost:8001'
```

## Sich anmelden

Überspringen Sie diesen Schritt nur, wenn Ihre isolierte Instanz bereits mit `AUTH_ENABLED=false` läuft. Lassen Sie dann den Authorization-Header bei den folgenden Anfragen weg. Deaktivieren Sie die Authentifizierung nicht eigens für eine Integration. Siehe [Konfiguration](../configuration/index.md).

Senden Sie die Zugangsdaten als JSON:

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login" \
  --json '{"username_or_email":"<USERNAME>","password":"<PASSWORD>"}'
```

Nach abgeschlossener Anmeldung erhalten Sie `access_token` und `refresh_token`. Enthält die Antwort stattdessen `challenge_token`, führen Sie die folgende Anfrage mit diesem Token und einem aktuellen Authenticator-Code oder unbenutzten Wiederherstellungscode aus. Das Challenge-Token ist kein Zugriffstoken. Falls eine Einrichtung verlangt wird, schließen Sie diese zuerst in der Anwendung ab; siehe [Zwei-Faktor-Authentifizierung](../user-guide/two-factor-auth.md).

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login/2fa" \
  --json '{"challenge_token":"<CHALLENGE_TOKEN>","code":"<CODE>"}'
```

Kopieren Sie das erhaltene `access_token`. Führen Sie diesen Befehl aus, fügen Sie das Token ein und drücken Sie die Eingabetaste. Bash blendet die Eingabe aus und speichert das Token selbst nicht im Befehlsverlauf:

```bash
read -r -s TOKEN
```

## Eine Seite mit Prompts lesen

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts?page=1&limit=10&item_type=prompt"
```

Erwartet werden HTTP 200 und die Felder `prompts`, `page`, `limit`, `total_count`, `total_pages`, `has_next` und `has_previous`. `prompts` ist ein Objekt mit Element-IDs als Schlüsseln, kein Array. Eine leere Seite ist möglich. Bei aktiver Authentifizierung bestimmen Ihre Identität und Berechtigungen die Ergebnisse.

## Einen Test-Prompt erstellen

Diese Anfrage legt Daten an. Verwenden Sie ein Testkonto und Beispieldaten. Die Erstellung erwartet Formularfelder statt JSON:

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts" \
  --data-urlencode 'title=API tutorial' \
  --data-urlencode 'prompt=Summarize this sample text.' \
  --data-urlencode 'tags=api-tutorial'
```

Erwartet werden HTTP 201 und `{"success":true,"prompt_id":...}`. Übernehmen Sie die erhaltene `prompt_id` in den nächsten Befehl:

```bash
PROMPT_ID='<PROMPT_ID>'
```

## Suchen und Versionen lesen

Die Suche verwendet `search`, nicht `q`. Mit `item_type=prompt` schließen Sie Skills aus Listen- und Suchergebnissen aus.

```bash
curl --silent --show-error --fail-with-body --get \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/search" \
  --data-urlencode 'search=API tutorial' \
  --data-urlencode 'item_type=prompt'
```

```bash
curl --silent --show-error --fail-with-body \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/$PROMPT_ID/versions"
```

Die Verlaufsantwort enthält `versions`. Routen zum Ändern, Wiederherstellen und Löschen finden Sie in der [Referenz](reference.md). Löschen Sie nur Ihren Test-Prompt. Entfernen Sie danach das lokale Token mit `unset TOKEN`; die Serversitzung bleibt bestehen. Lesen Sie bei Fehlern die [Fehlerhilfe](reference.md#einen-fehlgeschlagenen-aufruf-prüfen), bevor Sie die Anfrage wiederholen.

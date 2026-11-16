---
title: API-Referenz
sidebar_position: 3
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# API-Referenz

Hier finden Sie die vorhandenen Routengruppen. Das vollständige Schema steht unter `/docs` an der Adresse Ihrer **Anwendung**, nicht auf der Dokumentationsseite. Beginnen Sie für eine Anleitung mit den [ersten API-Aufrufen](getting-started.md).

## Authentifizierung und Zugriff {#authentication-and-access}

Senden Sie in Skripten `Authorization: Bearer <ACCESS_TOKEN>`. Anmeldung und Token-Erneuerung erwarten JSON. Das Erstellen und Ändern von Prompts erwartet Formularfelder.

Zugriffstokens laufen standardmäßig nach 15 Minuten ab. Senden Sie das neueste Aktualisierungstoken als `{"refresh_token":"<REFRESH_TOKEN>"}` an `POST /api/auth/refresh`. Ersetzen Sie danach **beide** Tokens. Die Wiederverwendung eines alten Aktualisierungstokens kann die Sitzung widerrufen. Führen Sie keine gleichzeitigen Erneuerungen aus. `POST /api/auth/logout` beendet die Sitzung mit dem aktuellen Aktualisierungstoken als JSON.

Bei aktiver Authentifizierung liefern Liste und Suche nur sichtbare Elemente. Ohne Zugangsdaten oder mit einem ungültigen beziehungsweise abgelaufenen Token kann eine leere Seite statt 401 erscheinen. Eine leere Seite bestätigt daher keine erfolgreiche Authentifizierung. Eigentum, Administratorrechte, Freigaben und ältere Sichtbarkeitseinstellungen bestimmen den Zugriff. Eine Bearbeitungsfreigabe erlaubt Änderungen und Wiederherstellungen, aber kein Löschen oder Verwalten von Freigaben. Siehe [Freigaben](../user-guide/sharing.md). Für Skills gelten eigene Regeln; siehe [Skills](../user-guide/skills.md).

## Eine Operation finden {#find-an-operation}

Ersetzen Sie `{id}` durch eine Prompt-ID und `{version_id}` durch eine Kennung aus dem Verlauf. Die Tabelle dient zur Orientierung und listet nicht alle Verwaltungsoperationen auf.

| Operation                                  | Route                                                                                                          |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Auflisten / suchen                         | `GET /api/prompts` · `GET /api/prompts/search`                                                                 |
| Erstellen / lesen / ändern / löschen       | `POST /api/prompts` · `GET /api/prompts/{id}` · `PUT /api/prompts/{id}` · `DELETE /api/prompts/{id}`           |
| Verlauf / einzelne Version lesen           | `GET /api/prompts/{id}/versions` · `GET /api/prompts/{id}/versions/{version_id}`                               |
| Eine Version wiederherstellen              | `POST /api/prompts/{id}/versions/{version_id}/revert`                                                          |
| Prompt-Freigaben verwalten                 | `POST /api/prompts/{id}/shares` · `GET /api/prompts/{id}/shares` · `DELETE /api/prompts/{id}/shares/{user_id}` |
| Skills importieren / lesen / herunterladen | `POST /api/skills/import` · `GET /api/skills/{id}` · `GET /api/skills/{id}/download`                           |
| Kategorien / Tags lesen                    | `GET /api/categories` · `GET /api/tags`                                                                        |
| Prompts importieren / exportieren          | `POST /api/import` · `POST /api/export`                                                                        |
| Backups verwalten                          | `GET /api/backups` · `POST /api/backups`                                                                       |
| Konten / Sitzungen / Zeitpläne verwalten   | `/api/admin/users` · `/api/admin/sessions` · `/api/admin/scheduler/...`                                        |

Berechtigungen und Anfrageformate für Verwaltungsoperationen stehen in der Live-Referenz.

Formularfelder für Erstellung und Änderung: `title`, `prompt`, `category`, `tags`, `commit_message` und optional `semantic_version`. `title` und `prompt` sind in beiden Fällen erforderlich. Trennen Sie Tags durch Kommas. Eine Wiederherstellung akzeptiert das optionale Formularfeld `commit_message` und erzeugt einen neuen Verlaufseintrag. Löschen entfernt Daten; verwenden Sie diese Operation nur gezielt.

## Ergebnisse seitenweise lesen {#read-paginated-results}

Liste und Suche verwenden standardmäßig `page=1` und `limit=50`, höchstens 100 Elemente pro Seite. Lesen Sie weiter, solange `has_next` den Wert `true` hat. Das Objekt `prompts` verwendet IDs als Schlüssel. `item_type` akzeptiert `all`, `prompt` oder `skill`; Skills enthalten keinen `prompt`-Text. `filter=shared-with-me` beschränkt die Ergebnisse auf ausdrückliche Freigaben.

Die Suche akzeptiert `search`, `category`, `tag`, `favorites`, `case_sensitive` und `ranked`. Geben Sie Suchausschnitte niemals als unverarbeitetes HTML aus. Weitere Hinweise stehen in der [Suchanleitung](../user-guide/search.md).

## Einen fehlgeschlagenen Aufruf prüfen {#resolve-a-failed-call}

Prüfen Sie HTTP-Status und Antworttext. Je nach Operation enthalten Fehler `detail`, `error` oder eine strukturierte Meldung. Ein fehlender Prompt kann etwa `{"detail":"Prompt with ID 123 not found"}` zurückgeben.

| Status | Mögliche Ursache                                                    | Maßnahme                                                                             |
| ------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 401    | Fehlende, ungültige oder abgelaufene Zugangsdaten                   | Melden Sie sich an oder erneuern Sie einmal mit dem neuesten Aktualisierungstoken.   |
| 403    | Fehlende Rechte oder unvollständige vorgeschriebene 2FA-Einrichtung | Prüfen Sie Ihre Rechte und schließen Sie die Einrichtung in der Anwendung ab.        |
| 404    | Falsche oder deaktivierte Route, fehlendes oder verborgenes Element | Prüfen Sie Adresse, ID und Zugriff; setzen Sie die Existenz nicht voraus.            |
| 409    | Operation passt nicht zum Elementtyp                                | Verwenden Sie Skill-Routen für Skills und Prompt-Routen für reine Prompt-Funktionen. |
| 422    | Fehlende Felder, falsches Format oder ungültige Werte               | Lesen Sie die Feldfehler; senden Sie zum Erstellen und Ändern Formularfelder.        |
| 429    | Anfragelimit erreicht                                               | Warten Sie die in `Retry-After` angegebene Anzahl Sekunden.                          |

Grenzwerte hängen von Operation und Server ab; siehe [Konfiguration](../configuration/index.md). Prüfen Sie nach einer Zeitüberschreitung, ob eine Änderung bereits erfolgreich war, bevor Sie diese erneut senden. Hilfe bei Verbindungs- und Serverproblemen finden Sie unter [Fehlerbehebung](../troubleshooting/index.md).

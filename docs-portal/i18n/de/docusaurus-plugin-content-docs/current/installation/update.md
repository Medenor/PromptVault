---
title: PromptVault aktualisieren
description: Eine selbst gehostete PromptVault-Installation sicher aktualisieren.
---

# PromptVault aktualisieren

Mit diesen Schritten aktualisieren Sie die Docker-Compose-Installation aus der [Installationsanleitung](index.md). Die Datenbank behält ihre Daten, während Sie die Dienste `web` und `docs` neu erstellen.

## Vor dem Start

1. Lesen Sie die [Versionshinweise](../release-notes/index.md) zu Änderungen, die Ihre Installation betreffen.
2. Prüfen Sie, ob auf dem Server genug Speicherplatz für eine Datenbanksicherung und neue Images vorhanden ist.
3. Planen Sie ein kurzes Wartungsfenster ein. Während des Neustarts können sich Nutzer möglicherweise nicht anmelden.
4. Stellen Sie sicher, dass Sie auf den PromptVault-Projektordner und den Datenbank-Container zugreifen können.

## 1. Datenbank sichern

Erstellen und prüfen Sie eine komprimierte Datenbanksicherung, bevor Sie das Update herunterladen oder starten. Führen Sie diese Befehle im PromptVault-Projektordner aus:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

Der letzte Befehl muss ohne Fehler enden. Prüfen Sie, dass die Sicherungsdatei nicht leer ist. Lassen Sie sie für eine mögliche Wiederherstellung in `data/backups` und kopieren Sie eine zweite Datei an einen sicheren Ort außerhalb des Servers. Fahren Sie nicht fort, wenn die Sicherung fehlgeschlagen ist.

## 2. Version herunterladen und neu erstellen

Wählen Sie im PromptVault-Projektordner die gewünschte Version aus. Ein Release-Tag ist die Kennzeichnung einer veröffentlichten Version. Verwenden Sie ein Tag aus den Versionshinweisen:

```bash
git fetch --tags
git checkout <RELEASE_TAG>
```

Erstellen und starten Sie die Anwendungs- und Dokumentationsdienste neu:

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

Das Projekt ist so konfiguriert, dass `web` erst startet, wenn Datenbank und Redis bereit sind.

## 3. Datenbank aktualisieren

Eine Datenbankmigration passt die Datenbankstruktur an die neue PromptVault-Version an. Führen Sie die Migration aus und prüfen Sie anschließend, welche Migrationsversion aktiv ist:

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

Der zweite Befehl sollte die aktuelle Migrationsversion anzeigen. Wenn die Migration fehlschlägt, halten Sie hier an und lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

## 4. Update prüfen

```bash
curl --fail http://localhost:8001/api/health
```

Die Gesundheitsprüfung sollte erfolgreich sein. Öffnen Sie PromptVault im Browser, melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Öffnen Sie auch den Dokumentationsdienst, falls Sie ihn verwenden (Standardadresse: `http://localhost:7876`).

## Bei Problemen

Prüfen Sie die Dienstprotokolle auf Fehlermeldungen:

```bash
docker compose logs --tail=100 web docs
```

Wenn ein Neuaufbau ohne Cache mit `No module named 'psycopg'` fehlschlägt, verwenden Sie PromptVault 1.13.1 oder neuer. Diese Version behebt das Abhängigkeitsproblem aus [Ticket #94](https://codeberg.org/medenor/promptvault/issues/94). Bei anderen Fehlern lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

### Zur vorherigen Version zurückkehren

Mit diesen Schritten stellen Sie die Datenbanksicherung von vor dem Update wieder her und setzen die Anwendung und Dokumentation auf die vorherige Version zurück. Die Wiederherstellung ersetzt die aktuelle Datenbank durch die frühere Sicherung. Prompts und andere Änderungen seit dieser Sicherung gehen verloren, wenn Sie die aktuelle Datenbank nicht zuerst sichern.

Wenn Sie nach dem Update Prompts erstellt oder geändert haben, sichern Sie die aktuelle Datenbank vor der Wiederherstellung:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Stoppen Sie anschließend die Anwendung, wählen Sie in den Versionshinweisen das Tag der vorherigen Version und erstellen Sie deren Images neu:

```bash
docker compose stop web
git fetch --tags
git checkout <VORHERIGES_RELEASE_TAG>
docker compose build web docs
```

Stellen Sie die geprüfte Sicherung von vor dem Update wieder her. Ersetzen Sie `<SICHERUNGSDATEI>` durch den Dateinamen aus Schritt 1. Der erste Befehl löscht den aktuellen Datenbankinhalt, bevor die Sicherung geladen wird:

```bash
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
set -euo pipefail
gzip -dc "data/backups/<SICHERUNGSDATEI>" \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Starten Sie die vorherige Version und prüfen Sie, ob PromptVault funktioniert:

```bash
docker compose up -d web docs
curl --fail http://localhost:8001/api/health
```

Melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Wenn die Wiederherstellung oder der Start fehlschlägt, halten Sie an und lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

---
title: PromptVault aktualisieren
description: Eine selbst gehostete PromptVault-Installation sicher aktualisieren.
---

# PromptVault aktualisieren

Mit diesen Schritten aktualisieren Sie die Docker-Compose-Installation aus der [Installationsanleitung](index.md). Die Datenbank behält ihre Daten, während Sie die Dienste `web` und `docs` neu erstellen.

## Vor dem Start {#before-you-start}

1. Lesen Sie die [Versionshinweise](../release-notes/index.md) und `CHANGELOG.md` auf inkompatible Änderungen und Hinweise zu Datenbankmigrationen.
2. Prüfen Sie, ob auf dem Server genug Speicherplatz für eine Datenbanksicherung und neue Images vorhanden ist.
3. Testen Sie das Update zuerst auf einer Testinstallation, falls verfügbar.
4. Planen Sie ein kurzes Wartungsfenster ein. Während des Neustarts können sich Nutzer möglicherweise nicht anmelden.
5. Stellen Sie sicher, dass Sie auf den PromptVault-Projektordner und den Datenbank-Container zugreifen können.

## 1. Datenbank sichern {#1-back-up-the-database}

Erstellen und prüfen Sie eine komprimierte Datenbanksicherung, bevor Sie das Update herunterladen oder starten. Führen Sie diese Befehle im PromptVault-Projektordner aus:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

Der letzte Befehl muss ohne Fehler enden. Prüfen Sie, dass die Sicherungsdatei nicht leer ist. Lassen Sie sie für eine mögliche Wiederherstellung in `data/backups` und kopieren Sie eine zweite Datei an einen sicheren Ort außerhalb des Servers. Fahren Sie nicht fort, wenn die Sicherung fehlgeschlagen ist.

## 2. Version herunterladen und neu erstellen {#2-download-and-rebuild}

Wechseln Sie im PromptVault-Projektordner auf den neuesten Stand von `main`. Für eine bestimmte stabile Version verwenden Sie stattdessen deren Tag.

```bash
git checkout main
git pull origin main
```

Um eine bestimmte veröffentlichte Version zu installieren, rufen Sie deren Tag ab und wechseln Sie dorthin:

```bash
git fetch --tags
git checkout <RELEASE_TAG>
```

Erstellen Sie die Images ohne Cache neu und ersetzen Sie anschließend den Web-Container. Datenbank und Redis sollen dabei weiterlaufen:

```bash
docker-compose build --no-cache
docker-compose stop web
docker-compose rm web
docker-compose up -d db redis
sleep 15
docker-compose up -d web docs
```

Warten Sie nach dem Start von Datenbank und Redis 15 Sekunden, damit die Datenbank ihre Initialisierung abschließen kann. Das Projekt wartet außerdem auf erfolgreiche Gesundheitsprüfungen von Datenbank und Redis, bevor `web` startet.

## 3. Datenbank aktualisieren {#3-apply-database-updates}

Eine Datenbankmigration passt die Datenbankstruktur an die neue PromptVault-Version an. Führen Sie die Migration aus und prüfen Sie anschließend, welche Migrationsversion aktiv ist:

```bash
docker-compose exec -T web alembic upgrade head
docker-compose exec -T web alembic current
```

Führen Sie die Migration erst aus, wenn `web` gestartet ist. Der zweite Befehl sollte die aktuelle Migrationsversion anzeigen. Wenn die Migration fehlschlägt, halten Sie hier an und lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

## 4. Update prüfen {#4-check-the-update}

```bash
docker-compose logs web | head -50
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Die Gesundheitsprüfung sollte erfolgreich sein. Öffnen Sie PromptVault im Browser, melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Öffnen Sie auch den Dokumentationsdienst, falls Sie ihn verwenden (Standardadresse: `http://localhost:7876`).

## Bei Problemen {#if-something-goes-wrong}

Prüfen Sie die Dienstprotokolle auf Fehlermeldungen:

```bash
docker-compose logs --tail=100 web docs
```

Wenn ein Neuaufbau ohne Cache mit `No module named 'psycopg'` fehlschlägt, verwenden Sie PromptVault 1.13.1 oder neuer. Diese Version behebt das Abhängigkeitsproblem aus [Ticket #94](https://github.com/Medenor/PromptVault/issues/94). Bei anderen Fehlern lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

### Zur vorherigen Version zurückkehren {#return-to-the-previous-version}

Mit diesen Schritten stellen Sie die Datenbanksicherung von vor dem Update wieder her und setzen die Anwendung und Dokumentation auf die vorherige Version zurück. Die Wiederherstellung ersetzt die aktuelle Datenbank durch die frühere Sicherung. Prompts und andere Änderungen seit dieser Sicherung gehen verloren, wenn Sie die aktuelle Datenbank nicht zuerst sichern.

Stoppen Sie die Anwendung, bevor Sie fortfahren:

```bash
docker-compose stop web
```

Wenn Sie nach dem Update Prompts erstellt oder geändert haben, sichern Sie die aktuelle Datenbank vor der Wiederherstellung:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Stellen Sie die geprüfte Sicherung von vor dem Update wieder her. Ersetzen Sie `<SICHERUNGSDATEI>` durch den Dateinamen aus Schritt 1, ohne den Ordnerpfad `data/backups/`. Diese Befehle löschen und erstellen die Datenbank neu, bevor die Sicherung geladen wird:

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<SICHERUNGSDATEI>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

Wählen Sie anschließend die vorherige Version aus und erstellen Sie deren Images ohne Cache neu:

```bash
git fetch --tags
git checkout <VORHERIGES_RELEASE_TAG>
docker-compose build --no-cache
```

Starten Sie die vorherige Version und prüfen Sie die Protokolle sowie die Gesundheitsprüfung:

```bash
docker-compose up -d web docs
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Wenn die Wiederherstellung oder der Start fehlschlägt, halten Sie an und lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

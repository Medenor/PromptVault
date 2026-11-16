---
title: PromptVault aktualisieren
description: Eine selbst gehostete PromptVault-Installation sicher aktualisieren.
---

# PromptVault aktualisieren

Diese Schritte gelten für die in [Installation](index.md) beschriebene Docker-Compose-Installation. Sie aktualisieren die Dienste `web` und `docs`, während die Datenbank und ihr benanntes Volume erhalten bleiben.

## Vor dem Start

1. Lesen Sie die [Versionshinweise](../release-notes/index.md) auf Änderungen, die Ihre Installation betreffen.
2. Prüfen Sie, ob auf dem Server genug Speicherplatz für eine Datenbanksicherung und neue Images vorhanden ist.
3. Planen Sie ein kurzes Wartungsfenster ein. Während des Neustarts können sich Nutzer möglicherweise nicht anmelden.
4. Stellen Sie sicher, dass Sie auf den Projektordner auf dem Server und den Datenbank-Container zugreifen können.

## 1. Datenbank sichern

Erstellen und prüfen Sie einen komprimierten Datenbank-Dump, bevor Sie das Update herunterladen oder starten:

```bash
mkdir -p data/backups
docker compose exec -T db pg_dump -U promptvault -d promptvault \
  | gzip > "data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
gzip -t data/backups/*.sql.gz
```

Prüfen Sie, dass die neueste Datei nicht leer ist und `gzip -t` ohne Fehler endet. Bewahren Sie die Sicherung sicher auf. Fahren Sie nicht fort, wenn die Sicherung fehlgeschlagen ist.

## 2. Herunterladen und neu erstellen

Wechseln Sie in den PromptVault-Projektordner und holen Sie die gewünschte Version. Verwenden Sie das Release-Tag aus den Versionshinweisen, wenn Sie nicht die neueste Entwicklungsversion möchten:

```bash
git fetch --tags
git checkout <release-tag>
```

Erstellen Sie die Images neu und starten Sie Anwendungs- und Dokumentationsdienste:

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

Datenbank und Redis müssen gesund sein, bevor die Anwendung startet. Compose wartet auf die im Projekt konfigurierten Gesundheitsprüfungen.

## 3. Datenbankmigrationen ausführen

Führen Sie die Migration mit dem aktualisierten Web-Image aus:

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

Der zweite Befehl zeigt die aktuelle Revision. Falls die Migration fehlschlägt, halten Sie hier an und lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

## 4. Update prüfen

```bash
curl --fail http://localhost:8001/api/health
```

Der Health-Endpunkt sollte erfolgreich antworten. Öffnen Sie PromptVault im Browser, melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Öffnen Sie auch den Dokumentationsdienst, falls Sie ihn verwenden (Standard: `http://localhost:7876`).

## Bei Problemen

Prüfen Sie zuerst die Dienstprotokolle:

```bash
docker compose logs --tail=100 web docs
```

Ein Neuaufbau ohne Cache kann eine fehlende Python-Abhängigkeit sichtbar machen, wenn deren Version nicht korrekt festgelegt ist. Die in den Versionshinweisen zu [Ticket #94](https://codeberg.org/medenor/promptvault/issues/94) korrigierte SQLAlchemy-Versionsbeschränkung verhindert beispielsweise ein bekanntes Installationsproblem mit `psycopg`. Weitere Symptome finden Sie unter [Fehlerbehebung](../troubleshooting/index.md).

### Datenbanksicherung wiederherstellen

Wenn die neue Version nicht funktioniert, wechseln Sie zur vorherigen Anwendungsversion und stellen Sie den geprüften Dump wieder her. Dabei wird der aktuelle Datenbankinhalt ersetzt. Sichern Sie den aktuellen Stand zuerst, falls er neue Daten enthält.

```bash
docker compose stop web
# Kopieren Sie die Sicherungsdatei bei Bedarf auf den Server, dann:
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
gzip -dc data/backups/<sicherungsdatei>.sql.gz \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Starten Sie nach der Wiederherstellung die Dienste `web` und `docs` der vorherigen Version. Hilfe finden Sie unter [Fehlerbehebung](../troubleshooting/index.md).

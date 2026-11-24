---
title: Fehlerbehebung
sidebar_position: 4
---

# Fehlerbehebung

Verwenden Sie diese Seite, um das Symptom zu bestimmen, die kleinste sichere Änderung vorzunehmen und es erneut zu versuchen. Löschen Sie beim Beheben eines Problems in einer bestehenden Installation keine Datenbank und kein Docker-Volume. Für eine ausführliche Behandlung siehe `docs/TROUBLESHOOTING.md` des Projekts.

## Port bereits belegt {#port-already-in-use}

Wenn Port `8001` (Web), `5432` (PostgreSQL) oder `6379` (Redis) bereits von einem anderen Prozess belegt ist, schlägt `docker-compose up` beim Starten dieses Dienstes fehl. Beenden Sie den blockierenden Prozess, oder ändern Sie den zugeordneten Port in Ihrer `.env`/`docker-compose.yml`, bevor Sie es erneut versuchen.

## Docker-Daemon läuft nicht {#docker-daemon-not-running}

`docker-compose`-Befehle schlagen mit einem Verbindungsfehler fehl, wenn Docker selbst nicht läuft. Starten Sie Docker Desktop (oder den `docker`-Dienst unter Linux) und versuchen Sie es erneut.

## Datenbankverbindung fehlgeschlagen {#database-connection-failed}

Wenn PromptVault beim Start keine Verbindung zu PostgreSQL herstellen kann:

- Bestätigen Sie, dass der Container/Dienst tatsächlich läuft (`docker-compose ps`).
- Prüfen Sie, ob `DATABASE_URL` in `.env` mit den Zugangsdaten und dem Host/Port übereinstimmt, auf dem PostgreSQL tatsächlich lauscht.
- Wenn Sie `POSTGRES_PASSWORD` geändert haben, übernimmt ein bestehendes initialisiertes Datenvolume das neue Passwort nicht automatisch. Ändern Sie bei einer bestehenden Installation das Passwort zuerst in der Datenbank: siehe [Datenbankpasswort](../installation/production-setup.md#replace-the-default-database-password). Erstellen Sie ein Volume nur für eine neue Installation ohne zu behaltende Daten neu.
- Wenn Sie Docker Compose mit `--env-file .env.production` starten, verwenden Sie diese Option bei jedem Befehl. Ohne sie liest Compose `.env` und verwendet möglicherweise ein anderes `POSTGRES_PASSWORD` (oder den Standardwert `changeme`), als die Datenbank erwartet.

## Start schlägt mit `No module named 'psycopg'` fehl {#psycopg-missing}

Unter PostgreSQL startet der `web`-Container in einer Schleife neu, und sein Protokoll endet mit `ModuleNotFoundError: No module named 'psycopg'`. Derselbe Fehler erscheint bei `alembic upgrade head`. Betroffen sind PromptVault 1.16.0 und daraus gebaute Images: Sie verwenden eine neuere Datenbankbibliothek, die den Treiber psycopg v3 erwartet, den diese Version nicht installiert hat. SQLite-Installationen sind nicht betroffen.

Aktualisieren Sie auf PromptVault 1.17.0 oder neuer, indem Sie [PromptVault aktualisieren](../installation/update.md) folgen. Sie müssen `DATABASE_URL` nicht ändern: `postgresql://` und die ältere Form `postgresql+psycopg2://` funktionieren beide.

## Migrationsfehler {#migration-failures}

Wenn `alembic upgrade head` mittendrin fehlschlägt:

- Führen Sie es erneut aus — die meisten Migrationen sind idempotent geschrieben.
- Wenn eine Migration speziell auf einer frischen SQLite-Datenbank mit einem PostgreSQL-spezifischen SQL-Fehler fehlschlägt, verwenden Sie wahrscheinlich eine veraltete Version — aktuelle Releases haben Migrationen behoben, die nicht portables, dialektspezifisches SQL verwendeten. Stellen Sie sicher, dass Sie keinen älteren Commit ausführen.
- Bearbeiten Sie niemals das Datenbankschema manuell, um einen Migrationsfehler zu umgehen — öffnen Sie stattdessen ein Issue mit der genauen Fehlermeldung, da manuelle Schemaänderungen zukünftige Migrationen unvorhersehbar machen.

## JWT-Schlüsselfehler {#jwt-key-errors}

Wenn die Anwendung beim Start mit einer Beschwerde über fehlende oder ungültige JWT-Schlüssel nicht startet, bestätigen Sie, dass `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` auf ein gültiges ES256-Schlüsselpaar zeigen, erzeugt mit:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Mit einer anderen Kurve oder einem anderen Algorithmus erzeugte Schlüssel funktionieren nicht — PromptVault erwartet ausdrücklich ES256 (P-256/prime256v1).

## Nach fehlgeschlagenen Anmeldungen ausgesperrt {#locked-out-after-failed-logins}

Wiederholte fehlgeschlagene Anmeldeversuche sperren Ihr Konto vorübergehend. Standardmäßig geschieht dies nach fünf Versuchen (`MAX_LOGIN_ATTEMPTS`) für 15 Minuten (`ACCOUNT_LOCKOUT_DURATION_SECONDS`). Warten Sie, bis die Sperre endet. Wenn Sie der einzige Administrator sind, warten Sie, statt weitere Passwörter zu versuchen: Weitere Versuche verkürzen den Zeitraum nicht.

## Ratenlimit-Fehler (429) {#rate-limit-errors-429}

Wenn Massenoperationen, Importe/Exporte oder Backup-Aktionen `429 Too Many Requests` zurückgeben, haben Sie eines der pro Benutzer geltenden Ratenlimit-Kontingente aus [Konfiguration](../configuration/index.md#rate-limiting) erreicht. Die Antwort enthält einen `Retry-After`-Header; warten Sie dieses Zeitfenster ab, oder bitten Sie einen Administrator, die betreffende `RATE_LIMIT_*`-Variable zu erhöhen, wenn der Standardwert für Ihren Arbeitsablauf tatsächlich zu niedrig ist.

## Import/Export stellt Freigaben nicht wieder her {#importexport-doesnt-restore-sharing}

Wenn Sie eine zuvor exportierte Datei importieren und geteilte Prompts wieder privat und ohne Berechtigungen erscheinen, ist dies erwartet — Export/Import überträgt absichtlich keinen Freigabezustand (siehe [Prompts teilen](../user-guide/sharing.md#exportimport-and-sharing)). Verwenden Sie stattdessen ein vollständiges Backup/eine Wiederherstellung, wenn Freigaben erhalten bleiben sollen.

Für ein geplantes Update folgen Sie der Anleitung [PromptVault aktualisieren](../installation/update.md).

## Immer noch festgefahren? {#still-stuck}

Prüfen Sie die vollständige `docs/TROUBLESHOOTING.md` im Repository, oder öffnen Sie ein Issue auf [GitHub](https://github.com/Medenor/PromptVault) mit der genauen Fehlermeldung und dem ausgeführten Befehl.

---
title: Fehlerbehebung
sidebar_position: 4
---

# Fehlerbehebung

Diese Seite behandelt die häufigsten Probleme bei Installation oder Betrieb von PromptVault. Für eine ausführliche Behandlung siehe `docs/TROUBLESHOOTING.md` des Projekts.

## Port bereits belegt

Wenn Port `8001` (Web), `5432` (PostgreSQL) oder `6379` (Redis) bereits von einem anderen Prozess belegt ist, schlägt `docker-compose up` beim Starten dieses Dienstes fehl. Beenden Sie den blockierenden Prozess, oder ändern Sie den zugeordneten Port in Ihrer `.env`/`docker-compose.yml`, bevor Sie es erneut versuchen.

## Docker-Daemon läuft nicht

`docker-compose`-Befehle schlagen mit einem Verbindungsfehler fehl, wenn Docker selbst nicht läuft. Starten Sie Docker Desktop (oder den `docker`-Dienst unter Linux) und versuchen Sie es erneut.

## Datenbankverbindung fehlgeschlagen

Wenn PromptVault beim Start keine Verbindung zu PostgreSQL herstellen kann:

- Bestätigen Sie, dass der Container/Dienst tatsächlich läuft (`docker-compose ps`).
- Prüfen Sie, ob `DATABASE_URL` in `.env` mit den Zugangsdaten und dem Host/Port übereinstimmt, auf dem PostgreSQL tatsächlich lauscht.
- Wenn Sie gerade `POSTGRES_PASSWORD` geändert haben: Bestehende Container mit einem bereits initialisierten Datenvolume übernehmen das neue Passwort nicht automatisch — Sie müssen das Volume für eine Neuinstallation eventuell neu anlegen oder stattdessen das Passwort innerhalb der bestehenden Datenbank ändern.

## Migrationsfehler

Wenn `alembic upgrade head` mittendrin fehlschlägt:

- Führen Sie es erneut aus — die meisten Migrationen sind idempotent geschrieben.
- Wenn eine Migration speziell auf einer frischen SQLite-Datenbank mit einem PostgreSQL-spezifischen SQL-Fehler fehlschlägt, verwenden Sie wahrscheinlich eine veraltete Version — aktuelle Releases haben Migrationen behoben, die nicht portables, dialektspezifisches SQL verwendeten. Stellen Sie sicher, dass Sie keinen älteren Commit ausführen.
- Bearbeiten Sie niemals das Datenbankschema manuell, um einen Migrationsfehler zu umgehen — öffnen Sie stattdessen ein Issue mit der genauen Fehlermeldung, da manuelle Schemaänderungen zukünftige Migrationen unvorhersehbar machen.

## JWT-Schlüsselfehler

Wenn die Anwendung beim Start mit einer Beschwerde über fehlende oder ungültige JWT-Schlüssel nicht startet, bestätigen Sie, dass `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` auf ein gültiges ES256-Schlüsselpaar zeigen, erzeugt mit:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Mit einer anderen Kurve oder einem anderen Algorithmus erzeugte Schlüssel funktionieren nicht — PromptVault erwartet ausdrücklich ES256 (P-256/prime256v1).

## Nach fehlgeschlagenen Anmeldungen ausgesperrt

Wiederholte fehlgeschlagene Anmeldeversuche lösen eine temporäre Kontosperrung aus (`MAX_LOGIN_ATTEMPTS`, Standard 5 Versuche, `ACCOUNT_LOCKOUT_DURATION_SECONDS`, Standard 15 Minuten). Warten Sie das Sperrfenster ab, oder lassen Sie es von einem Administrator zurücksetzen, statt es wiederholt erneut zu versuchen — wiederholte Versuche während einer Sperrung setzen den Timer nicht vorzeitig zurück.

## Ratenlimit-Fehler (429)

Wenn Massenoperationen, Importe/Exporte oder Backup-Aktionen `429 Too Many Requests` zurückgeben, haben Sie eines der pro Benutzer geltenden Ratenlimit-Kontingente aus [Konfiguration](../configuration/index.md#ratenbegrenzung) erreicht. Die Antwort enthält einen `Retry-After`-Header; warten Sie dieses Zeitfenster ab, oder bitten Sie einen Administrator, die betreffende `RATE_LIMIT_*`-Variable zu erhöhen, wenn der Standardwert für Ihren Arbeitsablauf tatsächlich zu niedrig ist.

## Import/Export stellt Freigaben nicht wieder her

Wenn Sie eine zuvor exportierte Datei importieren und geteilte Prompts wieder privat und ohne Berechtigungen erscheinen, ist dies erwartet — Export/Import überträgt absichtlich keinen Freigabezustand (siehe [Prompts teilen](../user-guide/sharing.md#exportimport-und-freigabe)). Verwenden Sie stattdessen ein vollständiges Backup/eine Wiederherstellung, wenn Freigaben erhalten bleiben sollen.

## Immer noch festgefahren?

Prüfen Sie die vollständige `docs/TROUBLESHOOTING.md` im Repository, oder öffnen Sie ein Issue auf [Codeberg](https://codeberg.org/medenor/promptvault) mit der genauen Fehlermeldung und dem ausgeführten Befehl.

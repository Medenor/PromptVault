---
title: PromptVault aktualisieren
description: Eine selbst gehostete PromptVault-Installation sicher aktualisieren.
---

# PromptVault aktualisieren

Mit diesen Schritten aktualisieren Sie die Docker-Compose-Installation aus der [Installationsanleitung](index.md). Die Datenbank behält ihre Daten, während Sie die Dienste `web` und `docs` neu erstellen.

Wenn Ihre Produktionseinstellungen in einer separaten Datei `.env.production` liegen (empfohlen, siehe [Produktionsumgebung einrichten](production-setup.md)), teilen Sie das Docker Compose vor dem Start einmal mit. Jeder `docker-compose`-Befehl im selben Terminalfenster verwendet sie dann:

```bash
export COMPOSE_ENV_FILES=.env.production
```

Führen Sie die Befehle dieser Seite in diesem Terminalfenster aus. Ohne diese Einstellung liest Docker Compose `.env`, und Ihre Entwicklungswerte ersetzen die Produktionswerte. Das setzt Docker Compose 2.24 oder neuer voraus; bei einer älteren Version siehe [Produktionsumgebung einrichten](production-setup.md#use-a-separate-environment-file).

## Vor dem Start {#before-you-start}

1. Lesen Sie die [Versionshinweise](../release-notes/index.md) und `CHANGELOG.md` auf inkompatible Änderungen und Hinweise zu Datenbankmigrationen.
2. Prüfen Sie, ob auf dem Server genug Speicherplatz für eine Datenbanksicherung und neue Images vorhanden ist.
3. Testen Sie das Update zuerst auf einer Testinstallation, falls verfügbar.
4. Planen Sie ein kurzes Wartungsfenster ein. Während des Neustarts können sich Nutzer möglicherweise nicht anmelden.
5. Stellen Sie sicher, dass Sie auf den PromptVault-Projektordner und den Datenbank-Container zugreifen können.

## 1. Datenbank sichern {#1-back-up-the-database}

Erstellen Sie eine komprimierte Datenbanksicherung und prüfen Sie, dass das Archiv unbeschädigt ist, bevor Sie das Update herunterladen oder starten. Führen Sie diese Befehle im PromptVault-Projektordner aus:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

Der letzte Befehl muss ohne Fehler enden. Prüfen Sie, dass die Sicherungsdatei nicht leer ist. Lassen Sie sie für eine mögliche Wiederherstellung in `data/backups` und kopieren Sie eine zweite Datei an einen sicheren Ort außerhalb des Servers. Fahren Sie nicht fort, wenn die Sicherung fehlgeschlagen ist. Die Prüfung mit `gzip -t` zeigt, dass die Datei nicht beschädigt ist. Sie testet keine Wiederherstellung.

Versehen Sie als Nächstes das Image, das Ihr Produktionscontainer gerade ausführt, mit einem Tag, damit Sie ohne Neuaufbau dorthin zurückkehren können. Das *Image* ist die verpackte Kopie von PromptVault, die der Container ausführt. Verwenden Sie die Image-ID des Containers statt `:latest`: Der Tag `:latest` auf Ihrem Rechner kann bereits auf einen neueren Build zeigen.

```bash
docker tag "$(docker inspect promptvault-web --format '{{.Image}}')" promptvault-web:pre-update
docker run --rm --entrypoint python promptvault-web:pre-update -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

Der zweite Befehl muss die Version ausgeben, die Sie gerade betreiben. Gibt er eine andere Version aus, fahren Sie nicht fort: Prüfen Sie den Containernamen mit `docker-compose ps` und führen Sie den ersten Befehl erneut aus.

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
# Letzte Protokollzeilen: auf Fehler achten
docker-compose logs web | head -50
# Gesundheitsprüfung: muss erfolgreich sein
curl --fail http://localhost:8001/api/health
# Anzahl der Prompts: muss Ihrer Erwartung entsprechen
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
# Laufende Version: muss die neue Version sein
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
# Verwendete Einstellungen: Produktion braucht ENVIRONMENT=production und DISABLE_RATE_LIMITING=false
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

Die Antwort der Gesundheitsprüfung enthält keine Version. Bestätigen Sie das Update daher mit dem Versionsbefehl. Öffnen Sie PromptVault im Browser, melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Wenn Sie den Dokumentationsdienst nutzen, öffnen Sie ihn ebenfalls (Standardadresse: `http://localhost:7876`).

## Bei Problemen {#if-something-goes-wrong}

Prüfen Sie die Dienstprotokolle auf Fehlermeldungen:

```bash
docker-compose logs --tail=100 web docs
```

Wenn der `web`-Container unter PostgreSQL in einer Schleife mit `No module named 'psycopg'` neu startet, lesen Sie die [Fehlerbehebung](../troubleshooting/index.md#psycopg-missing). Bei anderen Fehlern lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

### Zur vorherigen Version zurückkehren {#return-to-the-previous-version}

Kehren Sie zu dem Image zurück, das Sie in Schritt 1 mit einem Tag versehen haben (`promptvault-web:pre-update`). Führen Sie diese Schritte der Reihe nach aus.

**1. Starten Sie das vorherige Image.**

```bash
docker tag promptvault-web:pre-update promptvault-web:latest
docker-compose up -d --no-build web
docker-compose logs web --tail=20
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

Der letzte Befehl muss die vorherige Version ausgeben. Prüfen Sie den Gesundheitsendpunkt (`curl --fail http://localhost:8001/api/health`), melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Wenn alles funktioniert und das Update keine Datenbankmigrationen ausgeführt hat, sind Sie fertig. Die Zeile „Aktualisierung“ in den [Versionshinweisen](../release-notes/index.md) der installierten Version nennt, ob sie Migrationen ausgeführt hat; viele Versionen haben keine. Falls ja, fahren Sie mit Schritt 2 fort.

**2. Stoppen Sie die Anwendung.** Tun Sie das nur, wenn Sie die Datenbank wiederherstellen.

```bash
docker-compose stop web
```

**3. Sichern Sie die aktuelle Datenbank (optional).**

Wenn Sie nach dem Update Prompts erstellt oder geändert haben, sichern Sie die aktuelle Datenbank vor der Wiederherstellung:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

**4. Stellen Sie die Sicherung wieder her.** Die Wiederherstellung ersetzt die aktuelle Datenbank: Prompts und andere Änderungen seit der Sicherung gehen verloren, wenn Sie sie nicht in Schritt 3 gesichert haben.

Stellen Sie die geprüfte Sicherung von vor dem Update wieder her. Ersetzen Sie `<SICHERUNGSDATEI>` durch den Dateinamen aus Schritt 1, ohne den Ordnerpfad `data/backups/`. Diese Befehle löschen und erstellen die Datenbank neu, bevor die Sicherung geladen wird:

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<SICHERUNGSDATEI>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

**5. Starten Sie das vorherige Image erneut und prüfen Sie es.**

```bash
docker-compose up -d --no-build web
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Melden Sie sich an und prüfen Sie, ob Ihre Prompts vorhanden sind. Wenn die Wiederherstellung oder der Start fehlschlägt, halten Sie an und lesen Sie die [Fehlerbehebung](../troubleshooting/index.md).

**Wenn Sie in Schritt 1 kein Image mit einem Tag versehen haben,** checken Sie das Git-Tag der vorherigen Version aus (`git fetch --tags`, dann `git checkout <VORHERIGES_RELEASE_TAG>`) und führen Sie `docker-compose build` ohne `--no-cache` aus. Docker kann zwischengespeicherte Abhängigkeits-Layer wiederverwenden, garantiert das aber nicht. Prüfen Sie daher Version und Start der Anwendung, bevor Sie sich darauf verlassen.

Kehren Sie nicht zurück, indem Sie die alte Version auschecken und mit `--no-cache` neu bauen. Der Build installiert seine Abhängigkeiten erneut, das Ergebnis kann sich also vom bisherigen Image unterscheiden, und manche Versionen lassen sich gar nicht mehr bauen: Ein Image aus dem Quellcode von Version 1.16.0 stürzt zum Beispiel mit PostgreSQL ab.

---
title: Produktionsumgebung einrichten
description: Produktionseinstellungen von der Entwicklung trennen und das Standard-Datenbankpasswort ersetzen.
---

# Produktionsumgebung einrichten

Führen Sie diese Schritte auf dem Server aus, auf dem PromptVault mit Docker Compose läuft. Docker Compose liest die Datei `.env` neben `docker-compose.yml`, dieselbe Datei, die Sie für die Entwicklung verwenden. Eine Entwicklungseinstellung wie `ENVIRONMENT=development` oder `DISABLE_RATE_LIMITING=true` kann daher Ihre Produktionscontainer erreichen. Mit diesen Schritten liegen die Produktionseinstellungen in einer eigenen Datei.

## Eine separate Umgebungsdatei verwenden {#use-a-separate-environment-file}

Führen Sie diese Befehle im PromptVault-Projektordner aus. Stellen Sie sicher, dass Git die neue Datei ignoriert, bevor sie Geheimnisse enthält:

```bash
echo '.env.production' >> .gitignore
cp .env .env.production

sed -i.bak \
  -e 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' \
  -e 's/^LOG_LEVEL=.*/LOG_LEVEL=WARNING/' \
  -e 's/^DISABLE_RATE_LIMITING=.*/DISABLE_RATE_LIMITING=false/' \
  .env.production && rm .env.production.bak
grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)=' .env.production
```

Der letzte Befehl muss `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` und `DISABLE_RATE_LIMITING=false` anzeigen. Fehlt eine Variable in der Ausgabe, ergänzen Sie sie in `.env.production`.

Sagen Sie Docker Compose, dass es die neue Datei verwenden soll. Tun Sie das einmal in jedem Terminalfenster, das Sie für die Produktion nutzen; jeder `docker-compose`-Befehl in diesem Fenster verwendet sie dann:

```bash
export COMPOSE_ENV_FILES=.env.production
docker-compose up -d
```

`COMPOSE_ENV_FILES` setzt Docker Compose 2.24 oder neuer voraus (prüfen Sie mit `docker-compose version`). Bei einer älteren Version fügen Sie stattdessen `--env-file .env.production` zu jedem `docker-compose`-Befehl hinzu.

Docker Compose gibt nur diese Variablen aus der Datei an die Container weiter:

- `ENVIRONMENT`, `LOG_LEVEL`, `DISABLE_RATE_LIMITING` und `POSTGRES_PASSWORD`
- `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` und `JWT_REFRESH_TOKEN_EXPIRE_SECONDS`
- `DOCS_APP_URL` und `VITE_DOCS_PORTAL_URL`

Die übrigen Werte in `.env` (etwa `DATABASE_URL`) gelten nur, wenn Sie PromptVault direkt auf einem Computer ausführen, nicht mit Docker Compose. Die Seite [Konfiguration](../configuration/index.md) beschreibt jede Variable.

`ENVIRONMENT=production` kann strengeres Verhalten erzwingen als die Entwicklung. Lesen Sie nach dem Wechsel `docker-compose logs --tail 30 web` und beheben Sie, was dort gemeldet wird.

## Verwendete Einstellungen prüfen {#check-the-settings-in-use}

Zeigen Sie die Einstellungen an, die der laufende Container verwendet:

```bash
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

Die Ausgabe muss `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` und `DISABLE_RATE_LIMITING=false` zeigen. Zeigt sie Entwicklungswerte, wurde der Container ohne die Produktionsdatei gestartet: Setzen Sie `COMPOSE_ENV_FILES` wie oben und führen Sie `docker-compose up -d` erneut aus.

`docker-compose config` gibt `POSTGRES_PASSWORD` im Klartext aus, fügen Sie die Ausgabe daher nirgends ein.

## Das Standard-Datenbankpasswort ersetzen {#replace-the-default-database-password}

Ist `POSTGRES_PASSWORD` nicht gesetzt, verwendet Docker Compose stillschweigend `changeme`. Nur Container im selben Docker-Netzwerk erreichen die Datenbank, ersetzen Sie den Standardwert trotzdem.

PostgreSQL liest `POSTGRES_PASSWORD` nur, wenn es das Datenvolume zum ersten Mal anlegt. Die Variable allein zu ändern ändert das Passwort einer bestehenden Datenbank daher **nicht**. Ändern Sie es zuerst in der Datenbank und dann in Compose:

```bash
# 1. Erzeugen Sie ein Passwort ohne Sonderzeichen (es wird Teil einer Verbindungs-URL)
NEWPW=$(openssl rand -hex 24)

# 2. Ändern Sie es in der Datenbank
docker exec promptvault-db psql -U promptvault -d promptvault -c "ALTER USER promptvault PASSWORD '$NEWPW'"

# 3. Speichern Sie es für Compose und erstellen Sie die Container sofort neu
echo "POSTGRES_PASSWORD=$NEWPW" >> .env.production
docker-compose up -d
```

Tun Sie das zu einem ruhigen Zeitpunkt: Zwischen Schritt 2 und 3 hält der Web-Container noch das alte Passwort, neue Verbindungen schlagen daher einige Sekunden lang fehl. Erstellen Sie danach eine neue Sicherung.

Prüfen Sie das Ergebnis vom Web-Container aus, nicht aus dem Datenbankcontainer. Das Datenbank-Image vertraut Verbindungen aus dem eigenen Container, ein Test dort akzeptiert daher jedes Passwort. Führen Sie beide Befehle aus:

```bash
# Das alte Passwort muss abgelehnt werden
docker exec promptvault-web python -c "import psycopg; psycopg.connect(host='db', user='promptvault', password='changeme', dbname='promptvault', connect_timeout=5)" >/dev/null 2>&1 && echo "old password: ACCEPTED" || echo "old password: rejected"

# Das aktuelle Passwort muss funktionieren
docker exec promptvault-web python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)" >/dev/null 2>&1 && echo "current password: works" || echo "current password: FAILED"
```

Erwartete Ausgabe: `old password: rejected`, dann `current password: works`. War das ersetzte Passwort nicht `changeme`, tragen Sie es stattdessen im ersten Befehl ein.

Bewahren Sie `.env.production` an einem sicheren Ort auf, etwa in einem Passwortmanager: Die Datei enthält die einzige Kopie des Passworts außerhalb der Datenbank.

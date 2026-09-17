---
title: Installation
sidebar_position: 1
---

# Installation

PromptVault ist eine selbst gehostete Anwendung. Diese Seite behandelt die beiden unterstützten Wege, sie zum Laufen zu bringen: den automatisierten Einrichtungsassistenten und eine manuelle Docker-Compose-Bereitstellung.

## Voraussetzungen

- Python 3.14+
- PostgreSQL 15+ (für die Produktion empfohlen) oder SQLite (für Entwicklung/Einzelbenutzerbetrieb ausreichend)
- Docker und Docker Compose (empfohlener Bereitstellungsweg)
- Git

## Schnellstart mit dem Einrichtungsassistenten

Der schnellste Weg zu einer funktionierenden Instanz ist der mitgelieferte Einrichtungsassistent, der JWT-Schlüsselerzeugung, Umgebungskonfiguration, Datenbankeinrichtung und Admin-Benutzererstellung interaktiv übernimmt.

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
python scripts/setup/setup.py
```

Folgen Sie den Anweisungen. Am Ende ist PromptVault bereitgestellt und einsatzbereit.

## Manuelle Einrichtung mit Docker Compose

Wenn Sie jeden Schritt lieber selbst konfigurieren möchten:

```bash
# Repository klonen
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault

# Umgebung konfigurieren
cp .env.example .env
# Bearbeiten Sie .env und setzen Sie POSTGRES_PASSWORD (und weitere Werte nach Bedarf)

# JWT-Signaturschlüssel für die Authentifizierung erzeugen
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem

# .env auf die erzeugten Schlüssel verweisen lassen
echo "JWT_PRIVATE_KEY_PATH=$(pwd)/es256-private.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=$(pwd)/es256-public.pem" >> .env

# Dienste starten (PostgreSQL + PromptVault)
docker-compose up -d

# Datenbankmigrationen ausführen
docker-compose exec web alembic upgrade head

# Standard-Admin-Benutzer anlegen
docker-compose exec web python scripts/create_admin_user.py

# (Optional) Vorhandene JSON-Daten migrieren
docker-compose exec web python scripts/migrate_json_to_db.py
```

Sobald die Container laufen, öffnen Sie `http://localhost:8001` und melden Sie sich mit den soeben erstellten Admin-Zugangsdaten an.

## Aus dem Quellcode bauen

Wenn Sie lokal entwickeln statt über Docker bereitzustellen, kapselt das `Makefile` des Repositories den gesamten Build-/Test-/Lint-Ablauf:

```bash
make install   # Backend- (.venv) und Frontend-Abhängigkeiten (npm)
make dev       # Backend auf Port :8003, Frontend-Entwicklungsserver auf :5173
make build     # Produktions-Frontend-Assets + Docker-Image
```

Die vollständige Zielreferenz, Umgebungsvariablen und häufige Fehlerursachen finden Sie in `docs/DEVELOPMENT.md` des Projekts, falls ein Schritt nicht wie erwartet funktioniert.

## Admin-Benutzer anlegen

Jede neue Installation benötigt mindestens ein Admin-Konto:

```bash
# Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# Lokal
python scripts/create_admin_user.py
```

Das Skript fragt nach Benutzername, E-Mail-Adresse und Passwort, prüft das Passwort gegen die konfigurierte Richtlinie und legt einen Benutzer mit vollständigen Admin-Rechten an. Bewahren Sie diese Zugangsdaten sicher auf.

## Nächste Schritte

- Lesen Sie die [Konfigurationsreferenz](../configuration/index.md) für Umgebungsvariablen, die Sie wahrscheinlich anpassen möchten (Ratenbegrenzungen, Sitzungs-Timeouts, Backup-Speicher).
- Falls etwas nicht wie erwartet funktioniert, prüfen Sie die [Fehlerbehebung](../troubleshooting/index.md).

---
title: Konfiguration
sidebar_position: 2
---

# Konfigurationsreferenz

PromptVault wird vollständig über Umgebungsvariablen konfiguriert, typischerweise in einer `.env`-Datei im Repository-Root gesetzt (kopieren Sie `.env.example` als Ausgangspunkt). Diese Seite behandelt die Einstellungen, die Sie am wahrscheinlichsten benötigen.

## Datenbank

| Variable | Standard | Zweck |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data-dev/promptvault.db` | Verbindungszeichenfolge. Verwenden Sie in der Produktion eine `postgresql://`-URL. |
| `DB_POOL_SIZE` | `20` | Größe des Verbindungspools (bei SQLite ignoriert). |
| `DB_POOL_TIMEOUT` | `30` | Timeout für die Pool-Auscheckung, in Sekunden. |
| `DB_POOL_RECYCLE` | `3600` | Sekunden, bevor eine gepoolte Verbindung erneuert wird. |
| `DB_ECHO` | `false` | Protokolliert jede SQL-Anweisung — nützlich zum Debuggen, störend in der Produktion. |

## Anwendung

| Variable | Standard | Zweck |
|---|---|---|
| `ENVIRONMENT` | `development` | Einer von `development`, `testing`, `production`. |
| `PROMPTVAULT_DATA_DIR` | `./data-dev` | Verzeichnis für Datendateien, Backups und Protokolle. **Verwenden Sie pro Umgebung (Dev/Staging/Prod) einen eigenen Pfad**, selbst wenn sie sich ein Dateisystem teilen — ein gemeinsames Datenverzeichnis über Umgebungen hinweg kann dazu führen, dass geplante Backups und Wiederherstellungen kollidieren. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` oder `CRITICAL`. |
| `AUDIT_LOG_LEVEL` | `INFO` | Protokollstufe speziell für Versionskontroll- und Backup-Audit-Ereignisse. |

## Authentifizierung

| Variable | Standard | Zweck |
|---|---|---|
| `AUTH_ENABLED` | `true` | Nur bei einer vertrauenswürdigen, netzwerklosen Einzelbenutzer-Bereitstellung auf `false` setzen — dies deaktiviert den Login und macht jeden Endpunkt öffentlich zugänglich. |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | — | Pfade zum ES256-Schlüsselpaar zum Signieren/Verifizieren von JWTs. Erzeugen Sie es mit `openssl ecparam`/`openssl ec`, wie unter [Installation](../installation/index.md) gezeigt. |
| `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `900` (15 Min.) | Lebensdauer des Zugriffstokens. |
| `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `604800` (7 Tage) | Lebensdauer des Refresh-Tokens. |
| `MAX_LOGIN_ATTEMPTS` | `5` | Fehlgeschlagene Versuche vor Kontosperrung. |
| `ACCOUNT_LOCKOUT_DURATION_SECONDS` | `900` | Dauer der Sperrung. |
| `MAX_SESSIONS_PER_USER` | `5` | Obergrenze gleichzeitiger Sitzungen (`0` = unbegrenzt). |
| `SESSION_INACTIVE_TIMEOUT_SECONDS` | `2592000` (30 Tage) | Ablauf bei Inaktivität. |

Die Passwortrichtlinie (`PASSWORD_MIN_LENGTH`, `PASSWORD_REQUIRE_UPPERCASE`, `PASSWORD_REQUIRE_LOWERCASE`, `PASSWORD_REQUIRE_DIGIT`, `PASSWORD_REQUIRE_SPECIAL`) ist ebenfalls konfigurierbar — die Standardwerte erzwingen mindestens 12 Zeichen mit allen vier Zeichenklassen.

## Ratenbegrenzung

Ratenlimits gelten pro Benutzer (bei anonymen Anfragen als Fallback pro IP-Adresse) und sind in unabhängig konfigurierbare Kategorien gruppiert:

| Kategorie | Standard | Umgebungsvariablen-Präfix |
|---|---|---|
| Lesen (GET-Anfragen) | 300/Min | `RATE_LIMIT_READ_*` |
| Schreiben (Erstellen/Aktualisieren/Löschen/Zurücksetzen) | 60/Min | `RATE_LIMIT_WRITE_*` |
| Aufwendig (Import/Export, Backup erstellen/wiederherstellen/prüfen) | 10/Min | `RATE_LIMIT_EXPENSIVE_*` |
| Massenoperationen (Massenlöschung, alle Backups löschen, komprimieren) | 5/Min | `RATE_LIMIT_BULK_*` |

Jede Kategorie besitzt `_ATTEMPTS`- und `_WINDOW_SECONDS`-Variablen, z. B. `RATE_LIMIT_WRITE_ATTEMPTS=60` / `RATE_LIMIT_WRITE_WINDOW_SECONDS=60`. Auth-spezifische Endpunkte (Login, Registrierung, Passwort-Reset) haben eigene, separate Limits (`RATE_LIMIT_LOGIN_*`, `RATE_LIMIT_REGISTER_*`, `RATE_LIMIT_PASSWORD_RESET_*`). Ratenbegrenzung erfordert eine erreichbare `REDIS_URL`.

## E-Mail (Passwort-Reset)

| Variable | Zweck |
|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS` | SMTP-Serververbindung. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP-Zugangsdaten. |
| `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` | Absenderidentität ausgehender E-Mails. |
| `PASSWORD_RESET_TOKEN_EXPIRE_SECONDS` | Standardmäßig `3600` — wie lange ein Reset-Link gültig bleibt. |
| `APP_BASE_URL` | Basis-URL zum Erstellen des per E-Mail versendeten Reset-Links. |

## Backups

| Variable | Zweck |
|---|---|
| `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` | Nur erforderlich, wenn Sie Cloud-Backup-Speicher konfigurieren — verschlüsselt gespeicherte Anbieter-Zugangsdaten (Access-/Secret-Keys) im Ruhezustand. Erzeugen mit `python -c "import secrets; print(secrets.token_hex(32))"` und niemals committen. |

Siehe [Backups](../user-guide/backups.md), wie Zeitpläne, Verschlüsselung und Cloud-Speicher zusammenwirken.

## Frontend-Assets

| Variable | Standard | Zweck |
|---|---|---|
| `USE_VITE_ASSETS` | `false` | Auf `true` setzen, um CSS/JS aus dem kompilierten Vite-Build statt aus dem Quellcode auszuliefern. |

## Beispiel: PostgreSQL-Produktion

```bash
DATABASE_URL=postgresql://promptvault_user:secure_password@localhost:5432/promptvault_prod
DB_POOL_SIZE=30
DB_POOL_TIMEOUT=60
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

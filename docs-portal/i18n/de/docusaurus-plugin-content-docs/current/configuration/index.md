---
title: Konfiguration
sidebar_position: 2
---

# Konfigurationsreferenz

PromptVault wird über Umgebungsvariablen konfiguriert, die normalerweise in der `.env`-Datei im Repository-Root stehen. Beginnen Sie mit einer Kopie von `.env.example`. Dies ist eine Administratorreferenz: Ändern Sie einen Wert nur, wenn Sie das gewünschte Ergebnis kennen. Starten Sie anschließend den betroffenen Dienst neu und prüfen Sie, dass er erfolgreich startet.

Begriffe: Eine URL ist die Adresse für die Verbindung zu einem Dienst; SQL ist die Abfragesprache der Datenbank; Redis ist der Dienst für Ratenbegrenzungen; SMTP ist das Protokoll zum Versenden von E-Mails.

## Datenbank {#database}

| Variable | Standard | Zweck |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data-dev/promptvault.db` | Verbindungszeichenfolge. Verwenden Sie in der Produktion eine `postgresql://`-URL. |
| `DB_POOL_SIZE` | `20` | Größe des Verbindungspools (bei SQLite ignoriert). |
| `DB_POOL_TIMEOUT` | `30` | Timeout für die Pool-Auscheckung, in Sekunden. |
| `DB_POOL_RECYCLE` | `3600` | Sekunden, bevor eine gepoolte Verbindung erneuert wird. |
| `DB_ECHO` | `false` | Protokolliert jede SQL-Anweisung — nützlich zum Debuggen, störend in der Produktion. |

## Anwendung {#application}

| Variable | Standard | Zweck |
|---|---|---|
| `ENVIRONMENT` | `development` | Einer von `development`, `testing`, `production`. |
| `PROMPTVAULT_DATA_DIR` | `./data-dev` | Verzeichnis für Datendateien, Backups und Protokolle. **Verwenden Sie pro Umgebung (Dev/Staging/Prod) einen eigenen Pfad**, selbst wenn sie sich ein Dateisystem teilen — ein gemeinsames Datenverzeichnis über Umgebungen hinweg kann dazu führen, dass geplante Backups und Wiederherstellungen kollidieren. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` oder `CRITICAL`. |
| `AUDIT_LOG_LEVEL` | `INFO` | Protokollstufe speziell für Versionskontroll- und Backup-Audit-Ereignisse. |

## Authentifizierung {#authentication}

| Variable | Standard | Zweck |
|---|---|---|
| `AUTH_ENABLED` | `true` | Nur bei einer vertrauenswürdigen, netzwerklosen Einzelbenutzer-Bereitstellung auf `false` setzen — dies deaktiviert den Login und macht jeden Endpunkt öffentlich zugänglich. |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | — | Pfade zum ES256-Schlüsselpaar zum Signieren und Verifizieren von JSON Web Tokens (JWTs). Erzeugen Sie es mit den Befehlen unter [Installation](../installation/index.md). |
| `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `900` (15 Min.) | Lebensdauer des Zugriffstokens. |
| `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `604800` (7 Tage) | Lebensdauer des Refresh-Tokens. |
| `TOTP_ENCRYPTION_KEY` | — | Serverseitiges Geheimnis, das TOTP-Geheimnisse der Zwei-Faktor-Authentifizierung im Ruhezustand verschlüsselt. Erforderlich, sobald ein Nutzer 2FA aktiviert. Erzeugen Sie ihn mit `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Ändern Sie ihn nie ohne Migrationsplan: Eine Änderung macht bestehende 2FA-Einrichtungen ungültig. |
| `MAX_LOGIN_ATTEMPTS` | `5` | Fehlgeschlagene Versuche vor Kontosperrung. |
| `ACCOUNT_LOCKOUT_DURATION_SECONDS` | `900` | Dauer der Sperrung. |
| `MAX_SESSIONS_PER_USER` | `5` | Obergrenze gleichzeitiger Sitzungen (`0` = unbegrenzt). |
| `SESSION_INACTIVE_TIMEOUT_SECONDS` | `2592000` (30 Tage) | Ablauf bei Inaktivität. |

Die Passwortrichtlinienvariablen `PASSWORD_MIN_LENGTH`, `PASSWORD_REQUIRE_UPPERCASE`, `PASSWORD_REQUIRE_LOWERCASE`, `PASSWORD_REQUIRE_DIGIT` und `PASSWORD_REQUIRE_SPECIAL` sind ebenfalls konfigurierbar. Standardmäßig verlangen sie mindestens 12 Zeichen und alle vier Zeichenklassen.

## Ratenbegrenzung {#rate-limiting}

Ratenlimits gelten pro Benutzer (bei anonymen Anfragen als Fallback pro IP-Adresse) und sind in unabhängig konfigurierbare Kategorien gruppiert:

| Kategorie | Standard | Umgebungsvariablen-Präfix |
|---|---|---|
| Lesen (GET-Anfragen) | 300/Min | `RATE_LIMIT_READ_*` |
| Schreiben (Erstellen/Aktualisieren/Löschen/Zurücksetzen) | 60/Min | `RATE_LIMIT_WRITE_*` |
| Aufwendig (Import/Export, Backup erstellen/wiederherstellen/prüfen) | 10/Min | `RATE_LIMIT_EXPENSIVE_*` |
| Massenoperationen (Massenlöschung, alle Backups löschen, komprimieren) | 5/Min | `RATE_LIMIT_BULK_*` |

Jede Kategorie besitzt `_ATTEMPTS`- und `_WINDOW_SECONDS`-Variablen, zum Beispiel `RATE_LIMIT_WRITE_ATTEMPTS=60` und `RATE_LIMIT_WRITE_WINDOW_SECONDS=60`. Authentifizierungsendpunkte haben separate Limits: `RATE_LIMIT_LOGIN_*`, `RATE_LIMIT_REGISTER_*` und `RATE_LIMIT_PASSWORD_RESET_*`. Ratenbegrenzung funktioniert nur, wenn der Redis-Dienst unter `REDIS_URL` erreichbar ist. Wenn Sie Redis nicht betreiben, dürfen Sie nicht davon ausgehen, dass diese Limits aktiv sind.

## E-Mail (Passwort-Reset) {#email-password-reset}

| Variable | Zweck |
|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS` | SMTP-Serververbindung. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP-Zugangsdaten. |
| `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` | Absenderidentität ausgehender E-Mails. |
| `PASSWORD_RESET_TOKEN_EXPIRE_SECONDS` | Standardmäßig `3600` — wie lange ein Reset-Link gültig bleibt. |
| `APP_BASE_URL` | Basis-URL zum Erstellen des per E-Mail versendeten Reset-Links. |

## Backups {#backups}

| Variable | Zweck |
|---|---|
| `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` | Nur erforderlich, wenn Sie Cloud-Backup-Speicher konfigurieren — verschlüsselt gespeicherte Anbieter-Zugangsdaten (Access-/Secret-Keys) im Ruhezustand. Erzeugen mit `python -c "import secrets; print(secrets.token_hex(32))"` und niemals committen. |

Siehe [Backups](../user-guide/backups.md), wie Zeitpläne, Verschlüsselung und Cloud-Speicher zusammenwirken.

## Frontend-Assets {#frontend-assets}

| Variable | Standard | Zweck |
|---|---|---|
| `USE_VITE_ASSETS` | `false` | Auf `true` setzen, um CSS/JS aus dem kompilierten Vite-Build statt aus dem Quellcode auszuliefern. |

## Beispiel: PostgreSQL-Produktion {#example-postgresql-production}

```bash
DATABASE_URL=postgresql://promptvault_user:secure_password@localhost:5432/promptvault_prod
DB_POOL_SIZE=30
DB_POOL_TIMEOUT=60
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

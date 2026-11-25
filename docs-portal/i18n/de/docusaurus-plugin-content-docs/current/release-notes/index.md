---
title: Release Notes
sidebar_position: 1
---

# Release Notes

Highlights der letzten PromptVault-Releases. Die vollständige, ungekürzte Historie finden Sie in `docs/CHANGELOG.md` im Repository.

Die Schritte zum Aktualisieren finden Sie unter [PromptVault aktualisieren](../installation/update.md).

## 1.17.1

- **API-Korrektur**. Bei aktivierter Ratenbegrenzung liefern das Erstellen und Löschen von Prompts sowie das Importieren und Ersetzen von Skill-Archiven jetzt den erwarteten HTTP-Status und die Header zur Ratenbegrenzung.
- **Bereitstellung**. Der Produktionsleitfaden erklärt jetzt, wie Sie eine separate `.env.production` verwenden, das Standardpasswort der Datenbank ändern und zum vorherigen Image zurückkehren.

## 1.17.0

- **Korrektur**: PostgreSQL-Installationen mit 1.16.0 starteten nicht mehr (`No module named 'psycopg'`). PromptVault liefert jetzt den Treiber psycopg v3 mit. Ihre `DATABASE_URL` muss nicht geändert werden: `postgresql://` und `postgresql+psycopg2://` funktionieren beide. SQLite ist nicht betroffen.
- **Sicherheitskorrektur**: PyJWT wurde auf 2.15.1 aktualisiert. Ein Token mit stark verschachteltem JSON führte bei den Endpunkten für Aktualisierung, Abmeldung und 2FA zu einem Serverfehler statt zu einem 401. Im Anfragetext gesendete Tokens sind jetzt auf 4096 Zeichen begrenzt. PromptVault akzeptiert nur ES256-Tokens, daher betreffen die übrigen PyJWT-Sicherheitshinweise Sie nicht.
- **Härtung**: Das Zurücksetzen des Passworts gibt das Klartext-Token nicht mehr an den Aufrufer zurück und protokolliert eine maskierte statt der echten E-Mail-Adresse.
- **Oberfläche**: Auf jeder Prompt-Karte ist Kopieren jetzt die blaue Hauptaktion und Bearbeiten die zweite. Verlauf, Kopieren + Version, Teilen und Löschen stehen im Menü „Weitere Aktionen“. Die Kopfzeile ist auf allen Seiten neutral. Der Dunkelmodus ist für Badges, Banner, Schaltflächen, Fußzeilenlinks und den Favoritenstern korrigiert. Schlägt das erste Laden der Prompt-Liste fehl, erscheint jetzt eine Fehlermeldung mit der Schaltfläche „Erneut versuchen“.
- **Aktualisierung**: Images neu bauen und neu starten. Eine Datenbankmigration ist nicht nötig.

## 1.16.0

- **Sicherheitskorrektur**: Die Anfrage zum Zurücksetzen des Passworts antwortet jetzt gleich, ob ein Konto existiert oder nicht, und der Link zum Zurücksetzen wird nicht mehr in die Anwendungsprotokolle geschrieben. Die Links laufen nach einer Stunde ab, Sie können aber ältere Protokollzeilen mit `reset-password?token=` löschen.
- **Fix**: `setup_env.py --from-file` akzeptiert jetzt YAML-Werte ohne Anführungszeichen (`true`, `20`) und behält den Standardwert für Schlüssel, die in der Datei fehlen. `DB_POOL_SIZE` wird als positive Zahl statt als Port geprüft.
- **Einrichtungsassistent**: Seine Abhängigkeiten (`click`, `rich`, `httpx`) liegen jetzt im Extra `setup`, und das Docker-Image installiert sie nicht mehr. Führen Sie vor `scripts/setup/setup.py` `pip install -e ".[setup]"` (oder `make install`) aus.
- **Build**: Zum Bauen des Frontends ist jetzt Node.js 26 oder neuer erforderlich.
- **Update**: Erstellen Sie die Images neu und starten Sie neu. Eine Datenbankmigration ist nicht nötig.

## 1.15.0

- **Anleitungen für API-Entwickler**: Ein neuer Bereich Entwickler / API erklärt, wie Sie die PromptVault-API aufrufen: erste Aufrufe (Anmeldung mit 2FA, Lesen, Erstellen, Suchen, Verlauf) und eine Referenz zu Routen, Berechtigungen, Paginierung und Fehlern. Siehe [Entwickler / API](../developer-api/index.md).
- **Update-Anleitung**: Das Portal enthält jetzt eine Anleitung zum Sichern, Aktualisieren, Prüfen und Wiederherstellen einer Docker-Compose-Installation. Siehe [PromptVault aktualisieren](../installation/update.md).
- **Zurück zu PromptVault**: Jede Seite hat einen Link zurück zur Anwendung. Legen Sie beim Erstellen des Doku-Images `DOCS_APP_URL` fest, damit der Link auf Ihre Instanz verweist.
- **Jetzt auf GitHub**: Quellcode, Tickets und Releases sind von Codeberg nach https://github.com/Medenor/PromptVault umgezogen, und der Link im Seitenfuß folgt.

## 1.14.1

- **Fix**: Die Dialoge zum Importieren und Bearbeiten von Skills folgen jetzt dem Dunkelmodus, statt auf weißem Hintergrund zu erscheinen.

## 1.14.0

- **Skills**: PromptVault speichert jetzt Skills (eine `SKILL.md` mit Skripten, Referenzen und weiteren Dateien) neben Ihren Prompts. Importieren Sie einen Skill aus einer `.zip`-Datei über **Neu ▾ → Skill importieren**, durchsuchen Sie die gerenderten Anweisungen und den Dateibaum, bearbeiten Sie die Details, ersetzen Sie die Dateien, laden Sie ihn als `.zip` herunter oder löschen Sie ihn. Skills sind durchsuchbar, nach Typ filterbar und in Datenbank-Backups enthalten. Versionsverlauf, Freigabe, Platzhalter und Massenimport/-export gelten für Skills noch nicht. Siehe die neue Seite „Skills“ im Benutzerhandbuch.
- **Menüs in der Kopfzeile**: „Neuer Prompt“ und „Skill importieren“ teilen sich jetzt das Menü **Neu ▾**, und sekundäre Links wandern bei mittleren Bildschirmbreiten in das Menü **Mehr ▾**, damit die Navigation in eine Zeile passt.
- **Sicherheitskorrektur**: Die Sammelaktualisierung von Tags prüft jetzt, ob Sie Eigentümer (oder Administrator) jedes ausgewählten Elements sind.
- **Update**: Wenden Sie die Datenbankmigration an und erstellen Sie die Images neu. Einmalig kann ein Neuladen der Seite nötig sein, um neue Übersetzungen zu erhalten.

## 1.13.1

- **Korrektur**: Das Neubauen des Docker-Images ohne Cache schlägt nicht mehr mit `No module named 'psycopg'` fehl (die SQLAlchemy-Abhängigkeit ist nun auf Versionen unter 2.1 begrenzt).
- **Korrektur**: Der Dokumentationslink im Anwendungsmenü funktioniert nun in Docker-Deployments. Der Docker-Stack enthält einen `docs`-Dienst, der das Portal auf Port 7876 bereitstellt. Bauen Sie nach dem Update beide Images neu: `docker-compose build web docs && docker-compose up -d docs web`.

## 1.13.0

- **Optionale Zwei-Faktor-Authentifizierung (zeitbasiertes Einmalkennwort, TOTP)**: Nutzer können in ihrem Profil eine Authenticator-App aktivieren und erhalten einmal verwendbare Wiederherstellungscodes. Administratoren können 2FA pro Rolle verpflichtend machen.
- **Link zum Dokumentationsportal**: Das Anwendungsmenü verlinkt nun auf das Dokumentationsportal. Die Deployment-URL wird mit `VITE_DOCS_PORTAL_URL` konfiguriert; die lokale Entwicklung verwendet `http://localhost:7876`.
- **Volltextsuche mit Relevanzsortierung**: Die Suche läuft nun gegen einen echten Volltextindex statt gegen einen einfachen Teilstring-Scan, mit nach Relevanz sortierten Ergebnissen und hervorgehobenen Treffer-Ausschnitten.
- **App-Version in der Fußzeile angezeigt**.
- Diverse Backend-Zuverlässigkeitskorrekturen (Absturz des Coverage-Berichts bei Templates, Portabilität von Migrationen, Bereinigung von totem Code).

## 1.12.0

- **Prompt-Freigabe & Teamzusammenarbeit**: Prompt-Eigentümer können Teammitgliedern Lese- oder Bearbeitungszugriff auf einzelne Prompts gewähren, mit einem Filter „Mit mir geteilt" und klarer Kennzeichnung zwischen einer expliziten Freigabe und einem standardmäßig sichtbaren Prompt. Der Freigabezustand ist absichtlich nicht in Export/Import enthalten — verwenden Sie ein vollständiges Backup/eine Wiederherstellung, wenn er erhalten bleiben soll.
- **Sichtbarkeitsänderung**: Neue Prompts sind standardmäßig privat; Prompts, die vor diesem Release existierten, wurden als „Öffentlich (Legacy)" eingestuft und können (einseitig) von ihrem Eigentümer oder einem Administrator privat gemacht werden.
- Umfangreiches internes Refactoring überdimensionierter Templates und TypeScript-Module — keine für Benutzer sichtbare Verhaltensänderung.
- **Sicherheit**: Ratenbegrenzung von Auth-Endpunkten auf alle zustandsändernden und aufwendigen Endpunkte erweitert (Import/Export, Backups, Massenaktionen), nun tatsächlich pro Benutzer statt versehentlich global. Mehrere Stored-XSS-Risiken durch unsichere `innerHTML`-Verwendung behoben.

## 1.11.0

- Sicherheitspatches für Abhängigkeiten (Jinja2, python-multipart und andere), die 24 bekannte CVEs schließen.
- Neuer CI-Sicherheitsaudit-Job, der bei jedem Push/PR Schwachstellenscans für Abhängigkeiten ausführt.
- **Dynamische Prompt-Platzhalter**: Prompt-Inhalte können `[NAME]`/`{NAME}`-artige Tokens enthalten, die beim Kopieren ausgefüllt werden.

## 1.10.0

- Serverseitige Paginierung der Prompt-Liste, sodass große Bibliotheken seitenweise statt als gesamter Datensatz geladen werden.
- **Erweitertes Backup- & Wiederherstellungssystem**: Verschlüsselung, Cloud-Speicher (S3-kompatibel, Google Drive, Dropbox), Zeitplanung und Audit-Protokollierung für Backups sowie mehrere backupbezogene Sicherheitskorrekturen (Path Traversal, Stored XSS, unauthentifizierte Endpunkte).
- Globaler Sprachwähler im Header jeder Seite hinzugefügt.
- Neues Entwickler-Workflow-Makefile (`make install`, `make dev`, `make test`, `make lint`, `make build`) als einheitlicher Einstiegspunkt für gängige Aufgaben.
- Mobile-responsive UI-Verbesserungen: touch-optimierte Navigation, Offline-Unterstützung und Installierbarkeit als Progressive Web App.

## 1.9.0

- **Semantische Prompt-Versionierung**: Prompts können beim Erstellen oder Bearbeiten eine optionale `MAJOR.MINOR.PATCH`-Versionsnummer erhalten.

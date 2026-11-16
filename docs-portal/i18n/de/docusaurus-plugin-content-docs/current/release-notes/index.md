---
title: Release Notes
sidebar_position: 1
---

# Release Notes

Highlights der letzten PromptVault-Releases. Die vollständige, ungekürzte Historie finden Sie in `docs/CHANGELOG.md` im Repository.

Die Schritte zum Aktualisieren finden Sie unter [PromptVault aktualisieren](../installation/update.md).

## Demnächst

Das Portal enthält jetzt eine Anleitung zum Sichern, Aktualisieren, Prüfen und Wiederherstellen einer Docker-Compose-Installation. Jede Seite hat außerdem einen Link „Zurück zu PromptVault“. Legen Sie beim Erstellen des Doku-Images `DOCS_APP_URL` fest, damit der Link auf Ihre Instanz verweist. Siehe [PromptVault aktualisieren](../installation/update.md).

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

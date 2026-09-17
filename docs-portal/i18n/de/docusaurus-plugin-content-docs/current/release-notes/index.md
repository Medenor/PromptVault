---
title: Release Notes
sidebar_position: 1
---

# Release Notes

Highlights der letzten PromptVault-Releases. Die vollständige, ungekürzte Historie finden Sie in `docs/CHANGELOG.md` im Repository.

## Unreleased

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

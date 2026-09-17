---
title: Zwei-Faktor-Authentifizierung
sidebar_position: 5
---

# Zwei-Faktor-Authentifizierung

## Aktueller Stand

Zeitbasierte Einmalkennwort-Zwei-Faktor-Authentifizierung (TOTP) ist in PromptVault **noch nicht verfügbar**. Sie ist eine geplante Härtung des Authentifizierungssystems, die auf der Projekt-Roadmap geführt wird, aber es existiert heute noch kein Registrierungsablauf, kein Login-Herausforderungsschritt und keine Admin-Durchsetzungsrichtlinie in der Anwendung.

## Was bereits vorhanden ist

Auch wenn dedizierte 2FA noch nicht verfügbar ist, umfasst der Authentifizierungsstack von PromptVault bereits mehrere Schutzebenen für Ihr Konto:

- **Starkes Passwort-Hashing** (Argon2id) mit einer durchgesetzten Passwortrichtlinie (Mindestlänge und Zeichenklassen-Anforderungen).
- **Kontosperrung** nach wiederholten fehlgeschlagenen Anmeldeversuchen für eine konfigurierbare Dauer.
- **Kurzlebige, rotierende JWT-Zugriffs-/Refresh-Tokens** mit Wiederverwendungserkennung — ein gestohlenes Refresh-Token kann nicht unbegrenzt wiederverwendet werden.
- **Eine Obergrenze gleichzeitiger Sitzungen pro Konto**, mit Geräte-/IP-Verfolgung und der Möglichkeit, jede aktive Sitzung zu widerrufen.
- **Ein Passwort-Reset-Ablauf ohne Enumeration** — Reset-Anfragen verraten nie, ob eine E-Mail-Adresse ein Konto besitzt.

Siehe `docs/AUTHENTICATION_SECURITY.md` des Projekts für vollständige Details zu diesen Kontrollen.

## Geplantes Design

Die Roadmap beschreibt TOTP-2FA als eine Opt-in-Registrierung (QR-Code + Geheimnis, mit einmal verwendbaren Wiederherstellungscodes), die nach Aktivierung für ein Konto einen Herausforderungsschritt in den Login einfügt, sowie eine Admin-Richtlinie, um sie für bestimmte Rollen zu erzwingen. Verifizierungsversuche würden ratenbegrenzt, und Registrierungs-/Deaktivierungs-/Herausforderungsereignisse würden protokolliert — konsistent damit, wie andere sicherheitsrelevante Aktionen in PromptVault bereits heute protokolliert werden.

## Empfehlung in der Zwischenzeit

Wenn Ihre Bereitstellung heute stärkeren Schutz als nur ein Passwort benötigt, sind die praktischen Optionen: `AUTH_ENABLED=true` beibehalten (führen Sie niemals eine vernetzte Mehrbenutzer-Instanz mit deaktivierter Authentifizierung aus), eine starke Passwortrichtlinie über die `PASSWORD_*`-Umgebungsvariablen erzwingen und sich auf die vorhandene Sitzungsobergrenze und die Widerrufskontrollen verlassen, um den Schaden eines kompromittierten Zugangsdatensatzes zu begrenzen. Diese Seite wird aktualisiert, sobald TOTP-Unterstützung verfügbar ist.

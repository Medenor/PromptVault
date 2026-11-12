---
title: Zwei-Faktor-Authentifizierung
sidebar_position: 5
---

# Zwei-Faktor-Authentifizierung

Die Zwei-Faktor-Authentifizierung (2FA) fügt beim Anmelden eine zusätzliche Prüfung hinzu. Nach Ihrem Passwort fragt PromptVault nach einem 6-stelligen Code aus einer Authenticator-App oder nach einem Ihrer Wiederherstellungscodes. Die 2FA ist für die meisten Nutzer optional. Administratoren können sie für bestimmte Rollen verpflichtend machen.

## Einrichten der 2FA

1. Öffnen Sie Ihr Profil und suchen Sie die Karte **Zwei-Faktor-Authentifizierung**. Wählen Sie **Zwei-Faktor-Authentifizierung einrichten**.
2. Scannen Sie den QR-Code mit einer Authenticator-App wie Google Authenticator, Authy oder 1Password. Wenn das nicht geht, öffnen Sie **Code lässt sich nicht scannen?** und geben Sie den **Einrichtungsschlüssel** von Hand in die App ein.
3. Geben Sie den 6-stelligen Code aus Ihrer App ein und wählen Sie **Prüfen und aktivieren**.
4. Speichern Sie Ihre Wiederherstellungscodes. PromptVault zeigt 10 Codes nur einmal an. Kopieren Sie sie oder laden Sie sie als Textdatei herunter, und bewahren Sie sie an einem sicheren Ort auf.

Die 2FA ist erst nach Schritt 3 aktiv. Wenn Sie die Einrichtung vor der Bestätigung neu starten, ersetzt der neue Einrichtungsschlüssel den alten.

## Anmelden mit 2FA

1. Geben Sie Ihr Passwort wie gewohnt ein.
2. Geben Sie auf dem Bildschirm **Zwei-Faktor-Authentifizierung** den 6-stelligen Code aus Ihrer App ein und wählen Sie **Prüfen**.

Der Anmeldeschritt läuft nach 2 Minuten ab. Danach beginnen Sie wieder beim Passwortschritt.

App-Codes wechseln alle 30 Sekunden. Ein Code funktioniert auch einen Zeitschritt vor oder nach der aktuellen Zeit. Eine Telefonuhr, die etwas abweicht, bleibt deshalb nutzbar.

## Anmelden mit einem Wiederherstellungscode

Geben Sie auf demselben Bildschirm anstelle des App-Codes einen Wiederherstellungscode ein. Wiederherstellungscodes sehen so aus: `xxxx-xxxx`. Jeder Code funktioniert nur einmal. Nach der Verwendung funktioniert er nicht mehr.

Verwenden Sie einen Wiederherstellungscode, um wieder Zugang zu erhalten, wenn Sie Ihr Telefon verloren haben. Erzeugen Sie danach neue Codes.

## Wiederherstellungscodes neu erzeugen

Wählen Sie in Ihrem Profil **Wiederherstellungscodes neu erzeugen**. Geben Sie Ihr aktuelles Passwort und einen aktuellen App-Code oder Wiederherstellungscode ein. PromptVault erstellt 10 neue Codes. Alle früheren Codes funktionieren sofort nicht mehr.

## 2FA deaktivieren

Wählen Sie in Ihrem Profil **Zwei-Faktor-Authentifizierung deaktivieren**. Geben Sie Ihr aktuelles Passwort und einen aktuellen App-Code oder Wiederherstellungscode ein. Beim Deaktivieren werden Ihre 2FA-Einrichtung und alle verbleibenden Wiederherstellungscodes entfernt. Danach melden Sie sich nur noch mit Ihrem Passwort an.

## 2FA für eine Rolle verpflichtend machen

Wählen Sie im Abschnitt **Richtlinie zur Zwei-Faktor-Authentifizierung** der Administration, welche Rollen (Betrachter, Bearbeiter, Administrator) 2FA verwenden müssen. Eine Änderung gilt ab der nächsten Anmeldung jedes Nutzers. Bestehende Sitzungen werden dadurch nicht beendet.

- Ein Nutzer in einer verpflichtenden Rolle, der 2FA noch nicht eingerichtet hat, wird direkt nach der Anmeldung zu einem Einrichtungsschritt geleitet. Die übrige Anwendung kann er erst nutzen, wenn die Einrichtung abgeschlossen ist.
- Ein Nutzer in einer verpflichtenden Rolle, der 2FA bereits eingerichtet hat, meldet sich über den üblichen Codeschritt an.
- Wenn Sie eine Anforderung aufheben, wird die bestehende 2FA-Einrichtung niemandes entfernt.

## Wenn Sie Ihre App und Ihre Wiederherstellungscodes verloren haben

PromptVault kann 2FA in diesem Fall nicht für Sie zurücksetzen. Derzeit gibt es keine Administratoroption, die 2FA aus einem Konto entfernt. Wenden Sie sich an die Person, die Ihren PromptVault-Server betreibt. Bewahren Sie Ihre Wiederherstellungscodes sicher auf, damit es nicht so weit kommt.

## Sicherheitshinweise

- Ihre 2FA-Einrichtung wird verschlüsselt gespeichert. Wiederherstellungscodes werden so gespeichert, dass sie nicht wieder ausgelesen werden können, und lassen sich daher nicht erneut anzeigen.
- Falsche Codes zählen zur selben Sperre wie falsche Passwörter. Zu viele falsche Versuche sperren das Konto für kurze Zeit.
- Das Auditprotokoll erfasst das Aktivieren oder Deaktivieren von 2FA, das Neuerzeugen von Wiederherstellungscodes und Änderungen der Anforderung einer Rolle.
- PromptVault begrenzt, wie oft Einrichtung, Prüfung, Deaktivierung und Neuerzeugen versucht werden können. Erscheint eine Meldung über zu viele Versuche, warten Sie eine Minute und versuchen Sie es erneut.
- Der Serverbetreiber muss `TOTP_ENCRYPTION_KEY` setzen. Siehe [Konfiguration](../configuration/index.md).

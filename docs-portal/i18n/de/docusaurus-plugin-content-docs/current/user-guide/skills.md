---
title: Skills
sidebar_position: 4
---

# Skills

Ein Skill ist ein Ordner mit Anweisungen und Hilfsdateien, den ein KI-Agent für eine Aufgabe laden kann. Er enthält immer eine Datei `SKILL.md` und kann außerdem Skripte, Referenzen und weitere Dateien enthalten. PromptVault speichert Skills neben deinen Prompts, damit du beides an einem Ort organisieren, durchsuchen, sichern und exportieren kannst.

## Was ein Skill ist

Ein Skill wird als `.zip`-Archiv gespeichert. Die Datei `SKILL.md` beginnt mit einem kurzen Kopfbereich (Name und Beschreibung), gefolgt von den Anweisungen. PromptVault folgt dem offenen Agent-Skills-Format.

In der Liste des Tresors zeigt ein Skill ein **Skill**-Kennzeichen und eine kurze Beschreibung statt eines Prompt-Textes. Mit dem Filter **Typ** über der Liste siehst du nur Prompts oder nur Skills.

## Einen Skill importieren

1. Wähle **Skill importieren** in der Kopfzeile.
2. Wähle eine `.zip`-Datei aus. Die `SKILL.md` kann im Stammverzeichnis des Archivs oder in genau einem Ordner der obersten Ebene liegen.
3. Füge bei Bedarf eine Kategorie und Tags hinzu und wähle **Importieren**.

Der Skill wird in einem Schritt gespeichert: Stimmt etwas mit dem Archiv nicht, wird nichts gespeichert. Funktioniert der Import, öffnet sich der Skill sofort.

## Formatwarnungen

PromptVault akzeptiert Skills auch dann, wenn sie das Format nicht genau einhalten. Du siehst dann einen Hinweis, der jede verletzte Regel auflistet, zum Beispiel einen fehlenden Namen, einen Namen, der nicht aus Kleinbuchstaben mit Bindestrichen besteht, eine Beschreibung mit mehr als 1.024 Zeichen oder eine `SKILL.md` im Stammverzeichnis des Archivs statt in einem Ordner. Die Warnungen bleiben in der Detailansicht des Skills sichtbar. Sie blockieren nie einen Import.

## Grenzen und abgelehnte Archive

Ein Archiv wird abgelehnt, und es wird nichts gespeichert, wenn es:

- keine gültige Zip-Datei ist oder verschlüsselt ist;
- keine `SKILL.md` im Stammverzeichnis oder in genau einem Ordner der obersten Ebene hat;
- einen Pfad enthält, der den Skill-Ordner verlässt, einen symbolischen Link, einen doppelten Pfad oder einen Dateinamen, der auf gängigen Systemen ungültig ist;
- eine Grenze überschreitet: Upload-Größe (standardmäßig 10 MB), entpackte Größe (50 MB), Anzahl der Dateien (500), Ordnertiefe (10 Ebenen) oder Größe einer einzelnen Datei (10 MB).

Die Meldung nennt die verletzte Regel und, wo es passt, den Eintrag, der sie ausgelöst hat. Administratoren können die Grenzen mit den `SKILL_*`-Einstellungen im Bereitstellungshandbuch ändern.

## Einen Skill ansehen

Die Detailansicht zeigt die Beschreibung, die formatierten Anweisungen und die Dateiliste als Baum. Ordner stehen zuerst. Du kannst den Baum mit den Pfeiltasten durchlaufen, Ordner mit der Pfeiltaste nach rechts öffnen und mit der Eingabetaste eine Datei auswählen.

Textdateien werden als schreibgeschützter Text angezeigt. Binärdateien zeigen ihre Größe und einen Download-Link. Nichts aus einem Skill wird jemals ausgeführt oder als Webseite dargestellt, und Platzhalter wie `${CLAUDE_SKILL_DIR}` bleiben einfacher Text.

## Einen Skill herunterladen

**Skill herunterladen** liefert `<skill-name>.zip` mit genau einem Ordner darin, im Standardaufbau. Jede Datei ist identisch mit der importierten. Der Archivname verwendet die Skill-Kennung, deshalb ändert ein neuer Titel ihn nicht. Du kannst auch eine einzelne Datei aus der Ansicht herunterladen.

## Bearbeiten, ersetzen und löschen

- **Details bearbeiten** ändert Titel, Kategorie, Tags, Notiz und Favorit. Die Dateien bleiben unberührt, und es entsteht kein Versionsverlauf.
- **Dateien ersetzen** lädt ein neues Archiv hoch. Titel, Notiz, Tags, Kategorie und Favorit bleiben erhalten; Beschreibung und Kennung stammen aus der neuen `SKILL.md`. Wird das neue Archiv abgelehnt, bleibt der Skill genau so, wie er war.
- **Skill löschen** entfernt den Skill samt allen Dateien endgültig. Das lässt sich nicht rückgängig machen, deshalb wirst du vorher um eine Bestätigung gebeten.

## Suche, Sicherungen und was Skills nicht tun

Die Suche findet einen Skill über Titel, Notiz und den Text seiner `SKILL.md`. In Skripten und anderen mitgelieferten Dateien sucht sie nicht. Skills sind in vollständigen Datenbanksicherungen enthalten und kommen nach einer Wiederherstellung unverändert zurück.

Skills sind privat für die Person, die sie importiert hat. Sie haben keinen Versionsverlauf, kein Teilen und keine Platzhalter, und der Massenexport von Prompts enthält sie nicht: Exportiere einen Skill aus seiner eigenen Ansicht.

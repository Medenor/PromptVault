---
title: Backups
sidebar_position: 2
---

# Backups

PromptVault enthält Funktionen für Backup und Wiederherstellung mit Zeitplanung, Integritätsprüfung, Verschlüsselung und optionalem Cloud-Speicher. Ein Backup hilft bei der Wiederherstellung von Daten; ein Export ersetzt es nicht, wenn Freigabeberechtigungen erhalten bleiben müssen.

## Geplante Backups {#scheduled-backups}

Administratoren konfigurieren automatische Backups auf der Backup-Verwaltungsseite. Wählen Sie einen täglichen, wöchentlichen oder monatlichen Zeitplan und eine Uhrzeit, und aktivieren Sie dann den Zeitplan. Würde ein geplantes Backup starten, während ein anderes noch läuft, überspringt PromptVault den neuen Lauf und protokolliert diese Entscheidung.

Das erste Backup einer Installation (oder das erste nach einem unbrauchbar gewordenen vorherigen Backup) ist immer ein vollständiges Backup; nachfolgende geplante Backups sind inkrementell und speichern nur, was sich seit dem letzten vollständigen Backup geändert hat, um den Speicherverbrauch gering zu halten.

## Integritätsprüfung {#integrity-verification}

Der Inhalt jedes Backups wird nach der Erstellung validiert, und das Ergebnis wird gespeichert. Eine Prüfsumme wird zusammen mit den Metadaten jedes Backups abgelegt, damit die Integrität später erneut geprüft werden kann. Sie können jederzeit auch manuell einen Integritätstest für ein vorhandenes Backup über die Backup-Verwaltungsseite auslösen — nützlich, bevor Sie sich tatsächlich auf eine Wiederherstellung verlassen müssen.

## Verschlüsselung {#encryption}

Backups können mit einem von Ihnen bereitgestellten Schlüssel verschlüsselt werden, bevor sie gespeichert werden; PromptVault speichert Verschlüsselungsschlüssel niemals im Klartext. Schlüsselrotation wird unterstützt — bereits mit einem vorherigen Schlüssel verschlüsselte Backups bleiben während des Übergangs zu einem neuen Schlüssel zugänglich.

## Cloud-Speicher {#cloud-storage}

Sie können einen S3-kompatiblen Anbieter, Google Drive oder Dropbox als Backup-Ziel über die Admin-Oberfläche konfigurieren. Eine lokale Kopie wird immer aufbewahrt, auch wenn ein Cloud-Upload konfiguriert ist, und Sie können direkt aus dem Cloud-Speicher wiederherstellen, nicht nur aus lokalen Backups.

Zugangsdaten für Cloud-Anbieter (Access-Key/Secret-Key) werden mit `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` im Ruhezustand verschlüsselt — siehe [Konfiguration](../configuration/index.md#backups). Diese Variable ist erforderlich, bevor Sie einen Cloud-Anbieter hinzufügen können.

## Wiederherstellungsvorschau und selektive Wiederherstellung {#restore-preview-and-selective-restore}

Prüfen Sie vor einer Wiederherstellung die Vorschau: Sie listet Prompts auf, die hinzugefügt, aktualisiert oder gelöscht werden. Wählen Sie nur die wiederherzustellenden Prompts aus, oder stellen Sie das vollständige Backup wieder her. Wenden Sie die Wiederherstellung erst an, wenn Sie die aufgelisteten Änderungen verstehen.

## Aufbewahrung {#retention}

Ein konfigurierbarer Aufbewahrungszeitraum (in Tagen) bestimmt, wann ältere Backups für die Bereinigung infrage kommen, damit der Backup-Speicher nicht unbegrenzt wächst.

## Praktische Hinweise {#practical-notes}

- Halten Sie `PROMPTVAULT_DATA_DIR` pro Umgebung (Dev/Staging/Prod) getrennt — ein gemeinsames Datenverzeichnis über Umgebungen hinweg kann dazu führen, dass geplante Backups und Wiederherstellungen kollidieren, da Backups relativ zu diesem Verzeichnis gespeichert werden.
- Testen Sie gelegentlich eine Wiederherstellung, nicht nur ein Backup — die Integritätsprüfung bestätigt, dass die Backup-Datei lesbar ist, aber erst ein vollständiger Wiederherstellungsvorschau-Lauf bestätigt, dass die enthaltenen Daten tatsächlich Ihren Erwartungen entsprechen.

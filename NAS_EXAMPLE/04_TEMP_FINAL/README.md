<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/04_TEMP_FINAL
Rolle: TEMP_FINAL
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# 04_TEMP_FINAL

Dieser Ordner ist der kontrollierte Ausgabepunkt nach Abschluss von Phase 2. Nur Batches, die vollständig archiviert wurden, validierte ZIP-Archive enthalten und bereit für den Langzeitspeicher oder Weitertransfer sind, sollen hier landen. Der Ordner dient als gepufferter Übergabepunkt zwischen Phase 2 (Archivierung) und Phase 3 (optionaler Transfer zu Cloud/extern). Er ist nicht für ungesichtete Eingänge, laufende Reviews oder Rohdaten gedacht. Wenn ein Batch noch in Bearbeitung ist, muss er in `TEMP_IMAGES` bleiben; wenn ein Fehler vorliegt, ist `TEMP_ERROR` der richtige Ort.

## Zulässige Daten

In diesem Ordner sind ausschließlich folgende Dateitypen erlaubt:

- `*.zip` – Vollständige, validierte Archive (JPG + ARW)
- `batch_manifest.json` – Finale Metadaten nach Phase 2
- `archive_plan.json` – Archivierungsprotokoll mit Hash-Werten
- `review_state.json` – Finaler Status (`phase2_complete`)

Keine anderen Dateien dürfen in diesem Ordner abgelegt werden. Technische Artefakte wie Logs, Summaries, Caches oder Modelle gehören in `WORKFLOW_DATA/runtime/`.

## Verwendung für Phase 3

Dieser Ordner kann als Quelle für Phase 3 (Transfer) dienen:

- **Cloud-Upload:** Archive können zu Google Photos, Synology C2 oder externem Speicher transferiert werden
- **Backup:** Archive können auf externes Backup-Medium kopiert werden
- **Langzeitarchiv:** Archive können auf NAS-Shares für Langzeitspeicherung verschoben werden

Nach erfolgreichem Transfer bleiben die Archive in `TEMP_FINAL` als lokale Kopie erhalten, es sei denn, die Konfiguration erzwingt ein Aufräumen.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten im Review sind, gehört der Inhalt nach `TEMP_IMAGES`. Wenn ein Fehler, Konflikt oder Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Wenn die Archive noch nicht finalisiert sind, gehören sie nach `05_ARCHIVE` (in Arbeit). Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.

## Automatische Bereinigung

Der Workflow räumt diesen Ordner standardmäßig **nicht** automatisch. Archive verbleiben als lokale Sicherungskopie. Bei Bedarf kann in `config.yaml` eine Aufräum-Regel konfiguriert werden, die Archive nach erfolgreichem Transfer löscht oder auf ein externes Ziel verschiebt.
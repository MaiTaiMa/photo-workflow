# 2. Architektur, Verzeichnisse, Datenflüsse

## 2.1 Systemübersicht

Das Projekt trennt Betriebsschnittstelle, CLI, Fachmodule und den persistenten NAS-Datenbereich. Shell-Skripte prüfen nur Umgebung und starten den Workflow; sie enthalten keine Geschäftslogik. Die Python-CLI lädt `config/config.yaml`, validiert die Konfiguration und delegiert an spezialisierte Module. Die Fachmodule erzeugen testbare Ergebnisobjekte und kapseln Dateisystemmutationen.

## 2.2 Projektstruktur

- `NAS_EXAMPLE/`: Beispiel für den persistenten NAS-
  - `00_TEMP_ERROR/`: Quarantäne und Fehlerfälle.
  - `01_TEMP_SD/`: Neue Eingangsbatches.
  - `02_TEMP_IMAGES/`: Phase-1-Review-Ausgabe.
  - `03_TEMP_DONE/`: Menschlich freigegebene Übergabe.
  - `04_TEMP_FINAL/` (optional): Kontrollierter lokaler Finalisierungsbereich für erfolgreich durch PHASE2 verarbeitete Batches, wenn vor der Veröffentlichung eine lokale Zwischenprüfung erforderlich ist.
  - `finalization.publish_to_synology_photos.target_folder`: Separat validierter Veröffentlichungszielpfad innerhalb von `paths.publish_root`.
  - `WORKFLOW_DATA/`: States, Logs, Summaries, Caches, Referenzen, Modelle.
  - `MANUAL_KEEP/inbox/`: Manuelle Keep-Eingänge.
  - `MANUAL_KEEP/used/`: Bereits zugeordnete Keep-Dateien.

- `photo-workflow/`
  - `app/`: Python-Fachmodule und CLI.
  - `config/`: Zentrale kommentierte Konfiguration.
  - `scripts/`: DSM-/Docker-Start- und Vorprüfungsskripte.
  - `tests/`: Unit- und Vertragsprüfungen.
  - `docs/`: Handbuch, Architektur, Testdokumentation.

## 2.3 Kanonische Arbeitsordner

| Ordner | Zweck |
|---|---|
| `00_TEMP_ERROR` | Quarantäne für fehlerhafte oder unsichere Fälle. |
| `01_TEMP_SD` | Eingang für neue Kameraordner. |
| `02_TEMP_IMAGES` | Ergebnis aus Phase 1 zur manuellen Sichtung. |
| `03_TEMP_DONE` | Manuell freigegebene Ordner für Phase 2. |
| `04_TEMP_FINAL` (optional) | Kontrollierter lokaler Bereich für erfolgreich finalisierte Batches, sofern kein Direkttransfer nach `target_folder` genutzt wird. |
| `WORKFLOW_DATA` | Zentrale Daten (faces, models, runtime, samples, reports, archives, config). |
| `MANUAL_KEEP` | Vorab ausgewählte, extern erhaltene JPGs (inbox, used). |
| `finalization.publish_to_synology_photos.target_folder` | Optionaler Veröffentlichungszielpfad. Er wird von Synology Photos indexiert. |

Die tatsächlichen Arbeits-, Daten-, Archiv- und Referenzpfade müssen innerhalb von `paths.basedir` liegen. Der Veröffentlichungszielpfad `target_folder` ist die einzige Ausnahme und muss innerhalb von `paths.publish_root` liegen. Beide Wurzeln und alle darunterliegenden Pfade werden kanonisch validiert.

`03_TEMP_DONE` bleibt der Arbeits- und Übergabebereich nach manueller Freigabe und während PHASE2. `04_TEMP_FINAL` kann als optionaler lokaler Finalisierungsbereich verwendet werden. Bei direktem Transfer wird der Batch nach `target_folder` übertragen. Bei deaktivierter Veröffentlichung bleibt der Batch in `03_TEMP_DONE` oder im kontrollierten `04_TEMP_FINAL` unverändert.

## 2.4 Batch-Struktur und Benennung

Ein Batch enthält verbindlich die Unterordner:

- `ARW` (für ausgelagerte ARWs)
- `SAVE` (für JPG-Archiv und Scores)
- `Review` (für zur Prüfung vorgemerkte Bilder)
- `Rejected` (für abgelehnte Bilder)

Nur JPGs im Batch-Hauptordner gelten als aktiv. Ein aus `Review` oder `Rejected` in den Hauptordner zurückgelegtes JPG ist wieder aktiv und schützt sein passendes ARW.

**ARW-Schutz:** Ein ARW ist geschützt, wenn ein aktives JPG mit demselben eindeutig normalisierten Basename existiert. Mehrdeutige Paarungen, mehrere wirksame JPG-Kopien, fehlende Quellhashes oder widersprüchliche Ordnerzustände blockieren Phase 2 mit `review_state_invalid`; es darf keine ARW-Aktion stattfinden.

## 2.7 Manual Keep

**MANUAL_KEEP** ist der kontrollierte Eingang für externe, vorab ausgewählte JPGs (z. B. per WhatsApp erhalten). Die Zuordnung erfolgt streng getrennt vom Culling, Serienlogik und persönlichem Geschmack. Die Vergleichsbilder können von der Auflösung und dem Dateinamen unterschiedlich zum Original sein.

- `inbox/`: Neue, noch nicht zugeordnete Manual-Keep-Bilder.
- `used/`: Bereits zugeordnete Manual-Keep-Bilder.

Detaillierte Logik: Siehe Abschnitt 4.6.
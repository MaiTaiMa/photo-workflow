# AP21.5 Abnahme und Reststatus

## Zweck

Dieses Dokument bewertet den Implementierungsbranch gegen die acht kanonischen Spezifikationsdateien. Es beschreibt, welche Verträge als Code und Test vorhanden sind und welche Punkte vor einem produktiven NAS-Lauf noch manuell nachgewiesen werden müssen.

## Abnahmematrix

| Spezifikation | Automatisiert vorbereitet | Restnachweis |
|---|---|---|
| 00 Geltungsbereich | Pfad-, Secret- und Dry-Run-Gates | vollständiger Produktivlauf ohne Datenverlust |
| 01 Architektur | App-, Config-, Test- und Adaptergrenzen | vollständige Legacy-CLI-Migration |
| 02 Batch/Recovery | StateStore, Phase-Gates, Archive, Quarantäne | vollständiger Resume- und Quarantäne-Pilot |
| 03 Scoring/Faces | Scores, Face-Vertrag, Match-Marge, Metadatenvertrag | echte Detection-/Crop-Kalibrierung |
| 04 Referenzpools | selection.json, Rebuild, Ranking, Limits, RAM-Cache | reale Poolmigration und menschliche Aktivierung |
| 05 Betrieb | Config-Gates, Runtime-Stop, Security-Audit | NAS-/Docker-Test mit echten Mounts |
| 06 Synology API | Dry-Run-Adapter und Capability-Gate | zielsystemspezifischer Readback-Pilot |
| 07 Anhänge | CI, Acceptance-Dokument und Tests | Kommentar-/README-Vollständigkeitsprüfung |

## CI-Abdeckung

Der Workflow führt die Unit-, Integrations- und Security-Tests mit Python 3.11 aus. Modellgewichte, private Fotos, NAS-Pfade, Secrets und Synology-Zugriffe sind nicht Bestandteil der CI.

## Sicherheitsgrenze

Ein grüner CI-Lauf ist keine Freigabe für einen Produktionslauf. Vor dem NAS-Pilot müssen insbesondere `finalization.enabled`, API-Schreibzugriffe und bekannte Personen-Zuordnungen bewusst konfiguriert und separat nachgewiesen werden.

## Offene Abnahme-Gates

- Legacy-CLI vollständig an den Orchestrator anbinden.
- PHASE2- und PHASE3-State-Historie einschließlich Resume abschließend testen.
- Face-Detection, Crop-Qualität und Modellfingerprint auf dem Zielsystem prüfen.
- Docker-/NAS-Mount-, SIGTERM- und Fehlerisolationslauf durchführen.
- Synology-Photos-Pilot nur mit Testbild, Testperson, Readback und Dry-Run-Rückfallebene durchführen.

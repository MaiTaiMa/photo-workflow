# Synology Photo Workflow (Python/Docker)

> **Vollständige Dokumentation:** Siehe [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) für Installation, Konfiguration, Phasenablauf, Score-Logik und Betriebsabläufe.
> Diese Seite ist ein kompakter Einstieg.

## Überblick

Der Python-Workflow ersetzt das ursprüngliche Bash-Skript (siehe `legacy/`) und ergänzt es um KI-gestütztes JPG-Culling, Gesichtserkennung für bekannte Personen und eine vertragsbasierte Phasenarchitektur mit nachvollziehbaren Zustandsübergängen.

## Arbeitsordner

| Ordner | Zweck |
|---|---|
| `01_TEMP_SD` | Eingang für neue Kamera-Batches |
| `02_TEMP_IMAGES` | Phase-1-Ergebnis zur manuellen Sichtung |
| `03_TEMP_DONE` | Manuell freigegebene Batches für Phase 2 |
| `04_TEMP_FINAL` | Finalisierte Batches (nur bei aktiviertem Move, siehe Handbuch) |
| `00_TEMP_ERROR` | Quarantäne für fehlerhafte Batches |
| `MANUAL_KEEP` | Extern ausgewählte Vergleichsbilder |
| `WORKFLOW_DATA` | Zustände, Logs, Modelle, Referenzpools |

**Wichtigste Regel:** Nur JPGs im Hauptordner eines Batches gelten als aktiv ausgewählt. Bilder in `Review/` oder `Rejected/` sind bewusst ausgelagert; ein manuelles Zurückschieben in den Hauptordner erhält auch das passende ARW.

## CLI-Befehle

```bash
# Nur Phase 1: Import, Bewertung, Übergabe nach TEMP_IMAGES
python /app/app/photo_workflow.py --config /app/config/config.yaml phase1

# Nur Phase 2: ARW-Archivierung, Review/Rejected-Bereinigung
python /app/app/photo_workflow.py --config /app/config/config.yaml phase2

# Konfigurierte Pipeline (Standard: phase1 + phase2)
python /app/app/photo_workflow.py --config /app/config/config.yaml pipeline

# Alias, identisch zu pipeline
python /app/app/photo_workflow.py --config /app/config/config.yaml phase12

# Family-Cache gezielt neu aufbauen
python /app/app/photo_workflow.py --config /app/config/config.yaml rebuild-family-cache

# Persönliches Geschmacksmodell trainieren
python /app/app/photo_workflow.py --config /app/config/config.yaml train-personal
```

Für den produktiven Betrieb (Docker, DSM Task Scheduler) nutze `run_photo_workflow.sh` oder `docker-compose.yml` – beide rufen konsistent `pipeline` auf.

## Legacy-Bash-Fallback

Das ursprüngliche Bash-Skript (`legacy/nas_photosort.sh`) bleibt als Rückfallebene erhalten und nutzt denselben Grundworkflow (`TEMP_SD` → `TEMP_IMAGES` → `TEMP_DONE`). Es kennt jedoch **keine** KI-Culling-Logik (`Review/`, `Rejected/`, Scoring) und ist daher nur ein Ordner-Fallback, kein vollwertiger Ersatz. Details siehe `legacy/README.md`.

## Logging für DSM Task Scheduler

Jeder Lauf schreibt einen Startblock, laufende Statusmeldungen und eine Abschlusszusammenfassung auf `stdout` – das kann der DSM Task Scheduler direkt als E-Mail versenden. Zusätzlich wird pro Lauf eine strukturierte JSON-Zusammenfassung unter `WORKFLOW_DATA/runtime/run_summaries/` abgelegt (siehe Handbuch, Kapitel 10.1).

## Sicherheit

- Alle produktiven Pfade liegen innerhalb von `base_dir`.
- Löschungen von Originaldaten sind nur in eng begrenzten, vertraglich definierten Fällen erlaubt (siehe `docs/AUTOMATION_AND_FINALIZATION_CONTRACT_v1-2.md`).
- Lockfiles verhindern parallele Läufe auf demselben Batch.
- Vor produktivem Einsatz sollte immer ein Testlauf mit Kopien echter Ordner erfolgen.

## Erweiterte Themen

Folgende Funktionen sind ausführlich im Benutzerhandbuch beschrieben:

- Score-Gewichtung und Komponenten (Handbuch, Kapitel 4.2 und 9.3)
- Familien-Gesichtserkennung, Referenzpools und Tag-Schema (Handbuch, Kapitel 7.3, 8.2 und Anhang D)
- Serienerkennung und Best-Bild-Logik (Handbuch, Kapitel 7.4)
- Legacy-Datumsrekonstruktion und Debug-Konfiguration (Handbuch, Anhang D.2)
- Metadaten-Tag-Schema (Handbuch, Anhang D.1)

## Projektstruktur

```text
app/      Python-Fachmodule und CLI
tests/    Automatisierte Prüfungen (Unit, Integration, Security)
config/   Zentrale Konfiguration (config.yaml)
docs/     Ausführliche Dokumentation, Spezifikation, Vertrag
legacy/   Historisches Bash-Skript als Fallback
```

Eine vollständige Modulübersicht mit Kurzbeschreibung findest du in `app/MODULE_OVERVIEW.md`.

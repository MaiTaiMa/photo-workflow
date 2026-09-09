# Basic Photo Workflow

Dieses Repository enthält einen konservativen Zwei-Phasen-Workflow für Kamera- und Foto-Batches auf Synology NAS und in Docker-Umgebungen.

## Einstieg

- **Ausführliche Dokumentation:** [`photo-workflow/docs/USER_MANUAL.md`](photo-workflow/docs/USER_MANUAL.md)
- **Kompakte README:** [`photo-workflow/README.md`](photo-workflow/README.md)
- **Konfiguration:** [`photo-workflow/config/config.yaml`](photo-workflow/config/config.yaml)

## Was das Projekt macht

Der Workflow trennt Eingang, Review, Freigabe und endgültige Archivierung:

1. **Phase 1:** Batch aus `01_TEMP_SD` verarbeiten, Bilder bewerten und nach `02_TEMP_IMAGES` übertragen.
2. **Phase 2:** ARW-Dateien archivieren, `_Review` und `_Rejected` bereinigen, optional nach `04_TEMP_FINAL` verschieben.
3. **Phase 3 (optional):** Finalisierte Batches nach targetfolder transferieren, indexieren, Metadaten übertragen.

## Inhalte des Repos

| Pfad | Zweck |
|---|---|
| `photo-workflow/app/` | Python-Fachmodule und CLI |
| `photo-workflow/tests/` | Automatisierte Prüfungen (Unit, Integration) |
| `photo-workflow/config/` | Zentrale Konfiguration (config.yaml) |
| `photo-workflow/docs/` | Ausführliche Dokumentation, Spezifikation, Vertrag |
| `photo-workflow/legacy/` | Historisches Bash-Skript als Fallback |
| `NAS_EXAMPLE/` | Persistente Zielstruktur für den NAS-Betrieb |

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

**Wichtigste Regel:** Nur JPGs im Hauptordner eines Batches gelten als aktiv ausgewählt. Bilder in `Rejected/` sind bewusst ausgelagert; ein manuelles Zurückschieben in den Hauptordner erhält auch das passende ARW.


## Wichtige Hinweise

- Der Repository-Root ist nur der Einstiegspunkt; die operative NAS-Struktur liegt in `NAS_EXAMPLE/`.
- Die aktive Konfiguration ist `photo-workflow/config/config.yaml`.
- Die Shell-Skripte prüfen und starten nur; die fachliche Logik liegt in Python.
- Für die ausführliche Inbetriebnahme und Nutzung nutze das Handbuch.

## Pipeline-Ausführung

Der Workflow kann einzelne Phasen oder eine konfigurierbare Pipeline ausführen. Die Pipeline führt die in `config/config.yaml` definierte Reihenfolge aus.

**Beispiel (CLI):**
```bash
cd photo-workflow

# Konfigurierte Pipeline (Standard: phase1 + phase2)
python /app/app/photo_workflow.py --config /app/config/config.yaml pipeline

# Nur Phase 1: Import, Bewertung, Übergabe nach TEMP_IMAGES
python /app/app/photo_workflow.py --config /app/config/config.yaml phase1

# Nur Phase 2: ARW-Archivierung, Rejected-Bereinigung
python /app/app/photo_workflow.py --config /app/config/config.yaml phase2

# Alias, identisch zu pipeline
python /app/app/photo_workflow.py --config /app/config/config.yaml phase12

# Nur Phase 3: Finalisierung und Transfer nach targetfolder
python /app/app/photo_workflow.py --config /app/config/config.yaml phase3

# Phase 3 mit explizitem Ziel
python /app/app/photo_workflow.py --config /app/config/config.yaml phase3 --folder 2025-11-01 --target /volume1/photo/wirser

# Pipeline mit allen Phasen (phase1 + phase2 + phase3)
python /app/app/photo_workflow.py --config /app/config/config.yaml pipeline

# Family-Cache gezielt neu aufbauen
python /app/app/photo_workflow.py --config /app/config/config.yaml rebuild-family-cache

```


**Konfiguration:**
```yaml
pipeline:
  phases:
    - phase1
    - phase2
    # - phase3  # Optional: Transfer nach targetfolder
  stop_on_error: true
```

## KI-Assistenz und Betriebsmodi

| Situation | Empfehlung |
|---|---|
| Keine oder wenige auswertbare Daten | `shadow` – Diagnose und Messung |
| Ausreichende Daten, kein bewusster Trust | `assisted` – Vorschläge mit manueller Prüfung |
| Ausreichende Daten + Trust aktiv + Gates erfüllt | `auto_phase1` – automatische Phase 1 |
| Wie oben + Handoff-Gates erfüllt | `auto_phase2` oder `full_auto` |

**Trust-System:**
- **Ziel:** `mode: full_auto` in Config
- **Wirkung ohne Trust:** Fail-closed bei `assisted`
- **Not trusted:** `trust-revoke --reason "..."` sperrt operative Automatik
- **Wiederaufstieg:** Manuelle Validierung + `trust-restore`

## Face-Vorschläge

- Bekannte Gesichter erzeugen Vorschläge in `WORKFLOW_DATA/faces/<slug>/new_faces/`
- Aktivierung nur durch manuelles Verschieben nach `reference/`
- Begrenzung: `max_new_per_batch` (Config)


## Auto-Learn und Personal-Modell

Der KI-Assistent lernt aus manuell als "Keep" markierten Bildern:

- **Auto-Learn-Exporte:** Keep-Bilder werden idempotent nach `samples/personal_training/reference/` exportiert
- **Personal-Modell:** Der Cache wird bei geänderter Referenzmenge im nächsten Lauf neu aufgebaut
- **Kein manuelles Training:** Der alte `train-personal`-CLI-Befehl wurde entfernt; Auto-Learn ist der Standardweg

## AUTO-VALIDATE

Human Reviews werden automatisch validiert:

- **Automatische Validation:** Am Batch-Ende wird geprüft, ob ausreichende menschliche Entscheidungen vorliegen
- **Validation-Dateien:** Ergebnisse unter `WORKFLOW_DATA/runtime/automation/validation/`
- **Kein `validate-reviews`-CLI nötig:** Der alte CLI-Befehl wurde entfernt; AUTO-VALIDATE ist der Standardweg


**Details:** Siehe [`photo-workflow/README.md`](photo-workflow/README.md) und Handbuch.

## Projektstruktur

```text
app/      Python-Fachmodule und CLI
tests/    Automatisierte Prüfungen (Unit, Integration, Security)
config/   Zentrale Konfiguration (config.yaml)
docs/     Ausführliche Dokumentation, Spezifikation, Vertrag
legacy/   Historisches Bash-Skript als Fallback
```

Eine vollständige Modulübersicht mit Kurzbeschreibung findest du in `app/MODULE_OVERVIEW.md`.

# Basic Photo Workflow

Dieses Repository enthält einen konservativen Zwei-Phasen-Workflow für Kamera- und Foto-Batches auf Synology NAS und in Docker-Umgebungen. Das Projekt inventarisiert Eingänge, bereitet eine manuelle Sichtprüfung vor und führt freigegebene Batches erst danach in eine kontrollierte Archiv- und Bereinigungsphase über.

## Einstieg

- [Benutzerhandbuch](photo-workflow/docs/MANUAL_DE.md)
- [Konfiguration](photo-workflow/config/config.yaml)

## Inhalte des Repos

- `synology-photo-workflow/app/` enthält die Python-Fachmodule und die CLI.
- `synology-photo-workflow/scripts/` enthält die Bash-Start- und Vorprüfungsskripte.
- `synology-photo-workflow/tests/` enthält die automatisierten Prüfungen.
- `synology-photo-workflow/docs/` enthält die ausführliche Dokumentation.
- `NAS_EXAMPLE/` zeigt die persistente Zielstruktur für den NAS-Betrieb.

## Was das Projekt macht

Der Workflow trennt Eingang, Review, Freigabe und endgültige Archivierung. Phase 1 erzeugt aus Eingangsbatches prüfbare Ergebnisse, Phase 2 verarbeitet nur manuell freigegebene Batches weiter. Optional können Face- und Referenzfunktionen aktiv werden, solange die Konfiguration, die Modelle und die Abnahme dazu passen.

## Wichtige Hinweise

- Der Repository-Root ist nur der Einstiegspunkt; die operative NAS-Struktur liegt in `NAS_EXAMPLE/`.
- Die aktive Konfiguration ist `photo-workflow/config/config.yaml`.
- Die Shell-Skripte prüfen und starten nur; die fachliche Logik liegt in Python.
- Für die ausführliche Inbetriebnahme und Nutzung nutze das Handbuch.


## Pipeline-Ausführung

Der Workflow kann einzelne Phasen oder eine konfigurierbare Pipeline ausführen.  
Die Pipeline führt die in `config/config.yaml` definierte Reihenfolge aus und ist für zukünftige Erweiterungen – beispielsweise Phase 3 – vorbereitet.

### Konfiguration

```yaml
# -----------------------------------------------------------------------------
# pipeline
# Steuerung der automatischen Ausführung mehrerer Workflow-Phasen.
# -----------------------------------------------------------------------------
pipeline:
  # phases: Reihenfolge der auszuführenden Workflow-Phasen.
  # Mögliche Werte: phase1, phase2, phase3, train-personal, rebuild-family-cache.
  # Auswirkung: Beim Command "pipeline" werden die Phasen in dieser Reihenfolge ausgeführt.
  phases:
    - phase1
    - phase2

  # stop_on_error: Pipeline beim ersten Fehler stoppen.
  # Mögliche Werte: true oder false.
  # Auswirkung: true verhindert die Ausführung nachfolgender Phasen nach einem Fehler.
  # false führt die weiteren konfigurierten Phasen trotz Fehler fort.
  stop_on_error: true
```

### Commands

```bash
# Nur Phase 1 ausführen: Import, Culling, MANUAL_KEEP und Übergabe nach TEMP_IMAGES.
python -m app.photo_workflow --config config/config.yaml phase1

# Nur Phase 2 ausführen: ARW-Archivierung, Review/Rejected-Bereinigung und optionaler Transfer nach TEMP_FINAL.
python -m app.photo_workflow --config config/config.yaml phase2

# Alle in pipeline.phases konfigurierten Phasen nacheinander ausführen.
python -m app.photo_workflow --config config/config.yaml pipeline

# Alias für die konfigurierte Pipeline.
python -m app.photo_workflow --config config/config.yaml phase12
```

### Ablauf

Bei der Standard-Konfiguration wird folgende Reihenfolge ausgeführt:

1. `phase1`: Batch aus `01_TEMP_SD` verarbeiten, Bilder bewerten und nach `02_TEMP_IMAGES` übertragen.
2. `phase2`: ARW-Dateien archivieren, `_Review` und `_Rejected` bereinigen sowie – wenn aktiviert – den Batch nach `04_TEMP_FINAL` verschieben.

### Erweiterung um Phase 3

Sobald Phase 3 implementiert ist, wird sie ausschließlich in der Konfiguration ergänzt:

```yaml
pipeline:
  phases:
    - phase1
    - phase2
    - phase3
```

Bei `stop_on_error: true` wird eine Pipeline nach einem Fehler abgebrochen. Dadurch wird verhindert, dass beispielsweise Phase 2 oder Phase 3 auf einem unvollständig verarbeiteten Batch läuft.
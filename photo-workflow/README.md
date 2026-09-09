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
python -m app.photo_workflow --config config/config.yaml pipeline
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

**Details:** Siehe [`photo-workflow/README.md`](photo-workflow/README.md) und Handbuch.

---

**Stand:** 2026-09-10 (nach A1-Codebereinigung, P7-Container)

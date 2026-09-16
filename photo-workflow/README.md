# Basic Photo Workflow

Dieses Repository enthält einen konservativen Zwei-Phasen-Workflow für Kamera- und Foto-Batches auf Synology NAS und in Docker-Umgebungen.

## Einstieg

- **Ausführliche Dokumentation:** [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)
- **Konfiguration:** [`config/config.yaml`](config/config.yaml)

## Was das Projekt macht

Der Workflow trennt Eingang, Review, Freigabe und endgültige Archivierung:

1. **Phase 1:** Batch aus `01_TEMP_SD` verarbeiten, Bilder bewerten und nach `02_TEMP_IMAGES` übertragen.
2. **Phase 2:** ARW-Dateien archivieren, `_Review` und `_Rejected` bereinigen, optional nach `04_TEMP_FINAL` verschieben.
3. **Phase 3 (optional):** Finalisierte Batches nach targetfolder transferieren, indexieren, Metadaten übertragen.

## Inhalte des Code-Ordners (Repo-Pfad: `photo-workflow/`)

| Pfad | Zweck |
|---|---|
| `app/` | Python-Fachmodule und CLI |
| `tests/` | Automatisierte Prüfungen (Unit, Integration) |
| `config/` | Zentrale Konfiguration (config.yaml) |
| `docs/` | Ausführliche Dokumentation, Spezifikation, Vertrag |
| `legacy/` | Historisches Bash-Skript als Fallback |
| `../NAS_EXAMPLE/` (Repo-Wurzel) | Persistente Zielstruktur für den NAS-Betrieb |

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
- Die aktive Konfiguration ist `config/config.yaml`.
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

## Serienerkennung

- Erkennt Serien automatisch: visuell (Standard), EXIF-Zeit mit transitiver
  Verkettung oder Dateinummern-Folge als Fallback bei fehlendem EXIF
- `max_series_size` teilt übergroße Serien zeitlich sortiert
- Pro Serie entstehen JSON- und Text-Reports; Keywords sind namensbasiert,
  Dry-Run schreibt nichts
- MANUAL_KEEP und Familienschutz gehen vor Serien-Overrides

## Bewertung und Keywords

- `final_score` aus gewichteten Komponenten; `smile_score` ist die 5. Komponente
  mit Gewicht 0.05 (`base_score` dafür von 0.55 auf 0.50 gesenkt, Summe bleibt 1.0)
  und wirkt als Tiebreak (Verschiebung max. ca. 0.02)
- Lächeln-Erkennung ist landmark-basiert (Mundbreite/Augenabstand) und liefert
  `None` ohne Gesicht, bei deaktivierter Config oder im Container
- Keyword `smile:found:true` wird ab `smile_score >= 0.45` gesetzt
  (idempotent, Dry-Run schreibt nichts)
- CLIP-Scoring ist bewusst deaktiviert (`clip_scoring: false`, Container ohne
  torch/transformers)


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
- **Synchronisation (F10):** Der Pool-Status folgt den Dateien beim nächsten
  Cull-Lauf automatisch — Datei in `reference/` gilt als aktiv, fehlende
  Dateien entfallen aus `selection.json`
- **Abschlussbericht:** `pending_review` wird live aus dem Pool gelesen,
  nicht aus dem letzten Lauf-Status



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
- **Policy-Pin:** Validierungen gelten nur für ihre `policy_version` (aktuell
  1.3); Reports älterer Policies zählen nicht für das Gate
- **Gate (fail-closed):** `auto_phase2`/`full_auto` erst ab 3 validierten
  Batches, mindestens 100 ausgewerteten Vorhersagen und jeweils >= 95 %
  Übereinstimmung, Keep- und Reject-Präzision
- **Reject-Regel (F11):** Entscheidet über `final_score` allein; Keep bleibt
  doppelt abgesichert
- **Umbenennungs-Warnung (F12):** Findet AUTO-VALIDATE keine Predictions zur
  Batch-ID, warnt das Log explizit vor Evidenz-Verlust durch umbenannte Ordner

### Benennungsregel für Batch-Ordner (wichtig)

- Die Batch-ID (z. B. `2026-04-24`) entsteht vor der Verarbeitung im
  Phase-1-Rename und bleibt bis zur Validierung unverändert
- Ein sprechender Titel kommt erst im Final-Ordner als Suffix dazu:
  `<batch-id>_<titel>` (z. B. `2026-04-24_Geburtstag-Finn`)
- Ordner nach dem Cull nie umbenennen oder zusammenführen — sonst verliert
  AUTO-VALIDATE die Predictions



**Details:** Siehe [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md).

## Abschlussbericht und Synology-Indexierung

- Der Abschlussbericht endet immer mit einer SSH-Kurzanleitung:
  `sudo synoindex -A /volume1/photo/<ORDNER>` (neu hinzufügen) bzw.
  `sudo synoindex -R /volume1/photo/<ORDNER>` (neu einlesen) — kein Slash
  am Ende des Pfads
- Im NAS-Container läuft die Indexierung automatisch
  (synofoto-bin-index-tool, Details im Handbuch)


## Projektstruktur

```text
app/      Python-Fachmodule und CLI
tests/    Automatisierte Prüfungen (Unit, Integration, Security)
config/   Zentrale Konfiguration (config.yaml)
docs/     Ausführliche Dokumentation, Spezifikation, Vertrag
legacy/   Historisches Bash-Skript als Fallback
```

Eine vollständige Modulübersicht mit Kurzbeschreibung findest du in `app/MODULE_OVERVIEW.md`.

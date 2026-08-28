# Benutzerhandbuch: Photo Workflow v1.2

**Stand:** 2026-08-28  
**Version:** 1.2  
**Geltungsbereich:** Lokale Phase 1 und Phase 2 (Synology-Photos-Transfer optional)

---

## 1. Zweck und Sicherheitsprinzipien

### 1.1 Zielsetzung

Der Photo Workflow automatisiert die Vorsortierung, Bewertung und Archivierung von Foto-Batches auf einem Synology-NAS. Drei gleichrangige Ziele:

1. **Originaldaten schützen** – keine unkontrollierten Änderungen an JPGs oder ARWs.
2. **Manuellen Aufwand reduzieren** – KI-Assistenz für Keep/Review/Reject-Entscheidungen.
3. **Entscheidungsqualität verbessern** – Lernschleife aus menschlichem Feedback.

### 1.2 Abwägungslogik (verbindlich)

Bei Zielkonflikten gilt diese Reihenfolge:

1. **Sicherheit** – keine unkontrollierten Dateiänderungen oder Datenverluste.
2. **Stabilität** – ein fehlerhafter Batch stoppt nicht den gesamten Lauf.
3. **Nutzen** – jede Funktion muss nachweislich besser vorsortieren oder Betriebssicherheit erhöhen.
4. **Einfachheit** – wenige verständliche Optionen, keine technische Doppelstruktur.
5. **Performance** – langsamer, begrenzter Betrieb ist akzeptabel.

### 1.3 Schutzgrenzen

| Datenklasse | Inhalt | Schutzregel |
|---|---|---|
| Originale | Kamera-JPGs und ARWs | Nur im geregelten Phasenablauf veränderbar. Nie still überschreiben oder löschen. |
| Abgeleitete Medien | Crops, ZIPs, Vorschauen | Nur mit Herkunft, Hash und dokumentierter Aktion. |
| Steuerdaten | Manifeste, Zustände, Logs | Schema-validiert, atomar, rekonstruierbar. |
| Modellartefakte | Modellgewichte, Config | Dürfen separat verwaltet werden (keine geschützten Bildinhalte). |

**Wichtig:** Embeddings und Face-Crops werden nur im RAM gehalten, nicht persistent gespeichert.

---

## 2. Installation und Konfiguration

### 2.1 Voraussetzungen

- Python 3.11+
- Docker (optional, für Container-Betrieb)
- ExifTool (für Metadaten)
- NAS mit ausreichendem Speicher

### 2.2 Konfigurationsdatei

Die zentrale Config ist `config/config.yaml`. Wichtige Blöcke:

```yaml
paths:
  base_dir: ../NAS_EXAMPLE
  temp_sd: ../NAS_EXAMPLE/01_TEMP_SD
  temp_images: ../NAS_EXAMPLE/02_TEMP_IMAGES
  temp_done: ../NAS_EXAMPLE/03_TEMP_DONE
  temp_final: ../NAS_EXAMPLE/04_TEMP_FINAL
  workflow_data_dir: ../NAS_EXAMPLE/WORKFLOW_DATA

automation:
  mode: shadow  # off, shadow, assisted, auto_phase1, auto_phase2, full_auto

culling:
  enabled: true
  keep_threshold: 0.65
  reject_threshold: 0.35
```

### 2.3 Umgebungsvariablen (für API-Credentials)

API-Secrets gehören **nicht** in die Config, sondern in Umgebungsvariablen:

```bash
export SYNO_API_KEY="..."
export SYNO_SESSION_TOKEN="..."
```

---

## 3. Verzeichnisstruktur und Datenfluss

### 3.1 Kanonische Arbeitsordner

| Ordner | Zweck |
|---|---|
| `01_TEMP_SD` | Eingang für neue Kamera-Batches. |
| `02_TEMP_IMAGES` | Phase-1-Ergebnis zur manuellen Sichtung. |
| `03_TEMP_DONE` | Manuell freigegebene Batches für Phase 2. |
| `04_TEMP_FINAL` | Lokal finalisierte Batches (nach Phase 2). |
| `00_TEMP_ERROR` | Quarantäne für fehlerhafte Batches. |
| `WORKFLOW_DATA` | States, Logs, Modelle, Referenzpools. |
| `MANUAL_KEEP/inbox` | Extern ausgewählte Vergleichsbilder. |
| `MANUAL_KEEP/used` | Bereits zugeordnete Manual-Keep-Quellen. |

### 3.2 Batch-Struktur

Ein Batch enthält nach Phase 1:

```text
<BATCH_NAME>/
  ARW/           # Ausgelagerte ARW-Dateien
  SAVE/          # JPG-Archiv und Scores
  Review/        # Zur Prüfung vorgemerkte Bilder
  Rejected/      # Abgelehnte Bilder
  *.JPG          # Aktive Bilder (im Hauptordner)
```

### 3.3 Datenfluss

```text
01_TEMP_SD
  -> Phase 1 (Analyse, Scoring, Metadaten)
  -> 02_TEMP_IMAGES
  -> manuelle Sichtung
  -> 03_TEMP_DONE (manueller Move oder automatic_handoff)
  -> Phase 2 (Archivierung, Bereinigung)
  -> 04_TEMP_FINAL
  -> (optional) Phase 3 (Transfer zu Synology Photos)
```

---

## 4. Phase 1: Analyse, Scoring und menschliche Sichtung

### 4.1 Ablauf

1. **Stabilitätsprüfung** – Batch muss größen- und hashstabil sein.
2. **Datumsnormalisierung** – Aufnahmedatum aus Metadaten ermitteln.
3. **ARW-Auslagerung** – Alle ARWs nach `ARW/` verschieben.
4. **JPG-Validierung** – Lesbarkeit und Integrität prüfen.
5. **Scoring** – Technische und KI-basierte Scores berechnen.
6. **Metadaten schreiben** – Ratings, Tags, Beschreibungen in JPGs.
7. **Sichtbare Ablage** – Bilder in Hauptordner, Review oder Rejected.
8. **State-Update** – `phase1_completed` setzen.

### 4.2 Score-Komponenten

| Score | Zweck | Bereich |
|---|---|---|
| `base_score` | Technische Bewertung (Schärfe, Belichtung, Ästhetik) | 0.0–1.0 |
| `personal_score` | Persönlicher Geschmack (CLIP, Referenzbilder) | 0.0–1.0 oder None |
| `eye_score` | Offene Augen (ONNX-Modell) | 0.0–1.0 oder None |
| `family_score` | Bekannte Gesichter (Referenzpools) | 0.0–1.0 oder None |

**Gesamtscore:** Gewichtete Kombination (Config: `culling.component_weights`).

### 4.3 Entscheidungslogik

| Bedingung | Entscheidung |
|---|---|
| `score >= keep_threshold` | `keep` (Hauptordner) |
| `reject_threshold < score < keep_threshold` | `review` (Review-Ordner) |
| `score <= reject_threshold` | `reject` (Rejected-Ordner) |

**Ausnahmen:**
- `manual_keep` erzwingt `keep`.
- `family_score` kann zu `review` statt `reject` führen (Schutzregel).
- `analysis_error` blockiert automatische Entscheidung.

### 4.4 State-Übergänge

```text
phase1_started -> phase1_moving -> phase1_completed
```

---

## 5. Phase 2: Freigabe, Bereinigung und Finalisierung

### 5.1 Voraussetzungen

- Phase 1 erfolgreich abgeschlossen (`phase1_completed`).
- Manuelle Freigabe (Move nach `03_TEMP_DONE`) oder `automatic_handoff`.

### 5.2 Ablauf

1. **State-Update** – `phase2_started` setzen.
2. **Review/Rejected bereinigen** – Keep-Dateien nach `temp_done`, Rejects nach `temp_error`.
3. **Bereinigung verifizieren** – Ordner müssen leer sein.
4. **State-Update** – `phase2_completed` setzen.
5. **Move nach `temp_final`** – (nur bei `full_auto` und aktivierter Option).

### 5.3 Move-Logik (98AP-Vertrag)

Ein `move` wird als `copy → verify → source removal` implementiert:

- **copy:** Batch wird zuerst kopiert (shutil.move verwendet intern copy2).
- **verify:** Ziel wird nach dem Move validiert (Dateiliste, Größe).
- **source removal:** Quelle wird nach erfolgreichem Move entfernt.

### 5.4 State-Übergänge

```text
phase1_completed -> phase2_started -> phase2_completed
```

---

## 6. Phase 3: Transfer und Resume (aktueller Status)

### 6.1 Verfügbarkeit

- CLI-Befehl `phase3` vorhanden.
- Implementierung: TODO (Grundgerüst in `phase3_transfer.py`, `phase3_resume.py`).

### 6.2 Geplanter Ablauf

1. **Transfer** – Batch von `04_TEMP_FINAL` nach `target_folder` (Synology-Photos-Zielpfad).
2. **Index-Resolution** – Warten auf Synology-Photos-Indexierung.
3. **Metadaten übertragen** – Ratings, Tags, Personen (nur lokale, bekannte Personen).
4. **Resume** – Bei Timeout oder Fehler kontrolliert fortsetzen.

### 6.3 Schutzgrenzen

- Keine unbekannten Gesichter übertragen.
- Keine Embeddings oder Face-Crops persistent speichern.
- API-Secrets nur über Umgebungsvariablen.

---

## 7. KI-Modelle und Score-Logik

### 7.1 Technische Bewertung (`base_score`)

- **Schärfe:** Kantenvarianz.
- **Belichtung:** Clipping-Analyse.
- **Ästhetik:** Kontrast, Sättigung, Bildbalance.

### 7.2 Persönlicher Geschmack (`personal_score`)

- **CLIP-Modell:** Lokales Transformers-Modell (kein Download).
- **Referenzbilder:** `WORKFLOW_DATA/samples/personal_training/reference`.
- **Training:** Automatisch bei Referenzänderung (Config: `personal_scoring.auto_train_on_change`).

### 7.3 Gesichtserkennung (`family_score`)

- **Referenzpools:** `WORKFLOW_DATA/faces/<slug>/reference`.
- **Face-Crops:** Automatisch in `new_faces/`, manuell nach `reference/` aktivieren.
- **Embeddings:** Nur im RAM, nicht persistent.

### 7.4 Serienerkennung

- **Gruppierung:** Aufnahmezeit, Bild-Embedding, Dateinamenlogik.
- **Best-Bild:** `series_best`-Flag, Aufwertung um max. eine Klasse.
- **Nicht-Best:** Abwertung oder Review.

---

## 8. Manual Keep und Referenzpools

### 8.1 Manual Keep

- **inbox:** Extern ausgewählte Vergleichsbilder (z. B. per WhatsApp).
- **used:** Bereits zugeordnete Quellen.
- **Logik:** Feature-Vektor-basiertes Matching (nicht Dateiname).
- **Wirkung:** Erzwingt `keep` für das Original.

### 8.2 Referenzpools

| Pool | Pfad | Zweck |
|---|---|---|
| `aesthetic_reference` | `WORKFLOW_DATA/samples/aesthetic_reference` | Stilprofil für `aesthetic_reference_score`. |
| `personal_training` | `WORKFLOW_DATA/samples/personal_training` | Persönliche Lieblingsbilder für `personal_score`. |
| `faces/<slug>` | `WORKFLOW_DATA/faces/<slug>` | Bekannte Personen für `family_score`. |

### 8.3 Pool-Verwaltung

- **`selection.json`:** Einzige Wahrheit für aktive Referenzen.
- **Kapazitätsgrenzen:** `max_active`, `min_active`, `max_new`.
- **Rebuild:** Bei Referenzänderung automatisch (Config: `auto_rebuild_on_active_change`).

---

## 9. Konfiguration (wichtigste Variablen)

### 9.1 Pfade

```yaml
paths:
  base_dir: ../NAS_EXAMPLE
  temp_sd: ../NAS_EXAMPLE/01_TEMP_SD
  temp_images: ../NAS_EXAMPLE/02_TEMP_IMAGES
  temp_done: ../NAS_EXAMPLE/03_TEMP_DONE
  temp_final: ../NAS_EXAMPLE/04_TEMP_FINAL
  workflow_data_dir: ../NAS_EXAMPLE/WORKFLOW_DATA
```

### 9.2 Automation

```yaml
automation:
  mode: shadow  # off, shadow, assisted, auto_phase1, auto_phase2, full_auto
  keep_score_min: 0.90
  reject_score_max: 0.15
  min_evaluated_batches: 10
  min_overall_agreement: 0.85
```

### 9.3 Culling

```yaml
culling:
  enabled: true
  keep_threshold: 0.65
  reject_threshold: 0.35
  component_weights:
    base_score: 0.55
    eye_score: 0.10
    aesthetic_reference_score: 0.10
    personal_score: 0.10
    family_score: 0.15
```

### 9.4 Phase 2

```yaml
phase2:
  cleanup_review_rejected: true
  move_to_temp_final: true  # nur bei full_auto
  dry_run: false
```

---

## 10. Reports, Zustände und Fehlerbehandlung

### 10.1 Reports

- **JSON-Summary:** `WORKFLOW_DATA/runtime/run_summaries/<timestamp>.json`.
- **CSV-Scores:** `SAVE/culling_scores.csv` im Batch.
- **Logs:** `WORKFLOW_DATA/runtime/logs/process.log`, `error.log`.

### 10.2 Zustände

| Zustand | Bedeutung |
|---|---|
| `phase1_started` | Phase 1 begonnen. |
| `phase1_moving` | Batch wird nach `temp_images` verschoben. |
| `phase1_completed` | Phase 1 erfolgreich abgeschlossen. |
| `phase2_started` | Phase 2 begonnen. |
| `phase2_completed` | Phase 2 erfolgreich abgeschlossen. |
| `quarantined` | Batch in Quarantäne (Fehler). |
| `review_state_invalid` | Blockierender Fehler (ARW-Aktion verboten). |

### 10.3 Fehlerbehandlung

- **`analysis_error`:** Bild nicht lesbar – keine automatische Entscheidung.
- **`review_state_invalid`:** Widersprüchliche Ordnerstruktur – keine ARW-Aktion.
- **Lock-Konflikt:** Paralleler Lauf blockiert – warten oder Lock manuell entfernen.
- **Pause/Resume:** Bei Zeit- oder Mengenlimit kontrolliert pausieren.

---

## 11. Empfohlene Betriebsabläufe

### 11.1 Manueller Betrieb (shadow/assisted)

```bash
# Neue Batches in 01_TEMP_SD ablegen
# Workflow starten
./run_photo_workflow.sh

# Phase-1-Ergebnis in 02_TEMP_IMAGES sichten
# Bilder bei Bedarf korrigieren (Keep/Review/Reject)
# Batch nach 03_TEMP_DONE verschieben

# Workflow erneut starten (Phase 2)
./run_photo_workflow.sh
```

### 11.2 Automatischer Betrieb (auto_phase2/full_auto)

```bash
# Config setzen:
# automation.mode: auto_phase2 oder full_auto
# automation.fullauto_gate.auto_execute: true (nach Readiness-Prüfung)

# Workflow starten
./run_photo_workflow.sh

# Batches werden automatisch durch Phase 1 und Phase 2 verarbeitet
# Ergebnisse in 04_TEMP_FINAL (bei full_auto)
```

### 11.3 Fehlerfälle

- **Batch in `00_TEMP_ERROR`:** Log prüfen, manuell korrigieren, erneut starten.
- **Lock-Konflikt:** `WORKFLOW_DATA/runtime/locks/` prüfen, verwaiste Locks entfernen.
- **State-Inkonsistenz:** `WORKFLOW_DATA/runtime/state/<batch_id>.json` prüfen, manuell korrigieren.

---

## 12. Was aktuell nicht automatisch ausgeführt wird

- **Phase 3:** CLI-Befehl vorhanden, Implementierung TODO.
- **Synology-Photos-Transfer:** Nicht Bestandteil von v1.2.
- **API-Integration:** Nicht Bestandteil von v1.2.

---

## Anhang A: CLI-Befehle

```bash
# Phase 1
python -m app.photo_workflow --config config/config.yaml phase1

# Phase 2
python -m app.photo_workflow --config config/config.yaml phase2

# Pipeline (Phase 1 + Phase 2)
python -m app.photo_workflow --config config/config.yaml pipeline

# Phase 3 (TODO)
python -m app.photo_workflow --config config/config.yaml phase3

# Menschliche Entscheidung nachtragen
python -m app.photo_workflow --config config/config.yaml review-decision --batch <BATCH_ID> --image <IMAGE> --decision keep

# Readiness-Report
python -m app.photo_workflow --config config/config.yaml readiness-report
```

---

## Anhang B: Zustandsdateien

| Datei | Zweck |
|---|---|
| `WORKFLOW_DATA/runtime/state/<batch_id>.json` | Batch-Zustand (Phase 1, Phase 2). |
| `WORKFLOW_DATA/runtime/state/<batch_id>.handoff.json` | Automatic-Handoff-State. |
| `WORKFLOW_DATA/runtime/run_summaries/*.json` | Laufzusammenfassungen. |
| `WORKFLOW_DATA/runtime/calibration/batches/*.json` | Menschliche Entscheidungen (Kalibrierung). |

---

## Anhang C: Kontakt und Support

- **Repo:** `MaiTaiMa/photo-workflow`
- **Branch:** `release/v1.2`
- **Spec:** `docs/spec_v1-2/`
- **Vertrag:** `docs/AUTOMATION_AND_FINALIZATION_CONTRACT_v1-2.md`


---

## Anhang D: Metadaten-Tags und Legacy-Kompatibilität

### D.1 Namespaced Metadaten-Tag-Schema

Culling-Entscheidungen werden optional als Metadaten in die JPG-Dateien geschrieben (Config: `metadata_culling.enabled`). Das Schema nutzt bewusst **namespaced Tags**, damit Synology Photos und andere Systeme sie robust lesen können:

| Namespace | Beispiel | Bedeutung |
|---|---|---|
| `workflow:` | `workflow:ai_cull` | Kennzeichnet KI-Culling-Verarbeitung |
| `decision:` | `decision:keep` | Finale Entscheidung (keep/review/reject) |
| `series:` | `series:id:series_4` | Serienzugehörigkeit und Rang |
| `family:` | `family:match:true` | Familienerkennung-Treffer |
| `person:` | `person:Kind1` | Erkannte Person (nur bekannte Referenzen) |

Zusätzlich können Score-Bereiche als Metadaten geschrieben werden (Config: `metadata_culling.write_score_bands: true`), z. B. `score_band:<component>:<band>`. Die exakten Rohscores bleiben primär in `culling_scores.csv` und den JSON-Reports.

**Wichtig:** Ältere, nicht-namespaced Tag-Namen wie `AI_CULL`, `DECISION_KEEP` oder `SERIES_BEST` sind **nicht mehr aktuell** und kommen im Code nicht vor. Falls du solche Tags in älteren Bildern findest, stammen sie aus einer früheren Projektphase.

### D.2 Legacy-Datumsrekonstruktion

Kameras liefern weiterhin das alte 8-stellige Namensformat (z. B. `20250315`). Der Workflow rekonstruiert daraus im Standardmodus `legacy_bash` das Jahr über ein konfigurierbares Dekaden-Präfix:

```yaml
workflow:
  date_reconstruction:
    mode: legacy_bash
    decade_prefix: "202"
    year_digit_index: 3
```

`decade_prefix: "202"` erzeugt zusammen mit der Jahresziffer an Position `year_digit_index` ein Jahr zwischen 2020 und 2029 (z. B. `20250315` → `2025-03-15`). Für ein neues Jahrzehnt genügt es, `decade_prefix` anzupassen (z. B. auf `"203"`).

Der alternative Modus `full_year` erwartet ein vollständiges vierstelliges Jahr direkt im Ordnernamen (echtes `YYYYMMDD`-Format).

### D.3 Familien-Referenzpfade (verifiziert)

Die tatsächlichen Pfade für die Familien-Gesichtserkennung laut `config.yaml`:

| Config-Feld | Pfad |
|---|---|
| `family_recognition.reference_dir` | `WORKFLOW_DATA/faces` |
| `family_recognition.cache_dir` | `WORKFLOW_DATA/models/family_faces` |

Jede Person hat einen eigenen Unterordner (Slug) unterhalb von `WORKFLOW_DATA/faces/<slug>/reference`. Der Cache unter `WORKFLOW_DATA/models/family_faces` speichert ausschließlich nicht-sensitive Metadaten (Fingerprints, Laufstatus) – **niemals Embeddings oder Face-Crops**.
\n
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
5. **Move nach `temp_final`** – (bei `phase2.move_to_temp_final: true`, unabhängig vom Automationsmodus).

### 5.3 Move-Logik (98AP-Vertrag)

Ein `move` wird als `copy → verify → source removal` implementiert:

- **copy:** Batch wird zuerst kopiert (shutil.move verwendet intern copy2).
- **verify:** Ziel wird nach dem Move validiert (Dateiliste, Größe).
- **source removal:** Quelle wird nach erfolgreichem Move entfernt.



### Merge-Verhalten bei doppelten Ordnern

#### Überblick

Wenn ein Ordner mit gleichem Datum (`JJJJ-MM-DD`) bereits im Zielverzeichnis existiert, wird automatisch ein Merge durchgeführt. Dies gilt für:

- **Handoff** (nach Phase 1): `02_TEMP_IMAGES` → `03_TEMP_DONE`
- **Phase 2**: `03_TEMP_DONE` → `04_TEMP_FINAL`

**Nicht betroffen** ist Phase 1 (`01_TEMP_SD` → `02_TEMP_IMAGES`), hier bleiben exakte Ordnernamen erhalten.

#### Datum-basiertes Merge (Standard: `merge_by_date_prefix: true`)

Standardmäßig werden Ordner mit gleichem Datumsprefix zusammengeführt. **Suffix-Namen haben dabei immer Priorität** (manuell benannte Ordner bleiben erhalten).

**Beispiele:**

| Quelle | Ziel existiert | Merge nach | Begründung |
|--------|---------------|------------|------------|
| `2025-11-02` | `2025-11-02` | `2025-11-02` | Exakter Match |
| `2025-11-02` | `2025-11-02_Urlaub` | `2025-11-02_Urlaub` | Suffix hat Priorität |
| `2025-11-02_Urlaub` | `2025-11-02` | `2025-11-02_Urlaub` | Suffix hat Priorität |
| `2025-11-02_Urlaub` | `2025-11-02_Hochzeit` | `2025-11-02_Hochzeit` | Suffix hat Priorität |
| `2025-11-02` | keiner | `2025-11-02` | Neuer Ordner |

**Beispiel-Ablauf:**

Lauf 1: 2026-01-01 → 03_TEMP_DONE/2026-01-01/ ✅
Lauf 2: 2026-01-01_Urlaub → 03_TEMP_DONE/2026-01-01/ ✅ (Merge nach 2026-01-01_Urlaub wenn existent)

#### Merge-Strategie

| Fall | Aktion |
|------|--------|
| Datei nur in Quelle | Nach Ziel kopieren |
| Datei nur in Ziel | Bleibt unverändert |
| Datei identisch (Name+Größe+mtime) | Überspringen |
| Datei gleiche Größe, unterschiedlicher Inhalt | Neuere überschreibt |
| Datei unterschiedliche Größe | Beide behalten, neuere mit `_NEW` Suffix |

#### Nach Merge: `.MERGE` Datei

Im Zielordner wird eine `.MERGE` Datei erstellt (konsistent zu `.DONE`, `.PROCESSED`):

Merge Log - 2026-09-02 13:00:00
Source: ../03_TEMP_DONE/2026-01-01
Target: ../04_TEMP_FINAL/2026-01-01

copied: 5
overwritten: 2
conflicts: 1
skipped: 10
errors: 0
Conflict Files:

    image_NEW.jpg (neuere Version von image.jpg)
    

#### Vorteile

- ✅ Konsistente Benennung (alle Marker als `.DATEI`)
- ✅ Keine `_MERGE`-Kaskaden (`2026-01-01_MERGE_MERGE`)
- ✅ Merge-Information dokumentiert im Ordner
- ✅ Einfacher zu parsen und zu prüfen
- ✅ Suffix-Namen (manuell) haben Priorität

#### Performance-Optimierung

- Schnelle Vorab-Prüfung (Name + Größe + mtime) bevor SHA256 berechnet wird
- Wenn identisch: Überspringen (kein SHA256 nötig)
- Nur bei Unterschieden: SHA256 berechnen

#### Konfiguration

In `config/config.yaml`:

```yaml
phase2:
  # Standard: true (datum-basiertes Merge aktiviert)
  merge_by_date_prefix: true
```

**Deaktivieren** (exakte Ordnernamen erzwingen):

```yaml
phase2:
  merge_by_date_prefix: false
```


### 5.4 State-Übergänge

```text
phase1_completed -> phase2_started -> phase2_completed
```

---

## 6. Phase 3: Transfer und Resume

### 6.1 Verfügbarkeit

- CLI-Befehl `phase3` implementiert (Transfer-Grundgerüst).
- Implementierung: `run_phase3()` in `app/photo_workflow.py`, `transfer_batch()` in `app/phase3_transfer.py`.
- Album-Upsert und Metadaten-API sind vorbereitet, aber noch nicht vollständig implementiert.

### 6.2 Ablauf

1. **Transfer** – Batch von `04_TEMP_FINAL` nach `target_folder` (Synology-Photos-Zielpfad).
   - Staging im Zielverzeichnis → SHA256-Verifikation → atomarer Rename.
   - Manifest (`finalization_manifest.json`) mit SHA256-Liste wird atomar geschrieben.
2. **Indexing** – Synology-Photos-Indexierung via `synofoto-bin-index-tool` (nur NAS-Docker).
3. **Album-Upsert** – Vorbereitung vorhanden, Implementierung nach Bedarf (via `SYNO.Foto.Browse.Album` API).
4. **Metadaten** – Vorbereitung vorhanden, API-Adapter implementiert, `apply_metadata()` noch nicht vollständig.

### 6.3 MWG-RS-Regionen

Wenn `family_recognition.write_face_regions: true` gesetzt ist, werden erkannte Gesichtsregionen als `XMP-mwg-rs:RegionInfo` geschrieben (Standard, kompatibel zu Lightroom, digiKam, Apple Photos).

- Koordinaten: normalisiert (0.0–1.0), Mittelpunkt der Box.
- `RegionName`: lesbarer Name aus `family_recognition.persons` (Fallback: `id`).
- Idempotenz: identische Regionen werden nicht doppelt geschrieben.

### 6.4 CLI

```bash
# Dry-Run (nur simulieren)
.venv/bin/python -m app.photo_workflow phase3 --folder <batch> --dry-run

# Echter Transfer
.venv/bin/python -m app.photo_workflow phase3 --folder <batch> --target <ziel>
```

### 6.5 Schutzgrenzen

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
  move_to_temp_final: true  # Move nach Phase-2-Cleanup, unabhängig vom Modus
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

- **Phase 3:** Transfer-Grundgerüst implementiert, standardmäßig deaktiviert (`finalization.enabled: false`).
- **Synology-Photos-Transfer:** Implementiert, erfordert `finalization.publish_to_synology_photos.enabled: true`.
- **Album-Upsert:** Vorbereitung vorhanden, erfordert `synology_api.album_upsert: true` und Pilotlauf-Nachweis.
- **API-Integration:** Capability-gated, `apply_metadata()` noch nicht vollständig implementiert.

---

## Anhang A: CLI-Befehle

```bash
# Phase 1
python -m app.photo_workflow --config config/config.yaml phase1

# Phase 2
python -m app.photo_workflow --config config/config.yaml phase2

# Pipeline (Phase 1 + Phase 2)
python -m app.photo_workflow --config config/config.yaml pipeline

# Phase 3 (Dry-Run)
python -m app.photo_workflow --config config/config.yaml phase3 --folder <batch> --dry-run

# Phase 3 (Echter Transfer)
python -m app.photo_workflow --config config/config.yaml phase3 --folder <batch> --target <ziel>

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

## 13. Quick-Start: Erster Start in 5 Schritten

### Schritt 1: Verzeichnisstruktur anlegen

```bash
cd ~/Programme/photo-workflow
mkdir -p NAS_EXAMPLE/{00_TEMP_ERROR,01_TEMP_SD,02_TEMP_IMAGES,03_TEMP_DONE,04_TEMP_FINAL,MANUAL_KEEP/{inbox,used},WORKFLOW_DATA/{faces,models,taste,runtime/{state,logs,quarantine,run_summaries}}}
```

### Schritt 2: Test-Batch vorbereiten

Kopiere 5-10 JPGs (und optional ARWs) in einen neuen Ordner unter `01_TEMP_SD`:

```bash
mkdir -p NAS_EXAMPLE/01_TEMP_SD/2026-08-29_Familienfeier
cp /pfad/zu/test/*.JPG NAS_EXAMPLE/01_TEMP_SD/2026-08-29_Familienfeier/
```

### Schritt 3: Config prüfen

```bash
cat config/config.yaml | head -50
```

Wichtigste Einstellungen für den Start:
- `paths.base_dir`: Muss auf `../NAS_EXAMPLE` zeigen
- `automation.mode`: Auf `shadow` oder `assisted` für den ersten Test
- `culling.enabled`: `true`

### Schritt 4: Ersten Testlauf starten

```bash
docker-compose run --rm photo-workflow pipeline
```

Oder lokal (Python):
```bash
python app/photo_workflow.py --config config/config.yaml pipeline
```

### Schritt 5: Ergebnisse prüfen

- **Phase 1:** Bilder sollten jetzt in `02_TEMP_IMAGES/2026-08-29_Familienfeier/` sein
  - `Review/`: Zur manuellen Prüfung vorgemerkte Bilder
  - `Rejected/`: Automatisch abgelehnte Bilder
  - Hauptordner: Automatisch behaltene Bilder
- **Logs:** `WORKFLOW_DATA/runtime/logs/process.log`

### Nächste Schritte

1. Bilder in `Review/` manuell sichten und nach `03_TEMP_DONE` verschieben
2. Workflow erneut starten (Phase 2)
3. Bei Erfolg: `automation.mode` auf `auto_phase2` oder `full_auto` erhöhen


## 14. Troubleshooting & FAQ

### Häufige Fehler und Lösungen

| Fehler | Ursache | Lösung |
|---|---|---|
| `Permission denied` beim Schreiben | Falsche Dateiberechtigungen | `chown -R $USER:$USER NAS_EXAMPLE/` |
| `Lock conflict` | Paralleler Lauf blockiert | `rm NAS_EXAMPLE/WORKFLOW_DATA/runtime/locks/.script.lock` |
| `No images found in batch` | Batch enthält nur ARWs oder ist leer | Mindestens 1 JPG im Hauptordner erforderlich |
| `Phase 2 startet nicht` | Batch nicht nach `03_TEMP_DONE` verschoben | Manueller Move erforderlich (außer bei `automatic_handoff`) |
| `CLIP-Modell nicht gefunden` | `models/clip/`-Ordner fehlt | Config: `clip_scoring.enabled: false` setzen |
| `Face-Erkennung liefert keine Treffer` | Keine Referenzbilder in `faces/<slug>/reference/` | Mindestens 1 Face-Crop pro Person als Referenz hinzufügen |

### Performance-Optimierung

**Für große Batches (>1000 Bilder):**

1. **Batch-Limit erhöhen** (Config):
```yaml
pipeline:
  max_batches_per_run: 10  # Standard: 3
```

2. **CLIP-Scoring deaktivieren** (schneller, aber weniger präzise):
```yaml
clip_scoring:
  enabled: false
```

3. **Parallelisierung** (nur auf Multi-Core-NAS):
```bash
# Mehrere Instanzen mit unterschiedlichen Batches
docker-compose run --rm photo-workflow phase1 --folder 01_TEMP_SD/Batch_A &
docker-compose run --rm photo-workflow phase1 --folder 01_TEMP_SD/Batch_B &
wait
```

### Backup & Recovery

**Wichtige Daten für Backup:**

```bash
# States (für Resume nach Absturz)
tar -czf workflow-states-backup.tar.gz NAS_EXAMPLE/WORKFLOW_DATA/runtime/state/

# Referenzpools (Faces, Geschmack)
tar -czf workflow-pools-backup.tar.gz NAS_EXAMPLE/WORKFLOW_DATA/faces/ NAS_EXAMPLE/WORKFLOW_DATA/models/taste/

# Logs & Reports (Audit)
tar -czf workflow-logs-backup.tar.gz NAS_EXAMPLE/WORKFLOW_DATA/runtime/logs/ NAS_EXAMPLE/WORKFLOW_DATA/runtime/run_summaries/
```

**Recovery nach System-Crash:**

1. Backup zurückspielen
2. Lock-Dateien entfernen:
```bash
rm NAS_EXAMPLE/WORKFLOW_DATA/runtime/locks/*.lock
```
3. Workflow mit `pipeline` neu starten – er setzt automatisch an der letzten sicheren State-Datei fort


## Anhang E: Beispiel-Workflows

### E.1: Manueller Betrieb (`shadow`-Mode)

**Szenario:** Vollständige Kontrolle, KI nur als Vorschlag.

**Config:**
```yaml
automation:
  mode: shadow
culling:
  enabled: true
```

**Ablauf:**
1. Batch in `01_TEMP_SD` ablegen
2. `pipeline` starten → Phase 1 läuft, aber ändert **nichts** an Dateien
3. Reports prüfen: `WORKFLOW_DATA/runtime/run_summaries/`
4. Bei Zustimmung: Batch manuell nach `03_TEMP_DONE` verschieben
5. `pipeline` erneut → Phase 2 archiviert

**Vorteil:** Maximale Sicherheit, keine automatischen Änderungen.
**Nachteil:** Höchster manueller Aufwand.

---

### E.2: Assistierter Betrieb (`assisted`-Mode)

**Szenario:** KI trifft Vorentscheidungen, Mensch bestätigt.

**Config:**
```yaml
automation:
  mode: assisted
culling:
  keep_threshold: 0.65
  reject_threshold: 0.35
```

**Ablauf:**
1. Batch in `01_TEMP_SD` ablegen
2. `pipeline` starten → Phase 1 sortiert automatisch in `Keep/Review/Rejected`
3. Nur `Review/`-Bilder manuell sichten
4. Batch nach `03_TEMP_DONE` verschieben
5. `pipeline` erneut → Phase 2

**Vorteil:** Deutlich weniger manueller Aufwand als `shadow`.
**Nachteil:** KI-Entscheidungen können falsch sein (Review-Ordner prüfen!).

---

### E.3: Vollautomatischer Betrieb (`full_auto`-Mode)

**Szenario:** Komplette Automatisierung nach erfolgreicher Readiness-Prüfung.

**Config:**
```yaml
automation:
  mode: full_auto
  policy_version: "1.2"
  fullauto_gate:
    auto_execute: true
phase2:
  cleanup_review_rejected: true
  move_to_temp_final: true
```

**Ablauf:**
1. Batch in `01_TEMP_SD` ablegen
2. `pipeline` starten → Phase 1 + Phase 2 laufen automatisch durch
3. Ergebnis in `04_TEMP_FINAL` prüfen
4. Bei `publish_to_synology_photos: true`: Automatische Veröffent-lichung

**Voraussetzungen:**
- `automation_readiness` muss `ready` melden (vorherige erfolgreiche Läufe)
- Kein aktiver Trust-Override
- Keine Manuel-Keep-Konflikte

**Vorteil:** Minimaler manueller Aufwand.
**Nachteil:** Höheres Risiko – nur nach ausführlichem Testing verwenden!

---

### E.4: Hybrid-Betrieb (Auto-Phase1, Manuell-Phase2)

**Szenario:** Phase 1 automatisch, Phase 2 manuell bestätigt.

**Config:**
```yaml
automation:
  mode: auto_phase1
phase2:
  cleanup_review_rejected: true
  move_to_temp_final: false  # Manueller Move erforderlich
```

**Ablauf:**
1. Batch in `01_TEMP_SD` ablegen
2. `pipeline` starten → Phase 1 automatisch
3. Ergebnisse in `02_TEMP_IMAGES` prüfen
4. Bei OK: Batch nach `03_TEMP_DONE` verschieben
5. `pipeline` erneut → Phase 2 (manuell getriggert)

**Vorteil:** Gute Balance aus Automatisierung und Kontrolle.
**Empfohlen für:** Produktiven Einstieg nach Testphase.

---

**Hinweis:** Alle Beispiele basieren auf der aktuellen Implementierung (v1.2). Bei Änderungen der Config-Schema-Version können Details abweichen – immer zuerst mit Test-Batches prüfen!

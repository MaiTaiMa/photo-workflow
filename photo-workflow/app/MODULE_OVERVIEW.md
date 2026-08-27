# Modul-Übersicht: app/

**Stand:** 2026-08-27  
**Version:** 1.0  
**Zweck:** Übersicht über alle Module in `app/` nach Verantwortung gruppiert.

Diese Datei dokumentiert die fachliche Trennung der 77 Module (Abschnitt 6.1.3). Keine Zusammenlegung vorgesehen—jedes Modul hat eine klare, eigenständige Verantwortung.

---

## Cluster: Automation & Contract (11 Module)

| Modul | Verantwortung |
|---|---|
| `automation_config.py` | Config-Loading, YAML-Validierung, Secrets-frei |
| `automation_contract.py` | Prediction-Record-Schema, Validierung (`build_prediction_record()`, `validate_prediction_record()`) |
| `automation_store.py` | Persistenz von Prediction-Batches (JSON, atomar) |
| `automation_readiness.py` | Readiness-Aggregation, Fullauto-Gate (`evaluate_fullauto_thresholds()`) |
| `automation_metrics.py` | Metriken aus Batches aggregieren (JSON-Report) |
| `auto_decision.py` | KI-Prediction (`predict_decision()`: keep/review/reject) |
| `auto_phase1_gate.py` | Gate-Prüfung vor automatischer Phase-1-Entscheidung |
| `automatic_handoff_gate.py` | Gate-Prüfung vor Handoff nach `03_TEMP_DONE` |
| `handoff_state.py` | Handoff-State persistieren (JSON, hash-verkettet) |
| `batch_identity.py` | Batch-ID, kanonische Pfadprüfung |
| `batch_layout.py` | Batch-Ordnerstruktur, ARW-Schutz |

---

## Cluster: Phase 1 – Analyse, Scoring, Prediction (16 Module)

| Modul | Verantwortung |
|---|---|
| `phase1_analysis.py` | Row-Analyse, Scores kombinieren (`combine_scores()`, `analyze_rows()`) |
| `phase1_analysis_builder.py` | Persistierbare Analysis-Rows bauen |
| `phase1_analysis_plan.py` | Analyseplan, Workunits, Hash-Verkettung (`Phase1AnalysisPlanStore`) |
| `phase1_execution_initializer.py` | Execution-Plan initialisieren |
| `phase1_workunit_runner.py` | Workunits einzeln ausführen |
| `phase1_workunit_executor.py` | Einzelne Workunit ausführen |
| `phase1_manifest.py` | Batch-Manifest (JSON, hash-verkettet) |
| `phase1_runtime_budget_state.py` | Runtime-Budget-State (Pause, Zeitlimit) |
| `phase1_state.py` | Phase-1-State (JSON, hash-verkettet) |
| `execution_plan.py` | Execution-Plan-Schema, Workunit-Definition |
| `workunit_state.py` | Workunit-State (JSON, hash-verkettet) |
| `aesthetic.py` | Base-Score, Personal-Model, Generic-Score (`base_score_components()`) |
| `personal_score_cache.py` | CLIP-Personal-Score Cache (JSON) |
| `clip_scorer.py` | CLIP-Embeddings, Similarity (`CLIPScorer`) |
| `family_recognition.py` | Face-Erkennung, Family-Score (`detect_family_members()`) |
| `manual_keep.py` | MANUAL_KEEP-Erkennung, Move nach `used/` |

---

## Cluster: Phase 2 – Cleanup, Finalisierung (4 Module)

| Modul | Verantwortung |
|---|---|
| `phase2_contract.py` | Cleanup-Logik, Move nach `04_TEMP_FINAL` (`cleanup_review_rejected()`, `move_to_temp_final()`) |
| `archive_contract.py` | Archiv-Vertrag (JPG-Zip, ARW-Zip) |
| `archive_verification.py` | Archiv-Verifikation (SHA256, Vollständigkeit) |
| `inventory.py` | Bestandsaufnahme, JSON-Report |

---

## Cluster: Faces & Family (7 Module in `app/faces/`)

| Modul | Verantwortung |
|---|---|
| `faces/reference_pool.py` | Referenzpool-Verwaltung (JSON, Kapazitätsgrenzen) |
| `faces/pool_rebuild.py` | Rebuild-Logik (neue Gesichter hinzufügen) |
| `faces/__init__.py` | Package-Init |
| *(weitere 4 Module)* | *(siehe `app/faces/`)* |

---

## Cluster: Review & Trust (7 Module)

| Modul | Verantwortung |
|---|---|
| `review_decision.py` | Menschliche Entscheidungen persistieren (`record_human_decision()`) |
| `review_validation.py` | Prediction ↔ Human-Decision vergleichen (`validate_batch_predictions()`) |
| `review_contract.py` | Review-Contract (JSON-Schema) |
| `human_review_contract.py` | Human-Review-Contract (JSON-Schema) |
| `human_review_store.py` | Human-Review-Store (JSON, pro Batch) |
| `trust_override.py` | Manueller Vertrauens-Widerruf (`TrustOverrideStore`) |
| `validate_reviews.py` | Review-Validierung (Vollständigkeit, Konsistenz) |

---

## Cluster: State & Recovery (7 Module)

| Modul | Verantwortung |
|---|---|
| `state_store.py` | Allgemeiner State-Store (JSON, hash-verkettet) |
| `state_validation.py` | State-Validierung (Schema, Hash) |
| `pause_checkpoint.py` | Pause/Resume Checkpoints (`PauseCheckpointStore`) |
| `recovery.py` | Recovery nach Fehlern (Quarantäne, Log) |
| `runtime_budget.py` | Runtime-Budget (Zeitlimit, Pausen) |
| `runtime_control.py` | Runtime-Control (Signal-Handler, Graceful-Stop) |
| `workflow_locks.py` | Workflow-Locks (PID, atomar) |

---

## Cluster: Scoring & Training (5 Module)

| Modul | Verantwortung |
|---|---|
| `training.py` | Modell-Training, Export (`train_from_directory()`) |
| `config_schema.py` | Config-Schema (Pydantic, Validierung) |
| `strict_config.py` | Strikte Config (keine unbekannten Schlüssel) |
| `score_integration.py` | Score-Integration (gewichtet, kombiniert) |
| `metadata_rating.py` | Metadaten-Rating (XMP, JSON) |

---

## Cluster: Serien & Selection (8 Module)

| Modul | Verantwortung |
|---|---|
| `series_culling.py` | Serien-basierte Vorsortierung (`apply_series_culling()`) |
| `series_detection.py` | Serien-Erkennung (EXIF, Zeitfenster) |
| `series_report.py` | Serien-Reports (JSON, Text) |
| `selection_pool.py` | Selection-Pool (JSON, Hash) |
| `selection_schema.py` | Selection-Schema (kanonisch, Hash) |
| `best_of_selection.py` | Best-of-Selection (Top-N pro Serie) |
| `pool_limits.py` | Pool-Limits (Kapazitätsgrenzen) |
| `pool_sorting.py` | Pool-Sorting (Score-basiert) |

---

## Cluster: Metadata & Paths (7 Module)

| Modul | Verantwortung |
|---|---|
| `metadata_writer.py` | XMP/JSON-Metadaten schreiben |
| `metadata_contract.py` | Metadata-Contract (JSON-Schema) |
| `path_security.py` | Pfad-Sicherheit (Traversal-Block, Mount-Check) |
| `runtime_paths.py` | Runtime-Pfade (kanonisch, geprüft) |
| `naming_convention.py` | Namenskonventionen (Batch, Workunit) |
| `idempotent_assignment.py` | Idempotente Zuweisung (Hash, dedupliziert) |
| `lock_manager.py` | Lock-Manager (PID, atomar) |

---

## Cluster: Security & Audit (4 Module)

| Modul | Verantwortung |
|---|---|
| `security_audit.py` | Security-Audit (Logging, Report) |
| `proposal_generator.py` | Proposal-Generator (Vorschläge) |
| `user_actions.py` | User-Actions (Log, Audit) |
| `dry_run.py` | Dry-Run-Modus (keine Seiteneffekte) |

---

## Cluster: Phase 3 – Synology Transfer (3 Module)

| Modul | Verantwortung |
|---|---|
| `phase3_transfer.py` | Synology-Transfer (API, Upload) |
| `phase3_resume.py` | Phase-3-Resume (Checkpoint, Fortsetzung) |
| `synology_photos_adapter.py` | Synology-Photos-Adapter (API-Client) |

---

## Cluster: Entry Point & Orchestration (3 Module)

| Modul | Verantwortung |
|---|---|
| `photo_workflow.py` | Haupt-Entry-Point (CLI, Orchestration) |
| `orchestrator.py` | Orchestration (Batch-Steuerung) |
| `decision_contract.py` | Decision-Contract (JSON-Schema) |

---

## Gesamtanzahl

- **app/*.py:** 77 Module
- **app/faces/*.py:** 7 Module
- **app/scoring/*.py:** 1 Module (falls vorhanden)
- **Gesamt:** 85 Module

**Fachliche Trennung:** Jedes Modul hat eine klare, eigenständige Verantwortung. Keine Zusammenlegung vorgesehen (Abschnitt 6.1.3 erfüllt).

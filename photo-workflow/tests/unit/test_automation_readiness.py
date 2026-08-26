"""
Skript: tests/unit/test_automation_readiness.py
Zweck: Prüft Readiness-Aggregation und fail-closed Fullauto-Gates.
Autor: Matthias Streser
Erstellt: 2026-08-26
Version: 1.0.0
Requires: pytest, app.automation_readiness, Automation-Teststores

Änderungsprotokoll:
  2026-08-26 | 1.0.0 | Header und Testdokumentation gemäß Implementierungsregeln ergänzt.
"""

from app.automation_readiness import (
    READINESS_POLICY,
    build_readiness_report,
    evaluate_fullauto_thresholds,
    is_fullauto_ready,
)


# -----------------------------------------------------------------------------
# Fixture für minimale, schema-konforme Validation-Report-Payloads.
# Alle Testfälle überschreiben nur die für ihren Vertragsfall relevanten Felder.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall:  report.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def _report(*, policy_version: str = "1.0", **overrides) -> dict:
    report = {
        "schema_version": "1.0",
        "producer_version": "v1.4",
        "policy_version": policy_version,
        "batch_id": "2025-11-02",
        "validated_at": "2026-08-11T00:00:00Z",
        "prediction_count": 0,
        "eligible_predictions": 0,
        "excluded_review_predictions": 0,
        "unreviewed_predictions": 0,
        "evaluated_predictions": 0,
        "matching_predictions": 0,
        "overall_agreement": None,
        "predicted_keep": 0,
        "predicted_reject": 0,
        "reviewed_predicted_keep": 0,
        "reviewed_predicted_reject": 0,
        "confirmed_keep": 0,
        "confirmed_reject": 0,
        "keep_precision": None,
        "reject_precision": None,
        "status": "not_evaluable",
    }
    report.update(overrides)
    return report


# -----------------------------------------------------------------------------
# Kernmetriken: Aggregation wird nach Prediction-Anzahl und nicht nach Batch gewichtet.
# Damit kann ein kleiner Batch keine große, bestätigte Evidenz unzulässig überstimmen.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall: test readiness uses prediction weighted metrics.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_readiness_uses_prediction_weighted_metrics() -> None:
    report = build_readiness_report(
        [
            _report(
                evaluated_predictions=100,
                matching_predictions=90,
                predicted_keep=50,
                confirmed_keep=45,
                predicted_reject=50,
                confirmed_reject=45,
            ),
            _report(
                evaluated_predictions=10,
                matching_predictions=10,
                predicted_keep=5,
                confirmed_keep=5,
                predicted_reject=5,
                confirmed_reject=5,
            ),
        ]
    )

    assert report["overall_agreement"] == 100 / 110
    assert report["keep_precision"] == 50 / 55
    assert report["reject_precision"] == 50 / 55
    assert report["status"] == "not_ready"


# -----------------------------------------------------------------------------
# Testfall: test readiness is not evaluable without evaluated predictions.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_readiness_is_not_evaluable_without_evaluated_predictions() -> None:
    report = build_readiness_report([_report(excluded_review_predictions=3)])

    assert report["status"] == "not_evaluable"
    assert report["overall_agreement"] is None
    assert report["readiness_reasons"] == ["no evaluated predictions are available"]


# -----------------------------------------------------------------------------
# Testfall: test readiness is ready when all policy thresholds are met.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_readiness_is_ready_when_all_policy_thresholds_are_met() -> None:
    count = READINESS_POLICY["minimum_evaluated_predictions"]
    report = build_readiness_report(
        [_report()],
        expected_policy_version="1.0",
    )
    # Re-build with sufficient evidence for the expected policy
    report = build_readiness_report(
        [
            _report(
                evaluated_predictions=count // 3,
                matching_predictions=count // 3,
                predicted_keep=count // 6,
                confirmed_keep=count // 6,
                predicted_reject=count // 6,
                confirmed_reject=count // 6,
            ),
            _report(
                evaluated_predictions=count // 3,
                matching_predictions=count // 3,
                predicted_keep=count // 6,
                confirmed_keep=count // 6,
                predicted_reject=count // 6,
                confirmed_reject=count // 6,
            ),
            _report(
                evaluated_predictions=count - (2 * (count // 3)),
                matching_predictions=count - (2 * (count // 3)),
                predicted_keep=count // 6,
                confirmed_keep=count // 6,
                predicted_reject=count - (5 * (count // 6)),
                confirmed_reject=count - (5 * (count // 6)),
            ),
        ]
    )

    assert report["status"] == "ready"
    assert report["evaluable_batch_count"] == 3
    assert report["evaluated_predictions"] == count


# -----------------------------------------------------------------------------
# Policy-Isolation: Historische oder fremde Policy-Evidenz darf nicht mitgezählt werden.
# Readiness bleibt dadurch an die konkrete, versionierte Automation-Policy gebunden.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall: test readiness filters by expected policy version.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_readiness_filters_by_expected_policy_version() -> None:
    min_preds = READINESS_POLICY["minimum_evaluated_predictions"]  # 100
    min_batches = READINESS_POLICY["minimum_evaluable_batches"]    # 3

    # Drei Batches für Policy 1.0, Summe = 100 evaluierte Predictions
    # Aufteilung: 34 + 33 + 33 = 100
    reports_1 = [
        _report(
            policy_version="1.0",
            evaluated_predictions=34,
            matching_predictions=34,
            predicted_keep=17,
            confirmed_keep=17,
            predicted_reject=17,
            confirmed_reject=17,
        ),
        _report(
            policy_version="1.0",
            evaluated_predictions=33,
            matching_predictions=33,
            predicted_keep=17,
            confirmed_keep=17,
            predicted_reject=16,
            confirmed_reject=16,
        ),
        _report(
            policy_version="1.0",
            evaluated_predictions=33,
            matching_predictions=33,
            predicted_keep=17,
            confirmed_keep=17,
            predicted_reject=16,
            confirmed_reject=16,
        ),
    ]
    # Drei Batches für Policy 2.0, gleiche Aufteilung
    reports_2 = [
        _report(
            policy_version="2.0",
            evaluated_predictions=34,
            matching_predictions=34,
            predicted_keep=17,
            confirmed_keep=17,
            predicted_reject=17,
            confirmed_reject=17,
        ),
        _report(
            policy_version="2.0",
            evaluated_predictions=33,
            matching_predictions=33,
            predicted_keep=17,
            confirmed_keep=17,
            predicted_reject=16,
            confirmed_reject=16,
        ),
        _report(
            policy_version="2.0",
            evaluated_predictions=33,
            matching_predictions=33,
            predicted_keep=17,
            confirmed_keep=17,
            predicted_reject=16,
            confirmed_reject=16,
        ),
    ]

    all_reports = reports_1 + reports_2

    report_1 = build_readiness_report(all_reports, expected_policy_version="1.0")
    report_2 = build_readiness_report(all_reports, expected_policy_version="2.0")
    report_any = build_readiness_report(all_reports, expected_policy_version=None)

    assert report_1["status"] == "ready"
    assert report_1["evaluable_batch_count"] == min_batches
    assert report_1["evaluated_predictions"] == min_preds

    assert report_2["status"] == "ready"
    assert report_2["evaluable_batch_count"] == min_batches
    assert report_2["evaluated_predictions"] == min_preds

    assert report_any["status"] == "ready"
    assert report_any["evaluable_batch_count"] == min_batches * 2
    assert report_any["evaluated_predictions"] == min_preds * 2


# -----------------------------------------------------------------------------
# Integration-Fixture: Persistiert bestätigte Predictions über die echten Store-Verträge.
# Sie erzeugt nur Testdaten im temporären pytest-Pfad und keine Produktivartefakte.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall:  seed ready reports.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def _seed_ready_reports(tmp_path, policy_version: str = "1.0") -> None:
    """Persist three evaluable batches with perfect agreement for one policy."""
    from app.automation_contract import build_prediction_record
    from app.automation_store import write_prediction_batch
    from app.human_review_contract import build_human_review_record
    from app.human_review_store import write_human_review_batch
    from app.review_validation import validate_batch_predictions

    # Drei Batches, Summe = 100 evaluierte Predictions
    batch_specs = [
        ("2025-11-01", 34, 17, 17),
        ("2025-11-02", 33, 17, 16),
        ("2025-11-03", 33, 17, 16),
    ]
    for batch_id, eval_preds, keep_half, reject_half in batch_specs:
        predictions = [
            build_prediction_record(
                producer_version="v1.4",
                batch_id=batch_id,
                image_id=f"keep_{i}.jpg",
                model_version="personal-score-v1",
                policy_version=policy_version,
                predicted_decision="keep",
                prediction_reason="high_confidence_keep",
                personal_score=0.95,
                final_score=0.92,
                predicted_at="2026-08-11T00:00:00Z",
            )
            for i in range(keep_half)
        ] + [
            build_prediction_record(
                producer_version="v1.4",
                batch_id=batch_id,
                image_id=f"reject_{i}.jpg",
                model_version="personal-score-v1",
                policy_version=policy_version,
                predicted_decision="reject",
                prediction_reason="high_confidence_reject",
                personal_score=0.10,
                final_score=0.12,
                predicted_at="2026-08-11T00:00:00Z",
            )
            for i in range(reject_half)
        ]
        write_prediction_batch(tmp_path, batch_id, predictions)

        reviews = [
            build_human_review_record(
                producer_version="v1.4",
                batch_id=batch_id,
                image_id=p["image_id"],
                human_decision=p["predicted_decision"],
                human_decided_at="2026-08-11T00:10:00Z",
            )
            for p in predictions
        ]
        write_human_review_batch(tmp_path, batch_id, reviews)

        # Validation report erzeugen
        validate_batch_predictions(tmp_path, batch_id, "v1.4")


# -----------------------------------------------------------------------------
# Gate-Grundbedingungen: Ein anderer Modus darf niemals Fullauto-Bereitschaft erhalten.
# Der erwartete Rückgabewert bleibt diagnostisch und strikt fail-closed.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall: test fullauto gate rejects wrong mode.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_fullauto_gate_rejects_wrong_mode(tmp_path) -> None:
    _seed_ready_reports(tmp_path, policy_version="1.0")
    config = {
        "automation": {
            "policy_version": "1.0",
            "mode": "assisted",
            "keep_score_min": 0.90,
            "reject_score_max": 0.15,
            "fullauto_gate": {
                "enabled": True,
                "auto_execute": False,
                "fallback_mode": "assisted",
                "min_overall_agreement": 0.95,
                "min_batch_agreement": 0.90,
            },
        }
    }

    is_ready, report = is_fullauto_ready(config, tmp_path)

    assert is_ready is False
    assert report["gate_reason"] == "mode_is_not_fullauto"
    assert report["mode"] == "assisted"


# -----------------------------------------------------------------------------
# Testfall: test fullauto gate rejects missing policy version.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_fullauto_gate_rejects_missing_policy_version(tmp_path) -> None:
    _seed_ready_reports(tmp_path, policy_version="1.0")
    config = {
        "automation": {
            "mode": "fullauto",
            "keep_score_min": 0.90,
            "reject_score_max": 0.15,
        }
    }

    is_ready, report = is_fullauto_ready(config, tmp_path)

    assert is_ready is False
    assert report["gate_reason"] == "policy_version_missing"


# -----------------------------------------------------------------------------
# Testfall: test fullauto gate passes when ready for policy.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_fullauto_gate_passes_when_ready_for_policy(tmp_path) -> None:
    _seed_ready_reports(tmp_path, policy_version="1.0")
    config = {
        "automation": {
            "policy_version": "1.0",
            "mode": "fullauto",
            "keep_score_min": 0.90,
            "reject_score_max": 0.15,
            "fullauto_gate": {
                "enabled": True,
                "auto_execute": False,
                "fallback_mode": "assisted",
                "min_overall_agreement": 0.95,
                "min_batch_agreement": 0.90,
            },
        }
    }

    is_ready, report = is_fullauto_ready(config, tmp_path)

    assert is_ready is True
    assert report["status"] == "ready"
    assert report["expected_policy_version"] == "1.0"


# -----------------------------------------------------------------------------
# Batch-Diagnostik: Der schwächste bestätigte Batch wird separat nachvollziehbar geführt.
# Diese Kennzahl ergänzt die Gesamtübereinstimmung für spätere strenge Gates.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall: test readiness reports per batch agreement.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_readiness_reports_per_batch_agreement() -> None:
    report = build_readiness_report(
        [
            _report(
                batch_id="batch-good",
                evaluated_predictions=100,
                matching_predictions=95,
            ),
            _report(
                batch_id="batch-borderline",
                evaluated_predictions=100,
                matching_predictions=90,
            ),
        ]
    )

    assert report["minimum_batch_agreement"] == 0.90
    assert report["batch_agreements"] == [
        {
            "batch_id": "batch-good",
            "policy_version": "1.0",
            "evaluated_predictions": 100,
            "matching_predictions": 95,
            "agreement": 0.95,
        },
        {
            "batch_id": "batch-borderline",
            "policy_version": "1.0",
            "evaluated_predictions": 100,
            "matching_predictions": 90,
            "agreement": 0.90,
        },
    ]


# -----------------------------------------------------------------------------
# Testfall: test fullauto threshold data detects overall below target.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_fullauto_threshold_data_detects_overall_below_target() -> None:
    report = build_readiness_report(
        [
            _report(
                batch_id="batch-a",
                evaluated_predictions=100,
                matching_predictions=94,
            ),
            _report(
                batch_id="batch-b",
                evaluated_predictions=100,
                matching_predictions=94,
            ),
            _report(
                batch_id="batch-c",
                evaluated_predictions=100,
                matching_predictions=94,
            ),
        ]
    )

    assert report["overall_agreement"] == 0.94
    assert report["minimum_batch_agreement"] == 0.94
    assert report["overall_agreement"] < 0.95


# -----------------------------------------------------------------------------
# Testfall: test fullauto threshold data detects weakest batch.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_fullauto_threshold_data_detects_weakest_batch() -> None:
    report = build_readiness_report(
        [
            _report(
                batch_id="batch-good-a",
                evaluated_predictions=100,
                matching_predictions=100,
            ),
            _report(
                batch_id="batch-good-b",
                evaluated_predictions=100,
                matching_predictions=100,
            ),
            _report(
                batch_id="batch-weak",
                evaluated_predictions=100,
                matching_predictions=89,
            ),
        ]
    )

    assert report["overall_agreement"] == 0.9633333333333334
    assert report["minimum_batch_agreement"] == 0.89
    assert report["overall_agreement"] >= 0.95
    assert report["minimum_batch_agreement"] < 0.90


# -----------------------------------------------------------------------------
# Schwellenprüfung: Vollständige Evidenz muss alle konfigurierten Grenzwerte erfüllen.
# Die Funktion bewertet nur Diagnosewerte und führt keine operative Aktion aus.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall: test evaluate fullauto thresholds accepts ready report.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_evaluate_fullauto_thresholds_accepts_ready_report() -> None:
    allowed, reasons = evaluate_fullauto_thresholds(
        {
            "fullauto_gate": {
                "enabled": True,
                "min_overall_agreement": 0.95,
                "min_batch_agreement": 0.90,
            }
        },
        {
            "overall_agreement": 0.95,
            "minimum_batch_agreement": 0.90,
        },
    )

    assert allowed is True
    assert reasons == []


# -----------------------------------------------------------------------------
# Testfall: test evaluate fullauto thresholds rejects weak overall agreement.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_evaluate_fullauto_thresholds_rejects_weak_overall_agreement() -> None:
    allowed, reasons = evaluate_fullauto_thresholds(
        {
            "fullauto_gate": {
                "enabled": True,
                "min_overall_agreement": 0.95,
                "min_batch_agreement": 0.90,
            }
        },
        {
            "overall_agreement": 0.94,
            "minimum_batch_agreement": 0.94,
        },
    )

    assert allowed is False
    assert reasons == ["fullauto_overall_agreement_below_threshold"]


# -----------------------------------------------------------------------------
# Testfall: test evaluate fullauto thresholds rejects weak batch agreement.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_evaluate_fullauto_thresholds_rejects_weak_batch_agreement() -> None:
    allowed, reasons = evaluate_fullauto_thresholds(
        {
            "fullauto_gate": {
                "enabled": True,
                "min_overall_agreement": 0.95,
                "min_batch_agreement": 0.90,
            }
        },
        {
            "overall_agreement": 0.96,
            "minimum_batch_agreement": 0.89,
        },
    )

    assert allowed is False
    assert reasons == ["fullauto_batch_agreement_below_threshold"]




# -----------------------------------------------------------------------------
# Testfall: test evaluate fullauto thresholds rejects missing gate.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_evaluate_fullauto_thresholds_rejects_missing_gate() -> None:
    allowed, reasons = evaluate_fullauto_thresholds(
        {},
        {
            "overall_agreement": 1.0,
            "minimum_batch_agreement": 1.0,
        },
    )

    assert allowed is False
    assert reasons == ["fullauto_gate_missing"]


# -----------------------------------------------------------------------------
# End-to-End-Gate: Readiness und zusätzliche Schwellen werden gemeinsam fail-closed geprüft.
# Ein einzelner nicht erfüllter Grenzwert verhindert die behauptete Freigabe.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Testfall: test is fullauto ready rejects overall threshold.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_is_fullauto_ready_rejects_overall_threshold(tmp_path) -> None:
    _seed_ready_reports(tmp_path, policy_version="1.0")

    config = {
        "automation": {
            "policy_version": "1.0",
            "mode": "fullauto",
            "fullauto_gate": {
                "enabled": True,
                "min_overall_agreement": 1.01,
                "min_batch_agreement": 0.90,
            },
        }
    }

    is_ready, report = is_fullauto_ready(config, tmp_path)

    assert is_ready is False
    assert report["gate_reason"] == (
        "fullauto_overall_agreement_below_threshold"
    )


# -----------------------------------------------------------------------------
# Testfall: test is fullauto ready rejects batch threshold.
# Prüft den abgegrenzten Readiness- oder Gate-Vertragsfall kontrolliert.
# Die Assertions sichern diagnostisches und fail-closed Verhalten.
# -----------------------------------------------------------------------------

def test_is_fullauto_ready_rejects_batch_threshold(tmp_path) -> None:
    _seed_ready_reports(tmp_path, policy_version="1.0")

    config = {
        "automation": {
            "policy_version": "1.0",
            "mode": "fullauto",
            "fullauto_gate": {
                "enabled": True,
                "min_overall_agreement": 0.95,
                "min_batch_agreement": 1.01,
            },
        }
    }

    is_ready, report = is_fullauto_ready(config, tmp_path)

    assert is_ready is False
    assert report["gate_reason"] == (
        "fullauto_batch_agreement_below_threshold"
    )



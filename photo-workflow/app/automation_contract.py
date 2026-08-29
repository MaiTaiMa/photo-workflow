# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/automation_contract.py
# PURPOSE:     Definiert und validiert versionierte KI-Prognose-Datensätze.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.3.0
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-26 | 1.3.0 | A1: Erweiterte Auditfelder (eye, family, Serie) additiv ergänzt.
#   2026-08-22 | 1.2.0 | C1.2.2: Policy und Prediction-ID verpflichtend gemacht.
#   2026-08-22 | 1.1.0 | C1.2.2: Deterministische Prediction-ID-Hilfsfunktion ergänzt.
# =============================================================================


from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping


PREDICTION_SCHEMA_VERSION = "1.0"
VALID_PREDICTED_DECISIONS = frozenset({"keep", "reject", "review"})
REQUIRED_FIELDS = frozenset({
    "schema_version",
    "producer_version",
    "batch_id",
    "image_id",
    "model_version",
    "policy_version",
    "prediction_id",
    "predicted_decision",
    "prediction_reason",
    "personal_score",
    "final_score",
    "predicted_at",
})


def build_prediction_id(record: Mapping[str, Any]) -> str:
    """Build a deterministic non-sensitive identifier for one prediction."""
    fields = (
        "schema_version",
        "producer_version",
        "batch_id",
        "image_id",
        "model_version",
        "policy_version",
        "predicted_decision",
        "prediction_reason",
        "personal_score",
        "final_score",
        "predicted_at",
    )
    try:
        identity = {field: record[field] for field in fields}
    except KeyError as error:
        raise ValueError(
            f"prediction identity misses required field: {error.args[0]}"
        ) from error

    payload = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_prediction_record(
    *,
    producer_version: str,
    batch_id: str,
    image_id: str,
    model_version: str,
    policy_version: str,
    predicted_decision: str,
    prediction_reason: str,
    personal_score: float | None,
    final_score: float | None,
    predicted_at: str,
    eye_score: float | None = None,
    family_score: float | None = None,
    series_id: str | None = None,
    series_rank: int | None = None,
    series_best: bool | None = None,
    known_person_match_count: int | None = None,
) -> dict[str, Any]:
    """Build and validate one immutable, non-operative prediction record.

    Erweiterte Auditfelder (additiv, rückwärtskompatibel):
    - eye_score: float [0,1] oder None (Spec 4.4)
    - family_score: float [0,1] oder None (Spec 4.5)
    - series_id: string oder None (Spec 4.3)
    - series_rank: int oder None (Spec 4.3)
    - series_best: bool oder None (Spec 4.3)
    - known_person_match_count: int >= 0 oder None (Spec 4.5, zählt nur bekannte Personen)
    """
    record = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "producer_version": producer_version,
        "batch_id": batch_id,
        "image_id": image_id,
        "model_version": model_version,
        "policy_version": policy_version,
        "predicted_decision": predicted_decision,
        "prediction_reason": prediction_reason,
        "personal_score": personal_score,
        "final_score": final_score,
        "predicted_at": predicted_at,
    }
    # Additive erweiterte Auditfelder (Master-Prompt 4.6)
    if eye_score is not None:
        record["eye_score"] = eye_score
    if family_score is not None:
        record["family_score"] = family_score
    if series_id is not None:
        record["series_id"] = series_id
    if series_rank is not None:
        record["series_rank"] = series_rank
    if series_best is not None:
        record["series_best"] = series_best

    # known_person_match_count: zählt ausschließlich bekannte, gepflegte Personen (Spec 4.5)
    # Unbekannte Gesichter dürfen nie gezählt oder protokolliert werden (Master-Prompt 3.4)
    if known_person_match_count is not None:
        record["known_person_match_count"] = known_person_match_count

    record["prediction_id"] = build_prediction_id(record)
    validate_prediction_record(record)
    return record


def validate_prediction_record(record: Mapping[str, Any]) -> None:
    """Raise ValueError when a prediction record violates the contract."""
    missing = REQUIRED_FIELDS.difference(record)
    if missing:
        raise ValueError(f"prediction record misses required fields: {sorted(missing)}")

    if record["schema_version"] != PREDICTION_SCHEMA_VERSION:
        raise ValueError("unsupported prediction schema_version")

    for field in (
        "producer_version",
        "batch_id",
        "image_id",
        "model_version",
        "policy_version",
        "prediction_reason",
    ):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{field} must be a non-empty string")

    decision = record["predicted_decision"]
    if decision not in VALID_PREDICTED_DECISIONS:
        raise ValueError(f"unsupported predicted_decision: {decision}")

    for field in ("personal_score", "final_score"):
        score = record[field]
        if score is not None and (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0.0 <= float(score) <= 1.0
        ):
            raise ValueError(f"{field} must be None or a number between 0.0 and 1.0")

    if decision in {"keep", "reject"} and (
        record["personal_score"] is None or record["final_score"] is None
    ):
        raise ValueError("keep and reject predictions require both scores")

    timestamp = record["predicted_at"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("predicted_at must be a non-empty string")

    # ---------------------------------------------------------------------
    # Erweiterte Auditfelder validieren (additiv, rückwärtskompatibel)
    # ---------------------------------------------------------------------
    if "eye_score" in record:
        val = record["eye_score"]
        if val is not None and (
            isinstance(val, bool)
            or not isinstance(val, (int, float))
            or not 0.0 <= float(val) <= 1.0
        ):
            raise ValueError("eye_score must be None or a number between 0.0 and 1.0")

    if "family_score" in record:
        val = record["family_score"]
        if val is not None and (
            isinstance(val, bool)
            or not isinstance(val, (int, float))
            or not 0.0 <= float(val) <= 1.0
        ):
            raise ValueError("family_score must be None or a number between 0.0 and 1.0")

    if "series_id" in record:
        val = record["series_id"]
        if val is not None and (not isinstance(val, str) or not val.strip()):
            raise ValueError("series_id must be None or a non-empty string")

    if "series_rank" in record:
        val = record["series_rank"]
        if val is not None and (
            isinstance(val, bool) or not isinstance(val, int) or val < 1
        ):
            raise ValueError("series_rank must be None or a positive integer")

    if "series_best" in record:
        val = record["series_best"]
        if val is not None and not isinstance(val, bool):
            raise ValueError("series_best must be None or a boolean")

    # known_person_match_count: int >= 0 oder None
    if "known_person_match_count" in record:
        val = record["known_person_match_count"]
        if val is not None and (not isinstance(val, int) or val < 0):
            raise ValueError("known_person_match_count must be None or a non-negative integer")
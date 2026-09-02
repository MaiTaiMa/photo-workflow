# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/review_decision.py
# PURPOSE:     Erfasst menschliche Keep-/Reject-Entscheidungen fuer bekannte KI-Prognosen.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.automation_store import prediction_batch_path, validate_prediction_batch
from app.human_review_contract import build_human_review_record
from app.human_review_store import (
    human_review_batch_path,
    validate_human_review_batch,
    write_human_review_batch,
)


def record_human_decision(
    *,
    runtime_path: str | Path,
    batch_id: str,
    image_id: str,
    decision: str,
    producer_version: str,
    reason: str | None = None,
) -> tuple[Path, str]:
    """Create or replace one human decision for a predicted image."""
    predictions = _load_prediction_batch(runtime_path, batch_id)
    known_image_ids = {record["image_id"] for record in predictions["predictions"]}
    if image_id not in known_image_ids:
        raise ValueError("image_id is not present in the prediction artifact")

    review_record = build_human_review_record(
        producer_version=producer_version,
        batch_id=batch_id,
        image_id=image_id,
        human_decision=decision,
        human_decided_at=datetime.now(timezone.utc).isoformat(),
        reason=reason,
    )

    target = human_review_batch_path(runtime_path, batch_id)
    reviews = _load_existing_reviews(target)
    previous = {record["image_id"]: record for record in reviews}
    status = "updated" if image_id in previous else "created"
    previous[image_id] = review_record

    target = write_human_review_batch(
        runtime_path,
        batch_id,
        [previous[key] for key in sorted(previous)],
    )
    return target, status


def runtime_path_from_config(config_path: str | Path) -> Path:
    """Resolve the controlled runtime directory from a YAML configuration."""
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("configuration must contain a mapping")
    paths = config.get("paths")
    if not isinstance(paths, dict) or not isinstance(paths.get("base_dir"), str):
        raise ValueError("configuration paths.base_dir is required")
    return Path(paths["base_dir"]) / "WORKFLOW_DATA" / "runtime"


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone review-decision command parser."""
    parser = argparse.ArgumentParser(
        description="Store a human keep/reject decision for a predicted image."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--decision", required=True, choices=("keep", "reject"))
    parser.add_argument("--reason", default=None)
    parser.add_argument("--producer-version", default="v1.4")
    return parser


def main() -> int:
    """Run the standalone review-decision command."""
    args = build_parser().parse_args()
    runtime_path = runtime_path_from_config(args.config)
    target, status = record_human_decision(
        runtime_path=runtime_path,
        batch_id=args.batch,
        image_id=args.image,
        decision=args.decision,
        reason=args.reason,
        producer_version=args.producer_version,
    )
    print(f"[REVIEW] status={status} path={target}")
    return 0


def _load_prediction_batch(runtime_path: str | Path, batch_id: str) -> dict[str, Any]:
    target = prediction_batch_path(runtime_path, batch_id)
    if not target.is_file():
        raise FileNotFoundError(f"prediction artifact does not exist: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_prediction_batch(payload)
    return payload


def _load_existing_reviews(target: Path) -> list[dict[str, Any]]:
    if not target.exists():
        return []
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_human_review_batch(payload)
    return [dict(record) for record in payload["reviews"]]


if __name__ == "__main__":
    pass


def save_human_decisions_from_batch(
    *,
    runtime_path: str | Path,
    batch_id: str,
    producer_version: str,
) -> tuple[dict[str, Any], Path]:
    """
    Liest menschliche Entscheidungen aus einem Batch und speichert sie.
    
    Liest aus 03_TEMP_DONE/<batch_id>/ die Ordner:
    - Hauptordner (ohne Review/Rejected) = keep
    - Review/ = review
    - Rejected/ = reject
    
    Schreibt nach automation/reviews/<batch_id>.json
    """
    from pathlib import Path
    from datetime import datetime, timezone
    import json
    import hashlib
    
    runtime_path = Path(runtime_path)
    base_dir = runtime_path.parent.parent  # ../NAS_EXAMPLE
    temp_done = base_dir / "03_TEMP_DONE" / batch_id
    
    if not temp_done.exists():
        return {"status": "error", "reason": "batch_not_found"}, runtime_path / "automation" / "reviews" / f"{batch_id}.json"
    
    decisions = []
    
    # 1. Hauptordner = keep (nur JPGs, keine ARWs)
    for f in sorted(temp_done.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg"):
            decisions.append({
                "image_id": f.name,
                "human_decision": "keep",
                "reason": "manual_keep",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "producer_version": producer_version,
            })
    
    # 2. Review/ = review
    review_dir = temp_done / "Review"
    if review_dir.exists():
        for f in sorted(review_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg"):
                decisions.append({
                    "image_id": f.name,
                    "human_decision": "review",
                    "reason": "manual_review",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "producer_version": producer_version,
                })
    
    # 3. Rejected/ = reject
    rejected_dir = temp_done / "Rejected"
    if rejected_dir.exists():
        for f in sorted(rejected_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg"):
                decisions.append({
                    "image_id": f.name,
                    "human_decision": "reject",
                    "reason": "manual_reject",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "producer_version": producer_version,
                })
    
    # Payload erstellen
    payload = {
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "producer_version": producer_version,
        "decisions": decisions,
        "decision_count": len(decisions),
    }
    
    # Hash berechnen
    unsigned = dict(payload)
    unsigned.pop("hash", None)
    payload["hash"] = hashlib.sha256(
        json.dumps(unsigned, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    
    # Speichern
    target = runtime_path / "automation" / "reviews" / f"{batch_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return {"status": "ok", "decision_count": len(decisions)}, target

    raise SystemExit(main())
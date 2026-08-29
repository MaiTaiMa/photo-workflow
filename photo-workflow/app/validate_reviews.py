# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/validate_reviews.py
# PURPOSE:     Erstellt einen auswertenden KI-gegen-Mensch-Validierungsbericht je Batch.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import argparse
from pathlib import Path
from typing import Any

import yaml

from app.review_validation import validate_batch_predictions


def runtime_path_from_config(config_path: str | Path) -> Path:
    """Resolve the controlled runtime directory from a YAML configuration."""
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("configuration must contain a mapping")
    paths = config.get("paths")
    if not isinstance(paths, dict) or not isinstance(paths.get("base_dir"), str):
        raise ValueError("configuration paths.base_dir is required")
    return Path(paths["base_dir"]) / "WORKFLOW_DATA" / "runtime"


def validate_reviews(
    *,
    runtime_path: str | Path,
    batch_id: str,
    producer_version: str,
) -> tuple[dict[str, Any], Path]:
    """Create or update the purely evaluative validation report for one batch."""
    return validate_batch_predictions(
        runtime_path=runtime_path,
        batch_id=batch_id,
        producer_version=producer_version,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone validation command parser."""
    parser = argparse.ArgumentParser(
        description="Validate AI predictions against human keep/reject decisions."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--producer-version", default="v1.4")
    return parser


def main() -> int:
    """Run the standalone validation command."""
    args = build_parser().parse_args()
    runtime_path = runtime_path_from_config(args.config)
    report, target = validate_reviews(
        runtime_path=runtime_path,
        batch_id=args.batch,
        producer_version=args.producer_version,
    )
    print(
        f"[VALIDATION] status={report['status']} batch={args.batch} "
        f"evaluated={report['evaluated_predictions']} "
        f"agreement={report['overall_agreement']} "
        f"keep_precision={report['keep_precision']} "
        f"reject_precision={report['reject_precision']} "
        f"path={target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
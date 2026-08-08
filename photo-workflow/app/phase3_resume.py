from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CorrelationRecord:
    relative_path: str
    resolved_item_status: str = "pending"
    metadata_status: str = "pending"
    attempt_count: int = 0
    last_error: str | None = None
    person_slug: str | None = None
    person_assignment_status: str | None = None


def index_resolution_status(elapsed_seconds: float, max_wait_seconds: float) -> str:
    return "timeout" if elapsed_seconds >= max_wait_seconds else "pending"


def write_correlation(path: str | Path, record: CorrelationRecord) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")


def load_correlation(path: str | Path) -> CorrelationRecord:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return CorrelationRecord(**value)

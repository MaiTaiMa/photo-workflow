from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BackendInfo:
    registry_id: str
    adapter_name: str
    model_hash: str
    provider: str
    preprocessing: str
    metric: str
    selection_fingerprint: str

@dataclass(frozen=True)
class FaceMatch:
    person_slug: str | None
    family_score: float | None
    status: str
    distance: float | None = None
    margin: float | None = None

class FaceBackend(Protocol):
    info: BackendInfo
    def embedding(self, image_path: str) -> object: ...


def validate_backend_info(info: BackendInfo) -> None:
    if not all((info.registry_id, info.adapter_name, info.model_hash,
                info.provider, info.preprocessing, info.metric,
                info.selection_fingerprint)):
        raise ValueError("Face backend metadata is incomplete")

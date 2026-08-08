from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesDecision:
    series_id: str
    series_rank: int
    series_size: int
    series_best: bool
    margin_to_best: float | None

    def validate(self) -> None:
        if not self.series_id:
            raise ValueError("series_id is required")
        if self.series_rank < 1 or self.series_size < 1:
            raise ValueError("series rank and size must be positive")
        if self.series_rank > self.series_size:
            raise ValueError("series_rank exceeds series_size")
        if self.series_best != (self.series_rank == 1):
            raise ValueError("series_best must match rank 1")


@dataclass(frozen=True)
class ManualKeepDecision:
    manual_keep: bool | None
    manual_keep_match: str | None
    verification_score: float | None = None

    def validate(self) -> None:
        if self.manual_keep is True and self.manual_keep_match != "matched":
            raise ValueError("manual keep requires a matched result")
        if self.manual_keep is not True and self.manual_keep_match == "matched":
            raise ValueError("matched manual keep must set manual_keep=true")
        if self.verification_score is not None and not 0.0 <= self.verification_score <= 1.0:
            raise ValueError("verification_score must be in [0, 1]")


def apply_manual_keep(row: dict, decision: ManualKeepDecision) -> dict:
    decision.validate()
    result = dict(row)
    result["manual_keep"] = decision.manual_keep
    result["manual_keep_match"] = decision.manual_keep_match
    if decision.manual_keep is True:
        result["decision"] = "keep"
        result["decision_reason"] = "manual_keep_match"
    return result

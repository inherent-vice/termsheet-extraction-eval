"""Core metrics over ComparisonResult sequences.

The proprietary version exposes 22 metrics across categories; this public
version keeps the five that carry the most information in production:

- ``match_rate`` — (MATCH + BOTH_NULL) / SCORE_TARGETS
- ``true_match_rate`` — MATCH / (MATCH + MISMATCH + OCR_NULL + NOT_FOUND)
- ``ocr_null_rate`` — OCR_NULL / SCORE_TARGETS
- ``mismatch_rate`` — MISMATCH / SCORE_TARGETS
- ``coverage`` — SCORE_TARGETS / total fields (how much was meaningful)

These five are sufficient to triangulate any single failure mode; adding
more metrics should be justified by a specific question they answer.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from termsheet_eval.compare.result import (
    ComparisonResult,
    FieldComparison,
    MATCH_RESULTS,
    SCORE_TARGETS,
)


@dataclass(frozen=True)
class MetricsReport:
    total_fields: int
    score_targets: int
    matches: int
    mismatches: int
    ocr_nulls: int
    not_found: int
    both_nulls: int

    @property
    def match_rate(self) -> float:
        if self.score_targets == 0:
            return 0.0
        return (self.matches + self.both_nulls) / self.score_targets

    @property
    def true_match_rate(self) -> float:
        denom = self.matches + self.mismatches + self.ocr_nulls + self.not_found
        if denom == 0:
            return 0.0
        return self.matches / denom

    @property
    def mismatch_rate(self) -> float:
        if self.score_targets == 0:
            return 0.0
        return self.mismatches / self.score_targets

    @property
    def ocr_null_rate(self) -> float:
        if self.score_targets == 0:
            return 0.0
        return self.ocr_nulls / self.score_targets

    @property
    def coverage(self) -> float:
        if self.total_fields == 0:
            return 0.0
        return self.score_targets / self.total_fields

    def as_dict(self) -> dict[str, float | int]:
        return {
            "total_fields": self.total_fields,
            "score_targets": self.score_targets,
            "matches": self.matches,
            "mismatches": self.mismatches,
            "ocr_nulls": self.ocr_nulls,
            "not_found": self.not_found,
            "both_nulls": self.both_nulls,
            "match_rate": round(self.match_rate, 4),
            "true_match_rate": round(self.true_match_rate, 4),
            "mismatch_rate": round(self.mismatch_rate, 4),
            "ocr_null_rate": round(self.ocr_null_rate, 4),
            "coverage": round(self.coverage, 4),
        }


def compute_metrics(fields: Iterable[FieldComparison]) -> MetricsReport:
    counts: Counter[ComparisonResult] = Counter(f.result for f in fields)
    total = sum(counts.values())
    score_targets = sum(counts[r] for r in SCORE_TARGETS)
    return MetricsReport(
        total_fields=total,
        score_targets=score_targets,
        matches=counts[ComparisonResult.MATCH],
        both_nulls=counts[ComparisonResult.BOTH_NULL],
        mismatches=counts[ComparisonResult.MISMATCH],
        ocr_nulls=counts[ComparisonResult.OCR_NULL],
        not_found=counts[ComparisonResult.NOT_FOUND],
    )

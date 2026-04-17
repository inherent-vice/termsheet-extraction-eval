"""The universal interface contract between pipeline stages.

Every field comparison produces exactly one ComparisonResult. Score targets
and match sets are explicit so downstream metrics cannot silently disagree
about semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ComparisonResult(str, Enum):
    """Result of comparing one field between extracted (OCR) and ground-truth (DB).

    The three-tier semantics are critical — collapsing BOTH_NULL and MATCH,
    or OCR_NULL and MISMATCH, hides real failure modes in production.
    """

    MATCH = "MATCH"                # extracted == ground truth (after normalization)
    BOTH_NULL = "BOTH_NULL"        # field absent on both sides (counts as match)
    MISMATCH = "MISMATCH"          # both present, disagree
    OCR_NULL = "OCR_NULL"          # extractor missed a value that exists in DB
    NOT_FOUND = "NOT_FOUND"        # product ID not found in ground truth
    DB_NULL = "DB_NULL"            # DB has no value (often irrelevant — excluded from scoring)
    SKIP = "SKIP"                  # field intentionally excluded


#: Results that contribute to denominator for match_rate.
SCORE_TARGETS: frozenset[ComparisonResult] = frozenset({
    ComparisonResult.MATCH,
    ComparisonResult.BOTH_NULL,
    ComparisonResult.MISMATCH,
    ComparisonResult.OCR_NULL,
    ComparisonResult.NOT_FOUND,
})

#: Results that count as a match.
MATCH_RESULTS: frozenset[ComparisonResult] = frozenset({
    ComparisonResult.MATCH,
    ComparisonResult.BOTH_NULL,
})


@dataclass(frozen=True)
class FieldComparison:
    """A single field-level comparison outcome."""

    product_id: str
    field: str
    extracted: Any
    ground_truth: Any
    result: ComparisonResult
    reason: str = ""


@dataclass(frozen=True)
class ProductComparison:
    """All field comparisons for one product."""

    product_id: str
    fields: tuple[FieldComparison, ...]

    def by_result(self, result: ComparisonResult) -> tuple[FieldComparison, ...]:
        return tuple(f for f in self.fields if f.result is result)

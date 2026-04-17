"""Overall Quality Score (OQS).

OQS is a weighted composite over per-field match rates. Fields that are
legally significant (e.g. maturity date, notional amount, coupon rate)
are weighted higher than aesthetic fields (e.g. item name).

In production, weights are derived from auditor-reviewed field importance
tiers. This public version ships a conservative default that gives
slightly higher weight to dates, notional, and rate-critical fields.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from termsheet_eval.compare.result import (
    ComparisonResult,
    FieldComparison,
    MATCH_RESULTS,
    SCORE_TARGETS,
)


#: Default importance weights. Anything not listed gets weight 1.0.
DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "maturity_date": 2.0,
    "notional_amount": 2.0,
    "coupon_rate": 2.0,
    "issue_date": 1.5,
    "spread": 1.5,
    "currency": 1.5,
    "day_count_method": 1.25,
    "option_holder": 1.0,
    "item_name": 0.5,
}


def compute_oqs(
    fields: Iterable[FieldComparison],
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted match rate across fields. Range: 0.0 to 1.0."""
    weights = weights or DEFAULT_FIELD_WEIGHTS

    numerator = 0.0
    denominator = 0.0

    # Group by field to compute per-field match rates before weighting
    per_field: dict[str, list[ComparisonResult]] = defaultdict(list)
    for f in fields:
        if f.result in SCORE_TARGETS:
            per_field[f.field].append(f.result)

    for field_name, results in per_field.items():
        weight = weights.get(field_name, 1.0)
        matches = sum(1 for r in results if r in MATCH_RESULTS)
        field_rate = matches / len(results) if results else 0.0
        numerator += weight * field_rate
        denominator += weight

    return numerator / denominator if denominator > 0 else 0.0


def grade_oqs(oqs: float) -> str:
    """Letter grade from OQS. Production uses the same cutoffs."""
    if oqs >= 0.90:
        return "A"
    if oqs >= 0.80:
        return "B"
    if oqs >= 0.70:
        return "C"
    if oqs >= 0.60:
        return "D"
    return "F"

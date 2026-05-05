"""Type-aware field comparators.

Each comparator takes (extracted, ground_truth) and returns ComparisonResult.
The goal is not to be "smart" but to be **explicit** — every acceptable
form-difference (% vs bp, KRW vs 1 code, "Callable" vs "B") is codified
as a named rule that shows up in the audit report.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from termsheet_eval.compare.normalizer import (
    normalize_numeric,
    normalize_value,
    tokenize,
)
from termsheet_eval.compare.result import ComparisonResult

# ---------- Primitive null-handling helper ----------


def _null_resolution(
    ext: Any, gt: Any
) -> tuple[ComparisonResult | None, str | None, str | None]:
    """Handle the null/present combinations uniformly.

    Returns (result, normalized_ext, normalized_gt). If the first element is
    not None, the comparator should return that result immediately.
    """
    ne = normalize_value(ext)
    ng = normalize_value(gt)
    if ne is None and ng is None:
        return ComparisonResult.BOTH_NULL, None, None
    if ne is None and ng is not None:
        return ComparisonResult.OCR_NULL, None, ng
    if ne is not None and ng is None:
        return ComparisonResult.DB_NULL, ne, None
    return None, ne, ng  # type: ignore[return-value]


# ---------- Rate ----------


def compare_rate(extracted: Any, ground_truth: Any, tol: float = 1e-4) -> ComparisonResult:
    """Compare interest rates, tolerating % vs bp unit differences (×100).

    Rule: 80bp and 0.8% should MATCH. Absolute tolerance 1e-4 (1 bp).
    """
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    xe = normalize_numeric(ne)
    xg = normalize_numeric(ng)
    if xe is None or xg is None:
        return ComparisonResult.MISMATCH
    for scale in (1.0, 100.0, 0.01):
        if abs(xe * scale - xg) <= tol:
            return ComparisonResult.MATCH
    return ComparisonResult.MISMATCH


# ---------- Numeric ----------

def compare_numeric(extracted: Any, ground_truth: Any, tol: float = 1e-9) -> ComparisonResult:
    """Compare exact numeric quantities without rate/basis-point scaling.

    Monetary notionals and counts are not rates: a 100x unit rescue that is
    valid for interest-rate fields is a silent false-positive for amounts.
    """
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    xe = normalize_numeric(ne)
    xg = normalize_numeric(ng)
    if xe is None or xg is None:
        return ComparisonResult.MISMATCH
    return ComparisonResult.MATCH if abs(xe - xg) <= tol else ComparisonResult.MISMATCH


# ---------- Spread ----------


def compare_spread(extracted: Any, ground_truth: Any, tol: float = 1e-4) -> ComparisonResult:
    """Spreads often come in mixed units — exact + ×100 + ×10000 all acceptable."""
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    xe = normalize_numeric(ne)
    xg = normalize_numeric(ng)
    if xe is None or xg is None:
        return ComparisonResult.MISMATCH
    for scale in (1.0, 100.0, 10_000.0, 0.01, 0.0001):
        if abs(xe * scale - xg) <= tol:
            return ComparisonResult.MATCH
    return ComparisonResult.MISMATCH


# ---------- Date ----------

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y%m%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def _parse_date(val: str) -> date | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def compare_date(extracted: Any, ground_truth: Any) -> ComparisonResult:
    """Date comparison with format-agnostic parsing."""
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    de = _parse_date(ne)  # type: ignore[arg-type]
    dg = _parse_date(ng)  # type: ignore[arg-type]
    if de is None or dg is None:
        return ComparisonResult.MISMATCH
    return ComparisonResult.MATCH if de == dg else ComparisonResult.MISMATCH


# ---------- Currency ----------

# Minimal code table — illustrative only. Numeric aliases are intentionally
# disjoint; otherwise ambiguous code spaces create silent false positives
# (for example, "1" must not match both KRW and USD).
_CURRENCY_CODES = {
    "krw": {"krw", "1"},
    "usd": {"usd", "2"},
    "eur": {"eur", "3"},
    "jpy": {"jpy", "4"},
    "gbp": {"gbp", "5"},
}


def compare_currency(extracted: Any, ground_truth: Any) -> ComparisonResult:
    """Currency comparison with name ↔ code mapping.

    Production distinguishes SN vs SSW code spaces; this public version
    merges them for simplicity.
    """
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    e_low = ne.lower()  # type: ignore[union-attr]
    g_low = ng.lower()  # type: ignore[union-attr]
    for canon, aliases in _CURRENCY_CODES.items():
        if e_low in aliases and g_low in aliases:
            return ComparisonResult.MATCH
    if e_low == g_low:
        return ComparisonResult.MATCH
    return ComparisonResult.MISMATCH


# ---------- Text ----------


def compare_text(
    extracted: Any, ground_truth: Any, jaccard_threshold: float = 0.6
) -> ComparisonResult:
    """Text comparison via token Jaccard similarity.

    Party names and item names rarely match character-for-character, but
    token overlap is a strong signal. Threshold 0.6 chosen empirically
    in production.
    """
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    te = tokenize(ne)
    tg = tokenize(ng)
    if not te or not tg:
        return ComparisonResult.MISMATCH
    if te == tg:
        return ComparisonResult.MATCH
    union = te | tg
    inter = te & tg
    if len(inter) < 2:
        return ComparisonResult.MISMATCH
    jaccard = len(inter) / len(union)
    return ComparisonResult.MATCH if jaccard >= jaccard_threshold else ComparisonResult.MISMATCH


# ---------- Boolean / enum ----------


def _canonical_enum(value: str, mapping: dict[str, str]) -> str:
    """Apply a case-insensitive enum alias map and return a lowercase token."""
    lowered = value.lower()
    lowered_mapping = {str(k).lower(): str(v).lower() for k, v in mapping.items()}
    return lowered_mapping.get(lowered, lowered)


def compare_enum(
    extracted: Any, ground_truth: Any, mapping: dict[str, str] | None = None
) -> ComparisonResult:
    """Enum / coded field comparison with optional alias mapping.

    Example mapping: {"Callable": "B", "Putable": "S"}
    """
    early, ne, ng = _null_resolution(extracted, ground_truth)
    if early is not None:
        return early
    if mapping:
        if _canonical_enum(str(ne), mapping) == _canonical_enum(str(ng), mapping):
            return ComparisonResult.MATCH
    if str(ne).lower() == str(ng).lower():
        return ComparisonResult.MATCH
    return ComparisonResult.MISMATCH


# ---------- Dispatcher ----------

# Per-field type registry — in production, this is derived from a schema file.
FIELD_TYPES: dict[str, str] = {
    "issue_date": "date",
    "maturity_date": "date",
    "first_coupon_date": "date",
    "penultimate_coupon_date": "date",
    "option_end_date": "date",
    "notional_amount": "numeric",
    "coupon_rate": "rate",
    "spread": "spread",
    "cap_rate": "rate",
    "floor_rate": "rate",
    "range_upper": "rate",
    "range_lower": "rate",
    "currency": "currency",
    "issuer": "text",
    "item_name": "text",
    "day_count_method": "enum",
    "option_holder": "enum",
    "fixed_flag": "enum",
}

_DISPATCHER = {
    "rate": compare_rate,
    "spread": compare_spread,
    "date": compare_date,
    "currency": compare_currency,
    "text": compare_text,
    "enum": compare_enum,
    "numeric": compare_numeric,
}

_FIELD_ENUM_MAPPINGS: dict[str, dict[str, str]] = {
    "option_holder": {
        "callable": "B",
        "putable": "S",
        "issuer": "B",
        "investor": "S",
    },
}


def compare_by_type(field: str, extracted: Any, ground_truth: Any) -> ComparisonResult:
    """Dispatch comparison by field type."""
    ftype = FIELD_TYPES.get(field, "text")
    comparator = _DISPATCHER[ftype]
    if ftype == "enum":
        return comparator(extracted, ground_truth, _FIELD_ENUM_MAPPINGS.get(field))
    return comparator(extracted, ground_truth)

"""Regression tests for evaluator false-positive and CLI contract bugs."""
from __future__ import annotations

from termsheet_eval.compare.comparators import (
    compare_by_type,
    compare_currency,
    compare_numeric,
)
from termsheet_eval.compare.result import ComparisonResult
from termsheet_eval.inference.null_inference import NullInferenceEngine


def test_numeric_fields_do_not_apply_rate_unit_scaling() -> None:
    """Notional amounts must not match merely because they differ by 100x."""
    assert compare_numeric("10,000", 10000) is ComparisonResult.MATCH
    assert compare_by_type("notional_amount", 10000, 1_000_000) is ComparisonResult.MISMATCH


def test_currency_numeric_aliases_are_not_ambiguous_across_currencies() -> None:
    assert compare_currency("KRW", "1") is ComparisonResult.MATCH
    assert compare_currency("usd", "2") is ComparisonResult.MATCH
    assert compare_currency("1", "USD") is ComparisonResult.MISMATCH


def test_option_holder_dispatcher_uses_field_specific_aliases() -> None:
    assert compare_by_type("option_holder", "Callable", "B") is ComparisonResult.MATCH
    assert compare_by_type("option_holder", "putable", "S") is ComparisonResult.MATCH


def test_null_inference_uses_normalized_null_sentinels() -> None:
    engine = NullInferenceEngine()
    extracted, applied = engine.infer(
        {"currency": "KRW", "day_count_method": ""},
        {"day_count_method": ComparisonResult.OCR_NULL},
    )
    assert extracted["day_count_method"] == "ACT/365"
    assert applied == ["A:day_count_method"]

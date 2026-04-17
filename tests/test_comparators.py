"""Tests for the field comparators.

Comparators are the only stage of the pipeline with enough branching to
warrant unit tests. Constraints, inference, and metrics are table-driven
and covered by the benchmark.
"""
from __future__ import annotations

import pytest

from termsheet_eval.compare.comparators import (
    compare_currency,
    compare_date,
    compare_enum,
    compare_rate,
    compare_spread,
    compare_text,
)
from termsheet_eval.compare.result import ComparisonResult


class TestCompareRate:
    def test_equal_rates_match(self) -> None:
        assert compare_rate(3.25, 3.25) is ComparisonResult.MATCH

    def test_percent_vs_bp_tolerance(self) -> None:
        # 80 bp = 0.8% — both scales acceptable
        assert compare_rate(80, 0.8) is ComparisonResult.MATCH
        assert compare_rate(0.8, 80) is ComparisonResult.MATCH

    def test_both_null(self) -> None:
        assert compare_rate(None, None) is ComparisonResult.BOTH_NULL

    def test_ocr_null(self) -> None:
        assert compare_rate(None, 3.25) is ComparisonResult.OCR_NULL

    def test_db_null(self) -> None:
        assert compare_rate(3.25, None) is ComparisonResult.DB_NULL

    def test_mismatch(self) -> None:
        assert compare_rate(3.25, 3.50) is ComparisonResult.MISMATCH

    def test_non_numeric_mismatch(self) -> None:
        assert compare_rate("abc", 3.25) is ComparisonResult.MISMATCH


class TestCompareSpread:
    def test_bp_and_percent_match(self) -> None:
        # 150 bp = 1.5%
        assert compare_spread(150, 1.5) is ComparisonResult.MATCH
        # 10000 bp = 1.0 (10000×)
        assert compare_spread(10000, 1.0) is ComparisonResult.MATCH

    def test_zero_spread(self) -> None:
        assert compare_spread(0, 0) is ComparisonResult.MATCH


class TestCompareDate:
    def test_iso_exact_match(self) -> None:
        assert compare_date("2025-03-15", "2025-03-15") is ComparisonResult.MATCH

    def test_different_formats_match(self) -> None:
        assert compare_date("2025/03/15", "2025-03-15") is ComparisonResult.MATCH
        assert compare_date("20250315", "2025-03-15") is ComparisonResult.MATCH
        assert compare_date("15/3/2025", "2025-03-15") is ComparisonResult.MATCH

    def test_different_dates_mismatch(self) -> None:
        assert compare_date("2025-03-15", "2025-03-16") is ComparisonResult.MISMATCH


class TestCompareCurrency:
    def test_code_alias_match(self) -> None:
        # "KRW" and "1" should both map to the KRW canon
        assert compare_currency("KRW", "1") is ComparisonResult.MATCH
        assert compare_currency("usd", "2") is ComparisonResult.MATCH

    def test_case_insensitive(self) -> None:
        assert compare_currency("krw", "KRW") is ComparisonResult.MATCH

    def test_different_currencies(self) -> None:
        assert compare_currency("KRW", "USD") is ComparisonResult.MISMATCH


class TestCompareText:
    def test_exact_token_match(self) -> None:
        assert (
            compare_text("Sample Bank Co Ltd", "Sample Bank Co Ltd")
            is ComparisonResult.MATCH
        )

    def test_jaccard_above_threshold(self) -> None:
        # 4 tokens shared of 5 total = 0.8 > 0.6
        assert (
            compare_text("Sample Bank Co Ltd Kr", "Sample Bank Co Ltd")
            is ComparisonResult.MATCH
        )

    def test_jaccard_below_threshold(self) -> None:
        # Only 1 shared token of 5 — fails both the 2-token and Jaccard check
        assert compare_text("Alpha", "Sample Bank Co Ltd") is ComparisonResult.MISMATCH


class TestCompareEnum:
    def test_alias_mapping(self) -> None:
        mapping = {"Callable": "B", "Putable": "S"}
        assert compare_enum("Callable", "B", mapping) is ComparisonResult.MATCH
        assert compare_enum("Putable", "S", mapping) is ComparisonResult.MATCH

    def test_direct_match(self) -> None:
        assert compare_enum("B", "B") is ComparisonResult.MATCH

    def test_case_insensitive_direct(self) -> None:
        assert compare_enum("b", "B") is ComparisonResult.MATCH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

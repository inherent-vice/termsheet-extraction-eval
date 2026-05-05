"""CLI contract tests for explicit benchmark fixture paths."""
from __future__ import annotations

from pathlib import Path

from termsheet_eval.cli import main

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "data" / "synthetic" / "ground_truth.json"
RAW_EXTRACTIONS = ROOT / "data" / "synthetic" / "raw_extractions.json"


def test_compare_accepts_explicit_fixture_paths(capsys) -> None:  # type: ignore[no-untyped-def]
    exit_code = main([
        "compare",
        "--ground-truth",
        str(GROUND_TRUTH),
        "--raw-extractions",
        str(RAW_EXTRACTIONS),
        "--product-id",
        "TS001",
        "--version",
        "v3",
    ])

    assert exit_code == 0
    assert "Product: TS001" in capsys.readouterr().out


def test_benchmark_accepts_explicit_fixture_paths(capsys) -> None:  # type: ignore[no-untyped-def]
    exit_code = main([
        "benchmark",
        "--version",
        "v3",
        "--ground-truth",
        str(GROUND_TRUTH),
        "--raw-extractions",
        str(RAW_EXTRACTIONS),
    ])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "v3" in out
    assert "0.994" in out

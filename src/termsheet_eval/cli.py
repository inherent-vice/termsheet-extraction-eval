"""Command-line interface.

Two subcommands:
    benchmark — run v1/v2/v3 across synthetic data and print a summary table
    compare   — run a single product and print its per-field breakdown
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from termsheet_eval.extract.mock_client import MockExtractor
from termsheet_eval.pipeline import CONFIGS, Pipeline


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "synthetic"
RESULTS_DIR = ROOT / "benchmarks" / "results"


def _load_synthetic() -> tuple[dict[str, Any], Path]:
    gt_path = DATA_DIR / "ground_truth.json"
    extractions_path = DATA_DIR / "raw_extractions.json"
    if not gt_path.exists() or not extractions_path.exists():
        sys.exit(
            f"Synthetic data not found at {DATA_DIR}. "
            "Run from the repo root after cloning."
        )
    with gt_path.open() as f:
        ground_truth = json.load(f)
    return ground_truth, extractions_path


def _build_pipeline(version: str) -> Pipeline:
    config = CONFIGS.get(version)
    if config is None:
        sys.exit(f"Unknown version '{version}'. Choices: {list(CONFIGS)}")
    _, extractions_path = _load_synthetic()
    extractor = MockExtractor(raw_extractions_path=extractions_path)
    return Pipeline(extractor=extractor, config=config)


def cmd_benchmark(args: argparse.Namespace) -> int:
    versions = ["v1", "v2", "v3"] if args.version == "all" else [args.version]
    ground_truth, _ = _load_synthetic()

    print("━" * 72)
    print(f"{'Version':<8} {'Match Rate':<12} {'True Match':<12} {'OQS':<8} {'Grade':<6}")
    print("━" * 72)

    all_reports: dict[str, Any] = {}
    for version in versions:
        pipeline = _build_pipeline(version)
        comparisons = pipeline.run_all(ground_truth)
        summary = pipeline.summarize(comparisons)
        all_reports[version] = summary

        print(
            f"{version:<8} "
            f"{summary['metrics']['match_rate']:.3f}       "
            f"{summary['metrics']['true_match_rate']:.3f}       "
            f"{summary['oqs']:.3f}   "
            f"{summary['grade']:<6}"
        )

        if args.write:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            out = RESULTS_DIR / f"{version}.json"
            with out.open("w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

    print("━" * 72)

    # Ablation delta summary
    if len(versions) > 1:
        print("\nAblation:")
        base = all_reports.get("v1", {}).get("metrics", {}).get("match_rate", 0.0)
        for v in ("v2", "v3"):
            if v in all_reports:
                diff = all_reports[v]["metrics"]["match_rate"] - base
                print(f"  {v} vs v1: {diff:+.1%} match rate")

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    ground_truth, _ = _load_synthetic()
    pipeline = _build_pipeline(args.version)

    if args.product_id not in ground_truth:
        sys.exit(f"Unknown product id '{args.product_id}'")

    result = pipeline.run_product(args.product_id, ground_truth[args.product_id])

    print(f"Product: {result.product_id}")
    print(f"Version: {args.version}")
    print("━" * 72)
    for f in result.fields:
        mark = "✓" if f.result.value in ("MATCH", "BOTH_NULL") else "✗"
        print(
            f"  {mark} {f.field:<25} {f.result.value:<12} "
            f"ext={f.extracted!r} gt={f.ground_truth!r}"
            + (f"  [{f.reason}]" if f.reason else "")
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="termsheet-eval")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bench = sub.add_parser("benchmark", help="Run synthetic benchmark")
    p_bench.add_argument(
        "--version",
        default="all",
        choices=["all", "v1", "v2", "v3"],
        help="Pipeline version to run (default: all)",
    )
    p_bench.add_argument(
        "--write",
        action="store_true",
        help="Persist results to benchmarks/results/",
    )
    p_bench.set_defaults(func=cmd_benchmark)

    p_compare = sub.add_parser("compare", help="Compare one product")
    p_compare.add_argument("--product-id", required=True)
    p_compare.add_argument("--version", default="v3", choices=["v1", "v2", "v3"])
    p_compare.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

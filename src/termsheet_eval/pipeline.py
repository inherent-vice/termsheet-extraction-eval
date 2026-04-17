"""5-stage evaluation pipeline.

Wires together extract → compare → constraints → inference → metrics.
Each stage is independently testable. Turning constraints/inference on and
off is how we build the v1/v2/v3 ablation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from termsheet_eval.compare.comparators import compare_by_type, FIELD_TYPES
from termsheet_eval.compare.result import (
    ComparisonResult,
    FieldComparison,
    ProductComparison,
)
from termsheet_eval.constraints.engine import ConstraintEngine
from termsheet_eval.extract.base import Extractor
from termsheet_eval.inference.null_inference import NullInferenceEngine
from termsheet_eval.metrics.core import MetricsReport, compute_metrics
from termsheet_eval.metrics.scoring import compute_oqs, grade_oqs


@dataclass(frozen=True)
class PipelineConfig:
    """Ablation configuration for the pipeline."""

    version: str  # "v1" | "v2" | "v3"
    prompt_version: str  # file in prompts/
    constraints_enabled: bool
    inference_enabled: bool


V1_CONFIG = PipelineConfig(
    version="v1",
    prompt_version="v1",
    constraints_enabled=False,
    inference_enabled=False,
)
V2_CONFIG = PipelineConfig(
    version="v2",
    prompt_version="v2",
    constraints_enabled=True,
    inference_enabled=False,
)
V3_CONFIG = PipelineConfig(
    version="v3",
    prompt_version="v3",
    constraints_enabled=True,
    inference_enabled=True,
)

CONFIGS: dict[str, PipelineConfig] = {
    "v1": V1_CONFIG,
    "v2": V2_CONFIG,
    "v3": V3_CONFIG,
}


@dataclass
class Pipeline:
    """Evaluation pipeline.

    ``extractor`` is injected so the same pipeline runs against OpenAI,
    Anthropic, Gemini, or the deterministic mock extractor.
    """

    extractor: Extractor
    config: PipelineConfig
    constraint_engine: ConstraintEngine = field(default_factory=ConstraintEngine)
    inference_engine: NullInferenceEngine = field(default_factory=NullInferenceEngine)

    # ---------- Per-product ----------

    def run_product(
        self, product_id: str, ground_truth: dict[str, Any]
    ) -> ProductComparison:
        """Run extract → compare (→ constraints → inference) for one product."""
        # Stage 1: extract
        extracted = self.extractor.extract(product_id, self.config.prompt_version)

        # Stage 2: initial compare
        raw_results = {
            f: compare_by_type(f, extracted.get(f), ground_truth.get(f))
            for f in FIELD_TYPES
        }

        # Stage 3: constraints (if enabled)
        applied_constraints: list[str] = []
        if self.config.constraints_enabled:
            extracted, applied_constraints = self.constraint_engine.apply(extracted)
            # Re-compare the constraint-touched fields
            for fld in ("spread", "coupon_rate_base", "option_end_date",
                        "range_upper", "range_lower"):
                if fld in FIELD_TYPES:
                    raw_results[fld] = compare_by_type(
                        fld, extracted.get(fld), ground_truth.get(fld)
                    )

        # Stage 4: NULL inference (if enabled)
        applied_inferences: list[str] = []
        if self.config.inference_enabled:
            extracted, applied_inferences = self.inference_engine.infer(
                extracted, raw_results
            )
            for fld in ("day_count_method", "option_holder", "spread"):
                if fld in FIELD_TYPES:
                    raw_results[fld] = compare_by_type(
                        fld, extracted.get(fld), ground_truth.get(fld)
                    )

        all_rules = applied_constraints + applied_inferences

        def _field_reasons(field_name: str) -> str:
            """Only report rules that actually touched this field."""
            return "; ".join(
                r for r in all_rules
                if r.endswith(f":{field_name}") or r.endswith(field_name)
            )

        fields = tuple(
            FieldComparison(
                product_id=product_id,
                field=f,
                extracted=extracted.get(f),
                ground_truth=ground_truth.get(f),
                result=raw_results[f],
                reason=_field_reasons(f),
            )
            for f in FIELD_TYPES
        )
        return ProductComparison(product_id=product_id, fields=fields)

    # ---------- Across products ----------

    def run_all(
        self, ground_truth_by_id: dict[str, dict[str, Any]]
    ) -> list[ProductComparison]:
        return [
            self.run_product(pid, gt) for pid, gt in ground_truth_by_id.items()
        ]

    # ---------- Report ----------

    @staticmethod
    def summarize(comparisons: list[ProductComparison]) -> dict[str, Any]:
        all_fields = tuple(f for p in comparisons for f in p.fields)
        metrics = compute_metrics(all_fields)
        oqs = compute_oqs(all_fields)
        return {
            "num_products": len(comparisons),
            "num_field_comparisons": len(all_fields),
            "metrics": metrics.as_dict(),
            "oqs": round(oqs, 4),
            "grade": grade_oqs(oqs),
        }

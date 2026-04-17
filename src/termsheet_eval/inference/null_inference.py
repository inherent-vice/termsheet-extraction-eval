"""NULL inference engine.

Half of the remaining ``OCR_NULL`` results after constraints are actually
**DB defaults that the term sheet never mentioned** — the LLM correctly
returned NULL, and the DB populated a conventional default. Treating those
as mismatches punishes correct behaviour.

This engine encodes three **public** inference categories:

- **Category A** — rule-based defaults (e.g. ``day_count_method`` defaults to
  ``ACT/365`` in KRW markets when absent)
- **Category B** — inferable from sibling fields (e.g. ``option_holder``
  defaults to ``B`` (Callable) when option fields are present)
- **Category C** — silent defaults vs extraction gaps (if the product is
  NOT structured for this field type, the correct answer is NULL, not a
  default)

The proprietary version has five categories (A–E) covering schedule-based
inference and conditional CMS spread default values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from termsheet_eval.compare.result import ComparisonResult


@dataclass(frozen=True)
class InferenceRule:
    category: str
    field: str
    applies_when: Callable[[dict[str, Any]], bool]
    default_value: Any
    description: str


# ----- Category A: rule-based defaults -----

DAY_COUNT_DEFAULT_ACT365 = InferenceRule(
    category="A",
    field="day_count_method",
    applies_when=lambda rec: rec.get("currency") in ("KRW", 1, "1"),
    default_value="ACT/365",
    description="KRW-denominated products default to ACT/365 when day count is absent.",
)


# ----- Category B: inferable from siblings -----

OPTION_HOLDER_DEFAULT_CALLABLE = InferenceRule(
    category="B",
    field="option_holder",
    applies_when=lambda rec: rec.get("option_end_date") is not None,
    default_value="B",
    description="If an option end date exists, default the holder to B (Callable).",
)


# ----- Category C: silent defaults vs extraction gaps -----

SPREAD_DEFAULT_ZERO_WHEN_FIXED = InferenceRule(
    category="C",
    field="spread",
    applies_when=lambda rec: rec.get("fixed_flag") in (1, "1", "Y", True),
    default_value=0,
    description=(
        "For fixed-rate products, spread is definitionally 0. If the LLM returned "
        "NULL (because the term sheet didn't mention spread — correctly), infer 0."
    ),
)


DEFAULT_RULES: tuple[InferenceRule, ...] = (
    DAY_COUNT_DEFAULT_ACT365,
    OPTION_HOLDER_DEFAULT_CALLABLE,
    SPREAD_DEFAULT_ZERO_WHEN_FIXED,
)


@dataclass
class NullInferenceEngine:
    rules: tuple[InferenceRule, ...] = field(default_factory=lambda: DEFAULT_RULES)

    def infer(
        self,
        extracted: dict[str, Any],
        comparison_results: dict[str, ComparisonResult],
    ) -> tuple[dict[str, Any], list[str]]:
        """Apply inference to fields currently marked OCR_NULL.

        Returns ``(updated_record, applied_rule_names)``. Only fields where
        the comparison was OCR_NULL and an inference rule matches are touched.
        """
        rec = dict(extracted)
        applied: list[str] = []

        for rule in self.rules:
            fld = rule.field
            if comparison_results.get(fld) is not ComparisonResult.OCR_NULL:
                continue
            if not rule.applies_when(rec):
                continue
            if rec.get(fld) is None:
                rec[fld] = rule.default_value
                applied.append(f"{rule.category}:{rule.field}")

        return rec, applied

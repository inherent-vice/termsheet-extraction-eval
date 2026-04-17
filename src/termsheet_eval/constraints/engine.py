"""Cross-field constraint engine.

In production, ~20% of raw MISMATCH calls are actually resolvable via
cross-field constraints — e.g., a fixed-rate product naturally has
``Rate1 = 0, Factor1 = 0``, so if the LLM extracted those as NULL but
``FixedFlag = 1`` is present, we can safely upgrade NULL → 0.

This engine applies three **public** constraint groups (A, B, C). The
proprietary version has seven (A–G) covering reset types, Bermudan
options, CMS spread decomposition, and RA (Range Accrual) barrier
saturation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ConstraintRule:
    """A single cross-field rule.

    The predicate inspects the extracted record; if True, the fixers are
    applied to any NULL fields, converting them to the expected default.
    """

    group: str
    name: str
    description: str
    predicate: Callable[[dict[str, Any]], bool]
    fixers: dict[str, Any]  # field_name -> expected_value


# ----- Group A: Fixed-rate implications -----


def _is_fixed_rate(rec: dict[str, Any]) -> bool:
    flag = rec.get("fixed_flag")
    return flag in (1, "1", "Y", "y", "true", True)


FIXED_RATE_NULLIFIES_FLOAT = ConstraintRule(
    group="A",
    name="fixed_rate_nullifies_float",
    description=(
        "FixedFlag=1 implies Rate1 and Factor1 are 0 by convention (no variable "
        "component). If the LLM extracted them as NULL but FixedFlag is set, "
        "upgrade NULL → 0."
    ),
    predicate=_is_fixed_rate,
    fixers={"spread": 0, "coupon_rate_base": 0},
)


# ----- Group B: Option date implications -----


def _has_option_end(rec: dict[str, Any]) -> bool:
    oe = rec.get("option_end_date")
    mat = rec.get("maturity_date")
    return bool(oe) and bool(mat) and oe > mat  # option end cannot exceed maturity


OPTION_END_CAPPED_AT_MATURITY = ConstraintRule(
    group="B",
    name="option_end_capped_at_maturity",
    description=(
        "OptionEndDate must be <= MaturityDate. If extracted OptionEnd > "
        "MaturityDate, assume OCR artifact and replace with MaturityDate."
    ),
    predicate=_has_option_end,
    fixers={},  # populated at apply-time (see engine)
)


# ----- Group C: Range bound saturation -----


def _has_extreme_bound(rec: dict[str, Any]) -> bool:
    """9999 is a common ``unbounded`` sentinel but ±999 is the canonical form."""
    upper = rec.get("range_upper")
    lower = rec.get("range_lower")
    try:
        if upper is not None and abs(float(upper)) >= 9999:
            return True
        if lower is not None and abs(float(lower)) >= 9999:
            return True
    except (TypeError, ValueError):
        return False
    return False


RANGE_BOUND_SATURATION = ConstraintRule(
    group="C",
    name="range_bound_saturation",
    description=(
        "Range bounds of ±9999 are treated as equivalent to ±999 (unbounded). "
        "Normalize to canonical ±999 before comparison."
    ),
    predicate=_has_extreme_bound,
    fixers={},  # populated at apply-time
)


DEFAULT_RULES: tuple[ConstraintRule, ...] = (
    FIXED_RATE_NULLIFIES_FLOAT,
    OPTION_END_CAPPED_AT_MATURITY,
    RANGE_BOUND_SATURATION,
)


@dataclass
class ConstraintEngine:
    rules: tuple[ConstraintRule, ...] = field(default_factory=lambda: DEFAULT_RULES)

    def apply(self, extracted: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Apply all rules in order; return (updated_record, applied_rule_names)."""
        rec = dict(extracted)
        applied: list[str] = []

        for rule in self.rules:
            if not rule.predicate(rec):
                continue

            if rule.name == "fixed_rate_nullifies_float":
                for fld, default in rule.fixers.items():
                    if rec.get(fld) is None:
                        rec[fld] = default
                        applied.append(f"{rule.group}:{rule.name}:{fld}")

            elif rule.name == "option_end_capped_at_maturity":
                rec["option_end_date"] = rec["maturity_date"]
                applied.append(f"{rule.group}:{rule.name}")

            elif rule.name == "range_bound_saturation":
                for bound_fld in ("range_upper", "range_lower"):
                    val = rec.get(bound_fld)
                    if val is None:
                        continue
                    try:
                        fv = float(val)
                    except (TypeError, ValueError):
                        continue
                    if abs(fv) >= 9999:
                        rec[bound_fld] = 999 if fv > 0 else -999
                        applied.append(f"{rule.group}:{rule.name}:{bound_fld}")

        return rec, applied

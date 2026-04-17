# Prompt Engineering Log

> Three versions are committed to `prompts/`. This document explains
> what changed and why, so each improvement is attributable.

## v1 — baseline

```
You are an extraction assistant. Given a term sheet describing a
structured financial product, return a JSON object with the fields
requested by the schema.

Rules:
- Return only valid JSON matching the schema.
- If a field is not mentioned in the term sheet, return null.
- Preserve the original unit (%, bp) as stated.
- Dates should be in ISO-8601 (YYYY-MM-DD).
```

**Mock benchmark**: match rate 89.2%, OQS 0.895 (B).

**Failure modes observed**:

1. **Unit ambiguity** — "80bp" returned as literal `80` (number only, bp
   lost); downstream comparator accepts `×100` tolerance but many
   pipelines would mis-score.
2. **Range saturation** — "unlimited upper bound" rendered as `9999`
   which is the operator-entered sentinel in the DB.
3. **Option end overflow** — LLM occasionally returned option end date
   greater than maturity when the document phrasing was ambiguous.
4. **Silent defaults extracted as NULL** — `day_count_method = null`
   on KRW products (correct behaviour — term sheet doesn't say — but
   DB has ACT/365 populated).

## v2 — normative conventions in prompt

Added explicit unit, range, and option conventions:

```
Unit conventions (v2 addition):
- All rates must be returned as percent (e.g. 0.8, not 80bp).
- If the term sheet says "80bp", return 0.8.

Range accrual conventions (v2 addition):
- Use 999 (not 9999) for unbounded.

Option conventions (v2 addition):
- Option end date CANNOT exceed maturity date.
```

**Mock benchmark**: match rate 93.9% (+4.7pp), OQS 0.944 (A).

**What improved**: The constraint engine (Group B, Group C) is redundant
with the prompt rules in v2 — the LLM is told the same convention. In
production, we still keep the engine because:

1. LLMs don't follow rules 100% of the time. The engine is a safety net.
2. Some documents genuinely are ambiguous, and the engine applies the
   convention consistently regardless of phrasing.

**What didn't improve**: Silent defaults (day count, option holder) —
the prompt says "return null if not mentioned", which is correct, but
the DB still has defaults populated.

## v3 — explicit responsibility separation

The insight: **the prompt should tell the LLM what's in the document;
the post-processing should apply industry conventions**.

```
Semantic clarity (v3 addition):
- For fixed-rate products, set fixed_flag = 1. The spread and
  floating-reference fields should remain null in your output —
  downstream systems will apply the "fixed ⇒ 0" convention. Do not
  fabricate 0 values.
- For KRW-denominated products, if day count is not specified,
  return null. (KRW market convention is ACT/365 but the downstream
  inference engine should apply that default, not the extractor.)
- For callable products with an option end date, if the holder is
  not specified, return null.

Principle: the extractor is responsible for what is in the document;
the downstream engine is responsible for applying conventions.
```

**Mock benchmark**: match rate 99.4% (+5.6pp from v2), OQS 0.996 (A).

**What improved**: The NULL inference engine's three public categories
(A, B, C) now have clean contracts with the prompt. The prompt says
"return null when the document doesn't say"; the inference engine says
"when extractor returns null, apply the convention". Each component has
exactly one responsibility.

## Meta-pattern

The prompt engineering journey here mirrors a pattern we've seen
repeatedly in production:

1. **v1** — "tell the LLM what we want as final output"
2. **v2** — "tell the LLM the rules"
3. **v3** — "tell the LLM only about the document; rules live elsewhere"

v3 is both more accurate and more **maintainable**. When a rule changes
(e.g., DCM convention for a new currency), we change one constant in
`inference/null_inference.py`, not a prompt paragraph the LLM may
interpret inconsistently.

## Version comparison summary

| Version | Match Rate | OQS | Grade | Δ from v1 | Reason for improvement |
|---------|-----------:|----:|:-----:|----------:|------------------------|
| v1      | 89.2%      | 0.895 | B   | —         | Baseline                |
| v2      | 93.9%      | 0.944 | A   | +4.7pp    | Constraint engine (explicit unit / bound / option rules) |
| v3      | 99.4%      | 0.996 | A   | +10.3pp   | + NULL inference (responsibility separation) |

## Production version has 13 prompts

The KAP production system has 13 prompt versions reaching OQS 92.52%.
The gains across v3 → v13 come from domain-specific conventions:

- **v4–v6**: Korean market–specific conventions (bond code to rate
  ID mapping, reset type defaults, T+N settlement lag handling)
- **v7–v9**: Structured product typology (CMS spread decomposition,
  Bermudan exercise type, step-up schedule)
- **v10–v13**: Anomaly class handling (`db_stale_post_transition`,
  `leg_swap_suspected`, etc. — each class warranted prompt-level
  disambiguation rather than inference-engine handling)

These are intentionally not public because the prompt verbiage itself
encodes trade-secret domain knowledge.

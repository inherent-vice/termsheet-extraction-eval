# Architecture

## Why this architecture exists

When a regulated industry adopts LLM-based extraction, the first system
that ships looks like this:

```
Term sheet → LLM with nice prompt → JSON → insert into DB
```

It works 65–75% of the time. Then three things happen simultaneously:

1. An auditor catches a field that says `"MATCH"` but is actually wrong —
   because the LLM produced a subtly incorrect value that the comparison
   code accepted.
2. The team tries to improve accuracy by fixing the prompt. Each prompt
   change fixes one class of errors and regresses another.
3. Evaluation drifts. "94% accuracy" means different things across weeks
   because the denominator and the comparator logic keep changing.

This project is a reference implementation of the patterns that solved
those problems in a production system at KAP (89 fields × 410 derivative
products, reaching OQS 92.52%):

1. **Type-aware comparators with explicit tolerance rules.**
2. **A constraint engine that resolves cross-field dependencies deterministically.**
3. **A NULL inference engine that distinguishes silent defaults from
   extraction failures.**
4. **Explicit scoring semantics** — `BOTH_NULL`, `OCR_NULL`, and
   `DB_NULL` are never collapsed into `MATCH` or `MISMATCH`.
5. **Versioned prompts with ablation** — so every accuracy claim is
   attributable to a specific change.

## The 5 stages

```
     ┌───────────────────────────────────────────┐
     │  Extractor (LLM adapter)                  │
     │  OpenAI / Anthropic / Gemini / Mock       │
     │  + system_prompt_vN.txt + schema.json     │
     └─────────────────┬─────────────────────────┘
                       │ extracted: dict[field, value]
                       ▼
     ┌───────────────────────────────────────────┐
     │  Comparator (per field, by type)          │
     │  rate  │ date  │ spread  │ currency │ text│
     │  → ComparisonResult                        │
     └─────────────────┬─────────────────────────┘
                       │ comparison_results: dict[field, Result]
                       ▼
     ┌───────────────────────────────────────────┐
     │  Constraint Engine (cross-field)          │
     │  Group A: fixed-rate implications         │
     │  Group B: option date bounds              │
     │  Group C: range bound saturation          │
     │  → updated extracted dict, re-compare     │
     └─────────────────┬─────────────────────────┘
                       │
                       ▼
     ┌───────────────────────────────────────────┐
     │  NULL Inference Engine (per field)        │
     │  Category A: rule-based defaults          │
     │  Category B: infer from sibling fields    │
     │  Category C: silent defaults              │
     │  → updated extracted dict, re-compare     │
     └─────────────────┬─────────────────────────┘
                       │
                       ▼
     ┌───────────────────────────────────────────┐
     │  Metrics & Scoring                        │
     │  match_rate, true_match_rate, OQS         │
     │  per-field, per-category, per-product     │
     └───────────────────────────────────────────┘
```

## Scoring semantics

Every field comparison produces exactly one of:

| Result       | Meaning                                       | In numerator? | In denominator? |
|--------------|-----------------------------------------------|:-------------:|:---------------:|
| `MATCH`      | Values equal after normalization              | ✓             | ✓               |
| `BOTH_NULL`  | Both extractor and ground-truth are NULL      | ✓             | ✓               |
| `MISMATCH`   | Both present, disagree                        |               | ✓               |
| `OCR_NULL`   | Extractor missed a value that is in ground-truth |            | ✓               |
| `NOT_FOUND`  | Product ID not in ground truth                |               | ✓               |
| `DB_NULL`    | Ground truth NULL, extractor has value        |               |                 |
| `SKIP`       | Intentionally excluded                        |               |                 |

The critical design choice is **keeping `BOTH_NULL` and `OCR_NULL`
distinct**. Collapsing them into `MATCH`/`MISMATCH` respectively removes
the signal we need to improve the inference engine.

The `match_rate` reported is `(MATCH + BOTH_NULL) / SCORE_TARGETS`. The
`true_match_rate` reported is `MATCH / (MATCH + MISMATCH + OCR_NULL + NOT_FOUND)` —
a stricter metric that excludes BOTH_NULL from the numerator. These
two rates answer different questions; auditors want both.

## Constraint engine design

Constraints are **cross-field**, **deterministic**, and **idempotent**.
Each rule has:

- a `predicate` — takes the extracted record, returns bool
- `fixers` — a `{field: value}` dict applied when the predicate is true

The engine iterates rules in declaration order. Re-comparison after
applying constraints is done at the pipeline level, not inside the engine,
so the engine has no dependency on the comparator.

Public rules (ships in this repo):

- **Group A — fixed-rate implications**: If `fixed_flag == 1`, then
  `spread == 0` and `coupon_rate_base == 0` by convention. If the
  extractor returned NULL, upgrade to 0.

- **Group B — option end bounds**: `option_end_date > maturity_date`
  is an OCR artifact. Cap at maturity.

- **Group C — range bound saturation**: ±9999 is normalized to ±999
  (the canonical "unbounded" form).

Proprietary rules (not shipped):

- **Group D** — CMS spread decomposition (distributive vs linear
  formulas, `10 * (curve + spread%)` vs `10 * (curve%) + spread%`)
- **Group E** — Bermudan option exercise type normalization
- **Group F** — RA daily n/N vs binary barrier
- **Group G** — reset type cross-checks

## NULL inference engine design

Inference fires only on fields currently marked `OCR_NULL`. This is the
most conservative design choice: we never overwrite a value the extractor
returned. We only fill in NULLs when a rule and sibling evidence combine
to make the default unambiguous.

Public categories:

- **Category A — rule-based defaults**: `day_count_method` defaults to
  `ACT/365` on KRW-denominated products.
- **Category B — infer from siblings**: `option_holder` defaults to
  `B` (Callable) when `option_end_date` is present.
- **Category C — silent-default vs extraction-gap**: `spread` defaults
  to `0` when `fixed_flag == 1`.

The key principle: **the extractor's job is to report what the document
says; the inference engine's job is to apply industry conventions**. These
are separate concerns and should live in separate code.

## Why not LangChain / LlamaIndex / agents framework?

Three reasons:

1. **Debuggability** — every stage is a pure function over plain data.
   No hidden state, no callback labyrinth, no implicit message passing.
2. **Auditability** — an auditor reviewing this code can read each
   comparator, each constraint rule, each inference rule, and understand
   exactly what will happen to any input.
3. **Domain complexity** — the interesting logic is domain conventions
   (Korean derivative markets, regulatory reporting defaults), not agent
   orchestration. Agent frameworks optimize for the opposite direction.

For a multi-agent orchestration use case (research, code generation,
conversation), the tradeoffs flip. This project is explicitly for
structured extraction from regulated-industry documents.

## What's not shown in the public version

The production system at KAP also includes:

- **DB authority check** (Stage 1.5) — independent SQL Server query of
  IRDRV product master, cross-checked against the extracted description.
  Catches silent parser bugs where engine + verifier share the same
  faulty parse logic.
- **QuantLib-style schedule engine** — reconstructs coupon payment dates
  from `issue_date + stepmonth + business-day conventions`, used to
  validate dates the extractor returns.
- **22-metric evaluation harness** — not just match rate, but per-field
  confidence scores, delta analysis between runs, systematic anomaly
  taxonomy (`db_stale_post_transition`, `stepup_excel_wrong_stage`,
  `leg_swap_suspected`, etc.) with operator action prescriptions.
- **RAG oracle over 470 ground-truth descriptions** — ChromaDB +
  multilingual SBERT, k=5 neighbor voting for ambiguous cases.

These are discussed architecturally, not implemented. If you want to
see the full shape, see the README section "Proprietary equivalent".

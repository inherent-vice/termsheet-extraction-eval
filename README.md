# termsheet-extraction-eval

> Reference architecture for evaluating LLM-extracted structured financial data
> against a ground-truth database.

Extracted from a production system that validates OCR-extracted term sheets
across **89 fields × 410 derivative products** at a Korean bond valuation firm,
with **94.5% field-level accuracy** (raw OCR: 71.4%, post-processed: 94.5%).

Public code shows the **architecture and evaluation philosophy**;
domain-specific rules and full constraint/inference engines remain proprietary.

---

## What this demonstrates

- **Multi-provider LLM extraction** — pluggable adapters (OpenAI / Anthropic / Gemini / Mock)
- **Type-aware field comparison** — rate, date, spread, currency, text
- **3-tier scoring** — `MATCH` / `BOTH_NULL` / `MISMATCH` / `OCR_NULL` / `NOT_FOUND`
- **Cross-field constraint engine** — resolves dependencies between extracted fields
- **NULL inference engine** — distinguishes OCR failures from genuine absence
- **Multi-dimensional metrics** — match rate, true match rate, OQS, per-category breakdown
- **Versioned prompt archive** — explicit v1 → v2 → v3 iteration with ablation
- **Synthetic benchmark** — 20 term sheets × 18 fields, reproducible

---

## Architecture in one diagram

```
┌──────────────┐
│ Term sheet   │ (synthetic PDF / JSON)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 1: Extract                                             │
│    LLM adapter (OpenAI / Anthropic / Gemini / Mock)           │
│    + system_prompt_vN.txt + schema.json                       │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 2: Compare (per field)                                 │
│    normalize → type-dispatch (rate/date/spread/currency/text) │
│    → {MATCH, MISMATCH, BOTH_NULL, OCR_NULL, NOT_FOUND}        │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 3: Cross-field Constraint Engine                       │
│    Group A: FixedFlag=1 ⇒ Rate=0, Factor=0                    │
│    Group B: OptionEnd ≤ Maturity                              │
│    Group C: Range bounds saturation                           │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 4: NULL Inference Engine                               │
│    Category A: rule-based defaults                            │
│    Category B: infer from sibling fields                      │
│    Category C: distinguish silent-default from extraction-gap │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 5: Metrics & Scoring                                   │
│    match_rate, true_match_rate, OQS (weighted by importance)  │
│    per-category / per-field / per-product breakdown           │
└──────────────────────────────────────────────────────────────┘
```

---

## Benchmark results (synthetic data, 20 products × 18 fields = 360 comparisons)

| Version | Description | Match Rate | True Match | OQS | Grade |
|---------|-------------|-----------:|-----------:|----:|:-----:|
| **v1** | comparators only (no post-processing) | 89.2% | 85.2% | 0.895 | **B** |
| **v2** | + cross-field constraint engine | 93.9% | 91.6% | 0.944 | **A** |
| **v3** | + NULL inference engine | **99.4%** | **99.2%** | **0.996** | **A** |

**Ablation**: v2 adds **+4.7 percentage points** (constraint recovery of
range bound saturation and option-end overflow). v3 adds another **+5.6pp**
(inference recovery of silent defaults — fixed-rate spread=0, KRW day
count = ACT/365, callable default holder = B).

> The raw LLM output is **unchanged** across versions. The demonstrated
> improvement comes entirely from post-processing. This is the critical
> lesson from production: type-aware comparators and constraint/inference
> engines recover more accuracy than most prompt improvements.

> The **raw extraction accuracy is intentionally unchanged** across versions.
> The gain comes entirely from post-processing — constraint resolution and
> null inference — because that is where audit-grade systems actually make
> their money in production.

Run it yourself:

```bash
pip install -e .
python -m termsheet_eval.cli benchmark --version all
```

---

## Why this matters

Extracting structured data from documents with an LLM is easy.
Making the extraction **trustworthy enough for regulated audit workflows**
is the hard part, and it is almost entirely a post-processing and evaluation
problem, not a model problem.

In production, silent bugs cost more than loud failures. An engine that
says `"MATCH"` when the value is secretly wrong — because engine + verifier
share the same parser bug — is worse than an engine that throws an error.
This package encodes the patterns that catch those silent failures:

- **Cross-verification** — multiple independent comparators per field type
- **External authority** — DB is the final word; LLM/engine can both be wrong
- **Explicit scoring semantics** — `BOTH_NULL ≠ MATCH ≠ OCR_NULL ≠ MISMATCH`
- **Versioned prompts with ablation** — every improvement attributable

---

## Quick start

```bash
git clone https://github.com/inherent-vice/termsheet-extraction-eval
cd termsheet-extraction-eval
pip install -e .

# Run full benchmark across v1/v2/v3 with mock extractor (no API key needed)
python -m termsheet_eval.cli benchmark --version all

# Run single version
python -m termsheet_eval.cli benchmark --version v3

# Compare specific term sheet
python -m termsheet_eval.cli compare \
    --term-sheet data/synthetic/term_sheets.json \
    --ground-truth data/synthetic/ground_truth.json \
    --product-id TS001 \
    --version v3
```

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — detailed system design
- [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md) — v1 → v3 iteration log
- [CLAUDE.md](CLAUDE.md) — Claude Code working notes

---

## Proprietary equivalent

The production version at KAP covers 89 fields × 410 derivative products
(structured notes, structured swaps, IRS), with 7 constraint groups, 5 NULL
inference categories, 22 metrics, and 13 versioned prompts reaching OQS 92.52%.
Available for discussion under NDA.

---

## License

MIT

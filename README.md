# termsheet-extraction-eval

[![CI](https://github.com/inherent-vice/termsheet-extraction-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/inherent-vice/termsheet-extraction-eval/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

> Reference architecture for evaluating LLM-extracted structured financial data
> against a ground-truth database.

Extracted from a production system that validates OCR-extracted term sheets
across **89 fields × 410 derivative products** at a Korean bond valuation firm,
with **94.5% field-level accuracy** (raw OCR: 71.4%, post-processed: 94.5%).

Public code shows the **architecture and evaluation philosophy**;
domain-specific rules and full constraint/inference engines remain proprietary.

---

## What this demonstrates

- **Extractor adapter interface** — deterministic Mock extractor included; OpenAI / Anthropic / Gemini dependencies are optional extension points
- **Type-aware field comparison** — rate, numeric amount, date, spread, currency, enum, text
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
│    normalize → type-dispatch (rate/numeric/date/currency/etc.) │
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
fixed-rate spread defaults and range-bound saturation). v3 adds another
**+5.6pp** (NULL inference recovery of KRW day count = ACT/365 and
callable default holder = B).

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
python -m pip install -e '.[dev]'
python -m termsheet_eval.cli benchmark --version all

# Or use the convenience targets
make test
make benchmark
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
python -m pip install -e '.[dev]'

# Run full benchmark across v1/v2/v3 with mock extractor (no API key needed)
python -m termsheet_eval.cli benchmark --version all

# Equivalent Make target
make benchmark

# Run single version
python -m termsheet_eval.cli benchmark --version v3

# Compare specific term sheet with bundled fixtures
python -m termsheet_eval.cli compare \
    --product-id TS001 \
    --version v3

# Or provide explicit fixture paths
python -m termsheet_eval.cli compare \
    --ground-truth data/synthetic/ground_truth.json \
    --raw-extractions data/synthetic/raw_extractions.json \
    --product-id TS001 \
    --version v3
```

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — detailed system design
- [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md) — v1 → v3 iteration log
- [data/synthetic/README.md](data/synthetic/README.md) — synthetic fixture provenance and error patterns
- [CLAUDE.md](CLAUDE.md) — Claude Code working notes

---

## Reproducibility, data provenance, and privacy

- The benchmark data is **synthetic** and intentionally small enough for CI.
- No proprietary term sheets, customer records, SQL Server schemas, API keys, or private prompts are included.
- The bundled `MockExtractor` makes the main benchmark deterministic and does not call external LLM APIs.
- Optional OpenAI / Anthropic / Gemini extras are extension points only; provider keys should be supplied through the environment and must never be committed.
- CI runs lint, tests, and the ablation gate on Python 3.10 / 3.11 / 3.12.

## Limitations and failure modes

- This is a **reference architecture**, not the full KAP production engine.
- Synthetic fixtures demonstrate error classes and recovery behavior; they are not a representative market dataset.
- Numeric currency aliases in fixtures are synthetic demo codes, not ISO numeric currency codes.
- `compare_numeric` intentionally avoids rate-style 100× scaling for amount fields; real notional extraction with rounding or unit suffixes should add an explicit unit-normalization policy.
- The benchmark proves regression behavior for the included fixtures, not universal LLM extraction accuracy.

---

## Proprietary equivalent

The production version at KAP covers 89 fields × 410 derivative products
(structured notes, structured swaps, IRS), with 7 constraint groups, 5 NULL
inference categories, 22 metrics, and 13 versioned prompts reaching OQS 92.52%.
Available for discussion under NDA.

---

## License

MIT

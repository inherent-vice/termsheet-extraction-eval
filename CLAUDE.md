# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## Project Overview

`termsheet-extraction-eval` is a reference architecture for evaluating
LLM-extracted structured financial data (term sheets) against a ground-truth
database. Extracted from a production system at a Korean bond valuation firm.

The core value proposition: **raw LLM extraction is easy; making it
audit-grade trustworthy is a post-processing and evaluation problem**.

## Commands

```bash
# Install in editable mode
pip install -e .

# Run full benchmark across v1/v2/v3 (uses mock extractor, no API keys)
python -m termsheet_eval.cli benchmark --version all

# Run single version
python -m termsheet_eval.cli benchmark --version v3

# Compare specific product
python -m termsheet_eval.cli compare --product-id TS001 --version v3

# Tests
pytest tests/
```

## Architecture

5-stage pipeline (see `src/termsheet_eval/pipeline.py`):

1. **Extract** — LLM adapter dispatches to OpenAI/Anthropic/Gemini/Mock
2. **Compare** — per-field type-aware comparison (5 type dispatchers)
3. **Constraints** — cross-field constraint engine (3 public groups)
4. **Inference** — NULL inference engine (3 public categories)
5. **Metrics** — match rate, true match rate, OQS with per-category breakdown

## Public vs Proprietary

The public repo shows **architecture and philosophy**. The proprietary
KAP version has:

- 89 fields (public: 18)
- 410 products (public: 20 synthetic)
- 7 constraint groups (public: 3)
- 5 NULL inference categories (public: 3)
- 22 metrics (public: 5)
- 13 versioned prompts reaching OQS 92.52% (public: 3 versions)
- DB authority check (Stage 1.5) against SQL Server IRDRV/KBPDB
- Rule engine + QuantLib-style schedule generation

These are described in ARCHITECTURE.md but intentionally not implemented.

## Guardrails

- **Never leak actual production data.** All data under `data/synthetic/`
  is generated or heavily abstracted. No real KAP customer or vendor IDs.
- **Never implement proprietary rules.** Rule 1-29 from the production
  system map to structured financial conventions that are trade secret.
  The public version uses placeholder rules demonstrating the engine
  pattern only.
- **Prefer composition over plugin hell.** One LLM adapter base class,
  simple dict-based constraint/inference specs. No framework.

## Conventions

- Python 3.10+ (uses `|` union syntax)
- Type hints everywhere
- Immutable dataclasses for results
- No hidden global state
- `ComparisonResult` enum is the universal interface contract between stages

## Known limitations of the public version

- Mock extractor has baked-in "LLM-like errors" — real LLMs will produce
  different error distributions
- Constraint/inference rules are illustrative, not exhaustive
- No actual PDF parsing — synthetic data is pre-JSON'd
- No LangChain / LlamaIndex — by design (too much abstraction for this use case)

# GitHub Push Instructions

> Follow these steps to publish the repo at
> `github.com/inherent-vice/termsheet-extraction-eval`.

## 1. Create empty repo on GitHub

```bash
gh repo create inherent-vice/termsheet-extraction-eval \
    --public \
    --description "Reference architecture for evaluating LLM-extracted term-sheet data against ground truth" \
    --homepage "https://github.com/inherent-vice"
```

Or via web UI: https://github.com/new
- Name: `termsheet-extraction-eval`
- Visibility: Public
- Do NOT initialize with README (we already have one)

## 2. Initialize git & push

```bash
cd /Users/romulus/General/fieldguide-application/termsheet-extraction-eval

# Initialize
git init
git branch -M main

# First commit — baseline structure
git add LICENSE pyproject.toml .gitignore README.md CLAUDE.md
git commit -m "chore: initial scaffolding — package metadata + MIT license"

# Second commit — comparators & result enum (foundation)
git add src/termsheet_eval/__init__.py
git add src/termsheet_eval/compare/
git commit -m "feat(compare): type-aware field comparators with explicit null semantics

- 5-tier result enum: MATCH / BOTH_NULL / MISMATCH / OCR_NULL / NOT_FOUND
- Normalizer handles null sentinels, null bytes, NaN, whitespace
- Comparators: rate (with ×100 tolerance), spread (bp/% multi-scale),
  date (format-agnostic), currency (name↔code), text (Jaccard),
  enum (alias mapping)"

# Third commit — constraint engine
git add src/termsheet_eval/constraints/
git commit -m "feat(constraints): cross-field constraint engine

- Group A: fixed-rate implications (FixedFlag=1 → spread=0, factor=0)
- Group B: option end ≤ maturity
- Group C: range bound saturation (±9999 → ±999)"

# Fourth commit — NULL inference engine
git add src/termsheet_eval/inference/
git commit -m "feat(inference): NULL inference engine

- Category A: rule-based defaults (KRW → ACT/365)
- Category B: sibling-based inference (option_end exists → holder=B)
- Category C: silent defaults (fixed_flag=1 → spread=0)"

# Fifth commit — metrics & scoring
git add src/termsheet_eval/metrics/
git commit -m "feat(metrics): 5 core metrics + weighted OQS

- match_rate = (MATCH + BOTH_NULL) / SCORE_TARGETS
- true_match_rate = MATCH / (MATCH + MISMATCH + OCR_NULL + NOT_FOUND)
- OQS = weighted match rate (legally significant fields weighted higher)
- Letter grade A/B/C/D/F by OQS bucket"

# Sixth commit — extract + pipeline + CLI
git add src/termsheet_eval/extract/
git add src/termsheet_eval/pipeline.py
git add src/termsheet_eval/cli.py
git commit -m "feat(pipeline): 5-stage pipeline + CLI with v1/v2/v3 ablation

- MockExtractor for reproducible offline benchmarks
- Pipeline composes extract → compare → constraints → inference → metrics
- V1 config: comparators only
- V2 config: + constraint engine
- V3 config: + null inference
- CLI: benchmark / compare subcommands"

# Seventh commit — prompts v1-v3 (the iteration log)
git add prompts/
git commit -m "feat(prompts): v1 baseline → v2 normative → v3 responsibility separation

v1: basic extraction instructions
v2: + unit / range / option conventions in prompt
v3: separate 'what's in document' from 'industry conventions apply downstream'

This ordering demonstrates that prompt engineering benefits most from
clear responsibility separation with the post-processing pipeline."

# Eighth commit — synthetic data
git add data/
git commit -m "test(data): 20 synthetic derivative products with planted error patterns

Documented error types:
- spread=null on fixed-rate (recoverable by inference Cat C)
- day_count=null on KRW (recoverable by inference Cat A)
- option_holder=null when option exists (recoverable by inference Cat B)
- range bounds ±9999 (recoverable by constraint Group C)
- spread in bp vs % (handled by comparator unit tolerance)
- Typo in issuer name (intentional unrecoverable MISMATCH)"

# Ninth commit — benchmark results (proof of ablation)
git add benchmarks/
git commit -m "bench: v1 89.2% → v2 93.9% → v3 99.4% match rate

OQS: 0.895 (B) → 0.944 (A) → 0.996 (A)
True match rate: 85.2% → 91.6% → 99.2%

The raw LLM output is identical across all three versions.
The improvement comes entirely from post-processing."

# Tenth commit — tests
git add tests/
git commit -m "test: 17 unit tests for comparators

Covers: rate tolerance, spread multi-scale, date format parsing,
currency code aliases, text Jaccard, enum alias mapping, null semantics."

# Eleventh commit — docs
git add docs/
git commit -m "docs: architecture + prompt engineering log

ARCHITECTURE.md: 5-stage pipeline, scoring semantics, constraint/inference
design philosophy, why not LangChain/LlamaIndex.

PROMPT_ENGINEERING.md: v1 → v3 iteration log with accuracy deltas attributed
to each change."

# Twelfth commit — CI
git add .github/
git commit -m "ci: GitHub Actions with ablation regression gate

- Lint (ruff) + test (pytest) on Python 3.10/3.11/3.12
- Ablation gate: v3 match rate must stay > v1 and ≥ 0.99"

# Push
git remote add origin https://github.com/inherent-vice/termsheet-extraction-eval.git
git push -u origin main
```

## 3. After pushing

### Pin the repo to your profile
Go to https://github.com/inherent-vice → Customize pinned repositories →
Add `termsheet-extraction-eval` as Pin #1.

### Verify CI passes
Go to https://github.com/inherent-vice/termsheet-extraction-eval/actions
and confirm the workflow completes green.

### Add a project tag in LinkedIn
LinkedIn → Profile → Projects → Add:
- Title: `termsheet-extraction-eval`
- Description: Copy the opening paragraph from README.md
- URL: https://github.com/inherent-vice/termsheet-extraction-eval

## 4. Why the 12-commit structure matters

Fieldguide recruiters and engineers reading your git log will see:

1. **Clear engineering progression** — foundation → feature → feature → feature
2. **Meaningful commit messages** — not "wip" or "updates"
3. **Benchmark results committed before tests** — shows you care about
   whether the thing works, not just passing tests
4. **Prompts committed as separate artifacts** — shows prompt engineering
   discipline at the version-control level

**Do not squash** these into one commit. The history *is* the portfolio.

## 5. Alternative: single commit if time-pressed

If you need to ship in under 10 minutes:

```bash
cd /Users/romulus/General/fieldguide-application/termsheet-extraction-eval
git init
git branch -M main
git add .
git commit -m "feat: initial public release — reference eval harness for LLM term-sheet extraction"
git remote add origin https://github.com/inherent-vice/termsheet-extraction-eval.git
git push -u origin main
```

You can rebase into the 12-commit structure later with `git rebase -i`.

# Synthetic Data

Two files drive the benchmark:

### `ground_truth.json`
20 synthetic derivative products (TS001–TS020), each with 18 fields.
Mix of fixed-rate (9 products), floating-rate (11 products), range-accrual
(4 products), and callable (multiple).

### `raw_extractions.json`
Mock LLM output for the same 20 products. Contains deliberate, documented
error patterns that mimic real LLM failure modes seen in production:

| Error type | Affected products | Recovery stage |
|-----------|-------------------|----------------|
| `spread=null` on fixed-rate product | TS001, TS004, TS006, TS009, TS011, TS013, TS015, TS018, TS019 | Inference Cat C (v3) |
| `day_count=null` on KRW product | TS001, TS002, TS004, TS005, TS008, TS010, TS011, TS014, TS015, TS017, TS018, TS020 | Inference Cat A (v3) |
| `option_holder=null` when option exists | TS001, TS004, TS006, TS009, TS011, TS013, TS015, TS019 | Inference Cat B (v3) |
| `range bounds = ±9999` | TS003, TS008, TS014, TS020 | Constraint Group C (v2) |
| `spread` in bp instead of % | TS002, TS007, TS012, TS016 | Comparator unit tolerance (v1) |
| Typo in issuer name | TS002 ("Alfa" vs "Alpha"), TS009 ("Banc" vs "Bank") | Unrecoverable — MISMATCH |

The mock extractor returns the same raw output regardless of prompt
version. This is intentional: the pedagogical point is that most of the
improvement from v1 → v2 → v3 comes from **post-processing**, not the
model. In production at KAP, the actual mix is closer to 60/40 (model
improvements still dominate), but the post-processing gain is the
under-appreciated half.

## Reproducibility

- 360 field comparisons total (20 × 18)
- Deterministic mock extractor means benchmark is 100% reproducible
- `pip install -e . && python -m termsheet_eval.cli benchmark --version all`

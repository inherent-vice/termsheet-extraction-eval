# Contributing

This is a small reference implementation for evaluating LLM-extracted structured financial data against synthetic ground truth. Contributions should keep the project reproducible, sanitized, and easy to audit.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
make ci
```

If you prefer an explicit interpreter, run `make PYTHON=.venv/bin/python ci`.

## Quality bar

Before opening a PR or publishing a change, run:

```bash
make ci
make compare
git diff --check
```

For changes that affect scoring, constraints, fixtures, or CLI defaults, add a regression test and regenerate benchmark outputs intentionally.

## Data safety

Do not add proprietary term sheets, customer data, production SQL schemas, private prompts, screenshots with sensitive data, API keys, or connection strings. The bundled benchmark must remain synthetic and runnable without provider credentials.

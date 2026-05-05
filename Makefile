PYTHON ?= python

.PHONY: install test lint benchmark compare ci clean

install:
	$(PYTHON) -m pip install -e '.[dev]'

lint:
	$(PYTHON) -m ruff check src tests

test:
	$(PYTHON) -m pytest tests -q

benchmark:
	$(PYTHON) -m termsheet_eval.cli benchmark --version all

compare:
	$(PYTHON) -m termsheet_eval.cli compare \
		--ground-truth data/synthetic/ground_truth.json \
		--raw-extractions data/synthetic/raw_extractions.json \
		--product-id TS001 \
		--version v3

ci: lint test benchmark

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info benchmarks/results
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

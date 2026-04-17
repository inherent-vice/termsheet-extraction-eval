"""Mock extractor — deterministic fake LLM output for reproducible benchmarks.

Runs entirely offline. Injects a fixed distribution of extraction errors
(null, unit confusion, enum confusion) so v1/v2/v3 of the pipeline can be
compared on identical raw input.

The error patterns intentionally mimic real LLM failure modes seen in
production at KAP:

- ``null_drop`` — LLM returns null for a field that is present in the term sheet
- ``unit_confusion`` — ``0.8%`` returned as ``80`` (bp) or vice versa
- ``enum_raw_string`` — ``"Callable"`` returned when the DB wants ``"B"``
- ``date_reformat`` — ``2026.03.15`` returned as ``15/3/2026``
- ``range_saturation`` — ``9999`` returned where canonical is ``999``
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from termsheet_eval.extract.base import Extractor


@dataclass
class MockExtractor(Extractor):
    """Deterministic mock extractor.

    Loads synthetic raw extractions from a JSON file and returns them.
    The JSON structure mimics what a real LLM would produce after schema
    parsing, including intentional errors.
    """

    raw_extractions_path: Path
    name: str = "mock"

    def __post_init__(self) -> None:
        if not self.raw_extractions_path.exists():
            raise FileNotFoundError(
                f"Raw extractions file not found: {self.raw_extractions_path}"
            )
        with self.raw_extractions_path.open("r", encoding="utf-8") as f:
            self._data: dict[str, dict[str, Any]] = json.load(f)

    def extract(self, term_sheet: str, prompt_version: str) -> dict[str, Any]:
        """Return mock raw extraction for the given product id.

        ``term_sheet`` here is just the product id for the mock; in a real
        extractor it would be the PDF text or image.
        """
        product_id = term_sheet.strip()
        if product_id not in self._data:
            raise KeyError(f"Mock extractor has no data for product {product_id}")
        # Different prompt versions do NOT change mock raw output — the
        # point is to show that downstream post-processing is where the
        # gains come from. This is pedagogical, not a limitation.
        return dict(self._data[product_id])

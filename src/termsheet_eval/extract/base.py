"""LLM extractor base protocol.

All provider adapters implement :class:`Extractor`. The interface is
intentionally minimal — ``extract(term_sheet_text, prompt_version)`` returns
a dict keyed by field name. Provider-specific parameters stay inside the
adapter, so the pipeline never needs to branch on which LLM it's talking to.
"""
from __future__ import annotations

from typing import Any, Protocol


class ExtractionError(Exception):
    """Raised when the LLM returns malformed output we cannot recover from."""


class Extractor(Protocol):
    """Protocol every LLM adapter must satisfy."""

    name: str

    def extract(self, term_sheet: str, prompt_version: str) -> dict[str, Any]:
        """Return a dict of extracted field values.

        ``prompt_version`` selects the system prompt (e.g. "v1", "v2", "v3").
        Unknown fields should be mapped to ``None``; the pipeline uses
        that signal to distinguish ``OCR_NULL`` from ``DB_NULL``.
        """
        ...

"""Normalization — the layer that turns 'looks similar' into actually equal.

In production, null-byte artifacts from binary decoding, NaN from pandas,
stray whitespace, and mixed-case sentinel strings are the top sources of
false MISMATCH calls. This module exists to flatten all of that before
type-specific comparators run.
"""
from __future__ import annotations

import math
import re
from typing import Any

_NULL_SENTINELS: frozenset[str] = frozenset({
    "", "nan", "null", "none", "n/a", "na", "-", "\x00",
})


def normalize_value(val: Any) -> str | None:
    """Normalize an arbitrary value to str or None.

    Handles:
    - Python None
    - Pandas NaN (float)
    - Null-byte artifacts from binary decoding
    - Case-insensitive null sentinels
    - Leading/trailing whitespace
    """
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    if not s:
        return None
    if s.lower() in _NULL_SENTINELS:
        return None
    # Null-byte contamination (seen in production with some OCR back-ends)
    if "\x00" in s:
        s = s.replace("\x00", "").strip()
        if not s:
            return None
    return s


def normalize_numeric(val: Any) -> float | None:
    """Parse a value as a float, tolerating % suffix and comma thousands."""
    s = normalize_value(val)
    if s is None:
        return None
    s = s.replace(",", "").rstrip("%").strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


_TOKEN_SPLIT = re.compile(r"[\s,;/()\[\]]+")


def tokenize(val: Any) -> frozenset[str]:
    """Token set for Jaccard-style text similarity."""
    s = normalize_value(val)
    if s is None:
        return frozenset()
    tokens = _TOKEN_SPLIT.split(s.lower())
    return frozenset(t for t in tokens if t)

"""
RFC 8785 JSON Canonicalization Scheme (JCS) Implementation.
Provides deterministic byte serialization for cryptographic signing.
FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

import json
from typing import Any, Dict
import rfc8785


def canonicalize_json(data: Dict[str, Any]) -> bytes:
    """
    Produce canonical byte sequence conforming to RFC 8785 (JCS).
    Key ordering is lexicographical, whitespace is eliminated,
    floating point numbers are formatted according to ECMAScript standard.
    """
    if not isinstance(data, dict):
        raise TypeError(f"canonicalize_json requires a dictionary, got {type(data).__name__}")
    return rfc8785.dumps(data)


def canonicalize_and_validate_size(data: Dict[str, Any], max_bytes: int = 4096) -> bytes:
    """
    Canonicalize JSON and enforce the Architecture v1.2 contract size limit.
    Initial profile limits canonical message to 4096 bytes.
    """
    raw_bytes = canonicalize_json(data)
    if len(raw_bytes) > max_bytes:
        raise ValueError(
            f"Canonical JSON size ({len(raw_bytes)} bytes) exceeds contract limit ({max_bytes} bytes)"
        )
    return raw_bytes

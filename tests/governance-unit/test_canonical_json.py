"""Unit tests for RFC 8785 JSON Canonicalization Scheme (JCS)."""

import pytest
from fcs_governance.crypto.canonical import canonicalize_and_validate_size, canonicalize_json


def test_rfc8785_key_sorting():
    """Verify that JSON keys are ordered lexicographically per RFC 8785."""
    data = {"zebra": 1, "apple": 2, "mango": 3}
    canonical = canonicalize_json(data)
    assert canonical == b'{"apple":2,"mango":3,"zebra":1}'


def test_rfc8785_no_whitespace():
    """Verify that unnecessary whitespace is eliminated."""
    data = {"key": [1, 2, {"nested": "value"}]}
    canonical = canonicalize_json(data)
    assert b" " not in canonical
    assert b"\n" not in canonical
    assert canonical == b'{"key":[1,2,{"nested":"value"}]}'


def test_canonicalize_and_validate_size_limit():
    """Verify enforcement of the 4096-byte canonical manifest contract limit."""
    small_data = {"release_id": "test", "data": "small"}
    assert len(canonicalize_and_validate_size(small_data, max_bytes=4096)) < 4096

    large_data = {"release_id": "test", "payload": "x" * 5000}
    with pytest.raises(ValueError, match="exceeds contract limit"):
        canonicalize_and_validate_size(large_data, max_bytes=4096)

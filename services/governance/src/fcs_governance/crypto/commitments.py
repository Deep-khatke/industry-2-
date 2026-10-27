"""
Privacy-Preserving Audit Commitments using Hiding Merkle Trees.
Enables verifiable audit batch anchoring on-chain without leaking private incident telemetry.
FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

import hashlib
import os
from typing import List, Tuple
from ..contracts.models import AuditBatchRecord


class AuditCommitmentTree:
    """
    Constructs a domain-separated, salt-blinded Merkle tree over an audit batch.
    Leaves are: SHA-384(DOMAIN_SEP || salt || canonical_audit_event_bytes)
    """

    DOMAIN_SEPARATOR = b"FCS_AUDIT_MERKLE_V1"

    def __init__(self, batch_id: str, raw_event_payloads: List[bytes], salt: bytes | None = None):
        if not raw_event_payloads:
            raise ValueError("Audit batch cannot be empty")

        self.batch_id = batch_id
        self.raw_event_payloads = raw_event_payloads
        self.salt = salt or os.urandom(32)
        self.leaves = [self._hash_leaf(payload) for payload in raw_event_payloads]
        self.tree_levels = self._build_tree(self.leaves)
        self.root = self.tree_levels[-1][0]

    def _hash_leaf(self, payload: bytes) -> bytes:
        """Domain-separated, salt-blinded leaf hash using SHA-384."""
        h = hashlib.sha384()
        h.update(self.DOMAIN_SEPARATOR)
        h.update(b":LEAF:")
        h.update(self.salt)
        h.update(payload)
        return h.digest()

    @staticmethod
    def _hash_internal(left: bytes, right: bytes) -> bytes:
        """Domain-separated parent node hash using SHA-384."""
        h = hashlib.sha384()
        h.update(b"FCS_AUDIT_MERKLE_V1:NODE:")
        h.update(left)
        h.update(right)
        return h.digest()

    def _build_tree(self, leaves: List[bytes]) -> List[List[bytes]]:
        """Construct balanced Merkle tree levels."""
        levels = [leaves]
        current = leaves
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else current[i]
                next_level.append(self._hash_internal(left, right))
            levels.append(next_level)
            current = next_level
        return levels

    def get_merkle_root_hex(self) -> str:
        """Return the root hash as hexadecimal string."""
        return self.root.hex()

    def get_salt_hex(self) -> str:
        """Return random blinding salt as hexadecimal string."""
        return self.salt.hex()

    def create_batch_record(self) -> AuditBatchRecord:
        """Generate AuditBatchRecord contract to submit on-chain."""
        return AuditBatchRecord(
            batch_id=self.batch_id,
            merkle_root_hex=self.get_merkle_root_hex(),
            leaf_count=len(self.raw_event_payloads),
            random_salt_hex=self.get_salt_hex(),
            domain_separator="FCS_AUDIT_MERKLE_V1",
        )

    def generate_proof(self, index: int) -> List[Tuple[str, str]]:
        """Generate Merkle audit path for the leaf at given index."""
        if not (0 <= index < len(self.leaves)):
            raise IndexError("Index out of bounds")

        proof = []
        idx = index
        for level in self.tree_levels[:-1]:
            is_right = (idx % 2 == 1)
            sibling_idx = idx - 1 if is_right else (idx + 1 if idx + 1 < len(level) else idx)
            proof.append(("left" if is_right else "right", level[sibling_idx].hex()))
            idx //= 2
        return proof

    @classmethod
    def verify_proof(
        cls,
        root_hex: str,
        leaf_payload: bytes,
        salt_hex: str,
        proof: List[Tuple[str, str]],
    ) -> bool:
        """Verify an inclusion proof against the committed Merkle root."""
        salt = bytes.fromhex(salt_hex)
        h = hashlib.sha384()
        h.update(cls.DOMAIN_SEPARATOR)
        h.update(b":LEAF:")
        h.update(salt)
        h.update(leaf_payload)
        current = h.digest()

        for direction, sibling_hex in proof:
            sibling = bytes.fromhex(sibling_hex)
            left = sibling if direction == "left" else current
            right = current if direction == "left" else sibling
            current = cls._hash_internal(left, right)

        return current.hex() == root_hex

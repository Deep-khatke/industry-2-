"""
Cryptographic Trust Store and Public Key Management.
Manages key registration, key rotation, revocation, expiration, and trust-anchor validation.
FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ..contracts.manifest import SignatureAlgorithm


class KeyStatus(str, Enum):
    """Lifecycle status of a registered cryptographic key."""
    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class TrustedKeyEntry(BaseModel):
    """Metadata record for a registered public key."""
    key_id: str
    algorithm: SignatureAlgorithm
    public_key_hex: str
    owner_org: str
    status: KeyStatus = KeyStatus.ACTIVE
    valid_from: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_until: str
    revocation_reason: Optional[str] = None
    revoked_at: Optional[str] = None


class TrustStore:
    """Manages trusted public key anchors, verification, and rotation."""

    def __init__(self):
        self._keys: Dict[str, TrustedKeyEntry] = {}

    def register_key(
        self,
        key_id: str,
        algorithm: SignatureAlgorithm,
        public_key_hex: str,
        owner_org: str,
        valid_until: str,
    ) -> TrustedKeyEntry:
        """Register a public key in the trust store."""
        entry = TrustedKeyEntry(
            key_id=key_id,
            algorithm=algorithm,
            public_key_hex=public_key_hex,
            owner_org=owner_org,
            valid_until=valid_until,
            status=KeyStatus.ACTIVE,
        )
        self._keys[key_id] = entry
        return entry

    def get_key(self, key_id: str) -> Optional[TrustedKeyEntry]:
        """Retrieve key metadata by key_id."""
        return self._keys.get(key_id)

    def is_key_trusted(self, key_id: str, public_key_hex: str) -> bool:
        """
        Verify that key_id is registered, matches public_key_hex,
        is in ACTIVE status, and has not expired.
        """
        entry = self._keys.get(key_id)
        if not entry:
            return False
        if entry.public_key_hex != public_key_hex:
            return False
        if entry.status != KeyStatus.ACTIVE:
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        if now_iso > entry.valid_until:
            entry.status = KeyStatus.EXPIRED
            return False

        return True

    def revoke_key(self, key_id: str, reason: str) -> None:
        """Revoke a compromised or retired key immediately."""
        entry = self._keys.get(key_id)
        if not entry:
            raise KeyError(f"Key ID {key_id} not found in trust store")
        entry.status = KeyStatus.REVOKED
        entry.revocation_reason = reason
        entry.revoked_at = datetime.now(timezone.utc).isoformat()

    def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str,
        new_public_key_hex: str,
        valid_until: str,
    ) -> TrustedKeyEntry:
        """Rotate an active key to a new key, marking the old one ROTATED."""
        old_entry = self._keys.get(old_key_id)
        if not old_entry:
            raise KeyError(f"Key ID {old_key_id} not found in trust store")
        old_entry.status = KeyStatus.ROTATED

        return self.register_key(
            key_id=new_key_id,
            algorithm=old_entry.algorithm,
            public_key_hex=new_public_key_hex,
            owner_org=old_entry.owner_org,
            valid_until=valid_until,
        )

    def list_keys(self) -> List[TrustedKeyEntry]:
        """List all registered keys."""
        return list(self._keys.values())

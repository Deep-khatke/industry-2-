"""ParticipantAdmissionValidator: Client-side round manifest governance and verification."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from fcs_pfl.contracts.manifests import RoundManifest

logger = logging.getLogger(__name__)

LOCKED_FEATURE_SCHEMA_DIGEST = "92f73ab100db06d82b252e0c86fac983083232fb247baf1cdf57afd6ba8dcbf0"


class ParticipantAdmissionValidator:
    """
    Validates that a training request received from the coordinator strictly adheres
    to tenant-authorized code digests, schema locks, cohort membership, and replay protection.
    """

    def __init__(self, tenant_id: str = "isp_01", approved_coordinator_id: str = "fcs_dev_coordinator_signed") -> None:
        self.tenant_id = tenant_id
        self.approved_coordinator_id = approved_coordinator_id
        self._seen_nonces: Set[str] = set()
        self._last_sequence: int = 0

    def validate(self, manifest: RoundManifest, participant_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Convenience method returning (is_valid, reason)."""
        pid = participant_id or self.tenant_id
        old_id = self.tenant_id
        self.tenant_id = pid
        res = self.validate_manifest(manifest)
        self.tenant_id = old_id
        if res["is_admitted"]:
            return True, None
        return False, "; ".join(res["reasons"])

    def validate_manifest(self, manifest: RoundManifest) -> Dict[str, Any]:
        """
        Conducts client-side pre-flight admission checks before joining a training round.
        Returns dict with is_admitted bool and reason list.
        """
        reasons: List[str] = []

        # 1. Verify coordinator signature/identity
        if manifest.coordinator_signature != self.approved_coordinator_id:
            reasons.append(f"UNAUTHORIZED_COORDINATOR: '{manifest.coordinator_signature}' does not match approved '{self.approved_coordinator_id}'")

        # 2. Check cohort membership
        if self.tenant_id not in manifest.cohort:
            reasons.append(f"NOT_IN_COHORT: Tenant '{self.tenant_id}' is not in approved cohort {manifest.cohort}")

        # 3. Check feature schema digest lock
        if manifest.feature_schema_digest != LOCKED_FEATURE_SCHEMA_DIGEST:
            reasons.append(f"SCHEMA_MISMATCH: Manifest digest '{manifest.feature_schema_digest}' != locked '{LOCKED_FEATURE_SCHEMA_DIGEST}'")

        # 4. Check replay attack protection (nonce & sequence)
        if manifest.nonce in self._seen_nonces:
            reasons.append(f"REPLAY_ATTACK_DETECTED: Nonce '{manifest.nonce}' has already been processed")
        if manifest.sequence <= self._last_sequence and self._last_sequence > 0:
            reasons.append(f"INVALID_SEQUENCE: Sequence {manifest.sequence} <= last sequence {self._last_sequence}")

        # 5. Check manifest expiration if specified
        if manifest.valid_until:
            try:
                valid_dt = datetime.fromisoformat(manifest.valid_until)
                if datetime.now(UTC) > valid_dt:
                    reasons.append(f"MANIFEST_EXPIRED: Manifest validity expired at {manifest.valid_until}")
            except Exception:
                reasons.append(f"MALFORMED_VALID_UNTIL: '{manifest.valid_until}' is invalid ISO datetime")

        is_admitted = len(reasons) == 0
        if is_admitted:
            self._seen_nonces.add(manifest.nonce)
            self._last_sequence = manifest.sequence

        return {
            "is_admitted": is_admitted,
            "reasons": reasons,
            "round_id": manifest.round_id,
            "tenant_id": self.tenant_id,
        }

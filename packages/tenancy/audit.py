"""Security audit logging with tamper-evident cryptographic chaining."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Structured security audit record."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str | None = None
    principal_id: str
    action: str
    target_resource: str
    outcome: str = Field(..., description="'ALLOWED', 'DENIED', or 'VIOLATION'")
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = Field(default="0" * 64)
    record_hash: str = Field(default="")

    def compute_hash(self) -> str:
        """Compute SHA-256 hash across canonical representation of record fields and prev_hash."""
        canonical_dict = {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "principal_id": self.principal_id,
            "action": self.action,
            "target_resource": self.target_resource,
            "outcome": self.outcome,
            "reason": self.reason,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
        }
        serialized = json.dumps(canonical_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def seal(self, prev_hash: str = "0" * 64) -> "AuditEvent":
        """Set prev_hash and finalize record_hash."""
        self.prev_hash = prev_hash
        self.record_hash = self.compute_hash()
        return self


class AuditLogger:
    """Tamper-evident append-only in-memory audit log with cryptographic chaining."""

    def __init__(self) -> None:
        self._records: list[AuditEvent] = []
        self._last_hash: str = "0" * 64

    def log(
        self,
        principal_id: str,
        action: str,
        target_resource: str,
        outcome: str,
        tenant_id: str | None = None,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Record and seal a new security audit event."""
        event = AuditEvent(
            tenant_id=tenant_id,
            principal_id=principal_id,
            action=action,
            target_resource=target_resource,
            outcome=outcome,
            reason=reason,
            metadata=metadata or {},
        )
        event.seal(self._last_hash)
        self._last_hash = event.record_hash
        self._records.append(event)
        return event

    def get_records(self, tenant_id: str | None = None) -> list[AuditEvent]:
        """Retrieve audit records, optionally filtered by tenant_id."""
        if tenant_id is None:
            return list(self._records)
        return [r for r in self._records if r.tenant_id == tenant_id]

    def verify_integrity(self) -> tuple[bool, str]:
        """Verify the cryptographic hash chain of all stored audit records."""
        expected_prev = "0" * 64
        for idx, record in enumerate(self._records):
            if record.prev_hash != expected_prev:
                return False, f"Integrity broken at index {idx}: prev_hash mismatch."
            recomputed = record.compute_hash()
            if record.record_hash != recomputed:
                return False, f"Integrity broken at index {idx}: record_hash tampered."
            expected_prev = record.record_hash
        return True, "Audit log cryptographic integrity intact."

    def to_json_lines(self) -> str:
        """Export records as serialized JSON Lines."""
        return "\n".join(r.model_dump_json() for r in self._records)

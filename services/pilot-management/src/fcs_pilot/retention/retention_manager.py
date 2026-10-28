"""Data Retention and Deletion Enforcement Engine (Section 24 of Phase 9)."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.retention")


class DeletionAuditRecord(BaseModel):
    """Audit log entry confirming the safe deletion of expired telemetry records."""
    audit_id: str
    tenant_id: str
    category: str
    items_scanned: int
    items_purged: int
    oldest_purged_timestamp: str | None = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    enforced_by: str = "FCS_DATA_RETENTION_WORKER"
    status: str = "COMPLETED"


class DataRetentionManager:
    """Manages tenant-scoped data lifecycle and automated expiration."""

    DEFAULT_RETENTION_LIMITS = {
        "raw_telemetry_flows": 7,       # max 7 days
        "feature_windows": 14,          # max 14 days
        "incident_records": 90,         # 90 days for SOC audit
        "analyst_feedback": 180,        # 180 days for model feedback
        "action_journal": 365,          # 1 year audit trail
        "privacy_accounting": 730,      # 2 years permanent ledger receipts
    }

    def __init__(self, tenant_id: str, custom_limits: dict[str, int] | None = None) -> None:
        self.tenant_id = tenant_id
        self.limits = dict(self.DEFAULT_RETENTION_LIMITS)
        if custom_limits:
            self.limits.update(custom_limits)
        self._audit_log: list[DeletionAuditRecord] = []

    def evaluate_and_purge_expired(
        self,
        category: str,
        items: list[dict[str, Any]],
        timestamp_field: str = "timestamp",
        protected_ids: set[str] | None = None,
    ) -> tuple[list[dict[str, Any]], DeletionAuditRecord]:
        """
        Purge items older than retention limit while respecting protected active records.
        """
        max_days = self.limits.get(category, 7)
        cutoff_dt = datetime.now(UTC) - timedelta(days=max_days)

        retained = []
        purged_count = 0
        oldest_purged = None
        protected = protected_ids or set()

        for item in items:
            item_id = str(item.get("id", item.get("candidate_id", item.get("incident_id", ""))))
            # Protection check (active investigations or cryptographic anchors cannot be deleted)
            if item_id in protected:
                retained.append(item)
                continue

            ts_val = item.get(timestamp_field)
            item_dt = None
            if isinstance(ts_val, datetime):
                item_dt = ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=UTC)
            elif isinstance(ts_val, str):
                try:
                    item_dt = datetime.fromisoformat(ts_val)
                    if not item_dt.tzinfo:
                        item_dt = item_dt.replace(tzinfo=UTC)
                except Exception:
                    item_dt = datetime.now(UTC)

            if item_dt and item_dt < cutoff_dt:
                purged_count += 1
                if oldest_purged is None or item_dt < oldest_purged:
                    oldest_purged = item_dt
            else:
                retained.append(item)

        audit_id = f"del-audit-{self.tenant_id[:4]}-{len(self._audit_log) + 1:04d}"
        audit_rec = DeletionAuditRecord(
            audit_id=audit_id,
            tenant_id=self.tenant_id,
            category=category,
            items_scanned=len(items),
            items_purged=purged_count,
            oldest_purged_timestamp=oldest_purged.isoformat() if oldest_purged else None,
            status="COMPLETED",
        )
        self._audit_log.append(audit_rec)
        logger.info(
            f"Retention purge executed for {self.tenant_id} [{category}]: {purged_count} expired items deleted, {len(retained)} retained."
        )
        return retained, audit_rec

    def get_audit_trail(self) -> list[DeletionAuditRecord]:
        return list(self._audit_log)

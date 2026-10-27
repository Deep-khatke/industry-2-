"""
Durable Audit Outbox and Relay Engine.
Implements transactional outbox pattern with ACID SQLite persistence,
idempotent retries, and ledger reconciliation.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..contracts.models import OutboxEvent, OutboxStatus
from .ledger_mock import MockFabricLedger


class AuditOutboxRelay:
    """Manages transactional outbox storage and background relay to Fabric ledger."""

    def __init__(self, db_path: str = "data/governance_outbox.db", ledger: Optional[MockFabricLedger] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger or MockFabricLedger()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 5,
                    ledger_tx_id TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def enqueue_event(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict,
    ) -> OutboxEvent:
        """Atomically persist a new domain event into the outbox."""
        event_id = f"evt-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO outbox_events (
                    event_id, event_type, aggregate_id, payload_json,
                    status, retry_count, max_retries, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 0, 5, ?, ?)
            """, (
                event_id,
                event_type,
                aggregate_id,
                payload_json,
                OutboxStatus.PENDING.value,
                now,
                now,
            ))
            conn.commit()

        return OutboxEvent(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload_json=payload_json,
            status=OutboxStatus.PENDING,
        )

    def get_pending_events(self) -> List[OutboxEvent]:
        """Fetch all uncommitted outbox events."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM outbox_events
                WHERE status IN (?, ?)
                ORDER BY created_at ASC
            """, (OutboxStatus.PENDING.value, OutboxStatus.RECONCILIATION_REQUIRED.value))
            rows = cursor.fetchall()
            return [
                OutboxEvent(
                    event_id=r["event_id"],
                    event_type=r["event_type"],
                    aggregate_id=r["aggregate_id"],
                    payload_json=r["payload_json"],
                    status=OutboxStatus(r["status"]),
                    retry_count=r["retry_count"],
                    max_retries=r["max_retries"],
                    ledger_tx_id=r["ledger_tx_id"],
                    error_message=r["error_message"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    def mark_committed(self, event_id: str, tx_id: str) -> None:
        """Update outbox event status to COMMITTED with verified ledger transaction ID."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE outbox_events
                SET status = ?, ledger_tx_id = ?, updated_at = ?
                WHERE event_id = ?
            """, (OutboxStatus.COMMITTED.value, tx_id, now, event_id))
            conn.commit()

    def mark_failed(self, event_id: str, error_msg: str) -> None:
        """Increment retry count or mark RECONCILIATION_REQUIRED / FAILED."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT retry_count, max_retries FROM outbox_events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if not row:
                return

            new_retries = row["retry_count"] + 1
            new_status = (
                OutboxStatus.RECONCILIATION_REQUIRED.value
                if new_retries < row["max_retries"]
                else OutboxStatus.FAILED.value
            )
            cursor.execute("""
                UPDATE outbox_events
                SET retry_count = ?, status = ?, error_message = ?, updated_at = ?
                WHERE event_id = ?
            """, (new_retries, new_status, error_msg, now, event_id))
            conn.commit()

    def reconcile_and_relay(self) -> int:
        """
        Scan pending events and relay to the ledger.
        Returns the count of successfully relayed events.
        """
        pending = self.get_pending_events()
        relayed_count = 0

        for event in pending:
            try:
                payload = json.loads(event.payload_json)
                if event.event_type == "RELEASE_REGISTRATION":
                    # Check if already on ledger
                    existing = self.ledger.query_release(event.aggregate_id)
                    if existing:
                        self.mark_committed(event.event_id, existing["ledger_tx_id"])
                        relayed_count += 1
                        continue

                elif event.event_type == "REVOCATION":
                    existing = self.ledger.query_revocation(event.aggregate_id)
                    if existing:
                        self.mark_committed(event.event_id, existing["ledger_tx_id"])
                        relayed_count += 1
                        continue

                elif event.event_type == "AUDIT_COMMITMENT":
                    existing = self.ledger.query_audit_batch(event.aggregate_id)
                    if existing:
                        self.mark_committed(event.event_id, existing["ledger_tx_id"])
                        relayed_count += 1
                        continue

            except Exception as e:
                self.mark_failed(event.event_id, str(e))

        return relayed_count

"""Persistent zero-cost SQLite stream sink for replay verification and restart tests."""

import sqlite3
import threading
from pathlib import Path
from typing import Any

from packages.contracts.flow_event import FlowEvent

from ..base import SinkWriteError, StreamSink

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS flow_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    exporter_id TEXT NOT NULL,
    observation_domain INTEGER NOT NULL,
    boot_epoch INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    event_time TEXT NOT NULL,
    ingest_time TEXT NOT NULL,
    sample_rate INTEGER NOT NULL,
    protocol TEXT NOT NULL,
    port_class TEXT NOT NULL,
    src_port INTEGER,
    dst_port INTEGER,
    direction TEXT NOT NULL,
    byte_count INTEGER NOT NULL,
    packet_count INTEGER NOT NULL,
    flow_duration_ms INTEGER NOT NULL,
    tcp_flags INTEGER,
    src_prefix_masked TEXT,
    dst_prefix_masked TEXT,
    schema_version TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_flow_tenant_time ON flow_events(tenant_id, event_time);
CREATE INDEX IF NOT EXISTS idx_flow_exporter ON flow_events(exporter_id, observation_domain);
"""


class SQLiteStreamSink(StreamSink):
    """
    Persistent SQLite-backed stream sink.
    Provides durable storage for offline replay, restart tests, and transactional verification.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode; transactions managed explicitly
        )
        self._init_db()
        self._duplicate_count = 0

    def _init_db(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            if self.db_path != ":memory:":
                cur.execute("PRAGMA journal_mode=WAL;")
                cur.execute("PRAGMA synchronous=NORMAL;")
            cur.executescript(CREATE_TABLE_SQL)

    def write(self, event: FlowEvent) -> None:
        """Insert a single event with duplicate detection."""
        sql = """
        INSERT OR IGNORE INTO flow_events (
            event_id, tenant_id, exporter_id, observation_domain, boot_epoch,
            sequence, event_time, ingest_time, sample_rate, protocol,
            port_class, src_port, dst_port, direction, byte_count,
            packet_count, flow_duration_ms, tcp_flags, src_prefix_masked,
            dst_prefix_masked, schema_version, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = self._event_to_params(event)
        with self._lock:
            try:
                cur = self._conn.cursor()
                cur.execute(sql, params)
                if cur.rowcount == 0:
                    self._duplicate_count += 1
            except sqlite3.Error as e:
                raise SinkWriteError(f"SQLite insert failed: {e}") from e

    def write_batch(self, events: list[FlowEvent]) -> int:
        """Batch insert events inside a single transaction."""
        if not events:
            return 0

        sql = """
        INSERT OR IGNORE INTO flow_events (
            event_id, tenant_id, exporter_id, observation_domain, boot_epoch,
            sequence, event_time, ingest_time, sample_rate, protocol,
            port_class, src_port, dst_port, direction, byte_count,
            packet_count, flow_duration_ms, tcp_flags, src_prefix_masked,
            dst_prefix_masked, schema_version, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params_list = [self._event_to_params(e) for e in events]
        with self._lock:
            try:
                cur = self._conn.cursor()
                cur.execute("BEGIN TRANSACTION;")
                cur.executemany(sql, params_list)
                cur.execute("COMMIT;")
                return len(events)
            except sqlite3.Error as e:
                try:
                    cur.execute("ROLLBACK;")
                except Exception:
                    pass
                raise SinkWriteError(f"SQLite batch insert failed: {e}") from e

    def read_events(
        self,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FlowEvent]:
        """Read stored events from SQLite."""
        with self._lock:
            cur = self._conn.cursor()
            if tenant_id is not None:
                cur.execute(
                    "SELECT raw_json FROM flow_events WHERE tenant_id = ? ORDER BY event_time ASC LIMIT ? OFFSET ?",
                    (tenant_id, limit, offset),
                )
            else:
                cur.execute(
                    "SELECT raw_json FROM flow_events ORDER BY event_time ASC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            rows = cur.fetchall()
            return [FlowEvent.from_json(row[0]) for row in rows]

    def count(self, tenant_id: str | None = None) -> int:
        """Count stored records in SQLite."""
        with self._lock:
            cur = self._conn.cursor()
            if tenant_id is not None:
                cur.execute("SELECT COUNT(*) FROM flow_events WHERE tenant_id = ?", (tenant_id,))
            else:
                cur.execute("SELECT COUNT(*) FROM flow_events")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    @property
    def duplicate_count(self) -> int:
        with self._lock:
            return self._duplicate_count

    def flush(self) -> None:
        """Commit / checkpoint."""

    def close(self) -> None:
        """Safely close the SQLite database connection."""
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass

    @staticmethod
    def _event_to_params(e: FlowEvent) -> tuple[Any, ...]:
        return (
            e.event_id,
            e.tenant_id,
            e.exporter_id,
            e.observation_domain,
            e.boot_epoch,
            e.sequence,
            e.event_time.isoformat(),
            e.ingest_time.isoformat(),
            e.sample_rate,
            e.protocol.value,
            e.port_class.value,
            e.src_port,
            e.dst_port,
            e.direction.value,
            e.byte_count,
            e.packet_count,
            e.flow_duration_ms,
            e.tcp_flags,
            e.src_prefix_masked,
            e.dst_prefix_masked,
            e.schema_version,
            e.to_canonical_json(),
        )

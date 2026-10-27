"""
Deterministic Fabric / SmartBFT Consortium Ledger Engine.
Provides zero-cost ACID SQLite persistence, 4-orderer SmartBFT simulation,
and 3-of-4 peer endorsement verification.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..contracts.models import (
    AuditBatchRecord,
    EndorsementRecord,
    ReleaseRecord,
    RevocationRecord,
)
from ..contracts.state import ReleaseState
from .endorsement import EndorsementPolicyEvaluator
from .topology import SmartBFTClusterConfig


class LedgerCommitError(Exception):
    """Raised when a ledger transaction fails validation or ordering."""
    pass


class QuorumLossError(LedgerCommitError):
    """Raised when SmartBFT consensus fails due to insufficient active orderers."""
    pass


class MockFabricLedger:
    """
    ACID-compliant Fabric ledger implementation backed by embedded SQLite.
    Accurately models SmartBFT consensus ordering and endorsement verification.
    """

    def __init__(self, db_path: str = "data/consortium_ledger.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.bft_config = SmartBFTClusterConfig()
        # Orderer health map (4 orderers in cluster)
        self.orderer_health: Dict[str, bool] = {
            "orderer1.fcs.net": True,
            "orderer2.fcs.net": True,
            "orderer3.fcs.net": True,
            "orderer4.fcs.net": True,
        }
        self.is_connected: bool = True
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_releases (
                    release_id TEXT PRIMARY KEY,
                    manifest_digest_sha384 TEXT NOT NULL,
                    artifact_digest_sha384 TEXT NOT NULL,
                    evaluation_digest TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    model_lineage_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    revocation_id TEXT,
                    committed_at TIMESTAMP NOT NULL,
                    ledger_tx_id TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    endorsements_json TEXT NOT NULL,
                    full_record_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_revocations (
                    revocation_id TEXT PRIMARY KEY,
                    target_release_id TEXT NOT NULL,
                    revoking_org TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    details TEXT NOT NULL,
                    revocation_digest_sha384 TEXT NOT NULL,
                    ledger_tx_id TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY(target_release_id) REFERENCES ledger_releases(release_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_audit_batches (
                    batch_id TEXT PRIMARY KEY,
                    merkle_root_hex TEXT NOT NULL,
                    leaf_count INTEGER NOT NULL,
                    random_salt_hex TEXT NOT NULL,
                    domain_separator TEXT NOT NULL,
                    ledger_tx_id TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_blocks (
                    block_number INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_hash TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    tx_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def set_orderer_status(self, orderer_id: str, is_healthy: bool) -> None:
        """Simulate orderer node crash or recovery for SmartBFT testing."""
        if orderer_id not in self.orderer_health:
            raise KeyError(f"Unknown orderer: {orderer_id}")
        self.orderer_health[orderer_id] = is_healthy

    def get_active_orderer_count(self) -> int:
        """Returns the number of healthy orderers."""
        return sum(1 for is_healthy in self.orderer_health.values() if is_healthy)

    def verify_smartbft_quorum(self) -> bool:
        """
        Verify that active orderers satisfy SmartBFT quorum (N=4, F=1, Quorum=3).
        Raises QuorumLossError if fewer than 3 orderers are active.
        """
        active = self.get_active_orderer_count()
        if active < self.bft_config.quorum_size:
            raise QuorumLossError(
                f"SmartBFT Quorum Lost: active orderers ({active}/{self.bft_config.total_orderers}) "
                f"below required quorum ({self.bft_config.quorum_size}). Consensus halted."
            )
        return True

    def _allocate_block(self, conn: sqlite3.Connection) -> int:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(block_number) FROM ledger_blocks")
        row = cursor.fetchone()
        last_num = row[0] if row[0] is not None else 0
        new_num = last_num + 1
        block_hash = f"block-{new_num}-{uuid.uuid4().hex[:12]}"
        prev_hash = f"block-{last_num}" if last_num > 0 else "genesis-0"
        cursor.execute(
            "INSERT INTO ledger_blocks (block_number, block_hash, previous_hash, tx_count) VALUES (?, ?, ?, ?)",
            (new_num, block_hash, prev_hash, 1),
        )
        return new_num

    def register_release(
        self,
        release: ReleaseRecord,
        endorsements: List[EndorsementRecord],
    ) -> str:
        """
        Submit RegisterRelease transaction.
        Enforces 3-of-4 endorsement policy and SmartBFT quorum ordering.
        """
        if not self.is_connected:
            raise LedgerCommitError("Ledger service unavailable: network disconnected")

        # 1. Verify 3-of-4 endorsement policy
        EndorsementPolicyEvaluator.evaluate(endorsements)

        # 2. Verify SmartBFT consensus quorum
        self.verify_smartbft_quorum()

        tx_id = f"tx-reg-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Check for existing release
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_releases WHERE release_id = ?", (release.release_id,))
            existing = cursor.fetchone()

            if existing:
                # Idempotency check
                if existing["manifest_digest_sha384"] == release.manifest_digest_sha384:
                    return existing["ledger_tx_id"]
                raise LedgerCommitError(
                    f"Conflicting duplicate release: {release.release_id} already exists with different digest"
                )

            block_num = self._allocate_block(conn)
            endorsements_json = json.dumps([e.model_dump() for e in endorsements])
            full_record_json = release.model_dump_json()

            cursor.execute("""
                INSERT INTO ledger_releases (
                    release_id, manifest_digest_sha384, artifact_digest_sha384,
                    evaluation_digest, policy_version, model_lineage_ref,
                    status, is_revoked, committed_at, ledger_tx_id,
                    block_number, endorsements_json, full_record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            """, (
                release.release_id,
                release.manifest_digest_sha384,
                release.artifact_digest_sha384,
                release.evaluation_digest,
                release.policy_version,
                release.model_lineage_ref,
                ReleaseState.LEDGER_COMMITTED.value,
                now,
                tx_id,
                block_num,
                endorsements_json,
                full_record_json,
            ))
            conn.commit()

        return tx_id

    def record_revocation(
        self,
        revocation: RevocationRecord,
        endorsements: List[EndorsementRecord],
    ) -> str:
        """Record model revocation on ledger with endorsement and quorum verification."""
        if not self.is_connected:
            raise LedgerCommitError("Ledger service unavailable: network disconnected")

        EndorsementPolicyEvaluator.evaluate(endorsements)
        self.verify_smartbft_quorum()

        tx_id = f"tx-rev-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Target release must exist
            cursor.execute("SELECT * FROM ledger_releases WHERE release_id = ?", (revocation.target_release_id,))
            rel_row = cursor.fetchone()
            if not rel_row:
                raise LedgerCommitError(f"Target release {revocation.target_release_id} not found on ledger")

            # 2. Check for duplicate revocation
            cursor.execute("SELECT * FROM ledger_revocations WHERE revocation_id = ?", (revocation.revocation_id,))
            if cursor.fetchone():
                return tx_id

            block_num = self._allocate_block(conn)

            # Update release asset
            cursor.execute("""
                UPDATE ledger_releases
                SET is_revoked = 1, revocation_id = ?, status = ?
                WHERE release_id = ?
            """, (revocation.revocation_id, ReleaseState.REVOKED.value, revocation.target_release_id))

            # Insert revocation record
            cursor.execute("""
                INSERT INTO ledger_revocations (
                    revocation_id, target_release_id, revoking_org, reason,
                    details, revocation_digest_sha384, ledger_tx_id, block_number, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                revocation.revocation_id,
                revocation.target_release_id,
                revocation.revoked_by_org.value,
                revocation.reason.value,
                revocation.details,
                revocation.revocation_digest_sha384,
                tx_id,
                block_num,
                now,
            ))
            conn.commit()

        return tx_id

    def record_audit_batch(
        self,
        batch: AuditBatchRecord,
        endorsements: List[EndorsementRecord],
    ) -> str:
        """Record privacy-preserving Merkle root commitment for audit batch."""
        if not self.is_connected:
            raise LedgerCommitError("Ledger service unavailable: network disconnected")

        EndorsementPolicyEvaluator.evaluate(endorsements)
        self.verify_smartbft_quorum()

        tx_id = f"tx-batch-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_audit_batches WHERE batch_id = ?", (batch.batch_id,))
            if cursor.fetchone():
                return tx_id

            block_num = self._allocate_block(conn)
            cursor.execute("""
                INSERT INTO ledger_audit_batches (
                    batch_id, merkle_root_hex, leaf_count, random_salt_hex,
                    domain_separator, ledger_tx_id, block_number, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch.batch_id,
                batch.merkle_root_hex,
                batch.leaf_count,
                batch.random_salt_hex,
                batch.domain_separator,
                tx_id,
                block_num,
                now,
            ))
            conn.commit()

        return tx_id

    def query_release(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Query a release record from the ledger."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_releases WHERE release_id = ?", (release_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def query_revocation(self, revocation_id: str) -> Optional[Dict[str, Any]]:
        """Query a revocation record from the ledger."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_revocations WHERE revocation_id = ?", (revocation_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def query_audit_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Query an audit batch commitment from the ledger."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_audit_batches WHERE batch_id = ?", (batch_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def list_releases(self) -> List[Dict[str, Any]]:
        """List all committed release records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_releases ORDER BY block_number DESC")
            return [dict(row) for row in cursor.fetchall()]

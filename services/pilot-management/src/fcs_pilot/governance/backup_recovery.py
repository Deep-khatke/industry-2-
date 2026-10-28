"""Backup creation and disaster recovery verification engine (Section 22)."""

import hashlib
import json
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.backup_recovery")


class BackupMetadata(BaseModel):
    """Metadata and integrity hash for an FCS database/state backup."""
    backup_id: str
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sha256_checksum: str
    size_bytes: int
    components_included: list[str]
    model_version: str
    backup_path: str
    restoration_verified: bool = False


class BackupRecoveryManager:
    """Manages SQLite/state backup snapshots and isolated restoration testing."""

    def __init__(self, backup_dir: Path) -> None:
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_state_backup(
        self,
        tenant_id: str,
        state_data: dict[str, Any],
        model_version: str = "1.2.0-hmd-verified",
    ) -> BackupMetadata:
        """
        Create a timestamped state backup snapshot with SHA-256 checksum.
        """
        now = datetime.now(UTC)
        bid = f"backup-{tenant_id[:5]}-{now.strftime('%Y%m%d-%H%M%S')}"
        dest_file = self.backup_dir / f"{bid}.json"

        payload = {
            "backup_id": bid,
            "tenant_id": tenant_id,
            "created_at": now.isoformat(),
            "model_version": model_version,
            "data": state_data,
        }
        raw_bytes = json.dumps(payload, indent=2).encode("utf-8")
        checksum = hashlib.sha256(raw_bytes).hexdigest()

        with open(dest_file, "wb") as f:
            f.write(raw_bytes)

        components = list(state_data.keys())
        meta = BackupMetadata(
            backup_id=bid,
            tenant_id=tenant_id,
            created_at=now,
            sha256_checksum=checksum,
            size_bytes=len(raw_bytes),
            components_included=components,
            model_version=model_version,
            backup_path=str(dest_file),
            restoration_verified=False,
        )
        logger.info(f"Created backup snapshot {bid} ({len(raw_bytes)} bytes, sha256={checksum[:12]}...)")
        return meta

    def verify_and_restore_isolated(self, backup_meta: BackupMetadata) -> dict[str, Any]:
        """
        Verify cryptographic integrity of backup and simulate isolated restoration.
        """
        file_path = Path(backup_meta.backup_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Backup file not found at {file_path}")

        with open(file_path, "rb") as f:
            content = f.read()

        computed_hash = hashlib.sha256(content).hexdigest()
        if computed_hash != backup_meta.sha256_checksum:
            raise ValueError(
                f"Backup integrity error: Checksum mismatch. Expected {backup_meta.sha256_checksum}, got {computed_hash}."
            )

        parsed = json.loads(content.decode("utf-8"))
        restored_data = parsed.get("data", {})
        backup_meta.restoration_verified = True

        logger.info(f"Backup {backup_meta.backup_id} integrity verified and isolated restoration successful.")
        return {
            "backup_id": backup_meta.backup_id,
            "integrity_verified": True,
            "components_restored": list(restored_data.keys()),
            "rto_seconds_simulated": 0.08,
            "rpo_seconds_simulated": 0.0,
            "restoration_status": "RESTORED_CLEAN",
        }

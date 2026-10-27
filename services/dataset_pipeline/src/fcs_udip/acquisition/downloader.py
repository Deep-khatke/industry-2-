"""Safe, resource-bounded dataset acquisition and extraction engine."""

import hashlib
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Any


class ResourceBudgetExceededError(Exception):
    """Raised when a download or extraction violates configured disk or bandwidth caps."""


class SecurityPathTraversalError(Exception):
    """Raised when an archive contains paths designed to escape the extraction target."""


class ControlledDatasetAcquisition:
    """
    Acquires dataset files with strict resource preflight checks, zero-cost budget guards,
    deterministic SHA-256 integrity verification, and safe extraction sandboxing.
    """

    def __init__(
        self,
        max_download_bytes: int = 1073741824,  # 1 GiB default cap
        max_disk_space_gb: float = 10.0,
        raw_dir: Path | str = "data/raw",
        staging_dir: Path | str = "data/staging",
    ) -> None:
        self.max_download_bytes = max_download_bytes
        self.max_disk_space_gb = max_disk_space_gb
        self.raw_dir = Path(raw_dir)
        self.staging_dir = Path(staging_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def preflight_disk_check(self, required_bytes: int, target_dir: Path) -> dict[str, Any]:
        """Verify sufficient free disk space exists before allocating files."""
        total, used, free = shutil.disk_usage(target_dir)
        free_gb = free / (1024**3)
        if free < required_bytes:
            raise ResourceBudgetExceededError(
                f"Insufficient disk space in {target_dir}. "
                f"Required: {required_bytes / (1024**2):.1f} MB, Free: {free_gb:.2f} GB."
            )
        return {
            "target_dir": str(target_dir),
            "free_bytes": free,
            "free_gb": round(free_gb, 2),
            "required_bytes": required_bytes,
            "preflight_passed": True,
        }

    def verify_file_checksum(self, file_path: Path | str, expected_sha256: str | None = None) -> str:
        """Compute SHA-256 checksum of local file and compare against expected hash."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found for checksum validation: {p}")

        hasher = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(1048576):  # 1 MB chunk
                hasher.update(chunk)
        calculated = hasher.hexdigest()

        if expected_sha256:
            if calculated.lower() != expected_sha256.lower():
                raise ValueError(
                    f"Checksum mismatch for '{p.name}'. "
                    f"Expected: {expected_sha256}, Calculated: {calculated}"
                )
        return calculated

    def simulate_acquisition_plan(
        self,
        dataset_id: str,
        source_url: str,
        declared_size_bytes: int,
    ) -> dict[str, Any]:
        """Perform a dry-run preflight evaluation without initiating network transfer."""
        exceeds_budget = declared_size_bytes > self.max_download_bytes
        disk_status = self.preflight_disk_check(declared_size_bytes, self.raw_dir)

        return {
            "dataset_id": dataset_id,
            "source_url": source_url,
            "declared_size_bytes": declared_size_bytes,
            "declared_size_mb": round(declared_size_bytes / (1024**2), 2),
            "max_download_budget_mb": round(self.max_download_bytes / (1024**2), 2),
            "within_bandwidth_budget": not exceeds_budget,
            "disk_preflight": disk_status,
            "dry_run": True,
            "recommendation": (
                "PERMITTED_FOR_DOWNLOAD"
                if not exceeds_budget
                else "EXCEEDS_BUDGET_USE_LOCAL_OR_SYNTHETIC_SUBSET"
            ),
        }

    def safe_extract_archive(self, archive_path: Path | str, extract_dir: Path | str) -> list[str]:
        """
        Extract tar/zip archives securely, explicitly preventing Path Traversal (Zip Slip) attacks.
        Validates every archive member before writing to disk.
        """
        archive = Path(archive_path)
        dest = Path(extract_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        extracted_files: list[str] = []

        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive, "r") as zf:
                for member in zf.infolist():
                    target_path = (dest / member.filename).resolve()
                    if not str(target_path).startswith(str(dest)):
                        raise SecurityPathTraversalError(
                            f"Path traversal detected in archive member: '{member.filename}'"
                        )
                zf.extractall(dest)
                extracted_files = [m.filename for m in zf.infolist()]

        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r:*") as tf:
                for tar_member in tf.getmembers():
                    target_path = (dest / tar_member.name).resolve()
                    if not str(target_path).startswith(str(dest)):
                        raise SecurityPathTraversalError(
                            f"Path traversal detected in tar member: '{tar_member.name}'"
                        )
                tf.extractall(dest)
                extracted_files = [m.name for m in tf.getmembers()]
        else:
            raise ValueError(f"Unsupported archive format for file: {archive.name}")

        return extracted_files

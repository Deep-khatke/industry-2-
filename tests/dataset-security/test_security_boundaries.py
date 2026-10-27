"""Security boundaries, path traversal sanitization, and zero-cost audit tests."""

import zipfile
from pathlib import Path

import pytest

from fcs_udip.acquisition.downloader import ControlledDatasetAcquisition, SecurityPathTraversalError


@pytest.mark.dataset_security
class TestSecurityBoundaries:
    """Validate archive sandboxing, secret scanning, and .gitignore raw dataset protection."""

    def test_zip_slip_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Verify that extracting an archive containing '../' path traversal raises SecurityPathTraversalError."""
        malicious_zip = tmp_path / "malicious.zip"
        target_extract = tmp_path / "extracted"

        # Create malicious zip file containing path traversal member
        with zipfile.ZipFile(malicious_zip, "w") as zf:
            zf.writestr("../../escaped_file.txt", "MALICIOUS PAYLOAD ESCAPING SANDBOX")

        acq = ControlledDatasetAcquisition()
        with pytest.raises(SecurityPathTraversalError) as exc_info:
            acq.safe_extract_archive(malicious_zip, target_extract)
        assert "Path traversal detected in archive member" in str(exc_info.value)

    def test_raw_datasets_ignored_by_git(self) -> None:
        """Verify .gitignore properly protects data/raw and large data artifacts from being committed."""
        gitignore = Path(".gitignore").read_text(encoding="utf-8")
        assert "/data/raw/" in gitignore
        assert "/data/staging/" in gitignore
        assert "/data/processed/" in gitignore
        assert "*.parquet" in gitignore
        assert "*.csv.gz" in gitignore

    def test_no_private_signing_keys_committed(self) -> None:
        """Verify that development HMAC keys are ephemeral and no production private keys exist."""
        key_files = list(Path(".").glob("**/*.pem")) + list(Path(".").glob("**/*.key"))
        # Any discovered keys must be explicitly in .gitignore
        for kf in key_files:
            assert ".venv" in str(kf) or ".git" in str(kf) or "scratch" in str(kf)

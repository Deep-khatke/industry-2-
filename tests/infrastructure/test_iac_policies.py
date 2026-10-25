"""Static policy and security constraint validation on OpenTofu IaC definitions."""

from pathlib import Path

import pytest

IAC_ROOT = Path(__file__).resolve().parent.parent.parent / "infrastructure" / "opentofu"


@pytest.mark.infrastructure
class TestIaCSecurityPolicies:
    """Offline static analysis of OpenTofu modules to verify security guardrails."""

    def test_no_unrestricted_ssh_ingress(self) -> None:
        """Verify that no security group allows 0.0.0.0/0 on port 22 or SSH."""
        for tf_file in IAC_ROOT.rglob("*.tf"):
            content = tf_file.read_text(encoding="utf-8")
            # Check for port 22 with 0.0.0.0/0
            if "from_port   = 22" in content or "to_port     = 22" in content or "from_port = 22" in content:
                assert '"0.0.0.0/0"' not in content, f"Unrestricted SSH found in {tf_file.name}"

    def test_s3_storage_public_access_blocked(self) -> None:
        """Verify S3 storage module includes public access block with all 4 protections enabled."""
        storage_main = (IAC_ROOT / "modules" / "storage" / "main.tf").read_text(encoding="utf-8")
        assert "aws_s3_bucket_public_access_block" in storage_main
        assert "block_public_acls       = true" in storage_main
        assert "block_public_policy     = true" in storage_main
        assert "ignore_public_acls      = true" in storage_main
        assert "restrict_public_buckets = true" in storage_main

    def test_s3_storage_enforces_tls_only(self) -> None:
        """Verify S3 bucket policy denies non-HTTPS requests."""
        storage_main = (IAC_ROOT / "modules" / "storage" / "main.tf").read_text(encoding="utf-8")
        assert '"aws:SecureTransport" = "false"' in storage_main
        assert 'Effect    = "Deny"' in storage_main or 'Effect = "Deny"' in storage_main

    def test_kinesis_stream_enforces_kms_encryption(self) -> None:
        """Verify Kinesis stream has encryption_type = 'KMS'."""
        streaming_main = (IAC_ROOT / "modules" / "streaming" / "main.tf").read_text(encoding="utf-8")
        assert 'encryption_type = "KMS"' in streaming_main

    def test_tenant_kms_isolation_boundaries(self) -> None:
        """Verify isolation module establishes dedicated KMS keys per tenant."""
        isolation_main = (IAC_ROOT / "modules" / "isolation" / "main.tf").read_text(encoding="utf-8")
        assert 'resource "aws_kms_key" "tenant_key"' in isolation_main
        assert "enable_key_rotation     = true" in isolation_main

    def test_iam_least_privilege_collector_role(self) -> None:
        """Verify collector IAM role does not grant wildcard * admin permissions."""
        iam_main = (IAC_ROOT / "modules" / "iam" / "main.tf").read_text(encoding="utf-8")
        # Collector must have put records to kinesis, NOT administrator access
        assert "kinesis:PutRecord" in iam_main
        assert '"Action": "*"' not in iam_main
        assert '"Action" = "*"' not in iam_main

package main

import (
	"testing"
	"time"
)

func TestRegisterRelease(t *testing.T) {
	stub := NewMemoryStateStore()
	contract := NewGovernanceContract()
	now := time.Now().UTC()

	// 1. Initial successful registration
	release, err := contract.RegisterRelease(
		stub,
		"rel-001",
		"sha384-manifest-digest-abc",
		"sha256-eval-digest-123",
		"1.2.0",
		"candidate-mlp-01",
		now,
	)
	if err != nil {
		t.Fatalf("unexpected error registering release: %v", err)
	}
	if release.ReleaseID != "rel-001" {
		t.Errorf("expected rel-001, got %s", release.ReleaseID)
	}
	if release.IsRevoked {
		t.Errorf("expected IsRevoked to be false")
	}

	// 2. Query release
	queried, err := contract.QueryRelease(stub, "rel-001")
	if err != nil {
		t.Fatalf("unexpected error querying release: %v", err)
	}
	if queried.ManifestDigestSHA384 != "sha384-manifest-digest-abc" {
		t.Errorf("digest mismatch: got %s", queried.ManifestDigestSHA384)
	}

	// 3. Idempotent duplicate registration (same content)
	reReg, err := contract.RegisterRelease(
		stub,
		"rel-001",
		"sha384-manifest-digest-abc",
		"sha256-eval-digest-123",
		"1.2.0",
		"candidate-mlp-01",
		now,
	)
	if err != nil {
		t.Fatalf("expected idempotent re-registration to succeed, got %v", err)
	}
	if reReg.ReleaseID != "rel-001" {
		t.Errorf("mismatched release ID")
	}

	// 4. Conflicting duplicate registration (different manifest digest)
	_, err = contract.RegisterRelease(
		stub,
		"rel-001",
		"sha384-DIFFERENT-manifest-digest",
		"sha256-eval-digest-123",
		"1.2.0",
		"candidate-mlp-01",
		now,
	)
	if err == nil {
		t.Fatalf("expected conflicting registration to be rejected, but it succeeded")
	}
}

func TestRecordRevocation(t *testing.T) {
	stub := NewMemoryStateStore()
	contract := NewGovernanceContract()
	now := time.Now().UTC()

	// Setup: Register release
	_, err := contract.RegisterRelease(
		stub,
		"rel-to-revoke",
		"manifest-digest",
		"eval-digest",
		"1.2.0",
		"lineage-1",
		now,
	)
	if err != nil {
		t.Fatalf("setup failed: %v", err)
	}

	// 1. Revoke release
	rev, err := contract.RecordRevocation(
		stub,
		"rev-001",
		"rel-to-revoke",
		"ISP_GOVERNANCE_A",
		"VULNERABILITY_DISCOVERED",
		"Critical defect discovered in model weights",
		"sha384-revocation-digest",
		now,
	)
	if err != nil {
		t.Fatalf("revocation failed: %v", err)
	}
	if rev.RevocationID != "rev-001" {
		t.Errorf("expected rev-001, got %s", rev.RevocationID)
	}

	// 2. Verify release is marked revoked
	rel, err := contract.QueryRelease(stub, "rel-to-revoke")
	if err != nil {
		t.Fatalf("query release failed: %v", err)
	}
	if !rel.IsRevoked {
		t.Errorf("expected release to be marked revoked")
	}
	if rel.RevocationID != "rev-001" {
		t.Errorf("expected revocation ID rev-001, got %s", rel.RevocationID)
	}

	// 3. Query revocation record
	qRev, err := contract.QueryRevocation(stub, "rev-001")
	if err != nil {
		t.Fatalf("query revocation failed: %v", err)
	}
	if qRev.Reason != "VULNERABILITY_DISCOVERED" {
		t.Errorf("reason mismatch: got %s", qRev.Reason)
	}

	// 4. Revocation of non-existent release fails
	_, err = contract.RecordRevocation(
		stub,
		"rev-nonexistent",
		"non-existent-release-id",
		"ISP_GOVERNANCE_B",
		"VULNERABILITY_DISCOVERED",
		"details",
		"digest",
		now,
	)
	if err == nil {
		t.Fatalf("expected error revoking non-existent release, got nil")
	}
}

func TestRecordAuditBatch(t *testing.T) {
	stub := NewMemoryStateStore()
	contract := NewGovernanceContract()
	now := time.Now().UTC()

	batch, err := contract.RecordAuditBatch(
		stub,
		"batch-101",
		"sha384-merkle-root-abc123",
		42,
		"salt-hex-789",
		"FCS_AUDIT_MERKLE_V1",
		now,
	)
	if err != nil {
		t.Fatalf("recording audit batch failed: %v", err)
	}
	if batch.LeafCount != 42 {
		t.Errorf("expected 42 leaves, got %d", batch.LeafCount)
	}

	queried, err := contract.QueryAuditBatch(stub, "batch-101")
	if err != nil {
		t.Fatalf("querying audit batch failed: %v", err)
	}
	if queried.MerkleRootHex != "sha384-merkle-root-abc123" {
		t.Errorf("merkle root mismatch: got %s", queried.MerkleRootHex)
	}
}

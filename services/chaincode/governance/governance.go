// Package main implements the Hyperledger Fabric Governance Chaincode for Federated Cyber Shield.
// Architecture baseline: FCS Architecture v1.2 | Phase 7 Consortium Governance.
// Strict Invariants:
// 1. Zero-Cost Policy: Free open-source Go implementation.
// 2. Data Protection: Never stores raw telemetry, private gradients, or model binaries on ledger.
// 3. Determinism: Idempotent transaction processing, strict state transition validation.

package main

import (
	"encoding/json"
	"fmt"
	"time"
)

// ReleaseAsset represents an approved federated model release on the consortium ledger.
type ReleaseAsset struct {
	DocType                string    `json:"doc_type"` // "release"
	ReleaseID              string    `json:"release_id"`
	ManifestDigestSHA384   string    `json:"manifest_digest_sha384"`
	EvaluationDigest       string    `json:"evaluation_digest"`
	PolicyVersion          string    `json:"policy_version"`
	ModelLineageRef        string    `json:"model_lineage_ref"`
	CommittedAt            time.Time `json:"committed_at"`
	IsRevoked              bool      `json:"is_revoked"`
	RevocationID           string    `json:"revocation_id,omitempty"`
}

// RevocationAsset represents a formal revocation of a model release.
type RevocationAsset struct {
	DocType                string    `json:"doc_type"` // "revocation"
	RevocationID           string    `json:"revocation_id"`
	TargetReleaseID        string    `json:"target_release_id"`
	RevokingOrg            string    `json:"revoking_org"`
	Reason                 string    `json:"reason"`
	Details                string    `json:"details"`
	RevocationDigestSHA384 string    `json:"revocation_digest_sha384"`
	Timestamp              time.Time `json:"timestamp"`
}

// AuditBatchAsset represents a privacy-preserving Merkle root commitment of incident audit events.
type AuditBatchAsset struct {
	DocType         string    `json:"doc_type"` // "audit_batch"
	BatchID         string    `json:"batch_id"`
	MerkleRootHex   string    `json:"merkle_root_hex"`
	LeafCount       int       `json:"leaf_count"`
	RandomSaltHex   string    `json:"random_salt_hex"`
	DomainSeparator string    `json:"domain_separator"`
	Timestamp       time.Time `json:"timestamp"`
}

// StateStore is an interface abstracting Fabric ledger state for testing and execution.
type StateStore interface {
	GetState(key string) ([]byte, error)
	PutState(key string, value []byte) error
}

// MemoryStateStore provides an in-memory ledger state store for unit testing.
type MemoryStateStore struct {
	store map[string][]byte
}

func NewMemoryStateStore() *MemoryStateStore {
	return &MemoryStateStore{store: make(map[string][]byte)}
}

func (m *MemoryStateStore) GetState(key string) ([]byte, error) {
	val, ok := m.store[key]
	if !ok {
		return nil, nil
	}
	return val, nil
}

func (m *MemoryStateStore) PutState(key string, value []byte) error {
	m.store[key] = value
	return nil
}

// GovernanceContract implements the core business logic.
type GovernanceContract struct{}

func NewGovernanceContract() *GovernanceContract {
	return &GovernanceContract{}
}

// RegisterRelease registers a verified, dual-signed model release on the consortium ledger.
func (c *GovernanceContract) RegisterRelease(
	stub StateStore,
	releaseID string,
	manifestDigest string,
	evaluationDigest string,
	policyVersion string,
	modelLineageRef string,
	timestamp time.Time,
) (*ReleaseAsset, error) {
	if releaseID == "" || manifestDigest == "" {
		return nil, fmt.Errorf("releaseID and manifestDigest must not be empty")
	}

	key := "RELEASE_" + releaseID
	existingBytes, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to read ledger: %w", err)
	}

	if existingBytes != nil {
		var existing ReleaseAsset
		if err := json.Unmarshal(existingBytes, &existing); err != nil {
			return nil, fmt.Errorf("corrupt ledger state for %s: %w", key, err)
		}
		// Idempotency: identical release submission is allowed
		if existing.ManifestDigestSHA384 == manifestDigest &&
			existing.EvaluationDigest == evaluationDigest {
			return &existing, nil
		}
		// Conflicting duplicate releaseID is rejected
		return nil, fmt.Errorf("conflict: release %s already registered with different manifest digest", releaseID)
	}

	release := ReleaseAsset{
		DocType:              "release",
		ReleaseID:            releaseID,
		ManifestDigestSHA384: manifestDigest,
		EvaluationDigest:     evaluationDigest,
		PolicyVersion:        policyVersion,
		ModelLineageRef:      modelLineageRef,
		CommittedAt:          timestamp,
		IsRevoked:            false,
	}

	payload, err := json.Marshal(release)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize release: %w", err)
	}

	if err := stub.PutState(key, payload); err != nil {
		return nil, fmt.Errorf("failed to put state: %w", err)
	}

	return &release, nil
}

// RecordRevocation revokes an existing model release.
func (c *GovernanceContract) RecordRevocation(
	stub StateStore,
	revocationID string,
	targetReleaseID string,
	revokingOrg string,
	reason string,
	details string,
	revocationDigest string,
	timestamp time.Time,
) (*RevocationAsset, error) {
	if revocationID == "" || targetReleaseID == "" {
		return nil, fmt.Errorf("revocationID and targetReleaseID must not be empty")
	}

	// 1. Verify target release exists
	releaseKey := "RELEASE_" + targetReleaseID
	releaseBytes, err := stub.GetState(releaseKey)
	if err != nil {
		return nil, fmt.Errorf("failed to read release: %w", err)
	}
	if releaseBytes == nil {
		return nil, fmt.Errorf("target release %s does not exist on ledger", targetReleaseID)
	}

	var release ReleaseAsset
	if err := json.Unmarshal(releaseBytes, &release); err != nil {
		return nil, fmt.Errorf("corrupt release state: %w", err)
	}

	// 2. Idempotency for revocation
	revKey := "REVOCATION_" + revocationID
	existingRevBytes, err := stub.GetState(revKey)
	if err != nil {
		return nil, fmt.Errorf("failed to read revocation: %w", err)
	}
	if existingRevBytes != nil {
		var existing RevocationAsset
		if err := json.Unmarshal(existingRevBytes, &existing); err == nil {
			return &existing, nil
		}
	}

	// 3. Mark release as revoked
	release.IsRevoked = true
	release.RevocationID = revocationID
	updatedReleaseBytes, err := json.Marshal(release)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize updated release: %w", err)
	}
	if err := stub.PutState(releaseKey, updatedReleaseBytes); err != nil {
		return nil, fmt.Errorf("failed to update release state: %w", err)
	}

	// 4. Save revocation record
	revocation := RevocationAsset{
		DocType:                "revocation",
		RevocationID:           revocationID,
		TargetReleaseID:        targetReleaseID,
		RevokingOrg:            revokingOrg,
		Reason:                 reason,
		Details:                details,
		RevocationDigestSHA384: revocationDigest,
		Timestamp:              timestamp,
	}

	revPayload, err := json.Marshal(revocation)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize revocation: %w", err)
	}
	if err := stub.PutState(revKey, revPayload); err != nil {
		return nil, fmt.Errorf("failed to put revocation state: %w", err)
	}

	return &revocation, nil
}

// RecordAuditBatch anchors a privacy-preserving Merkle root of incident audit batches.
func (c *GovernanceContract) RecordAuditBatch(
	stub StateStore,
	batchID string,
	merkleRootHex string,
	leafCount int,
	randomSaltHex string,
	domainSeparator string,
	timestamp time.Time,
) (*AuditBatchAsset, error) {
	if batchID == "" || merkleRootHex == "" {
		return nil, fmt.Errorf("batchID and merkleRootHex must not be empty")
	}

	key := "AUDIT_BATCH_" + batchID
	existingBytes, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to read audit batch state: %w", err)
	}
	if existingBytes != nil {
		var existing AuditBatchAsset
		if err := json.Unmarshal(existingBytes, &existing); err == nil {
			return &existing, nil
		}
	}

	batch := AuditBatchAsset{
		DocType:         "audit_batch",
		BatchID:         batchID,
		MerkleRootHex:   merkleRootHex,
		LeafCount:       leafCount,
		RandomSaltHex:   randomSaltHex,
		DomainSeparator: domainSeparator,
		Timestamp:       timestamp,
	}

	payload, err := json.Marshal(batch)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize audit batch: %w", err)
	}

	if err := stub.PutState(key, payload); err != nil {
		return nil, fmt.Errorf("failed to put audit batch state: %w", err)
	}

	return &batch, nil
}

// QueryRelease retrieves a release asset by ID.
func (c *GovernanceContract) QueryRelease(stub StateStore, releaseID string) (*ReleaseAsset, error) {
	key := "RELEASE_" + releaseID
	data, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to query release: %w", err)
	}
	if data == nil {
		return nil, fmt.Errorf("release %s not found", releaseID)
	}
	var release ReleaseAsset
	if err := json.Unmarshal(data, &release); err != nil {
		return nil, fmt.Errorf("corrupt state: %w", err)
	}
	return &release, nil
}

// QueryRevocation retrieves a revocation record by ID.
func (c *GovernanceContract) QueryRevocation(stub StateStore, revocationID string) (*RevocationAsset, error) {
	key := "REVOCATION_" + revocationID
	data, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to query revocation: %w", err)
	}
	if data == nil {
		return nil, fmt.Errorf("revocation %s not found", revocationID)
	}
	var rev RevocationAsset
	if err := json.Unmarshal(data, &rev); err != nil {
		return nil, fmt.Errorf("corrupt state: %w", err)
	}
	return &rev, nil
}

// QueryAuditBatch retrieves an audit batch asset by ID.
func (c *GovernanceContract) QueryAuditBatch(stub StateStore, batchID string) (*AuditBatchAsset, error) {
	key := "AUDIT_BATCH_" + batchID
	data, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to query audit batch: %w", err)
	}
	if data == nil {
		return nil, fmt.Errorf("audit batch %s not found", batchID)
	}
	var batch AuditBatchAsset
	if err := json.Unmarshal(data, &batch); err != nil {
		return nil, fmt.Errorf("corrupt state: %w", err)
	}
	return &batch, nil
}

func main() {
	fmt.Println("FCS Governance Chaincode initialized")
}

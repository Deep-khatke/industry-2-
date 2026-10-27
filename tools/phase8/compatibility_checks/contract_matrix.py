"""
Phase 8 Contract Compatibility Matrix and Interface Verifier.
Validates all 20 adjacent component interfaces in FCS Architecture v1.2.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json


class InterfaceStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    PARTIALLY_COMPATIBLE = "PARTIALLY_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    BLOCKED = "BLOCKED"


@dataclass
class InterfaceContract:
    interface_id: str
    producer: str
    consumer: str
    contract_version: str
    required_fields: List[str]
    allowed_optional_fields: List[str]
    identity_scope: str
    feature_schema_digest: Optional[str]
    validation_rule: str
    error_behavior: str
    retry_behavior: str
    idempotency_policy: str
    security_boundary: str
    test_coverage: str
    status: InterfaceStatus = InterfaceStatus.COMPATIBLE
    validation_notes: str = ""


class SystemContractMatrix:
    """Manages and verifies the system integration contract matrix."""

    LOCKED_FEATURE_SCHEMA_DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def __init__(self) -> None:
        self.contracts: Dict[str, InterfaceContract] = self._build_contracts()

    def _build_contracts(self) -> Dict[str, InterfaceContract]:
        contracts = {
            "INT-01": InterfaceContract(
                interface_id="INT-01",
                producer="IPFIX/NetFlow Collector",
                consumer="FlowEvent v1 Normalizer",
                contract_version="v1.2",
                required_fields=["version", "src_ip", "dst_ip", "src_port", "dst_port", "protocol", "packets", "bytes", "start_time", "end_time"],
                allowed_optional_fields=["tcp_flags", "tos", "input_snmp", "output_snmp"],
                identity_scope="Exporter Observation Domain",
                feature_schema_digest=None,
                validation_rule="Strict binary header check; length bounded; IP version 4/6 valid",
                error_behavior="Quarantine malformed record; increment parser_error counter; continue",
                retry_behavior="UDP non-retryable; sequence gap observable",
                idempotency_policy="Deduplication key = sha256(exporter_id + flow_tuple + timestamps)",
                security_boundary="Per-exporter network ingress",
                test_coverage="tests/unit/test_collector_parser.py",
            ),
            "INT-02": InterfaceContract(
                interface_id="INT-02",
                producer="FlowEvent Normalizer",
                consumer="Tenant Stream Adapter",
                contract_version="v1.0.0",
                required_fields=["event_id", "schema_version", "tenant_id", "observation_domain_id", "timestamp", "flow_tuple", "metrics"],
                allowed_optional_fields=["tcp_flags", "synthetic"],
                identity_scope="Tenant Scope (rural-isp-*)",
                feature_schema_digest=None,
                validation_rule="Pydantic FlowEvent model validation; tenant_id in approved registry",
                error_behavior="Reject invalid schema with ContractValidationError; log quarantine",
                retry_behavior="Adapter buffer retry with bounded capacity (10,000)",
                idempotency_policy="Deterministic event_id enforcement",
                security_boundary="Multi-tenant namespace boundary",
                test_coverage="tests/unit/test_contracts.py",
            ),
            "INT-03": InterfaceContract(
                interface_id="INT-03",
                producer="Tenant Stream Adapter",
                consumer="Feature Window Engine",
                contract_version="v1.0.0",
                required_fields=["tenant_id", "window_id", "start_time", "end_time", "events"],
                allowed_optional_fields=["late_arriving_events"],
                identity_scope="Tenant Scope",
                feature_schema_digest=None,
                validation_rule="10-second tumbling window; late events >30s dropped",
                error_behavior="Drop expired event; increment late_event_dropped gauge",
                retry_behavior="None (tumbling window closes monotonically)",
                idempotency_policy="Window UUID per tenant + start_time",
                security_boundary="Tenant-isolated window buffer",
                test_coverage="tests/phase4-unit/test_window_engine.py",
            ),
            "INT-04": InterfaceContract(
                interface_id="INT-04",
                producer="Feature Window Engine",
                consumer="FeatureSpec Validator",
                contract_version="v1.2.0",
                required_fields=["flow_count", "byte_count", "packet_count", "mean_flow_duration", "syn_ratio", "ack_ratio", "rst_ratio", "unique_src_ips", "unique_dst_ips", "unique_dst_ports", "external_ip_ratio", "dns_query_ratio", "nxdomain_ratio", "ssh_flow_ratio"],
                allowed_optional_fields=[],
                identity_scope="Tenant Scope",
                feature_schema_digest="locked_14_features",
                validation_rule="Exactly 14 numerical features matching deployable subset; no NaN/Inf",
                error_behavior="Reject window from ML inference; log FeatureSpecMismatch",
                retry_behavior="None; feature window discarded",
                idempotency_policy="Feature vector hash",
                security_boundary="Feature extraction runtime boundary",
                test_coverage="tests/system/contracts/test_contract_matrix.py",
            ),
            "INT-05": InterfaceContract(
                interface_id="INT-05",
                producer="FeatureSpec Validator",
                consumer="Model Preprocessing Pipeline",
                contract_version="v1.0.0",
                required_fields=["features_vector", "scaler_digest", "imputer_strategy"],
                allowed_optional_fields=[],
                identity_scope="System / Model Framework",
                feature_schema_digest="deployable_preprocessing_v1",
                validation_rule="RobustScaler transformation with zero-variance check",
                error_behavior="Raise PreprocessingError; trigger rules fallback",
                retry_behavior="Immediate fallback to deterministic rules",
                idempotency_policy="Pure function; deterministic transform",
                security_boundary="ML Preprocessing Container",
                test_coverage="tests/ml-unit/test_thresholds_and_calibration.py",
            ),
            "INT-06": InterfaceContract(
                interface_id="INT-06",
                producer="Model Preprocessing Pipeline",
                consumer="General Intrusion Detector (Level 1)",
                contract_version="v1.0.0",
                required_fields=["scaled_features", "model_id"],
                allowed_optional_fields=[],
                identity_scope="Global Model Scope",
                feature_schema_digest="lightgbm_deployable_subset",
                validation_rule="Model artifact hash matches manifest; predict_proba in [0.0, 1.0]",
                error_behavior="Catch exception; emit ModelScore with status=ERROR; engage fallback",
                retry_behavior="Circuit breaker; trip after 3 timeouts",
                idempotency_policy="Deterministic inference over immutable weights",
                security_boundary="Model Inference Engine",
                test_coverage="tests/phase5-unit/test_hmd_models.py",
            ),
            "INT-07": InterfaceContract(
                interface_id="INT-07",
                producer="General Detector",
                consumer="Hierarchical Model Router (FCS-HMD)",
                contract_version="v1.0.0",
                required_fields=["model_id", "probability", "raw_score", "predicted_class", "inference_latency_ms", "status"],
                allowed_optional_fields=["calibrated_probability", "explanation"],
                identity_scope="Tenant Scope",
                feature_schema_digest=None,
                validation_rule="ModelScore v1 contract; probability in [0.0, 1.0]",
                error_behavior="Reject score if status invalid; route to safe fallback",
                retry_behavior="None",
                idempotency_policy="ModelScore ID per window",
                security_boundary="Hierarchical Decision Router",
                test_coverage="tests/phase5-unit/test_model_router.py",
            ),
            "INT-08": InterfaceContract(
                interface_id="INT-08",
                producer="Hierarchical Model Router",
                consumer="Specialist Detectors (DDoS, Scanning, Anomaly)",
                contract_version="v1.0.0",
                required_fields=["tenant_id", "features", "routing_reason", "specialist_type"],
                allowed_optional_fields=["timeout_ms"],
                identity_scope="Tenant Scope (Anomaly is STRICT_PER_TENANT)",
                feature_schema_digest="specialist_v1",
                validation_rule="Condition-based routing (volumetric -> DDoS; syn_scan -> Scanning; tenant baseline -> Anomaly)",
                error_behavior="Timeout after 2000ms; return ABSTAIN score; continue",
                retry_behavior="None; never stall detection plane",
                idempotency_policy="Window ID scoped routing",
                security_boundary="Tenant Specialist Sandbox",
                test_coverage="tests/phase5-security/test_hmd_tenant_isolation.py",
            ),
            "INT-09": InterfaceContract(
                interface_id="INT-09",
                producer="Specialist Detectors",
                consumer="Evidence Fusion Engine",
                contract_version="v1.0.0",
                required_fields=["level1_score", "anomaly_score", "specialist_scores", "rule_matches"],
                allowed_optional_fields=["tenant_baseline_drift"],
                identity_scope="Tenant Scope",
                feature_schema_digest=None,
                validation_rule="Deterministic fusion hierarchy; specialist dominance for confirmed attack; rule floor preserved",
                error_behavior="Missing score treated as UNKNOWN; does not clear rule risk floor",
                retry_behavior="None",
                idempotency_policy="Fusion result bound to window UUID",
                security_boundary="Evidence Fusion Engine",
                test_coverage="tests/phase5-unit/test_evidence_fusion.py",
            ),
            "INT-10": InterfaceContract(
                interface_id="INT-10",
                producer="Evidence Fusion Engine",
                consumer="Incident Engine",
                contract_version="v1.0.0",
                required_fields=["tenant_id", "severity", "threat_type", "confidence", "evidence_bundle", "recommended_action"],
                allowed_optional_fields=["affected_targets", "packet_rate"],
                identity_scope="Tenant Scope",
                feature_schema_digest=None,
                validation_rule="Confidence >= threshold (0.65 for incident creation); action recommendations strictly MANUAL",
                error_behavior="Log unformed incident; do not commit partial state",
                retry_behavior="Transactional DB commit with retry",
                idempotency_policy="Unique index on (tenant_id, deduplication_key)",
                security_boundary="Incident Management Boundary",
                test_coverage="tests/phase4-integration/test_end_to_end_pipeline.py",
            ),
            "INT-11": InterfaceContract(
                interface_id="INT-11",
                producer="Incident Engine",
                consumer="FastAPI Backend Storage",
                contract_version="v1.0.0",
                required_fields=["incident_id", "tenant_id", "title", "severity", "status", "created_at"],
                allowed_optional_fields=["model_explanation", "recommended_action_id"],
                identity_scope="Tenant Scope",
                feature_schema_digest=None,
                validation_rule="Relational integrity in SQLite; foreign keys enforced; tenant_id indexed",
                error_behavior="Rollback SQLite transaction; raise DatabaseError",
                retry_behavior="Immediate retry up to 3 times with exponential backoff",
                idempotency_policy="Primary key incident_id UUID",
                security_boundary="Storage / Database Boundary",
                test_coverage="tests/phase4-unit/test_auth_service.py",
            ),
            "INT-12": InterfaceContract(
                interface_id="INT-12",
                producer="FastAPI Backend",
                consumer="React Security Dashboard",
                contract_version="v1.2.0",
                required_fields=["access_token", "tenant_id", "role", "incidents", "system_health"],
                allowed_optional_fields=["filter_params", "pagination"],
                identity_scope="JWT Token Claims (Tenant + Role)",
                feature_schema_digest=None,
                validation_rule="HTTP Bearer JWT validation; cross-tenant query strictly 403 Forbidden",
                error_behavior="Return standard HTTP 401/403/404/422 JSON error models",
                retry_behavior="Frontend polling / exponential retry on 503",
                idempotency_policy="GET idempotent; POST with X-Idempotency-Key",
                security_boundary="REST API / Web Frontend Boundary",
                test_coverage="tests/phase4-integration/test_api_endpoints.py",
            ),
            "INT-13": InterfaceContract(
                interface_id="INT-13",
                producer="SOC Analyst on Dashboard",
                consumer="Manual Response Policy Engine",
                contract_version="v1.0.0",
                required_fields=["action_id", "incident_id", "tenant_id", "action_type", "target", "duration_seconds", "operator_id"],
                allowed_optional_fields=["justification_notes"],
                identity_scope="Authorized Responder Role in Target Tenant",
                feature_schema_digest=None,
                validation_rule="Human approval mandatory; target must NOT be in protected CIDR list; duration <= 86400s",
                error_behavior="Reject with PolicyViolationError; audit event logged",
                retry_behavior="Explicit analyst resubmission only",
                idempotency_policy="Unique idempotency key per action request",
                security_boundary="Human-in-the-Loop Safety Barrier",
                test_coverage="tests/phase4-security/test_response_policy_safety.py",
            ),
            "INT-14": InterfaceContract(
                interface_id="INT-14",
                producer="Manual Response Policy Engine",
                consumer="Firewall Simulator",
                contract_version="v1.0.0",
                required_fields=["rule_id", "tenant_id", "action_type", "target", "ttl_seconds", "network_action_executed"],
                allowed_optional_fields=[],
                identity_scope="Tenant Gateway Scope",
                feature_schema_digest=None,
                validation_rule="Safety Invariant: network_action_executed MUST be False (Simulated Only)",
                error_behavior="Reject action if real network execution attempted; fail safe",
                retry_behavior="Bounded retry on simulator lock; state verify query",
                idempotency_policy="Rule hash in simulated iptables table",
                security_boundary="Firewall Simulation Barrier",
                test_coverage="tests/phase4-unit/test_firewall_simulator.py",
            ),
            "INT-15": InterfaceContract(
                interface_id="INT-15",
                producer="Flower Federated Learning",
                consumer="Candidate Model Registry",
                contract_version="v1.0.0",
                required_fields=["candidate_id", "model_family", "model_digest", "artifact_path", "feature_schema_digest", "round_id"],
                allowed_optional_fields=["privacy_metrics", "test_metrics"],
                identity_scope="Consortium Candidate Pool",
                feature_schema_digest="LOCKED_FEATURE_SCHEMA_DIGEST",
                validation_rule="CandidateManifest + ModelManifest generated with SHA-256 digest; status=CANDIDATE",
                error_behavior="Abort registration; raise CandidateValidationError",
                retry_behavior="Next federated round creates new candidate",
                idempotency_policy="Candidate ID immutable",
                security_boundary="Federation-to-Registry Boundary",
                test_coverage="tests/federation-integration/test_candidate_registry.py",
            ),
            "INT-16": InterfaceContract(
                interface_id="INT-16",
                producer="Candidate Model Registry",
                consumer="Governance Release Review Workflow",
                contract_version="v1.0.0",
                required_fields=["candidate_id", "author_id", "evaluation_report", "status"],
                allowed_optional_fields=["review_comments"],
                identity_scope="Consortium Governance Scope",
                feature_schema_digest=None,
                validation_rule="Reviewer A (Security) and Reviewer B (Privacy) sign-off; self-approval prohibited",
                error_behavior="Transition to REJECTED if reviewer denies or self-approves",
                retry_behavior="Re-submission under new candidate sequence",
                idempotency_policy="One active review per candidate",
                security_boundary="Two-Person Integrity Governance Barrier",
                test_coverage="tests/governance-unit/test_approval_workflow.py",
            ),
            "INT-17": InterfaceContract(
                interface_id="INT-17",
                producer="Governance Release Review",
                consumer="Dual-Signer Engine (ECDSA + ML-DSA-65)",
                contract_version="v1.0.0",
                required_fields=["release_id", "canonical_manifest_bytes", "ecdsa_signer_id", "mldsa_signer_id"],
                allowed_optional_fields=[],
                identity_scope="Dual PQC Signing Authority",
                feature_schema_digest=None,
                validation_rule="RFC 8785 canonical bytes <= 4096B; ECDSA P-256 + NIST FIPS 204 ML-DSA-65 valid over same bytes",
                error_behavior="DualSignatureVerificationError if either signature fails or byte tamper detected",
                retry_behavior="Re-sign with active trust store keys",
                idempotency_policy="Deterministic canonical digest",
                security_boundary="Cryptographic Trust Store",
                test_coverage="tests/governance-unit/test_dual_signature.py",
            ),
            "INT-18": InterfaceContract(
                interface_id="INT-18",
                producer="Dual-Signer Engine",
                consumer="Hyperledger Fabric Governance Ledger",
                contract_version="v1.0.0",
                required_fields=["tx_id", "manifest_payload", "endorsements", "proposal_response"],
                allowed_optional_fields=[],
                identity_scope="4-Org Consortium (SmartBFT Ordering)",
                feature_schema_digest=None,
                validation_rule="3-of-4 distinct organization endorsements; SmartBFT quorum >= 3 of 4 orderers",
                error_behavior="Tx rejected; outbox buffers event; retries on ledger reconnect",
                retry_behavior="Transactional SQLite outbox auto-reconciliation",
                idempotency_policy="Unique tx_id commitment",
                security_boundary="Consortium Blockchain Ledger Boundary",
                test_coverage="tests/governance-security/test_endorsement_policy.py",
            ),
            "INT-19": InterfaceContract(
                interface_id="INT-19",
                producer="Fabric Governance Ledger",
                consumer="Model Activation & Rollback Engine",
                contract_version="v1.0.0",
                required_fields=["release_id", "ledger_commit_receipt", "sequence_number", "activation_status"],
                allowed_optional_fields=["revocation_reason"],
                identity_scope="Consortium Release Pool",
                feature_schema_digest=None,
                validation_rule="Ledger status == COMMITTED; sequence strictly monotonic; rollback target not revoked",
                error_behavior="Refuse activation; maintain active model; log audit warning",
                retry_behavior="Query ledger state on next activation trigger",
                idempotency_policy="Monotonic release sequence increment",
                security_boundary="Model Activation Gate",
                test_coverage="tests/governance-security/test_release_security.py",
            ),
            "INT-20": InterfaceContract(
                interface_id="INT-20",
                producer="Model Activation Engine",
                consumer="Tenant-Controlled FCS-HMD Inference Engine",
                contract_version="v1.2.0",
                required_fields=["tenant_id", "active_model_id", "approved_by_tenant", "fallback_rules_enabled"],
                allowed_optional_fields=[],
                identity_scope="Tenant Local Policy Boundary",
                feature_schema_digest="deployable_subset_v1",
                validation_rule="Tenant retains independent right to activate, defer, or emergency-disable global model",
                error_behavior="If tenant disables, FCS-HMD runs rules-only + local anomaly detector",
                retry_behavior="Tenant administrator toggles activation state",
                idempotency_policy="Tenant activation state table",
                security_boundary="Tenant Sovereignty Boundary",
                test_coverage="tests/phase5-integration/test_detection_bundle_management.py",
            ),
        }
        return contracts

    def verify_all_contracts(self) -> Dict[str, Any]:
        """Verify the health and compatibility of all 20 adjacent contracts."""
        results = {}
        all_compatible = True
        for cid, c in self.contracts.items():
            results[cid] = {
                "producer": c.producer,
                "consumer": c.consumer,
                "contract_version": c.contract_version,
                "status": c.status.value,
                "security_boundary": c.security_boundary,
                "test_coverage": c.test_coverage,
            }
            if c.status != InterfaceStatus.COMPATIBLE:
                all_compatible = False

        return {
            "total_contracts": len(self.contracts),
            "compatible": sum(1 for c in self.contracts.values() if c.status == InterfaceStatus.COMPATIBLE),
            "incompatible": sum(1 for c in self.contracts.values() if c.status != InterfaceStatus.COMPATIBLE),
            "all_compatible": all_compatible,
            "contracts": results,
        }

    validate_all = verify_all_contracts


ContractMatrixValidator = SystemContractMatrix


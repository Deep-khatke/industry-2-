#!/usr/bin/env python3
"""
FCS Phase 7 End-to-End Autonomous Demonstration Script.
Executes complete 12-step consortium blockchain governance lifecycle:
Candidate -> 2-Person Approval -> Dual-Signing (ECDSA + ML-DSA-65) -> 3-of-4 Endorsement
-> Fabric Ledger Commit -> FCS-HMD General Detector Activation -> Outage Simulation -> Revocation.
FCS Architecture v1.2 | Phase 7 Consortium Governance | Zero-Cost: ₹0 / $0
"""

import hashlib
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
gov_src = project_root / "services" / "governance" / "src"
if str(gov_src) not in sys.path:
    sys.path.insert(0, str(gov_src))

from fcs_governance.contracts.models import (
    ApprovalRole,
    EndorsementRecord,
    GovernanceOrg,
    RevocationReason,
)
from fcs_governance.contracts.state import ReleaseState
from fcs_governance.crypto.dual_signer import DualSigner
from fcs_governance.fabric.ledger_mock import MockFabricLedger
from fcs_governance.fabric.outbox import AuditOutboxRelay
from fcs_governance.fabric.recovery import LedgerOutageManager
from fcs_governance.workflow.approval import GovernanceApprovalError, ReleaseApprovalEngine
from fcs_governance.workflow.integration import FCSHMDGovernanceAdapter
from fcs_governance.workflow.promotion import ModelPromotionPipeline
from fcs_governance.workflow.rollback import ModelRollbackEngine


def run_demo() -> int:
    print("=" * 70)
    print("FEDERATED CYBER SHIELD (FCS) — PHASE 7 AUTONOMOUS DEMONSTRATION")
    print("Consortium Blockchain Governance, Post-Quantum Cryptography & CI/CD")
    print("=" * 70)

    demo_db_dir = project_root / "data" / "demo_phase7"
    demo_db_dir.mkdir(parents=True, exist_ok=True)
    ledger_db = str(demo_db_dir / "consortium_ledger.db")
    outbox_db = str(demo_db_dir / "governance_outbox.db")

    if os.path.exists(ledger_db):
        os.remove(ledger_db)
    if os.path.exists(outbox_db):
        os.remove(outbox_db)

    ledger = MockFabricLedger(db_path=ledger_db)
    outbox = AuditOutboxRelay(db_path=outbox_db, ledger=ledger)
    outage_mgr = LedgerOutageManager(ledger=ledger, outbox=outbox)
    dual_signer, dev_keys = DualSigner.create_ephemeral_dev_signer()

    pipeline = ModelPromotionPipeline(
        ledger=ledger,
        outbox=outbox,
        dual_signer=dual_signer,
        registry_dir=str(project_root / "artifacts" / "candidate-models"),
    )
    rollback_engine = ModelRollbackEngine(ledger=ledger, outbox=outbox)
    adapter = FCSHMDGovernanceAdapter(tenant_id="isp_01")

    # Step 1: Candidate Verification
    print("\n[Step 1] Inspecting Phase 6 Federated Candidate Lineage...")
    candidate_id = "candidate_exp_e6_06"
    print(f"  [+] Target Candidate: {candidate_id}")
    release = pipeline.create_release_from_candidate(
        candidate_id=candidate_id,
        author_identity="fl_engineer_alice",
        manifest_sequence=1,
    )
    print(f"  [+] Created Release ID: {release.release_id} (Initial Status: {release.status.value})")
    print(f"  [+] Artifact SHA-384: {release.artifact_digest_sha384[:32]}...")

    # Step 2: Request Review
    print("\n[Step 2] Transitioning Candidate to UNDER_REVIEW...")
    pipeline.request_review(release.release_id)
    print(f"  [+] Release Status: {release.status.value}")

    # Step 3: Self-Approval Prevention Check
    print("\n[Step 3] Verifying Two-Person Integrity & Self-Approval Prevention...")
    try:
        ReleaseApprovalEngine.add_approval(
            release=release,
            reviewer_identity="fl_engineer_alice",
            reviewer_role=ApprovalRole.REVIEWER_A,
            governing_org=GovernanceOrg.ISP_GOVERNANCE_A,
            author_identity="fl_engineer_alice",
        )
        print("  [-] ERROR: Self-approval was not rejected!")
        return 1
    except GovernanceApprovalError as e:
        print(f"  [+] SUCCESS: Self-approval blocked as expected: '{e}'")

    # Step 4: Independent Reviewer Approvals
    print("\n[Step 4] Recording Independent Multi-Reviewer Approvals...")
    app_a = ReleaseApprovalEngine.add_approval(
        release=release,
        reviewer_identity="auditor_bob_security",
        reviewer_role=ApprovalRole.REVIEWER_A,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_A,
        author_identity="fl_engineer_alice",
        comments="Artifact provenance and security bounds verified.",
    )
    print(f"  [+] Reviewer A (Security): Approved by {app_a.reviewer_identity} ({app_a.governing_org.value})")

    app_b = ReleaseApprovalEngine.add_approval(
        release=release,
        reviewer_identity="auditor_charlie_privacy",
        reviewer_role=ApprovalRole.REVIEWER_B,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_B,
        author_identity="fl_engineer_alice",
        comments="DP-SGD epsilon budget and holdout fairness approved.",
    )
    print(f"  [+] Reviewer B (Privacy): Approved by {app_b.reviewer_identity} ({app_b.governing_org.value})")
    print(f"  [+] Dual Review Complete -> Status: {release.status.value}")

    # Step 5: Dual-Signing (ECDSA P-256 + ML-DSA-65)
    print("\n[Step 5] Applying Canonical Dual Cryptographic Signatures (RFC 8785)...")
    signed_manifest = pipeline.execute_dual_signing(release.release_id, manifest_sequence=1)
    print(f"  [+] Conventional Signature ({signed_manifest.conventional_signature.algorithm.value}): {signed_manifest.conventional_signature.signature_hex[:28]}...")
    print(f"  [+] Post-Quantum Signature ({signed_manifest.post_quantum_signature.algorithm.value}): {signed_manifest.post_quantum_signature.signature_hex[:28]}...")
    assert DualSigner.verify_manifest(signed_manifest)
    print("  [+] Dual Signature Verification: PASSED (Zero Plaintext Downgrade)")
    print(f"  [+] Release Status: {release.status.value}")

    # Step 6: 3-of-4 Consortium Endorsement & Fabric Ledger Commit
    print("\n[Step 6] Collecting 3-of-4 Consortium Endorsements & Committing to Ledger...")
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="cert-peer0-org1", endorsement_signature_hex="sig_org1_verified_hex_00001"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="cert-peer0-org2", endorsement_signature_hex="sig_org2_verified_hex_00002"),
        EndorsementRecord(endorser_msp_id="Org3MSP", org=GovernanceOrg.ISP_GOVERNANCE_C, endorser_cert_id="cert-peer0-org3", endorsement_signature_hex="sig_org3_verified_hex_00003"),
    ]
    tx_id = pipeline.commit_to_consortium_ledger(release.release_id, endorsements)
    print(f"  [+] Ledger Transaction ID: {tx_id}")
    print(f"  [+] Release Status: {release.status.value}")

    # Step 7: Tenant Authorization & Activation for FCS-HMD
    print("\n[Step 7] Tenant Authorization & Activation into FCS-HMD General Detector...")
    pipeline.activate_for_tenant(release.release_id, tenant_id="isp_01", tenant_admin_sig="sig_tenant_admin_auth")
    adapter.load_governed_release(release)
    hmd_status = adapter.get_active_model_status()
    print(f"  [+] Tenant General Detector: {hmd_status['active_model_name']}")
    print(f"  [+] Tenant Anomaly Detector Isolated: {hmd_status['tenant_anomaly_detector_isolated']}")
    print(f"  [+] Specialists Isolated (DDoS/Scan/Botnet): {hmd_status['ddos_specialist_isolated']}")
    print(f"  [+] Manual Response Enforced: {hmd_status['manual_response_mode_enforced']}")
    print(f"  [+] network_action_executed: {hmd_status['network_action_executed']} (Permanent Safety Invariant)")

    # Step 8: Ledger Outage Simulation & Detection Continuity
    print("\n[Step 8] Simulating Consortium Ledger Network Outage...")
    outage_mgr.simulate_outage()
    health = outage_mgr.get_governance_health()
    print(f"  [+] Governance Health: {health['status']} ({health['reason']})")
    print(f"  [+] New Model Promotions: {health['promotions_allowed']}")
    print(f"  [+] Detection Continuity: {health['detection_engine_status']}")
    assert adapter.get_active_model_status()["network_action_executed"] is False
    print("  [+] Detection Engine Unaffected: CONTINUOUS REAL-TIME SCORING PRESERVED")

    # Step 9: Reconnection and Outbox Reconciliation
    print("\n[Step 9] Restoring Ledger Connectivity & Reconciling Outbox...")
    outage_mgr.restore_connectivity()
    reconciled = outage_mgr.reconcile_on_recovery()
    print(f"  [+] Reconnected. Outbox Reconciled Count: {reconciled}")
    print(f"  [+] Governance Health: {outage_mgr.get_governance_health()['status']}")

    # Step 10: Model Revocation
    print("\n[Step 10] Executing Emergency Model Revocation...")
    rev = rollback_engine.revoke_release(
        release=release,
        revoking_org=GovernanceOrg.ISP_GOVERNANCE_A,
        revoker_identity="ciso_officer",
        reason=RevocationReason.CONSORTIUM_EMERGENCY_RECALL,
        details="Consortium-mandated emergency recall for test verification",
        endorsements=endorsements,
    )
    print(f"  [+] Revocation ID: {rev.revocation_id}")
    print(f"  [+] Target Release ID: {rev.target_release_id}")
    print(f"  [+] Updated Release Status: {release.status.value}")

    print("\n" + "=" * 70)
    print("PHASE 7 AUTONOMOUS DEMONSTRATION COMPLETED SUCCESSFULLY (EXIT 0)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_demo())

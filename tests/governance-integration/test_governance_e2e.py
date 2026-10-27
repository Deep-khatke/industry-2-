"""Integration test for full end-to-end model release lifecycle."""

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
from fcs_governance.workflow.approval import ReleaseApprovalEngine
from fcs_governance.workflow.integration import FCSHMDGovernanceAdapter
from fcs_governance.workflow.promotion import ModelPromotionPipeline
from fcs_governance.workflow.rollback import ModelRollbackEngine


def test_full_governance_end_to_end_lifecycle(tmp_path):
    """
    Complete end-to-end verification of Phase 7 governance:
    Candidate -> 2-person approval -> Dual-signed manifest -> 3-of-4 consortium commit
    -> Tenant activation in FCS-HMD -> Revocation & Rollback.
    """
    db_ledger = str(tmp_path / "ledger_e2e.db")
    db_outbox = str(tmp_path / "outbox_e2e.db")
    ledger = MockFabricLedger(db_path=db_ledger)
    outbox = AuditOutboxRelay(db_path=db_outbox, ledger=ledger)
    dual_signer, _ = DualSigner.create_ephemeral_dev_signer()

    pipeline = ModelPromotionPipeline(ledger=ledger, outbox=outbox, dual_signer=dual_signer)
    rollback_engine = ModelRollbackEngine(ledger=ledger, outbox=outbox)
    adapter = FCSHMDGovernanceAdapter(tenant_id="isp_01")

    # Step 1: Create release candidate
    release_v1 = pipeline.create_release_from_candidate(
        candidate_id="candidate_exp_e6_06",
        author_identity="ml_engineer_01",
        manifest_sequence=1,
    )
    assert release_v1.status == ReleaseState.CANDIDATE

    # Step 2: Request review
    pipeline.request_review(release_v1.release_id)
    assert release_v1.status == ReleaseState.UNDER_REVIEW

    # Step 3: Reviewer A (Security) and Reviewer B (Privacy) approvals
    ReleaseApprovalEngine.add_approval(
        release=release_v1,
        reviewer_identity="sec_officer_alice",
        reviewer_role=ApprovalRole.REVIEWER_A,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_A,
        author_identity="ml_engineer_01",
    )
    ReleaseApprovalEngine.add_approval(
        release=release_v1,
        reviewer_identity="privacy_researcher_bob",
        reviewer_role=ApprovalRole.REVIEWER_B,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_B,
        author_identity="ml_engineer_01",
    )
    assert release_v1.status == ReleaseState.APPROVED

    # Step 4: Dual-signing (ECDSA + ML-DSA-65)
    signed_manifest = pipeline.execute_dual_signing(release_v1.release_id, manifest_sequence=1)
    assert release_v1.status == ReleaseState.SIGNED
    assert signed_manifest.conventional_signature.algorithm.value == "ECDSA_P256_SHA384"
    assert signed_manifest.post_quantum_signature.algorithm.value == "ML_DSA_65"

    # Step 5: Consortium Endorsement (3-of-4) and Ledger Commitment
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="c2", endorsement_signature_hex="sig2_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org3MSP", org=GovernanceOrg.ISP_GOVERNANCE_C, endorser_cert_id="c3", endorsement_signature_hex="sig3_valid_hex_00000"),
    ]
    tx_id = pipeline.commit_to_consortium_ledger(release_v1.release_id, endorsements)
    assert release_v1.status == ReleaseState.ELIGIBLE_FOR_ACTIVATION
    assert tx_id.startswith("tx-reg-")

    # Step 6: Tenant Activation for FCS-HMD
    pipeline.activate_for_tenant(release_v1.release_id, tenant_id="isp_01", tenant_admin_sig="tenant_admin_auth")
    assert release_v1.status == ReleaseState.ACTIVE

    # Step 7: Load into FCS-HMD General Detector
    adapter.load_governed_release(release_v1)
    status = adapter.get_active_model_status()
    assert status["active_model_name"] == f"governed_{release_v1.release_id}"
    assert status["network_action_executed"] is False
    assert status["auto_mode_enabled"] is False

    # Step 8: Revoke release
    rev = rollback_engine.revoke_release(
        release=release_v1,
        revoking_org=GovernanceOrg.ISP_GOVERNANCE_A,
        revoker_identity="ciso_executive",
        reason=RevocationReason.ACCURACY_DEGRADATION,
        details="Field performance drift identified",
        endorsements=endorsements,
    )
    assert release_v1.status == ReleaseState.REVOKED
    assert rev.revocation_id.startswith("rev-")

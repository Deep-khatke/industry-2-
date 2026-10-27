"""Security tests for Hyperledger Fabric 3-of-4 endorsement policy."""

import pytest
from fcs_governance.contracts.models import EndorsementRecord, GovernanceOrg
from fcs_governance.fabric.endorsement import EndorsementPolicyError, EndorsementPolicyEvaluator


def test_endorsement_policy_3_of_4_pass():
    """Verify that 3 distinct authorized organization endorsements pass."""
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="c2", endorsement_signature_hex="sig2_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org3MSP", org=GovernanceOrg.ISP_GOVERNANCE_C, endorser_cert_id="c3", endorsement_signature_hex="sig3_valid_hex_00000"),
    ]
    assert EndorsementPolicyEvaluator.evaluate(endorsements) is True


def test_endorsement_policy_4_of_4_pass():
    """Verify that all 4 authorized organization endorsements pass."""
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="c2", endorsement_signature_hex="sig2_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org3MSP", org=GovernanceOrg.ISP_GOVERNANCE_C, endorser_cert_id="c3", endorsement_signature_hex="sig3_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org4MSP", org=GovernanceOrg.PLATFORM_GOVERNANCE, endorser_cert_id="c4", endorsement_signature_hex="sig4_valid_hex_00000"),
    ]
    assert EndorsementPolicyEvaluator.evaluate(endorsements) is True


def test_endorsement_policy_insufficient_endorsements_fails():
    """Verify that only 2 endorsements fails with Insufficient endorsements error."""
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="c2", endorsement_signature_hex="sig2_valid_hex_00000"),
    ]
    with pytest.raises(EndorsementPolicyError, match="Insufficient endorsements: received 2/3"):
        EndorsementPolicyEvaluator.evaluate(endorsements)


def test_endorsement_policy_duplicate_org_rejected():
    """Verify that duplicate endorsements from the same organization are rejected."""
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1_peer0", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1_peer1", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="c2_peer0", endorsement_signature_hex="sig2_valid_hex_00000"),
    ]
    with pytest.raises(EndorsementPolicyError, match="Duplicate endorsement detected"):
        EndorsementPolicyEvaluator.evaluate(endorsements)


def test_endorsement_policy_unauthorized_msp_rejected():
    """Verify that endorsements from unauthorized MSPs are rejected."""
    endorsements = [
        EndorsementRecord(endorser_msp_id="Org1MSP", org=GovernanceOrg.ISP_GOVERNANCE_A, endorser_cert_id="c1", endorsement_signature_hex="sig1_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="Org2MSP", org=GovernanceOrg.ISP_GOVERNANCE_B, endorser_cert_id="c2", endorsement_signature_hex="sig2_valid_hex_00000"),
        EndorsementRecord(endorser_msp_id="RogueAttackerMSP", org=GovernanceOrg.ISP_GOVERNANCE_C, endorser_cert_id="c3", endorsement_signature_hex="sig3_valid_hex_00000"),
    ]
    with pytest.raises(EndorsementPolicyError, match="Unauthorized endorser MSP ID"):
        EndorsementPolicyEvaluator.evaluate(endorsements)

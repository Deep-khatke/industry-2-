"""Unit tests for ReleaseApprovalEngine and two-person integrity."""

import pytest
from fcs_governance.contracts.models import ApprovalRole, GovernanceOrg, ReleaseRecord
from fcs_governance.contracts.state import ReleaseState
from fcs_governance.workflow.approval import GovernanceApprovalError, ReleaseApprovalEngine


def test_independent_two_person_approval():
    """Verify that distinct Reviewer A and Reviewer B approvals transition release to APPROVED."""
    release = ReleaseRecord(
        release_id="rel-app-01",
        manifest_digest_sha384="sha384-digest",
        artifact_digest_sha384="sha384-art",
        evaluation_digest="sha256-eval",
        policy_version="1.2.0",
        model_lineage_ref="lineage-1",
        status=ReleaseState.UNDER_REVIEW,
    )

    # 1. Reviewer A approves
    ReleaseApprovalEngine.add_approval(
        release=release,
        reviewer_identity="alice_sec_auditor",
        reviewer_role=ApprovalRole.REVIEWER_A,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_A,
        author_identity="dev_author",
    )
    assert not ReleaseApprovalEngine.is_fully_approved(release)
    assert release.status == ReleaseState.UNDER_REVIEW

    # 2. Reviewer B approves (distinct person, different role)
    ReleaseApprovalEngine.add_approval(
        release=release,
        reviewer_identity="bob_ml_privacy_auditor",
        reviewer_role=ApprovalRole.REVIEWER_B,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_B,
        author_identity="dev_author",
    )
    assert ReleaseApprovalEngine.is_fully_approved(release)
    assert release.status == ReleaseState.APPROVED


def test_self_approval_prohibited():
    """Verify that author cannot approve their own release."""
    release = ReleaseRecord(
        release_id="rel-app-02",
        manifest_digest_sha384="sha384-digest",
        artifact_digest_sha384="sha384-art",
        evaluation_digest="sha256-eval",
        policy_version="1.2.0",
        model_lineage_ref="lineage-1",
        status=ReleaseState.UNDER_REVIEW,
    )

    with pytest.raises(GovernanceApprovalError, match="Self-approval prohibited"):
        ReleaseApprovalEngine.add_approval(
            release=release,
            reviewer_identity="author_charlie",
            reviewer_role=ApprovalRole.REVIEWER_A,
            governing_org=GovernanceOrg.ISP_GOVERNANCE_A,
            author_identity="author_charlie",
        )


def test_duplicate_role_approval_prohibited():
    """Verify that multiple reviewers cannot submit for the same role."""
    release = ReleaseRecord(
        release_id="rel-app-03",
        manifest_digest_sha384="sha384-digest",
        artifact_digest_sha384="sha384-art",
        evaluation_digest="sha256-eval",
        policy_version="1.2.0",
        model_lineage_ref="lineage-1",
        status=ReleaseState.UNDER_REVIEW,
    )

    ReleaseApprovalEngine.add_approval(
        release=release,
        reviewer_identity="alice",
        reviewer_role=ApprovalRole.REVIEWER_A,
        governing_org=GovernanceOrg.ISP_GOVERNANCE_A,
    )

    with pytest.raises(GovernanceApprovalError, match="has already been filled"):
        ReleaseApprovalEngine.add_approval(
            release=release,
            reviewer_identity="dave",
            reviewer_role=ApprovalRole.REVIEWER_A,
            governing_org=GovernanceOrg.ISP_GOVERNANCE_B,
        )

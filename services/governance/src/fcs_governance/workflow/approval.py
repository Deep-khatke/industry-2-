"""
Multi-Reviewer Governance Approval Engine.
Enforces two-person integrity: Reviewer A and Reviewer B must be distinct authorized principals.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional
from ..contracts.models import ApprovalRecord, ApprovalRole, GovernanceOrg, ReleaseRecord
from ..contracts.state import ReleaseState, validate_release_transition


class GovernanceApprovalError(Exception):
    """Raised when release approval constraints are violated."""
    pass


class ReleaseApprovalEngine:
    """Manages independent human review approvals for model release candidates."""

    @staticmethod
    def add_approval(
        release: ReleaseRecord,
        reviewer_identity: str,
        reviewer_role: ApprovalRole,
        governing_org: GovernanceOrg,
        author_identity: Optional[str] = None,
        comments: str = "",
    ) -> ApprovalRecord:
        """
        Record a formal approval for a model candidate.
        Enforces:
          1. Self-approval prevention (author cannot approve)
          2. Role validation (Reviewer A vs Reviewer B)
          3. Duplicate approval prevention (same reviewer cannot approve twice)
        """
        # 1. Self-approval check
        if author_identity and reviewer_identity == author_identity:
            raise GovernanceApprovalError(
                f"Self-approval prohibited: Author '{author_identity}' cannot approve their own release."
            )

        # 2. Duplicate approval check
        for app in release.approvals:
            if app.reviewer_identity == reviewer_identity:
                raise GovernanceApprovalError(
                    f"Duplicate approval: Reviewer '{reviewer_identity}' has already submitted an approval."
                )
            if app.reviewer_role == reviewer_role:
                raise GovernanceApprovalError(
                    f"Role '{reviewer_role.value}' has already been filled by reviewer '{app.reviewer_identity}'."
                )

        approval = ApprovalRecord(
            approval_id=f"app-{uuid.uuid4().hex[:12]}",
            release_id=release.release_id,
            reviewer_identity=reviewer_identity,
            reviewer_role=reviewer_role,
            governing_org=governing_org,
            approved=True,
            comments=comments,
        )
        release.approvals.append(approval)

        # 3. Check if all independent approvals are collected
        has_rev_a = any(a.reviewer_role == ApprovalRole.REVIEWER_A and a.approved for a in release.approvals)
        has_rev_b = any(a.reviewer_role == ApprovalRole.REVIEWER_B and a.approved for a in release.approvals)

        if has_rev_a and has_rev_b:
            if release.status == ReleaseState.UNDER_REVIEW or release.status == ReleaseState.CANDIDATE:
                validate_release_transition(release.status, ReleaseState.APPROVED)
                release.status = ReleaseState.APPROVED

        return approval

    @staticmethod
    def is_fully_approved(release: ReleaseRecord) -> bool:
        """Verify that distinct Reviewer A and Reviewer B approvals are recorded."""
        reviewers = {
            a.reviewer_role: a.reviewer_identity
            for a in release.approvals
            if a.approved
        }
        if ApprovalRole.REVIEWER_A not in reviewers or ApprovalRole.REVIEWER_B not in reviewers:
            return False
        # Must be distinct individuals
        return reviewers[ApprovalRole.REVIEWER_A] != reviewers[ApprovalRole.REVIEWER_B]

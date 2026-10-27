"""
Hyperledger Fabric 3-of-4 Endorsement Policy Evaluator.
Validates that governance transactions receive valid endorsements from at least 3 distinct governing organizations.
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

from typing import List, Set
from ..contracts.models import EndorsementRecord, GovernanceOrg
from .topology import CONSORTIUM_ORGANIZATIONS


class EndorsementPolicyError(Exception):
    """Raised when an endorsement policy evaluation fails."""
    pass


class EndorsementPolicyEvaluator:
    """
    Evaluates 3-of-4 organization endorsement requirement for governance transactions:
    MAJORITY(Org1MSP, Org2MSP, Org3MSP, Org4MSP) -> Minimum 3 distinct valid endorsements.
    """

    REQUIRED_ENDORSEMENT_THRESHOLD = 3

    @classmethod
    def evaluate(cls, endorsements: List[EndorsementRecord]) -> bool:
        """
        Evaluate endorsement collection.
        Raises EndorsementPolicyError if requirements are not met.
        Returns True if 3-of-4 valid endorsements are verified.
        """
        if not endorsements:
            raise EndorsementPolicyError("No endorsements provided")

        valid_msps = {org_topo.msp_id: org_topo.org for org_topo in CONSORTIUM_ORGANIZATIONS.values()}
        endorsing_orgs: Set[GovernanceOrg] = set()

        for rec in endorsements:
            # 1. Verify MSP identity is an authorized consortium member
            if rec.endorser_msp_id not in valid_msps:
                raise EndorsementPolicyError(
                    f"Unauthorized endorser MSP ID: '{rec.endorser_msp_id}' is not in consortium topology"
                )

            expected_org = valid_msps[rec.endorser_msp_id]
            if rec.org != expected_org:
                raise EndorsementPolicyError(
                    f"Endorsement org mismatch: claims {rec.org}, but MSP is {rec.endorser_msp_id}"
                )

            # 2. Duplicate detection
            if rec.org in endorsing_orgs:
                raise EndorsementPolicyError(
                    f"Duplicate endorsement detected for organization {rec.org.value}"
                )

            # 3. Signature presence
            if not rec.endorsement_signature_hex or len(rec.endorsement_signature_hex) < 16:
                raise EndorsementPolicyError(
                    f"Invalid or empty endorsement signature from {rec.org.value}"
                )

            endorsing_orgs.add(rec.org)

        if len(endorsing_orgs) < cls.REQUIRED_ENDORSEMENT_THRESHOLD:
            raise EndorsementPolicyError(
                f"Insufficient endorsements: received {len(endorsing_orgs)}/{cls.REQUIRED_ENDORSEMENT_THRESHOLD} "
                f"required governing organizations. Endorsers: {[o.value for o in endorsing_orgs]}"
            )

        return True

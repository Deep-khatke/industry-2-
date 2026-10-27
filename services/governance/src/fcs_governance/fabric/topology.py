"""
Consortium Topology and SmartBFT Reference Architecture.
Defines the four governing organizations and consensus parameters.
FCS Architecture v1.2 | Phase 7 Consortium Governance | Zero-Cost: ₹0 / $0
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field
from ..contracts.models import GovernanceOrg


class OrgTopology(BaseModel):
    """Specification of a governing organization in the consortium."""
    org: GovernanceOrg
    msp_id: str
    peer_endpoints: List[str]
    ca_endpoint: str
    admin_identity: str


class SmartBFTClusterConfig(BaseModel):
    """
    SmartBFT ordering service configuration for Phase 7.
    Reference topology uses N=4 orderers, tolerating F=1 Byzantine fault.
    Quorum size: 2F + 1 = 3 orderers.
    """
    total_orderers: int = Field(default=4, description="Total orderer nodes N=3F+1")
    max_byzantine_faults: int = Field(default=1, description="Max tolerated faulty/Byzantine orderers F")
    quorum_size: int = Field(default=3, description="Quorum size: 2F+1")
    batch_timeout_ms: int = Field(default=500, description="Block batch timeout in milliseconds")
    max_message_count: int = Field(default=10, description="Max transactions per block")
    channel_id: str = Field(default="fcs-governance-channel", description="Consortium channel ID")


# Default 4-Organization Consortium Profile
CONSORTIUM_ORGANIZATIONS: Dict[GovernanceOrg, OrgTopology] = {
    GovernanceOrg.ISP_GOVERNANCE_A: OrgTopology(
        org=GovernanceOrg.ISP_GOVERNANCE_A,
        msp_id="Org1MSP",
        peer_endpoints=["peer0.org1.fcs.net:7051", "peer1.org1.fcs.net:7051"],
        ca_endpoint="ca.org1.fcs.net:7054",
        admin_identity="admin-org1",
    ),
    GovernanceOrg.ISP_GOVERNANCE_B: OrgTopology(
        org=GovernanceOrg.ISP_GOVERNANCE_B,
        msp_id="Org2MSP",
        peer_endpoints=["peer0.org2.fcs.net:7051", "peer1.org2.fcs.net:7051"],
        ca_endpoint="ca.org2.fcs.net:7054",
        admin_identity="admin-org2",
    ),
    GovernanceOrg.ISP_GOVERNANCE_C: OrgTopology(
        org=GovernanceOrg.ISP_GOVERNANCE_C,
        msp_id="Org3MSP",
        peer_endpoints=["peer0.org3.fcs.net:7051", "peer1.org3.fcs.net:7051"],
        ca_endpoint="ca.org3.fcs.net:7054",
        admin_identity="admin-org3",
    ),
    GovernanceOrg.PLATFORM_GOVERNANCE: OrgTopology(
        org=GovernanceOrg.PLATFORM_GOVERNANCE,
        msp_id="Org4MSP",
        peer_endpoints=["peer0.org4.fcs.net:7051", "peer1.org4.fcs.net:7051"],
        ca_endpoint="ca.org4.fcs.net:7054",
        admin_identity="admin-platform",
    ),
}

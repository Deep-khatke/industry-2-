"""Data models for dataset registry and licensing constraints."""

from enum import StrEnum

from pydantic import BaseModel, Field


class LicenseType(StrEnum):
    """Permitted dataset license classifications."""

    RESEARCH_ONLY = "RESEARCH_ONLY"
    OPEN_ACCESS_ACADEMIC = "OPEN_ACCESS_ACADEMIC"
    COMMERCIAL_ALLOWED = "COMMERCIAL_ALLOWED"
    LICENSE_REVIEW_REQUIRED = "LICENSE_REVIEW_REQUIRED"
    PROPRIETARY_RESTRICTED = "PROPRIETARY_RESTRICTED"


class DatasetSourceRecord(BaseModel):
    """Metadata record for an authoritative registered cybersecurity dataset source."""

    dataset_id: str = Field(..., description="Unique dataset identifier (e.g. NF-UQ-NIDS-v2)")
    version: str = Field(..., description="Dataset version string")
    official_url: str = Field(..., description="Authoritative official download URL")
    rdm_uq_url: str | None = Field(default=None, description="University research data repository URL if applicable")
    publisher: str = Field(..., description="Publishing institution or university laboratory")
    authors: str = Field(..., description="Original dataset authors and researchers")
    citation: str = Field(..., description="Required academic publication citation")
    license_type: LicenseType = Field(default=LicenseType.RESEARCH_ONLY, description="Classification of license")
    license_terms: str = Field(..., description="Summary of permissible use and restrictions")
    commercial_use_allowed: bool = Field(
        default=False,
        description="Whether commercial deployment or use is legally permitted",
    )
    feature_family: str = Field(default="NetFlow-v2", description="Feature family (NetFlow-v2, NetFlow-v3, etc.)")
    feature_count: int = Field(default=43, description="Expected number of flow feature columns")
    parent_sources: list[str] = Field(
        default_factory=list,
        description="Parent datasets incorporated into this combined dataset",
    )
    parent_overlap_policy: str = Field(
        default="MUTUALLY_EXCLUSIVE_OR_DISJOINT_ONLY",
        description="Rule regarding concurrent usage with parent sources",
    )
    known_limitations: list[str] = Field(
        default_factory=list,
        description="Documented domain limitations, testbed artifacts, or class imbalances",
    )

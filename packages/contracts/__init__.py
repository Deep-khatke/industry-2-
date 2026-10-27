"""Data contracts package for Federated Cyber Shield."""

from .dataset_manifest import DatasetManifest, SignatureMetadata
from .enums import FlowDirection, PortClass, TransportProtocol
from .exceptions import ContractValidationError, InvalidSchemaVersionError, RecordSizeLimitExceeded
from .feature_spec import (
    FeatureAvailabilityStatus,
    FeatureDefinition,
    FeatureSpec,
    get_deployable_feature_spec,
    get_research_feature_spec,
)
from .flow_event import FlowEvent, compute_deterministic_event_id
from .model_score import ModelScore, ModelType, ScoringStatus
from .partition_manifest import ClientPartitionInfo, FederatedPartitionSetManifest, PartitionRegime
from .split_manifest import SplitManifest
from .stubs import DetectionAlertStub, FederatedWeightsStub

__all__ = [
    "ClientPartitionInfo",
    "ContractValidationError",
    "DatasetManifest",
    "DetectionAlertStub",
    "FeatureAvailabilityStatus",
    "FeatureDefinition",
    "FeatureSpec",
    "FederatedPartitionSetManifest",
    "FederatedWeightsStub",
    "FlowDirection",
    "FlowEvent",
    "InvalidSchemaVersionError",
    "ModelScore",
    "ModelType",
    "PartitionRegime",
    "PortClass",
    "RecordSizeLimitExceeded",
    "ScoringStatus",
    "SignatureMetadata",
    "SplitManifest",
    "TransportProtocol",
    "compute_deterministic_event_id",
    "get_deployable_feature_spec",
    "get_research_feature_spec",
]

"""Unit tests for schema discovery, feature contracts, and NetFlow version validation."""

from pathlib import Path

import pytest

from fcs_udip.schemas.inspector import IncompatibleSchemaError, SchemaInspector
from packages.contracts.feature_spec import (
    FeatureAvailabilityStatus,
    get_deployable_feature_spec,
    get_research_feature_spec,
)


@pytest.mark.dataset_unit
class TestSchemaAndFeatures:
    """Validate canonical 43-feature NetFlow v2 schema matching and version isolation."""

    def test_canonical_43_features_spec(self) -> None:
        spec = get_research_feature_spec()
        assert len(spec.features) == 43
        names = spec.feature_names()
        assert "IPV4_SRC_ADDR" in names
        assert "L4_SRC_PORT" in names
        assert "IN_BYTES" in names
        assert "OUT_BYTES" in names
        assert "FLOW_DURATION_MILLISECONDS" in names
        assert "TCP_FLAGS" in names

        # Digest should be deterministic SHA-256
        digest1 = spec.compute_schema_digest()
        digest2 = spec.compute_schema_digest()
        assert digest1 == digest2
        assert len(digest1) == 64

    def test_deployable_subset_parity(self) -> None:
        deployable = get_deployable_feature_spec()
        # Deployable subset should only contain available / derivable fields
        for f in deployable.features:
            assert f.production_availability in (
                FeatureAvailabilityStatus.DIRECTLY_AVAILABLE,
                FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM,
            )
        assert len(deployable.features) < 43

    def test_inspect_clean_synthetic_fixture(self) -> None:
        fixture_path = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        inspector = SchemaInspector()
        info = inspector.inspect_file(fixture_path)

        assert info["detected_classification"] == "NETFLOW_V2_43"
        assert info["canonical_features_matched_count"] == 43
        assert len(info["missing_canonical_features"]) == 0
        assert info["has_binary_label"]
        assert info["has_attack_label"]
        assert info["is_netflow_v2_compatible"]

    def test_reject_netflow_v3_mixing(self) -> None:
        v3_fixture = Path("data/synthetic-fixtures/netflow_v3_test.parquet")
        inspector = SchemaInspector()
        with pytest.raises(IncompatibleSchemaError) as exc_info:
            inspector.validate_netflow_v2_compatibility(v3_fixture)
        assert "NetFlow v3 (53 features)" in str(exc_info.value)
        assert "NetFlow v3 must remain separately versioned" in str(exc_info.value)

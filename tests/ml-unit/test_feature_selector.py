"""Unit tests for FeatureSelector, tracks, and anti-leakage protection."""

import numpy as np
import polars as pl
import pytest

from fcs_ml.features.selector import FeatureSelector, FeatureTrack, TargetLeakageError


@pytest.mark.ml_unit
class TestFeatureSelector:
    """Validate feature extraction and anti-leakage guards."""

    def test_research_track_features(self) -> None:
        selector = FeatureSelector(track=FeatureTrack.RESEARCH_BENCHMARK, drop_raw_ips=True)
        available = ["IN_BYTES", "OUT_BYTES", "IPV4_SRC_ADDR", "L4_SRC_PORT", "binary_label", "canonical_attack_label"]
        f_names = selector.get_feature_names(available)
        assert "IN_BYTES" in f_names
        assert "OUT_BYTES" in f_names
        assert "L4_SRC_PORT" in f_names
        assert "IPV4_SRC_ADDR" not in f_names  # Dropped for privacy/anti-memorization

    def test_deployable_track_subset(self) -> None:
        selector = FeatureSelector(track=FeatureTrack.DEPLOYABLE_SUBSET)
        available = ["IN_BYTES", "OUT_BYTES", "FLOW_DURATION_MILLISECONDS", "L4_SRC_PORT", "NON_EXISTENT_DPI_FIELD"]
        f_names = selector.get_feature_names(available)
        assert "IN_BYTES" in f_names
        assert "NON_EXISTENT_DPI_FIELD" not in f_names

    def test_target_leakage_rejected(self) -> None:
        selector = FeatureSelector()
        prohibited_features = ["IN_BYTES", "Attack", "OUT_BYTES"]
        with pytest.raises(TargetLeakageError) as exc_info:
            selector.validate_features(prohibited_features)
        assert "TARGET LEAKAGE DETECTED: Column 'Attack'" in str(exc_info.value)

    def test_source_identifier_leakage_rejected(self) -> None:
        selector = FeatureSelector()
        with pytest.raises(TargetLeakageError) as exc_info:
            selector.validate_features(["IN_BYTES", "dataset_source"])
        assert "TARGET LEAKAGE DETECTED: Column 'dataset_source'" in str(exc_info.value)

    def test_matrix_extraction_and_nan_cleaning(self) -> None:
        selector = FeatureSelector(track=FeatureTrack.RESEARCH_BENCHMARK)
        df = pl.DataFrame({
            "IN_BYTES": [100.0, None, 300.0],
            "OUT_BYTES": [50.0, 150.0, np.nan],
            "L4_SRC_PORT": [80, 443, 8080],
            "binary_label": [0, 1, 0],
            "canonical_attack_label": ["Benign", "DoS", "Benign"],
        })
        X, y_bin, y_multi, f_names = selector.extract_matrices(df, ["IN_BYTES", "OUT_BYTES", "L4_SRC_PORT"])
        assert X.shape == (3, 3)
        assert not np.isnan(X).any()
        assert np.array_equal(y_bin, np.array([0, 1, 0]))
        assert len(y_multi) == 3

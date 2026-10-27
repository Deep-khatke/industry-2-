"""Security and data leakage prevention test suite."""

import polars as pl
import pytest

from fcs_udip.harmonization.feature_harmonizer import FeatureHarmonizer
from fcs_udip.harmonization.label_normalizer import LabelNormalizer, TargetLeakageError
from fcs_udip.preprocessing.preprocessor import TrainingOnlyPreprocessor
from fcs_udip.splitting.splitter import DatasetSplitter


@pytest.mark.dataset_security
class TestLeakagePrevention:
    """Security tests ensuring zero target leakage, session leakage, or preprocessor contamination."""

    def test_deliberate_label_leakage_rejected(self) -> None:
        normalizer = LabelNormalizer("configs/datasets/label_mapping.yaml")
        prohibited_leak_attempts = [
            "Label", "label",
            "Attack", "attack",
            "canonical_attack_label", "original_attack_label",
            "binary_label", "dataset_source", "tenant_id", "split_id"
        ]

        for prohibited in prohibited_leak_attempts:
            with pytest.raises(TargetLeakageError) as exc_info:
                normalizer.validate_predictor_features(["IN_BYTES", prohibited, "TCP_FLAGS"])
            assert f"TARGET LEAKAGE DETECTED: Column '{prohibited}'" in str(exc_info.value)

    def test_feature_harmonizer_rejects_target_columns_in_matrix(self) -> None:
        harmonizer = FeatureHarmonizer()
        # Create df with label column attempted to be extracted
        df = pl.DataFrame({
            "IN_BYTES": [100, 200],
            "OUT_BYTES": [50, 100],
            "FLOW_DURATION_MILLISECONDS": [10, 20],
            "binary_label": [0, 1],
            "canonical_attack_label": ["Benign", "DDoS"],
        })

        X, y_bin, y_multi = harmonizer.get_research_feature_matrix(df)
        # X must never contain binary_label or canonical_attack_label
        assert "binary_label" not in X.columns
        assert "canonical_attack_label" not in X.columns
        assert "Attack" not in X.columns
        assert "Label" not in X.columns

    def test_group_aware_isolation_prevents_host_session_leakage(self) -> None:
        # Create dataset where same host appears in multiple flows
        df = pl.DataFrame({
            "IPV4_SRC_ADDR": ["10.100.1.5", "10.100.1.5", "10.100.2.10", "10.100.3.15", "10.100.4.20"] * 10,
            "IN_BYTES": [100, 200, 300, 400, 500] * 10,
            "Attack": ["Benign", "DDoS", "Benign", "Scanning", "Benign"] * 10,
            "Label": [0, 1, 0, 1, 0] * 10,
        })

        splitter = DatasetSplitter(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2, seed=42)
        train_df, val_df, test_df, _ = splitter.split_group_aware(df, group_column="IPV4_SRC_ADDR")

        train_ips = set(train_df["IPV4_SRC_ADDR"].to_list())
        test_ips = set(test_df["IPV4_SRC_ADDR"].to_list())

        # No IP can cross the train/test boundary
        assert len(train_ips.intersection(test_ips)) == 0

    def test_preprocessor_fit_never_touches_test_distribution(self) -> None:
        train_df = pl.DataFrame({"IN_BYTES": [10.0, 20.0, 30.0]})
        test_df = pl.DataFrame({"IN_BYTES": [1_000_000.0, 2_000_000.0]})

        pre = TrainingOnlyPreprocessor(scaling_method="robust")
        pre.fit(train_df)

        # Train median is 20.0
        assert pre.scale_center["IN_BYTES"] == 20.0

        # Transforming test does NOT update the center
        pre.transform(test_df)
        assert pre.scale_center["IN_BYTES"] == 20.0

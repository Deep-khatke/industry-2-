"""Unit tests for label normalization, taxonomy mapping, and anti-leakage guards."""

import polars as pl
import pytest

from fcs_udip.harmonization.label_normalizer import LabelNormalizer, TargetLeakageError


@pytest.mark.dataset_unit
class TestLabelNormalization:
    """Validate cross-dataset label mapping and strict rejection of label leakage into predictors."""

    def test_cross_dataset_attack_mappings(self) -> None:
        normalizer = LabelNormalizer("configs/datasets/label_mapping.yaml")

        # NF-CSE-CIC-IDS2018-v2 variants
        assert normalizer.normalize_label("DDoS attacks-LOIC-HTTP", "NF-CSE-CIC-IDS2018-v2") == "DDoS"
        assert normalizer.normalize_label("DoS attacks-Slowloris", "NF-CSE-CIC-IDS2018-v2") == "DoS"
        assert normalizer.normalize_label("FTP-BruteForce", "NF-CSE-CIC-IDS2018-v2") == "Brute Force"
        assert normalizer.normalize_label("SQL Injection", "NF-CSE-CIC-IDS2018-v2") == "Injection"
        assert normalizer.normalize_label("Bot", "NF-CSE-CIC-IDS2018-v2") == "Botnet"

        # NF-BoT-IoT-v2 variants
        assert normalizer.normalize_label("OS_Fingerprint", "NF-BoT-IoT-v2") == "Scanning"
        assert normalizer.normalize_label("Service_Scan", "NF-BoT-IoT-v2") == "Scanning"

        # NF-ToN-IoT-v2 variants
        assert normalizer.normalize_label("password", "NF-ToN-IoT-v2") == "Brute Force"
        assert normalizer.normalize_label("xss", "NF-ToN-IoT-v2") == "Injection"

        # Benign
        assert normalizer.normalize_label("Benign", "NF-UQ-NIDS-v2") == "Benign"

    def test_apply_normalization_to_dataframe(self) -> None:
        normalizer = LabelNormalizer("configs/datasets/label_mapping.yaml")
        raw_df = pl.DataFrame({
            "Attack": ["Benign", "DDoS", "DoS attacks-Hulk", "OS_Fingerprint", "UnknownAttackXYZ"],
            "Label": [0, 1, 1, 1, 1],
            "IN_BYTES": [100, 200, 300, 400, 500],
        })

        norm_df = normalizer.apply_normalization(raw_df, source_id="NF-CSE-CIC-IDS2018-v2")
        assert isinstance(norm_df, pl.DataFrame)

        assert "canonical_attack_label" in norm_df.columns
        assert "binary_label" in norm_df.columns
        assert "dataset_source" in norm_df.columns
        assert "label_mapping_version" in norm_df.columns

        assert norm_df["canonical_attack_label"].to_list() == [
            "Benign",
            "DDoS",
            "DoS",
            "Scanning",  # OS_Fingerprint -> Scanning
            "Unknown",
        ]
        assert norm_df["binary_label"].to_list() == [0, 1, 1, 1, 1]

    def test_target_leakage_prohibition(self) -> None:
        normalizer = LabelNormalizer("configs/datasets/label_mapping.yaml")

        # Safe feature list
        safe_features = ["IN_BYTES", "OUT_BYTES", "FLOW_DURATION_MILLISECONDS", "TCP_FLAGS"]
        normalizer.validate_predictor_features(safe_features)

        # Attempt to leak label column
        with pytest.raises(TargetLeakageError) as exc_info:
            normalizer.validate_predictor_features(["IN_BYTES", "Attack", "TCP_FLAGS"])
        assert "TARGET LEAKAGE DETECTED: Column 'Attack'" in str(exc_info.value)

        # Attempt to leak binary_label
        with pytest.raises(TargetLeakageError) as exc_info:
            normalizer.validate_predictor_features(["IN_BYTES", "binary_label"])
        assert "TARGET LEAKAGE DETECTED: Column 'binary_label'" in str(exc_info.value)

        # Attempt to leak dataset_source shortcut
        with pytest.raises(TargetLeakageError) as exc_info:
            normalizer.validate_predictor_features(["IN_BYTES", "dataset_source"])
        assert "TARGET LEAKAGE DETECTED: Column 'dataset_source'" in str(exc_info.value)

"""Unit tests for data quality validation, anomaly quarantine, and bound checking."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.validation.quality_validator import DataQualityValidator


@pytest.mark.dataset_unit
class TestQualityValidation:
    """Validate ACCEPT, NORMALIZE, QUARANTINE, and REJECT rules."""

    def test_clean_fixture_100_percent_accepted(self) -> None:
        clean_path = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        df = pl.read_parquet(clean_path)

        validator = DataQualityValidator()
        clean_df, quaran_df, metrics = validator.validate_and_clean(df)

        assert metrics["initial_row_count"] == 1400
        assert metrics["clean_row_count"] == 1400
        assert metrics["quarantine_row_count"] == 0
        assert metrics["clean_ratio"] == 1.0
        assert len(quaran_df) == 0

    def test_corrupt_records_segregated_to_quarantine(self) -> None:
        corrupt_path = Path("data/synthetic-fixtures/corrupt_quality_test.parquet")
        df = pl.read_parquet(corrupt_path)

        validator = DataQualityValidator()
        clean_df, quaran_df, metrics = validator.validate_and_clean(df)

        # 20 corrupted records were injected into corrupt_quality_test
        assert metrics["clean_row_count"] == 1380
        assert metrics["quarantine_row_count"] == 20
        assert len(quaran_df) == 20
        assert "quarantine_reason" in quaran_df.columns

        # Verify quarantine reasons contain expected violations
        reasons = quaran_df["quarantine_reason"].to_list()
        assert any("Negative value in count/duration column: IN_BYTES" in r for r in reasons)
        assert any("Port out of range [0, 65535]: L4_SRC_PORT" in r for r in reasons)
        assert any("Protocol ID out of range [0, 255]" in r for r in reasons)

    def test_nan_imputation_in_clean_numeric_features(self) -> None:
        df = pl.DataFrame({
            "IN_BYTES": [100, 200, 300],
            "OUT_BYTES": [50, 100, 150],
            "IN_PKTS": [1, 2, 3],
            "OUT_PKTS": [1, 2, 3],
            "FLOW_DURATION_MILLISECONDS": [10, 20, 30],
            "L4_SRC_PORT": [1024, 2048, 4096],
            "L4_DST_PORT": [80, 443, 22],
            "PROTOCOL": [6, 6, 17],
            "SRC_TO_DST_SECOND_BYTES": [1000.0, float("nan"), 3000.0],  # NaN in non-critical float
            "Label": [0, 1, 0],
            "Attack": ["Benign", "DDoS", "Benign"],
        })

        validator = DataQualityValidator()
        clean_df, quaran_df, metrics = validator.validate_and_clean(df)

        assert metrics["clean_row_count"] == 3
        assert metrics["quarantine_row_count"] == 0
        # NaN should be normalized/imputed with 0
        assert not clean_df["SRC_TO_DST_SECOND_BYTES"].is_nan().any()
        assert clean_df["SRC_TO_DST_SECOND_BYTES"][1] == 0.0

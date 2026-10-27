"""Integration tests for model-specific dataset generation views."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.exports.model_exporter import ModelDatasetExporter


@pytest.mark.dataset_integration
class TestModelExports:
    """Validate dataset views tailored to General IDS, Specialists, and Anomaly Detectors."""

    @pytest.fixture
    def preprocessed_fixture(self) -> pl.DataFrame:
        p = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        df = pl.read_parquet(p)
        return df.with_columns(
            pl.col("Attack").alias("canonical_attack_label"),
            pl.col("Label").cast(pl.Int64).alias("binary_label"),
        )

    def test_export_general_ids(self, preprocessed_fixture: pl.DataFrame) -> None:
        exporter = ModelDatasetExporter()
        gen_df = exporter.export_general_ids(preprocessed_fixture)
        assert "binary_label" in gen_df.columns
        assert set(gen_df["binary_label"].unique().to_list()).issubset({0, 1})

    def test_export_ddos_specialist_isolation(self, preprocessed_fixture: pl.DataFrame) -> None:
        exporter = ModelDatasetExporter()
        ddos_df = exporter.export_ddos_specialist(preprocessed_fixture, negative_ratio=1.0)
        assert "specialist_target" in ddos_df.columns

        # Verify positive rows are strictly DDoS attacks
        positives = ddos_df.filter(pl.col("specialist_target") == 1)
        assert (positives["canonical_attack_label"] == "DDoS").all()

        # Verify negative rows do not contain DDoS
        negatives = ddos_df.filter(pl.col("specialist_target") == 0)
        assert not (negatives["canonical_attack_label"] == "DDoS").any()

    def test_export_scanning_specialist_isolation(self, preprocessed_fixture: pl.DataFrame) -> None:
        exporter = ModelDatasetExporter()
        scan_df = exporter.export_scanning_specialist(preprocessed_fixture)
        assert "specialist_target" in scan_df.columns

        positives = scan_df.filter(pl.col("specialist_target") == 1)
        assert positives["canonical_attack_label"].is_in(["Scanning", "Reconnaissance"]).all()

    def test_export_anomaly_detector_benign_isolation(self, preprocessed_fixture: pl.DataFrame) -> None:
        """Verify anomaly detector training view contains 100% benign network traffic."""
        exporter = ModelDatasetExporter()
        # Mock train and test
        train_half = preprocessed_fixture[:700]
        test_half = preprocessed_fixture[700:]

        anomaly_train, anomaly_eval = exporter.export_anomaly_detector_views(train_half, test_half)

        # Anomaly training baseline must be strictly benign
        assert (anomaly_train["binary_label"] == 0).all()
        assert (anomaly_train["canonical_attack_label"] == "Benign").all()

        # Evaluation view must retain both benign and attack traffic
        assert set(anomaly_eval["binary_label"].unique().to_list()) == {0, 1}

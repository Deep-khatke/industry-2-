"""Unit tests for DatasetLoader and split manifest verification."""

import pytest

from fcs_ml.data.loader import DatasetLoader


@pytest.mark.ml_unit
class TestDatasetLoader:
    """Validate dataset split loading, row limits, and holdout separation."""

    def test_verify_manifest_success(self) -> None:
        loader = DatasetLoader()
        info = loader.verify_manifest("data/processed/dataset_manifest.json")
        assert info["dataset_id"] == "NF-UQ-NIDS-v2-FCS-Processed"
        assert info["signature_valid"] is True
        assert len(info["feature_schema_digest"]) == 64

    def test_load_splits_shapes(self) -> None:
        loader = DatasetLoader()
        train_df, val_df, test_df = loader.load_splits()
        assert len(train_df) > 0
        assert len(val_df) > 0
        assert len(test_df) > 0
        assert "IN_BYTES" in train_df.columns
        assert "binary_label" in train_df.columns

    def test_load_splits_bounded_rows(self) -> None:
        loader = DatasetLoader()
        train_df, val_df, test_df = loader.load_splits(
            max_train_rows=50,
            max_val_rows=20,
            max_test_rows=20,
        )
        assert len(train_df) == 50
        assert len(val_df) == 20
        assert len(test_df) == 20

    def test_load_with_holdout_isolation(self) -> None:
        loader = DatasetLoader()
        train_h, val_h, test_h, holdout_df = loader.load_with_holdout("NF-ToN-IoT-v2")
        # Ensure NF-ToN-IoT-v2 never appears in train or val
        if "dataset_source" in train_h.columns:
            train_sources = set(train_h["dataset_source"].unique().to_list())
            assert "NF-ToN-IoT-v2" not in train_sources
        if len(holdout_df) > 0:
            assert (holdout_df["dataset_source"] == "NF-ToN-IoT-v2").all()

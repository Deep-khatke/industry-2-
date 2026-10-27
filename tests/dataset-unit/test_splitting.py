"""Unit tests for leakage-safe group-aware splitting and source holdout isolation."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.splitting.splitter import DatasetSplitter


@pytest.mark.dataset_unit
class TestDatasetSplitting:
    """Validate group-aware partitioning, seed determinism, and holdout exclusion."""

    def test_group_aware_zero_overlap(self) -> None:
        clean_path = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        df = pl.read_parquet(clean_path)

        splitter = DatasetSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
        train_df, val_df, test_df, manifest = splitter.split_group_aware(
            df, group_column="IPV4_SRC_ADDR"
        )

        assert len(train_df) > 0
        assert len(val_df) > 0
        assert len(test_df) > 0
        assert len(train_df) + len(val_df) + len(test_df) == len(df)

        # STRICT CHECK: Zero host IP overlap between train and test
        train_hosts = set(train_df["IPV4_SRC_ADDR"].unique().to_list())
        test_hosts = set(test_df["IPV4_SRC_ADDR"].unique().to_list())
        assert len(train_hosts.intersection(test_hosts)) == 0

        # Check manifest fields
        assert manifest.seed == 42
        assert manifest.row_counts["total"] == len(df)
        assert len(manifest.train_record_digest) == 64

    def test_independent_source_holdout_isolation(self) -> None:
        clean_path = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        df = pl.read_parquet(clean_path)

        # Reserve NF-ToN-IoT-v2 entirely as holdout
        splitter = DatasetSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
        train_df, val_df, test_df, manifest = splitter.split_group_aware(
            df, holdout_sources=["NF-ToN-IoT-v2"]
        )

        # NF-ToN-IoT-v2 must NEVER appear in train_df or val_df
        assert "NF-ToN-IoT-v2" not in train_df["dataset_source"].unique().to_list()
        assert "NF-ToN-IoT-v2" not in val_df["dataset_source"].unique().to_list()

        # It must be present in test_df
        assert "NF-ToN-IoT-v2" in test_df["dataset_source"].unique().to_list()
        assert "NF-ToN-IoT-v2" in manifest.independent_holdout_sources

    def test_seed_determinism(self) -> None:
        clean_path = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        df = pl.read_parquet(clean_path)

        splitter_a = DatasetSplitter(seed=123)
        train_a, val_a, test_a, m_a = splitter_a.split_group_aware(df)

        splitter_b = DatasetSplitter(seed=123)
        train_b, val_b, test_b, m_b = splitter_b.split_group_aware(df)

        assert len(train_a) == len(train_b)
        assert len(val_a) == len(val_b)
        assert len(test_a) == len(test_b)
        assert m_a.train_record_digest == m_b.train_record_digest

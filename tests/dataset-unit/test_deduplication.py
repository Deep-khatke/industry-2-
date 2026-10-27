"""Unit tests for duplicate detection, exact dropping, and cross-source overlap."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.deduplication.deduplicator import DatasetDeduplicator


@pytest.mark.dataset_unit
class TestDeduplication:
    """Validate deduplication modes and cross-source duplicate overlap detection."""

    def test_exact_duplicate_removal(self) -> None:
        dup_fixture = Path("data/synthetic-fixtures/duplicate_test.parquet")
        df = pl.read_parquet(dup_fixture)

        # In duplicate_test, 100 rows were duplicated twice -> 200 duplicate rows
        assert len(df) == 1600

        dedup = DatasetDeduplicator()
        dedup_df, stats = dedup.deduplicate(df, mode="exact")

        assert stats["initial_count"] == 1600
        assert stats["retained_count"] == 1400
        assert stats["duplicates_removed"] == 200
        assert len(dedup_df) == 1400

    def test_cross_source_overlap_detection(self) -> None:
        # Create dataset where the same flow vector appears under two different sources
        df = pl.DataFrame({
            "IN_BYTES": [100, 100, 500],
            "OUT_BYTES": [50, 50, 200],
            "L4_SRC_PORT": [1024, 1024, 2048],
            "L4_DST_PORT": [80, 80, 443],
            "PROTOCOL": [6, 6, 6],
            "dataset_source": ["NF-UQ-NIDS-v2", "NF-UNSW-NB15-v2", "NF-UQ-NIDS-v2"],
            "Attack": ["DDoS", "DDoS", "Benign"],
            "Label": [1, 1, 0],
        })

        dedup = DatasetDeduplicator()
        overlap_res = dedup.analyze_cross_source_overlap(df, source_column="dataset_source")

        assert overlap_res["overlap_detected"] is True
        assert overlap_res["overlapping_feature_signatures"] == 1
        assert "Cross-source dataset overlap detected" in overlap_res["risk_warning"]

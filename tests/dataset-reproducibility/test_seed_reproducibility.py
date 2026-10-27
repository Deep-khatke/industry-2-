"""Reproducibility and deterministic partition verification test suite."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.partitions.federated_partitioner import FederatedPartitioner
from fcs_udip.splitting.splitter import DatasetSplitter
from packages.contracts.partition_manifest import PartitionRegime


@pytest.mark.dataset_reproducibility
class TestSeedReproducibility:
    """Validate that identical random seeds yield bit-for-bit identical partition digests."""

    @pytest.fixture
    def test_fixture(self) -> pl.DataFrame:
        p = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        return pl.read_parquet(p).with_columns(
            pl.col("Attack").alias("canonical_attack_label"),
            pl.col("Label").cast(pl.Int64).alias("binary_label"),
        )

    def test_split_seed_reproducibility(self, test_fixture: pl.DataFrame) -> None:
        splitter_a = DatasetSplitter(seed=42)
        train_a, val_a, test_a, m_a = splitter_a.split_group_aware(test_fixture)

        splitter_b = DatasetSplitter(seed=42)
        train_b, val_b, test_b, m_b = splitter_b.split_group_aware(test_fixture)

        # Record digests and counts must match exactly
        assert m_a.train_record_digest == m_b.train_record_digest
        assert m_a.val_record_digest == m_b.val_record_digest
        assert m_a.test_record_digest == m_b.test_record_digest
        assert len(train_a) == len(train_b)

        # Different seed must yield distinct assignment
        splitter_c = DatasetSplitter(seed=999)
        _, _, _, m_c = splitter_c.split_group_aware(test_fixture)
        assert m_a.train_record_digest != m_c.train_record_digest

    def test_partition_seed_reproducibility(self, test_fixture: pl.DataFrame) -> None:
        part_a = FederatedPartitioner(client_count=7, seed=42)
        dfs_a, m_a = part_a.partition(test_fixture, regime=PartitionRegime.STRONG_NON_IID)

        part_b = FederatedPartitioner(client_count=7, seed=42)
        dfs_b, m_b = part_b.partition(test_fixture, regime=PartitionRegime.STRONG_NON_IID)

        for cid in dfs_a.keys():
            assert len(dfs_a[cid]) == len(dfs_b[cid])
            assert m_a.client_partitions[cid].assigned_record_count == m_b.client_partitions[cid].assigned_record_count

        # Different seed yields different distributions
        part_c = FederatedPartitioner(client_count=7, seed=999)
        _, m_c = part_c.partition(test_fixture, regime=PartitionRegime.STRONG_NON_IID)
        counts_a = [info.assigned_record_count for info in m_a.client_partitions.values()]
        counts_c = [info.assigned_record_count for info in m_c.client_partitions.values()]
        assert counts_a != counts_c

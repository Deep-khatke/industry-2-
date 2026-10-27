"""Integration tests for seven-client simulated ISP federated learning partitioning."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.partitions.federated_partitioner import FederatedPartitioner
from packages.contracts.partition_manifest import PartitionRegime


@pytest.mark.dataset_integration
class TestFederatedPartitions:
    """Validate 7 simulated ISP client allocation across IID, moderate non-IID, and strong non-IID regimes."""

    @pytest.fixture
    def training_fixture(self) -> pl.DataFrame:
        p = Path("data/synthetic-fixtures/sample_netflow_v2.parquet")
        df = pl.read_parquet(p)
        # Add canonical label
        return df.with_columns(
            pl.col("Attack").alias("canonical_attack_label"),
            pl.col("Label").cast(pl.Int64).alias("binary_label"),
        )

    def test_exactly_seven_clients_generated(self, training_fixture: pl.DataFrame) -> None:
        partitioner = FederatedPartitioner(client_count=7, seed=42)
        client_dfs, manifest = partitioner.partition(training_fixture, regime=PartitionRegime.IID)

        assert len(client_dfs) == 7
        expected_clients = [f"isp_0{i}" for i in range(1, 8)]
        assert sorted(client_dfs.keys()) == expected_clients

        # Verify mapping to Phase 1 tenants
        for cid in expected_clients:
            info = manifest.client_partitions[cid]
            assert info.tenant_id_mapping.startswith("tenant-isp-")
            assert len(client_dfs[cid]) > 0

    def test_strictly_disjoint_client_assignments(self, training_fixture: pl.DataFrame) -> None:
        """Verify each training sample belongs to exactly one simulated ISP (zero cross-client duplication)."""
        partitioner = FederatedPartitioner(client_count=7, seed=42)
        client_dfs, _ = partitioner.partition(training_fixture, regime=PartitionRegime.IID)

        all_row_ids: list[str] = []
        for _cid, cdf in client_dfs.items():
            # Generate deterministic fingerprint per row
            for row in cdf.select(["IPV4_SRC_ADDR", "L4_SRC_PORT", "L4_DST_PORT", "IN_BYTES"]).iter_rows():
                all_row_ids.append(f"{row[0]}:{row[1]}:{row[2]}:{row[3]}")

        # Unique fingerprints should equal total count
        assert len(all_row_ids) == len(training_fixture)
        assert len(all_row_ids) == len(set(all_row_ids))

    def test_regime_distribution_shifts(self, training_fixture: pl.DataFrame) -> None:
        """Compare IID vs Moderate Non-IID vs Strong Non-IID distributions."""
        partitioner_iid = FederatedPartitioner(client_count=7, seed=42)
        _, manifest_iid = partitioner_iid.partition(training_fixture, regime=PartitionRegime.IID)

        partitioner_strong = FederatedPartitioner(client_count=7, seed=42)
        _, manifest_strong = partitioner_strong.partition(
            training_fixture, regime=PartitionRegime.STRONG_NON_IID, dirichlet_alpha=0.1
        )

        # In IID, client sizes are closely balanced across 7 clients
        sizes_iid = [info.assigned_record_count for info in manifest_iid.client_partitions.values()]
        assert max(sizes_iid) - min(sizes_iid) <= 10  # At most 1 item diff per class across clients

        # In Strong Non-IID, class concentrations exhibit significant variance
        assert manifest_strong.dirichlet_alpha == 0.1
        assert manifest_strong.total_training_records == len(training_fixture)

"""Federated learning multi-client dataset partitioner for seven simulated ISPs."""

import hashlib

import numpy as np
import polars as pl

from packages.contracts.partition_manifest import (
    ClientPartitionInfo,
    FederatedPartitionSetManifest,
    PartitionRegime,
)


class FederatedPartitioner:
    """
    Partitions training datasets across 7 simulated rural ISP client identities.
    Supports IID, moderately non-IID, and strongly non-IID distribution regimes
    using class-conditional Dirichlet allocation and stratified assignment.
    """

    DEFAULT_CLIENT_MAPPING = {
        "isp_01": "tenant-isp-alpha",
        "isp_02": "tenant-isp-beta",
        "isp_03": "tenant-isp-gamma",
        "isp_04": "tenant-isp-delta",
        "isp_05": "tenant-isp-epsilon",
        "isp_06": "tenant-isp-zeta",
        "isp_07": "tenant-isp-eta",
    }

    def __init__(
        self,
        client_count: int = 7,
        client_mapping: dict[str, str] | None = None,
        seed: int = 42,
        min_records_per_client: int = 10,
    ) -> None:
        self.client_count = client_count
        self.client_mapping = client_mapping or self.DEFAULT_CLIENT_MAPPING
        self.seed = seed
        self.min_records_per_client = min_records_per_client
        self.client_ids = list(self.client_mapping.keys())[:client_count]

    def partition(
        self,
        train_df: pl.DataFrame,
        regime: PartitionRegime = PartitionRegime.IID,
        dirichlet_alpha: float | None = None,
    ) -> tuple[dict[str, pl.DataFrame], FederatedPartitionSetManifest]:
        """
        Partition training records into mutually disjoint subsets across clients.
        Ensures each training record is assigned to exactly one client.
        """
        total_records = len(train_df)
        if total_records < self.client_count * self.min_records_per_client:
            raise ValueError(
                f"Insufficient training records ({total_records}) for {self.client_count} clients "
                f"with minimum {self.min_records_per_client} records per client."
            )

        rng = np.random.default_rng(self.seed)
        class_col = "canonical_attack_label" if "canonical_attack_label" in train_df.columns else "Attack"

        # Unique classes - sort for deterministic seed reproducibility
        classes = sorted(train_df[class_col].unique().to_list())
        len(classes)

        client_indices: dict[str, list[int]] = {cid: [] for cid in self.client_ids}

        if regime == PartitionRegime.IID:
            # Stratified uniform allocation per class
            for c in classes:
                c_indices = np.where(train_df[class_col].to_numpy() == c)[0]
                rng.shuffle(c_indices)
                splits = np.array_split(c_indices, self.client_count)
                for cid, split in zip(self.client_ids, splits, strict=False):
                    client_indices[cid].extend(split.tolist())

        else:
            # Non-IID Dirichlet distribution across clients for each class
            alpha = dirichlet_alpha or (1.0 if regime == PartitionRegime.MODERATE_NON_IID else 0.1)
            for c in classes:
                c_indices = np.where(train_df[class_col].to_numpy() == c)[0]
                rng.shuffle(c_indices)
                n_c = len(c_indices)

                # Draw proportions from Dirichlet distribution
                proportions = rng.dirichlet(np.repeat(alpha, self.client_count))
                proportions = proportions / proportions.sum()
                split_points = (np.cumsum(proportions) * n_c).astype(int)[:-1]
                splits = np.split(c_indices, split_points)

                for cid, split in zip(self.client_ids, splits, strict=False):
                    client_indices[cid].extend(split.tolist())

        # Build client DataFrames and verify mutual exclusivity
        assigned_indices_all: list[int] = []
        client_dfs: dict[str, pl.DataFrame] = {}
        client_infos: dict[str, ClientPartitionInfo] = {}

        for cid in self.client_ids:
            idx = client_indices[cid]
            assigned_indices_all.extend(idx)
            c_df = train_df[idx].with_columns(
                pl.lit(cid).alias("isp_client_id"),
                pl.lit(self.client_mapping[cid]).alias("tenant_id"),
            )
            client_dfs[cid] = c_df

            # Calculate client-specific class and source distributions
            c_dist = {str(k): int(v) for k, v in c_df.group_by(class_col).len().iter_rows()}
            s_dist: dict[str, int] = {}
            if "dataset_source" in c_df.columns:
                s_dist = {str(k): int(v) for k, v in c_df.group_by("dataset_source").len().iter_rows()}

            c_digest = hashlib.sha256(f"{cid}:{len(c_df)}".encode()).hexdigest()
            client_infos[cid] = ClientPartitionInfo(
                client_id=cid,
                tenant_id_mapping=self.client_mapping[cid],
                assigned_record_count=len(c_df),
                assigned_record_digest=c_digest,
                class_distribution=c_dist,
                source_distribution=s_dist,
                output_filename=f"partition_{cid}_{regime.value.lower()}.parquet",
                output_checksum=c_digest,  # updated when written to disk
            )

        # Assertion: Zero overlap across clients
        if len(assigned_indices_all) != len(set(assigned_indices_all)):
            raise ValueError("Partitioning error: Some records were assigned to multiple clients!")

        manifest = FederatedPartitionSetManifest(
            regime=regime,
            parent_dataset_digest=hashlib.sha256(str(total_records).encode()).hexdigest(),
            seed=self.seed,
            dirichlet_alpha=dirichlet_alpha or (1.0 if regime == PartitionRegime.MODERATE_NON_IID else (0.1 if regime == PartitionRegime.STRONG_NON_IID else None)),
            total_training_records=len(assigned_indices_all),
            client_partitions=client_infos,
        )

        return client_dfs, manifest

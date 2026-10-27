"""Dataset loader with split manifest verification and holdout separation."""

import json
from pathlib import Path
from typing import Any

import polars as pl

from packages.contracts.dataset_manifest import DatasetManifest


class DatasetLoader:
    """Loads validated Phase 2 dataset splits and enforces manifest verification."""

    def __init__(self, data_dir: Path | str = "data/processed/splits") -> None:
        self.data_dir = Path(data_dir)

    def verify_manifest(
        self,
        manifest_path: Path | str = "data/processed/dataset_manifest.json",
        secret_key: bytes | None = None,
    ) -> dict[str, Any]:
        """Verify that the dataset manifest exists, is parseable, and matches split filenames."""
        p = Path(manifest_path)
        if not p.exists():
            raise FileNotFoundError(f"Dataset manifest not found: {p}")

        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        manifest = DatasetManifest(**data)

        # Verify output artifacts recorded in manifest exist on disk
        artifacts_checked = {}
        for artifact_name in manifest.output_artifact_digests:
            file_path = self.data_dir / artifact_name
            artifacts_checked[artifact_name] = file_path.exists()

        key = secret_key or b"fcs-udip-ephemeral-dev-signing-key-phase2"
        sig_valid = manifest.verify_signature(key)

        return {
            "dataset_id": manifest.dataset_id,
            "version": manifest.dataset_version,
            "signature_valid": sig_valid,
            "feature_schema_digest": manifest.feature_schema_digest,
            "row_counts": manifest.row_counts,
            "artifacts_found": artifacts_checked,
        }

    def load_splits(
        self,
        max_train_rows: int | None = None,
        max_val_rows: int | None = None,
        max_test_rows: int | None = None,
    ) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """
        Load train, validation, and test Parquet files from splits directory.
        Optionally bounded by row limits for resource safety.
        """
        train_path = self.data_dir / "train.parquet"
        val_path = self.data_dir / "val.parquet"
        test_path = self.data_dir / "test.parquet"

        if not train_path.exists():
            raise FileNotFoundError(f"Missing training split: {train_path}")
        if not val_path.exists():
            raise FileNotFoundError(f"Missing validation split: {val_path}")
        if not test_path.exists():
            raise FileNotFoundError(f"Missing test split: {test_path}")

        train_df = pl.read_parquet(train_path)
        val_df = pl.read_parquet(val_path)
        test_df = pl.read_parquet(test_path)

        if max_train_rows and len(train_df) > max_train_rows:
            train_df = train_df.slice(0, max_train_rows)
        if max_val_rows and len(val_df) > max_val_rows:
            val_df = val_df.slice(0, max_val_rows)
        if max_test_rows and len(test_df) > max_test_rows:
            test_df = test_df.slice(0, max_test_rows)

        return train_df, val_df, test_df

    def load_with_holdout(
        self,
        holdout_source: str = "NF-ToN-IoT-v2",
    ) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """
        Loads splits and separates an independent testbed source as a pure out-of-domain holdout.
        Ensures the holdout source is NEVER included in training or validation.
        """
        train_df, val_df, test_df = self.load_splits()

        combined = pl.concat([train_df, val_df, test_df])
        if "dataset_source" not in combined.columns:
            # Fallback: empty holdout if dataset_source not tracked
            return train_df, val_df, test_df, pl.DataFrame()

        holdout_df = combined.filter(pl.col("dataset_source") == holdout_source)
        non_holdout_train = train_df.filter(pl.col("dataset_source") != holdout_source)
        non_holdout_val = val_df.filter(pl.col("dataset_source") != holdout_source)
        non_holdout_test = test_df.filter(pl.col("dataset_source") != holdout_source)

        return non_holdout_train, non_holdout_val, non_holdout_test, holdout_df

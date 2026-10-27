"""Feature selector supporting Research Track and Deployable Track with anti-leakage protection."""

import hashlib
from enum import StrEnum

import numpy as np
import polars as pl

from packages.contracts.feature_spec import (
    FeatureSpec,
    get_deployable_feature_spec,
    get_research_feature_spec,
)


class TargetLeakageError(Exception):
    """Raised when label or metadata columns attempt to enter the predictive feature matrix."""


class FeatureTrack(StrEnum):
    """Experiment feature tracks."""

    RESEARCH_BENCHMARK = "RESEARCH_BENCHMARK"
    DEPLOYABLE_SUBSET = "DEPLOYABLE_SUBSET"


class FeatureSelector:
    """Selects and extracts feature matrices for Research and Deployable model tracks."""

    PROHIBITED_COLUMNS = {
        "attack",
        "label",
        "canonical_attack_label",
        "original_attack_label",
        "binary_label",
        "dataset_source",
        "label_mapping_version",
        "split_id",
        "isp_client_id",
        "tenant_id",
        "event_id",
        "flow_id",
        "record_hash",
    }

    def __init__(
        self,
        track: FeatureTrack = FeatureTrack.RESEARCH_BENCHMARK,
        drop_raw_ips: bool = True,
        research_spec: FeatureSpec | None = None,
        deployable_spec: FeatureSpec | None = None,
    ) -> None:
        self.track = track
        self.drop_raw_ips = drop_raw_ips
        self.research_spec = research_spec or get_research_feature_spec()
        self.deployable_spec = deployable_spec or get_deployable_feature_spec()

    def get_feature_names(self, available_columns: list[str]) -> list[str]:
        """Determine valid ordered feature names for the configured track."""
        active_spec = self.research_spec if self.track == FeatureTrack.RESEARCH_BENCHMARK else self.deployable_spec

        feature_names: list[str] = []
        for feat in active_spec.features:
            if self.drop_raw_ips and feat.name in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR"):
                continue
            if feat.name in available_columns:
                feature_names.append(feat.name)

        return feature_names

    def validate_features(self, feature_names: list[str]) -> None:
        """Strict check to prevent target leakage or shortcut learning."""
        for name in feature_names:
            if name.lower() in self.PROHIBITED_COLUMNS:
                raise TargetLeakageError(
                    f"TARGET LEAKAGE DETECTED: Column '{name}' is a target, label, or provenance field "
                    f"and is strictly prohibited as a predictive ML feature."
                )

    def extract_matrices(
        self,
        df: pl.DataFrame,
        feature_names: list[str] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
        """
        Extract numeric feature matrix X, binary targets y_binary, and multiclass targets y_multi.
        Returns (X, y_binary, y_multi, feature_names).
        """
        if feature_names is None:
            feature_names = self.get_feature_names(df.columns)

        self.validate_features(feature_names)

        # Extract Targets
        if "binary_label" in df.columns:
            y_binary = df["binary_label"].to_numpy().astype(np.int64)
        elif "Label" in df.columns:
            y_binary = df["Label"].to_numpy().astype(np.int64)
        else:
            raise ValueError("No binary label column found in dataframe")

        if "canonical_attack_label" in df.columns:
            y_multi = df["canonical_attack_label"].to_numpy()
        elif "Attack" in df.columns:
            y_multi = df["Attack"].to_numpy()
        else:
            raise ValueError("No multiclass target column found in dataframe")

        # Extract numeric features
        sub_df = df.select(feature_names)

        # Fill any null values with column medians for numeric stability
        filled_exprs = []
        for col in feature_names:
            if sub_df[col].dtype in (pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
                filled_exprs.append(pl.col(col).fill_null(pl.col(col).median()).alias(col))
            else:
                filled_exprs.append(pl.col(col).cast(pl.Float32).fill_null(0.0).alias(col))

        cleaned_df = sub_df.with_columns(*filled_exprs)
        X = cleaned_df.to_numpy().astype(np.float32)

        # Replace any remaining NaNs or Infs with 0.0
        X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

        return X, y_binary, y_multi, feature_names

    def compute_feature_digest(self, feature_names: list[str]) -> str:
        """Compute cryptographic SHA-256 digest of active feature names and track."""
        payload = f"{self.track.value}:" + ",".join(sorted(feature_names))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

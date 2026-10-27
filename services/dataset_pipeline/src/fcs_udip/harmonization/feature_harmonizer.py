"""Feature harmonization, case normalization, and privacy subnet masking."""

import ipaddress
from typing import overload

import polars as pl

from packages.contracts.feature_spec import (
    FeatureSpec,
    get_deployable_feature_spec,
    get_research_feature_spec,
)

from .label_normalizer import TargetLeakageError


def mask_ip_to_prefix_24(ip_val: str | None) -> str:
    """Mask IPv4 string to privacy-preserving /24 network prefix, matching Phase 1 normalizer."""
    if not ip_val:
        return "0.0.0.0/24"
    try:
        ip_obj = ipaddress.ip_address(str(ip_val).strip())
        if ip_obj.version == 4:
            net = ipaddress.IPv4Network(f"{ip_val}/24", strict=False)
            return str(net)
        return str(ip_val)
    except ValueError:
        # Fallback string truncation for dotted quads
        parts = str(ip_val).strip().split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        return "0.0.0.0/24"


class FeatureHarmonizer:
    """Harmonizes raw telemetry dataset columns into canonical research and deployable specifications."""

    def __init__(
        self,
        research_spec: FeatureSpec | None = None,
        deployable_spec: FeatureSpec | None = None,
    ) -> None:
        self.research_spec = research_spec or get_research_feature_spec()
        self.deployable_spec = deployable_spec or get_deployable_feature_spec()

    @overload
    def standardize_column_names(self, df: pl.DataFrame) -> pl.DataFrame:
        ...

    @overload
    def standardize_column_names(self, df: pl.LazyFrame) -> pl.LazyFrame:
        ...

    def standardize_column_names(self, df: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame | pl.LazyFrame:
        """Ensure all canonical NetFlow features use uppercase canonical spelling."""
        current_cols = df.collect_schema().names() if isinstance(df, pl.LazyFrame) else df.columns
        rename_map: dict[str, str] = {}
        canonical_map = {name.upper(): name for name in self.research_spec.feature_names()}

        for col in current_cols:
            upper_col = col.strip().upper()
            if upper_col in canonical_map and col != canonical_map[upper_col]:
                rename_map[col] = canonical_map[upper_col]

        if rename_map:
            return df.rename(rename_map)
        return df

    @overload
    def apply_privacy_subnet_masking(self, df: pl.DataFrame) -> pl.DataFrame:
        ...

    @overload
    def apply_privacy_subnet_masking(self, df: pl.LazyFrame) -> pl.LazyFrame:
        ...

    def apply_privacy_subnet_masking(
        self,
        df: pl.DataFrame | pl.LazyFrame,
    ) -> pl.DataFrame | pl.LazyFrame:
        """Derive masked /24 subnet prefixes from raw IP addresses for privacy preservation."""
        schema_names = df.collect_schema().names() if isinstance(df, pl.LazyFrame) else df.columns

        cols_to_add: list[pl.Expr] = []
        if "IPV4_SRC_ADDR" in schema_names:
            cols_to_add.append(
                pl.col("IPV4_SRC_ADDR")
                .map_elements(mask_ip_to_prefix_24, return_dtype=pl.String)
                .alias("SRC_PREFIX_MASKED")
            )
        if "IPV4_DST_ADDR" in schema_names:
            cols_to_add.append(
                pl.col("IPV4_DST_ADDR")
                .map_elements(mask_ip_to_prefix_24, return_dtype=pl.String)
                .alias("DST_PREFIX_MASKED")
            )

        if cols_to_add:
            return df.with_columns(*cols_to_add)
        return df

    def get_research_feature_matrix(
        self,
        df: pl.DataFrame,
        drop_raw_ips: bool = True,
    ) -> tuple[pl.DataFrame, pl.Series, pl.Series]:
        """
        Extract clean research feature matrix X, binary targets y_binary, and multiclass targets y_multi.
        Prevents target leakage by validating X columns.
        """
        target_cols = {"Label", "label", "Attack", "attack", "canonical_attack_label", "original_attack_label", "binary_label"}
        metadata_cols = {"dataset_source", "label_mapping_version", "split_id", "isp_client_id", "tenant_id", "event_id"}

        # Extract targets
        if "binary_label" in df.columns:
            y_binary = df["binary_label"]
        elif "Label" in df.columns:
            y_binary = df["Label"].cast(pl.Int64)
        else:
            raise ValueError("No binary target column found in dataframe")

        if "canonical_attack_label" in df.columns:
            y_multi = df["canonical_attack_label"]
        elif "Attack" in df.columns:
            y_multi = df["Attack"].cast(pl.String)
        else:
            raise ValueError("No multiclass target column found in dataframe")

        # Select valid feature columns
        feature_cols: list[str] = []
        for feat in self.research_spec.features:
            if drop_raw_ips and feat.name in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR"):
                continue
            if feat.name in df.columns:
                feature_cols.append(feat.name)

        # Strict target leakage check
        for col in feature_cols:
            if col in target_cols or col in metadata_cols:
                raise TargetLeakageError(f"Target column '{col}' cannot be included in feature matrix X")

        X = df.select(feature_cols)
        return X, y_binary, y_multi

    def get_deployable_feature_matrix(
        self,
        df: pl.DataFrame,
    ) -> tuple[pl.DataFrame, pl.Series, pl.Series]:
        """
        Extract deployable feature matrix matching Phase 1 FlowEvent v1 capabilities.
        Excludes unavailable DPI / application payload fields.
        """
        deployable_names = [
            f.name
            for f in self.deployable_spec.features
            if f.name not in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR") and f.name in df.columns
        ]
        y_binary = df["binary_label"] if "binary_label" in df.columns else df["Label"].cast(pl.Int64)
        y_multi = df["canonical_attack_label"] if "canonical_attack_label" in df.columns else df["Attack"].cast(pl.String)

        X = df.select(deployable_names)
        return X, y_binary, y_multi

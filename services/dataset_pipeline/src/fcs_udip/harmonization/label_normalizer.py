"""Attack label taxonomy normalization and target leakage prevention."""

from pathlib import Path
from typing import overload

import polars as pl
import yaml


class TargetLeakageError(Exception):
    """Raised when target labels or metadata columns leak into predictive feature matrices."""


class LabelNormalizer:
    """Normalizes heterogeneous dataset labels into a unified canonical attack taxonomy."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.canonical_classes: list[str] = []
        self.source_mappings: dict[str, dict[str, str]] = {}
        self.prohibited_predictors: set[str] = set()
        self.mapping_version = "1.2.0"

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: Path | str) -> None:
        """Load taxonomy rules and prohibited predictor column lists from YAML."""
        p = Path(config_path)
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.mapping_version = str(data.get("version", "1.2.0"))
        self.canonical_classes = data.get("canonical_classes", [])
        self.source_mappings = data.get("source_mappings", {})
        self.prohibited_predictors = {
            col.lower() for col in data.get("prohibited_predictor_columns", [])
        }

    def normalize_label(self, attack_str: str, source_id: str) -> str:
        """Map a single source attack string to canonical taxonomy class."""
        if not attack_str:
            return "Unknown"
        attack_clean = str(attack_str).strip()
        source_map = self.source_mappings.get(source_id, {})

        # Direct match in source-specific dictionary
        if attack_clean in source_map:
            return source_map[attack_clean]

        # Case-insensitive match in source-specific dictionary
        lower_map = {k.lower(): v for k, v in source_map.items()}
        if attack_clean.lower() in lower_map:
            return lower_map[attack_clean.lower()]

        # Fallback check against canonical classes directly
        for canon in self.canonical_classes:
            if attack_clean.lower() == canon.lower():
                return canon

        return "Unknown"

    @overload
    def apply_normalization(self, df: pl.DataFrame, source_id: str) -> pl.DataFrame:
        ...

    @overload
    def apply_normalization(self, df: pl.LazyFrame, source_id: str) -> pl.LazyFrame:
        ...

    def apply_normalization(
        self,
        df: pl.DataFrame | pl.LazyFrame,
        source_id: str,
    ) -> pl.DataFrame | pl.LazyFrame:
        """
        Add standardized target and metadata fields:
        - original_attack_label
        - canonical_attack_label
        - binary_label
        - dataset_source
        - label_mapping_version
        """
        # Determine raw attack column name
        schema_names = df.collect_schema().names() if isinstance(df, pl.LazyFrame) else df.columns
        attack_col = "Attack" if "Attack" in schema_names else ("attack" if "attack" in schema_names else None)
        label_col = "Label" if "Label" in schema_names else ("label" if "label" in schema_names else None)

        if not attack_col and not label_col:
            raise ValueError(f"No attack or label column detected in dataset from source '{source_id}'")

        # Build mapping expressions
        # If attack column is present, map each row
        # Build comprehensive mapping dict:
        # 1. Canonical classes self-map
        mapping_dict = {c: c for c in self.canonical_classes}
        mapping_dict.update({c.lower(): c for c in self.canonical_classes})
        # 2. Universal fallback from all source mappings
        for s_map in self.source_mappings.values():
            mapping_dict.update(s_map)
        # 3. Source-specific mapping takes precedence
        source_map = self.source_mappings.get(source_id, {})
        mapping_dict.update(source_map)

        if attack_col:
            expr_original = pl.col(attack_col).cast(pl.String).alias("original_attack_label")
            # Polars replace_strict for canonical attack label
            expr_canonical = (
                pl.col(attack_col)
                .cast(pl.String)
                .replace_strict(mapping_dict, default="Unknown")
                .alias("canonical_attack_label")
            )
        else:
            # Only binary label present
            assert label_col is not None
            expr_original = (
                pl.when(pl.col(label_col) == 0)
                .then(pl.lit("Benign"))
                .otherwise(pl.lit("Attack_Unspecified"))
                .alias("original_attack_label")
            )
            expr_canonical = (
                pl.when(pl.col(label_col) == 0)
                .then(pl.lit("Benign"))
                .otherwise(pl.lit("Unknown"))
                .alias("canonical_attack_label")
            )

        # Binary label: 0 for Benign, 1 for Attack
        expr_binary = (
            pl.when(expr_canonical == pl.lit("Benign"))
            .then(pl.lit(0))
            .otherwise(pl.lit(1))
            .cast(pl.Int64)
            .alias("binary_label")
        )

        expr_source = pl.lit(source_id).alias("dataset_source")
        expr_version = pl.lit(self.mapping_version).alias("label_mapping_version")

        return df.with_columns(
            expr_original,
            expr_canonical,
            expr_binary,
            expr_source,
            expr_version,
        )

    def validate_predictor_features(self, candidate_features: list[str]) -> None:
        """
        Strict security check preventing target leakage.
        Ensures NO label or provenance metadata columns can enter the predictive ML feature set.
        """
        for feature in candidate_features:
            if feature.lower() in self.prohibited_predictors:
                raise TargetLeakageError(
                    f"TARGET LEAKAGE DETECTED: Column '{feature}' is a label, target, or provenance identifier. "
                    f"It is strictly forbidden in predictive feature matrices."
                )

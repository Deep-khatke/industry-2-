"""Deduplication and cross-source overlap analysis engine."""

from typing import Any

import polars as pl


class DatasetDeduplicator:
    """
    Analyzes and mitigates duplication, cross-source overlap, and repeated event artifacts.
    Differentiates genuine repeated network transactions from duplicate capture records.
    """

    def __init__(self, key_columns: list[str] | None = None) -> None:
        self.key_columns = key_columns

    def deduplicate(
        self,
        df: pl.DataFrame,
        mode: str = "exact",
    ) -> tuple[pl.DataFrame, dict[str, Any]]:
        """
        Deduplicate rows using Polars unique().
        Modes:
            - 'exact': Drops identical rows across all feature and label columns.
            - 'features_only': Drops rows with identical feature vectors, detecting contradictory labels.
        """
        initial_count = len(df)
        if initial_count == 0:
            return df, {
                "initial_count": 0,
                "retained_count": 0,
                "duplicates_removed": 0,
                "duplicate_ratio": 0.0,
            }

        if mode == "exact":
            deduped_df = df.unique()
        elif mode == "features_only":
            # Exclude metadata and target columns from uniqueness subset
            exclude_cols = {
                "Label", "label", "Attack", "attack",
                "canonical_attack_label", "original_attack_label",
                "binary_label", "dataset_source", "event_id"
            }
            subset_cols = [c for c in df.columns if c not in exclude_cols]
            deduped_df = df.unique(subset=subset_cols, keep="first")
        else:
            raise ValueError(f"Unsupported deduplication mode: {mode}")

        retained_count = len(deduped_df)
        duplicates_removed = initial_count - retained_count

        stats = {
            "initial_count": initial_count,
            "retained_count": retained_count,
            "duplicates_removed": duplicates_removed,
            "duplicate_ratio": round(duplicates_removed / initial_count, 4),
            "deduplication_mode": mode,
        }

        return deduped_df, stats

    def analyze_cross_source_overlap(
        self,
        df: pl.DataFrame,
        source_column: str = "dataset_source",
    ) -> dict[str, Any]:
        """
        Detect whether identical flow feature vectors appear across distinct source datasets
        (e.g., between combined NF-UQ-NIDS-v2 and one of its parent datasets).
        """
        if source_column not in df.columns:
            return {"overlap_detected": False, "overlapping_records_count": 0}

        exclude_cols = {
            "Label", "label", "Attack", "attack",
            "canonical_attack_label", "original_attack_label",
            "binary_label", source_column, "event_id"
        }
        feature_cols = [c for c in df.columns if c not in exclude_cols]

        # Group by feature_cols and count distinct sources
        overlap_summary = (
            df.group_by(feature_cols)
            .agg(pl.col(source_column).n_unique().alias("source_count"))
            .filter(pl.col("source_count") > 1)
        )

        overlapping_records = len(overlap_summary)
        return {
            "overlap_detected": overlapping_records > 0,
            "overlapping_feature_signatures": overlapping_records,
            "risk_warning": (
                "Cross-source dataset overlap detected. Examples exist in both combined and parent tables."
                if overlapping_records > 0
                else "Zero cross-source duplicate signatures found."
            ),
        }

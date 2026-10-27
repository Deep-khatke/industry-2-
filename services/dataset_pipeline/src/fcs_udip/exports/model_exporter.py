"""Model-specific dataset generation for General IDS, Specialists, and Anomaly Detectors."""

from pathlib import Path

import polars as pl


class ModelDatasetExporter:
    """
    Produces specialized training and evaluation dataset views tailored to specific downstream ML models:
    - General Binary IDS
    - Multiclass Threat Classifier
    - DDoS Specialist (strictly distinct from generic DoS)
    - Scanning & Reconnaissance Specialist
    - Botnet Specialist (with network metadata caveats)
    - Benign Anomaly Detector (strictly benign training view, mixed evaluation view)
    """

    def __init__(self, output_dir: Path | str = "data/processed/models") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_general_ids(
        self,
        df: pl.DataFrame,
        split_name: str = "train",
    ) -> pl.DataFrame:
        """Export binary classification dataset (Benign = 0, Attack = 1)."""
        if "binary_label" not in df.columns:
            raise ValueError("binary_label column missing from input dataframe")
        return df

    def export_multiclass(
        self,
        df: pl.DataFrame,
        split_name: str = "train",
    ) -> pl.DataFrame:
        """Export multiclass dataset with standardized canonical attack taxonomy."""
        if "canonical_attack_label" not in df.columns:
            raise ValueError("canonical_attack_label column missing from input dataframe")
        return df

    def export_ddos_specialist(
        self,
        df: pl.DataFrame,
        split_name: str = "train",
        negative_ratio: float = 1.0,
    ) -> pl.DataFrame:
        """
        Export DDoS specialist dataset.
        Includes verified DDoS attacks vs non-DDoS negatives.
        Strictly distinguishes DDoS from host-targeted DoS.
        """
        label_col = "canonical_attack_label"
        ddos_df = df.filter(pl.col(label_col) == "DDoS").with_columns(
            pl.lit(1).alias("specialist_target")
        )
        non_ddos_df = df.filter(pl.col(label_col) != "DDoS").with_columns(
            pl.lit(0).alias("specialist_target")
        )

        n_ddos = len(ddos_df)
        if n_ddos == 0:
            return df.with_columns(pl.lit(0).alias("specialist_target"))

        n_neg = min(len(non_ddos_df), int(n_ddos * negative_ratio))
        neg_sample = non_ddos_df.sample(n=n_neg, seed=42) if n_neg < len(non_ddos_df) else non_ddos_df

        combined = pl.concat([ddos_df, neg_sample], how="vertical_relaxed").sample(fraction=1.0, shuffle=True, seed=42)
        return combined

    def export_scanning_specialist(
        self,
        df: pl.DataFrame,
        split_name: str = "train",
        negative_ratio: float = 1.0,
    ) -> pl.DataFrame:
        """Export scanning and reconnaissance specialist dataset."""
        label_col = "canonical_attack_label"
        scan_df = df.filter(pl.col(label_col).is_in(["Scanning", "Reconnaissance"])).with_columns(
            pl.lit(1).alias("specialist_target")
        )
        neg_df = df.filter(~pl.col(label_col).is_in(["Scanning", "Reconnaissance"])).with_columns(
            pl.lit(0).alias("specialist_target")
        )

        n_pos = len(scan_df)
        if n_pos == 0:
            return df.with_columns(pl.lit(0).alias("specialist_target"))

        n_neg = min(len(neg_df), int(n_pos * negative_ratio))
        neg_sample = neg_df.sample(n=n_neg, seed=42) if n_neg < len(neg_df) else neg_df

        combined = pl.concat([scan_df, neg_sample], how="vertical_relaxed").sample(fraction=1.0, shuffle=True, seed=42)
        return combined

    def export_botnet_specialist(
        self,
        df: pl.DataFrame,
        split_name: str = "train",
    ) -> pl.DataFrame:
        """
        Export botnet specialist dataset.
        Records documented limitation: reflects network flow communication patterns, not binary malware execution.
        """
        label_col = "canonical_attack_label"
        botnet_df = df.filter(pl.col(label_col) == "Botnet").with_columns(
            pl.lit(1).alias("specialist_target")
        )
        other_df = df.filter(pl.col(label_col) != "Botnet").with_columns(
            pl.lit(0).alias("specialist_target")
        )

        n_pos = len(botnet_df)
        if n_pos == 0:
            return df.with_columns(pl.lit(0).alias("specialist_target"))

        n_neg = min(len(other_df), n_pos * 2)
        neg_sample = other_df.sample(n=n_neg, seed=42) if n_neg < len(other_df) else other_df

        return pl.concat([botnet_df, neg_sample], how="vertical_relaxed").sample(fraction=1.0, shuffle=True, seed=42)

    def export_anomaly_detector_views(
        self,
        train_df: pl.DataFrame,
        test_df: pl.DataFrame,
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """
        Export views for unsupervised / one-class anomaly detection:
        - anomaly_train: STRICTLY benign network traffic (binary_label == 0).
        - anomaly_test: UNTOUCHED mixed evaluation traffic (benign + all attack categories).
        Ensures zero attack examples contaminate anomaly baseline fitting.
        """
        benign_train = train_df.filter(pl.col("binary_label") == 0)
        return benign_train, test_df

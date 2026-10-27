"""Data quality validation, anomaly quarantine, and audit metrics."""

from pathlib import Path
from typing import Any

import polars as pl
import yaml


class DataQualityValidator:
    """
    Executes automated quality checks across dataset batches.
    Segregates corrupted, out-of-bounds, or inconsistent telemetry rows into quarantine tables
    while preserving clean, reproducible records for ML pipelines.
    """

    def __init__(self, rules_config_path: Path | str | None = None) -> None:
        self.rules: list[dict[str, Any]] = []
        if rules_config_path:
            self.load_rules(rules_config_path)

    def load_rules(self, config_path: Path | str) -> None:
        """Load quality rules from YAML configuration."""
        p = Path(config_path)
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.rules = data.get("policies", [])

    def validate_and_clean(
        self,
        df: pl.DataFrame,
    ) -> tuple[pl.DataFrame, pl.DataFrame, dict[str, Any]]:
        """
        Validate dataset records against quality rules.
        Returns:
            - clean_df: Clean rows adhering to valid bounds
            - quarantine_df: Isolated invalid rows with quarantine_reason attached
            - metrics: Summary statistics of accepted, quarantined, and normalized counts
        """
        initial_row_count = len(df)
        if initial_row_count == 0:
            return df, pl.DataFrame(), {
                "initial_row_count": 0,
                "clean_row_count": 0,
                "quarantine_row_count": 0,
                "rule_violations": {},
            }

        # Build filter expressions for quarantine
        quarantine_reasons: list[tuple[pl.Expr, str]] = []

        # 1. Negative packet, byte, and duration counts
        for col in ["IN_BYTES", "OUT_BYTES", "IN_PKTS", "OUT_PKTS", "FLOW_DURATION_MILLISECONDS"]:
            if col in df.columns:
                quarantine_reasons.append(
                    (pl.col(col) < 0, f"Negative value in count/duration column: {col}")
                )

        # 2. Port number range check [0, 65535]
        for port_col in ["L4_SRC_PORT", "L4_DST_PORT"]:
            if port_col in df.columns:
                quarantine_reasons.append(
                    ((pl.col(port_col) < 0) | (pl.col(port_col) > 65535), f"Port out of range [0, 65535]: {port_col}")
                )

        # 3. Protocol byte range [0, 255]
        if "PROTOCOL" in df.columns:
            quarantine_reasons.append(
                ((pl.col("PROTOCOL") < 0) | (pl.col("PROTOCOL") > 255), "Protocol ID out of range [0, 255]")
            )

        # 4. Mandatory non-null / non-empty label check
        if "Attack" in df.columns:
            quarantine_reasons.append(
                (pl.col("Attack").is_null() | (pl.col("Attack").cast(pl.String).str.strip_chars() == ""), "Missing or empty attack label")
            )
        if "Label" in df.columns:
            quarantine_reasons.append(
                (~pl.col("Label").is_in([0, 1]), "Binary label not in (0, 1)")
            )

        # 5. NaN / Infinite values in core numeric fields
        critical_fields = ["IN_BYTES", "IN_PKTS", "PROTOCOL", "FLOW_DURATION_MILLISECONDS"]
        for cfield in critical_fields:
            if cfield in df.columns:
                quarantine_reasons.append(
                    (pl.col(cfield).is_null() | pl.col(cfield).is_nan() | pl.col(cfield).is_infinite(), f"Null/NaN/Inf in critical column: {cfield}")
                )

        # Combine all quarantine conditions
        combined_quarantine_expr = pl.lit(False)
        violation_counts: dict[str, int] = {}

        # Build chained reason string expression
        reason_expr = pl.lit("")
        for expr, reason in quarantine_reasons:
            flag_col = df.select(expr.alias("flag"))["flag"]
            v_count = int(flag_col.sum()) if flag_col.dtype == pl.Boolean else 0
            if v_count > 0:
                violation_counts[reason] = v_count
                combined_quarantine_expr = combined_quarantine_expr | expr
                reason_expr = (
                    pl.when(expr)
                    .then(
                        pl.when(reason_expr == pl.lit(""))
                        .then(pl.lit(reason))
                        .otherwise(reason_expr + pl.lit("; ") + pl.lit(reason))
                    )
                    .otherwise(reason_expr)
                )

        # Split into clean and quarantine
        quarantine_df = df.filter(combined_quarantine_expr).with_columns(
            reason_expr.alias("quarantine_reason")
        )
        clean_df = df.filter(~combined_quarantine_expr)

        # Post-clean normalization: impute minor non-critical NaN values with 0
        numeric_cols = [
            col
            for col, dtype in clean_df.schema.items()
            if dtype in (pl.Float32, pl.Float64, pl.Int32, pl.Int64)
        ]
        if numeric_cols:
            clean_df = clean_df.with_columns(
                [pl.col(c).fill_nan(0).fill_null(0) for c in numeric_cols]
            )

        clean_row_count = len(clean_df)
        quarantine_row_count = len(quarantine_df)

        metrics = {
            "initial_row_count": initial_row_count,
            "clean_row_count": clean_row_count,
            "quarantine_row_count": quarantine_row_count,
            "clean_ratio": round(clean_row_count / max(1, initial_row_count), 4),
            "rule_violations": violation_counts,
        }

        return clean_df, quarantine_df, metrics

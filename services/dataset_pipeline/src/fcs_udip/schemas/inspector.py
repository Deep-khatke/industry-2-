"""Schema discovery, feature presence verification, and version isolation."""

from pathlib import Path
from typing import Any

import polars as pl

from packages.contracts.feature_spec import get_research_feature_spec


class IncompatibleSchemaError(Exception):
    """Raised when an inspected dataset schema violates canonical requirements."""


class SchemaInspector:
    """Inspects dataset schemas using Polars lazy scanning to maintain bounded memory."""

    def __init__(self) -> None:
        self.canonical_spec = get_research_feature_spec()
        self.canonical_feature_names = set(self.canonical_spec.feature_names())

    def inspect_file(self, file_path: Path | str) -> dict[str, Any]:
        """
        Inspect the schema of a parquet or CSV dataset file without loading rows into RAM.
        Returns detailed feature matching, missing fields, and version classification.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Dataset file not found: {p}")

        if p.suffix in (".parquet", ".pq"):
            lf = pl.scan_parquet(str(p))
        elif p.suffix in (".csv", ".gz"):
            lf = pl.scan_csv(str(p))
        else:
            raise ValueError(f"Unsupported dataset format: {p.suffix}")

        schema = lf.collect_schema()
        column_names = schema.names()
        column_types = {name: str(dtype) for name, dtype in schema.items()}

        col_set = set(column_names)
        matched_features = sorted(col_set.intersection(self.canonical_feature_names))
        missing_canonical = sorted(self.canonical_feature_names - col_set)
        extra_columns = sorted(col_set - self.canonical_feature_names)

        # Check for NetFlow v3 indicator (53 features, or known v3 specific fields)
        v3_indicators = {"SRC_FRAGMENTS", "DST_FRAGMENTS", "SRC_TO_DST_IAT_MIN", "DST_TO_SRC_IAT_MIN"}
        is_netflow_v3 = bool(v3_indicators.intersection(col_set)) or len(column_names) >= 53

        # Check for CIC-DDoS2019 indicator (80 features)
        is_cic_ddos = len(column_names) >= 70 and ("Flow Duration" in col_set or " Flow Duration" in col_set)

        classification = "NETFLOW_V2_43"
        if is_netflow_v3:
            classification = "NETFLOW_V3_53_SEPARATE"
        elif is_cic_ddos:
            classification = "CIC_DDOS_2019_SEPARATE"
        elif len(matched_features) < 10:
            classification = "UNKNOWN_NON_STANDARD"

        has_binary_label = "Label" in col_set or "label" in col_set
        has_attack_label = "Attack" in col_set or "attack" in col_set

        return {
            "file_path": str(p),
            "file_size_bytes": p.stat().st_size,
            "total_columns": len(column_names),
            "columns": column_names,
            "column_types": column_types,
            "canonical_features_matched_count": len(matched_features),
            "matched_canonical_features": matched_features,
            "missing_canonical_features": missing_canonical,
            "extra_columns": extra_columns,
            "has_binary_label": has_binary_label,
            "has_attack_label": has_attack_label,
            "detected_classification": classification,
            "is_netflow_v2_compatible": classification == "NETFLOW_V2_43" and len(missing_canonical) == 0,
        }

    def validate_netflow_v2_compatibility(self, file_path: Path | str) -> dict[str, Any]:
        """
        Strict validation assertion ensuring the dataset adheres to 43-feature NetFlow v2 schema.
        Raises IncompatibleSchemaError if 53-feature NetFlow v3 is accidentally presented.
        """
        inspection = self.inspect_file(file_path)
        if inspection["detected_classification"] == "NETFLOW_V3_53_SEPARATE":
            raise IncompatibleSchemaError(
                f"File '{file_path}' detected as NetFlow v3 (53 features). "
                f"NetFlow v3 must remain separately versioned and cannot be merged into NetFlow v2 tables."
            )
        if inspection["detected_classification"] == "CIC_DDOS_2019_SEPARATE":
            raise IncompatibleSchemaError(
                f"File '{file_path}' detected as CIC-DDoS2019. "
                f"Cannot automatically merge CIC-DDoS2019 into NetFlow v2 tables."
            )
        if inspection["missing_canonical_features"]:
            raise IncompatibleSchemaError(
                f"File '{file_path}' is missing mandatory canonical NetFlow v2 features: "
                f"{inspection['missing_canonical_features']}"
            )
        return inspection

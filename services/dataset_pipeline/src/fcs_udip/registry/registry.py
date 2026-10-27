"""Dataset source registry and licensing verification engine."""

from pathlib import Path
from typing import Any

import yaml

from .models import DatasetSourceRecord, LicenseType


class LicenseViolationError(Exception):
    """Raised when an operation violates dataset licensing or commercial use prohibitions."""


class DatasetRegistry:
    """Registry maintaining authoritative cybersecurity dataset provenance and licensing policies."""

    def __init__(self, sources_config_path: Path | str | None = None) -> None:
        self._sources: dict[str, DatasetSourceRecord] = {}
        if sources_config_path:
            self.load_from_yaml(sources_config_path)

    def register_source(self, record: DatasetSourceRecord) -> None:
        """Register or update a dataset source record."""
        self._sources[record.dataset_id] = record

    def get_source(self, dataset_id: str) -> DatasetSourceRecord:
        """Retrieve registered dataset record by ID."""
        if dataset_id not in self._sources:
            raise KeyError(f"Dataset '{dataset_id}' is not registered in FCS dataset catalog.")
        return self._sources[dataset_id]

    def list_sources(self) -> list[DatasetSourceRecord]:
        """Return list of all registered dataset source records."""
        return list(self._sources.values())

    def load_from_yaml(self, path: Path | str) -> None:
        """Load dataset source records from a sources.yaml configuration file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Dataset sources configuration not found at: {config_path}")
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for _ds_id, ds_data in data.get("sources", {}).items():
            record = DatasetSourceRecord(**ds_data)
            self.register_source(record)

    def verify_licensing(
        self,
        dataset_id: str,
        intended_use: str = "RESEARCH",
    ) -> dict[str, Any]:
        """
        Verify whether the intended usage is permitted under the dataset's recorded license.
        Blocks commercial deployment of research-only academic datasets.
        """
        source = self.get_source(dataset_id)
        is_commercial = intended_use.upper() == "COMMERCIAL"

        if is_commercial and not source.commercial_use_allowed:
            raise LicenseViolationError(
                f"Commercial use of dataset '{dataset_id}' is strictly prohibited. "
                f"License type: {source.license_type}. "
                f"Terms: {source.license_terms}"
            )

        status = "PERMITTED"
        if source.license_type == LicenseType.LICENSE_REVIEW_REQUIRED:
            status = "REVIEW_REQUIRED"

        return {
            "dataset_id": dataset_id,
            "intended_use": intended_use.upper(),
            "status": status,
            "license_type": source.license_type.value,
            "commercial_allowed": source.commercial_use_allowed,
            "citation_required": source.citation,
            "publisher": source.publisher,
        }

    def check_parent_overlap_risk(self, dataset_ids: list[str]) -> list[dict[str, str]]:
        """
        Detect parent/child dataset overlap risks (e.g. including NF-UQ-NIDS-v2
        simultaneously with NF-BoT-IoT-v2 in the same experiment).
        """
        warnings: list[dict[str, str]] = []
        selected_set = set(dataset_ids)

        for ds_id in dataset_ids:
            if ds_id in self._sources:
                source = self._sources[ds_id]
                for parent in source.parent_sources:
                    if parent in selected_set:
                        warnings.append(
                            {
                                "combined_dataset": ds_id,
                                "parent_dataset": parent,
                                "risk": "DUPLICATE_OVERLAP_RISK",
                                "remediation": (
                                    f"Dataset '{ds_id}' already incorporates '{parent}'. "
                                    f"Do not combine them without explicitly disjoint sample partitions."
                                ),
                            }
                        )
        return warnings

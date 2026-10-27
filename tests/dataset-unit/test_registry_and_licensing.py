"""Unit tests for dataset registry, provenance tracking, and licensing constraints."""

from pathlib import Path

import pytest

from fcs_udip.registry.models import LicenseType
from fcs_udip.registry.registry import DatasetRegistry, LicenseViolationError


@pytest.mark.dataset_unit
class TestDatasetRegistryAndLicensing:
    """Validate dataset catalog registration, academic provenance, and commercial use blocking."""

    def test_load_sources_from_yaml(self) -> None:
        yaml_path = Path("configs/datasets/sources.yaml")
        registry = DatasetRegistry(yaml_path)
        sources = registry.list_sources()

        assert len(sources) >= 5
        source_ids = [s.dataset_id for s in sources]
        assert "NF-UQ-NIDS-v2" in source_ids
        assert "NF-UNSW-NB15-v2" in source_ids
        assert "NF-CSE-CIC-IDS2018-v2" in source_ids
        assert "NF-BoT-IoT-v2" in source_ids
        assert "NF-ToN-IoT-v2" in source_ids

    def test_nids_v2_provenance_and_citation(self) -> None:
        yaml_path = Path("configs/datasets/sources.yaml")
        registry = DatasetRegistry(yaml_path)
        source = registry.get_source("NF-UQ-NIDS-v2")

        assert source.publisher == "University of Queensland (UQ), Cyber Security Research Group"
        assert "Sarhan" in source.authors
        assert source.feature_count == 43
        assert source.feature_family == "NetFlow-v2"
        assert len(source.parent_sources) == 4
        assert source.license_type == LicenseType.RESEARCH_ONLY
        assert not source.commercial_use_allowed

    def test_commercial_use_strictly_blocked(self) -> None:
        yaml_path = Path("configs/datasets/sources.yaml")
        registry = DatasetRegistry(yaml_path)

        # Research use is permitted
        res_research = registry.verify_licensing("NF-UQ-NIDS-v2", intended_use="RESEARCH")
        assert res_research["status"] == "PERMITTED"

        # Commercial use must raise LicenseViolationError
        with pytest.raises(LicenseViolationError) as exc_info:
            registry.verify_licensing("NF-UQ-NIDS-v2", intended_use="COMMERCIAL")
        assert "Commercial use of dataset 'NF-UQ-NIDS-v2' is strictly prohibited" in str(exc_info.value)

    def test_parent_overlap_risk_detection(self) -> None:
        yaml_path = Path("configs/datasets/sources.yaml")
        registry = DatasetRegistry(yaml_path)

        # NF-UQ-NIDS-v2 contains NF-UNSW-NB15-v2
        warnings = registry.check_parent_overlap_risk(["NF-UQ-NIDS-v2", "NF-UNSW-NB15-v2"])
        assert len(warnings) == 1
        assert warnings[0]["risk"] == "DUPLICATE_OVERLAP_RISK"
        assert warnings[0]["combined_dataset"] == "NF-UQ-NIDS-v2"
        assert warnings[0]["parent_dataset"] == "NF-UNSW-NB15-v2"

    def test_unregistered_dataset_lookup_raises_keyerror(self) -> None:
        registry = DatasetRegistry()
        with pytest.raises(KeyError):
            registry.get_source("UNKNOWN_DATASET_XYZ")

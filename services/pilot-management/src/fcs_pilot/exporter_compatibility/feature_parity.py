"""Feature parity validator between exporter capabilities and locked FeatureSpec v1.2."""

import json
import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from packages.contracts.feature_spec import FeatureAvailabilityStatus, get_deployable_feature_spec

logger = logging.getLogger("fcs_pilot.feature_parity")


class FeatureParityResult(BaseModel):
    """Result of comparing exporter telemetry fields against deployable FeatureSpec."""
    exporter_id: str
    vendor: str
    protocol: str
    total_deployable_features: int
    matched_features: list[str]
    missing_features: list[str]
    parity_percentage: float
    compatible_models: list[str]
    disabled_specialists: list[str]
    is_fully_compatible: bool
    notes: list[str] = Field(default_factory=list)


class FeatureParityValidator:
    """Verifies feature availability and prevents imputation artifacts in live detection."""

    SPECIALIST_FEATURE_REQUIREMENTS = {
        "syn_flood_specialist": ["TCP_FLAGS", "IN_PKTS"],
        "dns_amplification_specialist": ["PROTOCOL", "IN_BYTES", "SRC_TO_DST_AVG_THROUGHPUT"],
        "port_scan_specialist": ["PROTOCOL", "IN_PKTS", "FLOW_DURATION_MILLISECONDS"],
        "udp_flood_specialist": ["PROTOCOL", "IN_BYTES", "IN_PKTS"],
        "general_anomaly_model": ["IN_BYTES", "IN_PKTS", "FLOW_DURATION_MILLISECONDS"],
    }

    def __init__(self) -> None:
        self._deployable_spec = get_deployable_feature_spec()
        self._locked_feature_names = [f.name for f in self._deployable_spec.features]

    def evaluate_parity(
        self,
        exporter_id: str,
        vendor: str,
        protocol: str,
        available_fields: list[str],
    ) -> FeatureParityResult:
        """
        Evaluate feature parity for an exporter given its available fields or IPFIX elements.
        """
        # Mapping from common NetFlow / IPFIX fields to FeatureSpec names
        field_mapping = {
            "protocolIdentifier": "PROTOCOL",
            "protocol": "PROTOCOL",
            "PROTOCOL": "PROTOCOL",
            "octetDeltaCount": "IN_BYTES",
            "byte_count": "IN_BYTES",
            "bytes_count": "IN_BYTES",
            "IN_BYTES": "IN_BYTES",
            "packetDeltaCount": "IN_PKTS",
            "packet_count": "IN_PKTS",
            "packets_count": "IN_PKTS",
            "IN_PKTS": "IN_PKTS",
            "flowStartMilliseconds": "FLOW_DURATION_MILLISECONDS",
            "flowEndMilliseconds": "FLOW_DURATION_MILLISECONDS",
            "flow_duration_ms": "FLOW_DURATION_MILLISECONDS",
            "FLOW_DURATION_MILLISECONDS": "FLOW_DURATION_MILLISECONDS",
            "tcpControlBits": "TCP_FLAGS",
            "tcp_flags": "TCP_FLAGS",
            "TCP_FLAGS": "TCP_FLAGS",
            "SRC_TO_DST_AVG_THROUGHPUT": "SRC_TO_DST_AVG_THROUGHPUT",
        }

        matched = set()
        for f in available_fields:
            if f in field_mapping:
                matched.add(field_mapping[f])
            if f.upper() in self._locked_feature_names:
                matched.add(f.upper())

        # If byte_count and duration are available, throughput is derivable
        if "IN_BYTES" in matched and "FLOW_DURATION_MILLISECONDS" in matched:
            matched.add("SRC_TO_DST_AVG_THROUGHPUT")

        total_features = len(self._locked_feature_names)
        matched_list = sorted(list(matched.intersection(set(self._locked_feature_names))))
        missing_list = sorted(list(set(self._locked_feature_names) - matched))

        # Check specialist compatibility
        compatible_specialists = []
        disabled_specialists = []
        for specialist, reqs in self.SPECIALIST_FEATURE_REQUIREMENTS.items():
            if all(r in matched for r in reqs):
                compatible_specialists.append(specialist)
            else:
                disabled_specialists.append(specialist)

        parity_pct = (len(matched_list) / total_features) * 100.0 if total_features > 0 else 0.0
        is_fully_compat = len(missing_list) == 0

        notes = []
        if disabled_specialists:
            notes.append(
                f"Missing fields {missing_list} safely disabled specialists: {disabled_specialists}. "
                "No zero-filling or synthetic imputation used."
            )
        else:
            notes.append("All required features present. Full FCS-HMD specialist bundle eligible.")

        return FeatureParityResult(
            exporter_id=exporter_id,
            vendor=vendor,
            protocol=protocol,
            total_deployable_features=total_features,
            matched_features=matched_list,
            missing_features=missing_list,
            parity_percentage=round(parity_pct, 1),
            compatible_models=compatible_specialists,
            disabled_specialists=disabled_specialists,
            is_fully_compatible=is_fully_compat,
            notes=notes,
        )

    def generate_reports(
        self,
        parity_results: list[FeatureParityResult],
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """
        Generate exporter_compatibility_report.json and feature_parity_report.md.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "exporter_compatibility_report.json"
        md_path = output_dir / "feature_parity_report.md"

        data = [res.model_dump() for res in parity_results]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        md_lines = [
            "# FCS Phase 9 Exporter Feature Parity & Model Compatibility Report",
            "",
            "> [!NOTE]",
            "> Evaluated against FeatureSpec v1.2 locked deployable subset (Phase 1 FlowEvent v1 specification).",
            "",
            "## Exporter Parity Summary Table",
            "",
            "| Exporter ID | Vendor | Protocol | Parity % | Matched Features | Missing Features | Eligible Specialists |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in parity_results:
            matched_str = f"{len(r.matched_features)}/{r.total_deployable_features}"
            missing_str = ", ".join(r.missing_features) if r.missing_features else "None"
            eligible_str = ", ".join(r.compatible_models)
            md_lines.append(
                f"| `{r.exporter_id}` | {r.vendor} | {r.protocol} | **{r.parity_percentage}%** | {matched_str} | {missing_str} | {eligible_str} |"
            )

        md_lines.extend([
            "",
            "## Imputation & Safety Policy",
            "1. **Zero Imputation Policy:** FCS v1.2 strictly prohibits zero-filling or mean-imputing missing router export fields during inference.",
            "2. **Graceful Specialist Degradation:** If an exporter omits TCP Flags, the SYN Flood specialist is decoupled while volumetric and behavioral models remain active.",
            "3. **Evidence Fusion:** Calibrated fusion adjusts confidence scores dynamically when optional specialists are absent.",
            "",
        ])

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        logger.info(f"Generated feature parity reports at {json_path} and {md_path}")
        return json_path, md_path

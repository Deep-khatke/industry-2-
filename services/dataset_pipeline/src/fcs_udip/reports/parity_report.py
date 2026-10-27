"""Markdown feature parity matrix comparing NetFlow v2 benchmark with FlowEvent v1."""

from pathlib import Path

from packages.contracts.feature_spec import (
    FeatureAvailabilityStatus,
    get_deployable_feature_spec,
    get_research_feature_spec,
)


def generate_feature_parity_report(output_path: Path | str | None = None) -> str:
    """Generate Markdown report detailing benchmark vs deployable telemetry feature parity."""
    research_spec = get_research_feature_spec()
    deployable_spec = get_deployable_feature_spec()

    rows = ""
    status_counts: dict[str, int] = {}

    for f in research_spec.features:
        status_val = f.production_availability.value
        status_counts[status_val] = status_counts.get(status_val, 0) + 1
        mapping = f.flow_event_mapping or "*None (Unavailable)*"
        rows += f"| `{f.name}` | `{f.data_type}` | `{f.unit}` | `{status_val}` | `{mapping}` |\n"

    report_md = f"""# FCS-UDIP Feature Parity Matrix Report
**Architecture Baseline:** Federated Cyber Shield v1.2
**Canonical Benchmark Specification:** `{research_spec.spec_id}` ({len(research_spec.features)} features)
**Production Deployable Specification:** `{deployable_spec.spec_id}` ({len(deployable_spec.features)} features)

---

## 1. Feature Parity Executive Summary
| Availability Status | Feature Count | Proportion | Interpretation |
|---|---|---|---|
| **DIRECTLY_AVAILABLE** | {status_counts.get(FeatureAvailabilityStatus.DIRECTLY_AVAILABLE.value, 0)} | {status_counts.get(FeatureAvailabilityStatus.DIRECTLY_AVAILABLE.value, 0)/43*100:.1f}% | Natively captured in Phase 1 FlowEvent v1 |
| **DERIVABLE_WITH_VERIFIED_TRANSFORM** | {status_counts.get(FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM.value, 0)} | {status_counts.get(FeatureAvailabilityStatus.DERIVABLE_WITH_VERIFIED_TRANSFORM.value, 0)/43*100:.1f}% | Accurately computed from duration & bytes/packets |
| **REQUIRES_ADDITIONAL_EXPORT_FIELDS** | {status_counts.get(FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS.value, 0)} | {status_counts.get(FeatureAvailabilityStatus.REQUIRES_ADDITIONAL_EXPORT_FIELDS.value, 0)/43*100:.1f}% | Requires router IPFIX template additions (Phase 4) |
| **UNAVAILABLE** | {status_counts.get(FeatureAvailabilityStatus.UNAVAILABLE.value, 0)} | {status_counts.get(FeatureAvailabilityStatus.UNAVAILABLE.value, 0)/43*100:.1f}% | Payload deep inspection fields absent from router NetFlow |

---

## 2. Canonical 43 NetFlow v2 Feature Inventory
| Canonical Feature | Data Type | Unit | Production Status | FlowEvent v1 Mapping |
|---|---|---|---|---|
{rows}

---

## 3. Strict Boundary Rules
1. **Unavailable Features Excluded from Deployable View:** Features marked `REQUIRES_ADDITIONAL_EXPORT_FIELDS` or `UNAVAILABLE` must NEVER silently enter the deployable ML feature set.
2. **Privacy Protection:** Raw `IPV4_SRC_ADDR` and `IPV4_DST_ADDR` are strictly masked to `/24` network prefixes matching Phase 1 privacy rules.
3. **No Target Leakage:** Labels (`Label`, `Attack`) and metadata (`dataset_source`, `tenant_id`) are excluded from predictive inputs.
"""
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as out_f:
            out_f.write(report_md)

    return report_md

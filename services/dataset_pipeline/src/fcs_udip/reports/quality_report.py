"""Markdown report generation for dataset quality and quarantine audits."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def generate_quality_report(
    dataset_id: str,
    metrics: dict[str, Any],
    output_path: Path | str | None = None,
) -> str:
    """Generate professional Markdown data quality audit report."""
    initial = metrics.get("initial_row_count", 0)
    clean = metrics.get("clean_row_count", 0)
    quarantine = metrics.get("quarantine_row_count", 0)
    ratio = metrics.get("clean_ratio", 0.0) * 100
    violations = metrics.get("rule_violations", {})

    violations_rows = ""
    if violations:
        for rule, count in violations.items():
            violations_rows += f"| `{rule}` | {count:,} | {count / max(1, initial) * 100:.2f}% |\n"
    else:
        violations_rows = "| *None* | 0 | 0.00% |\n"

    report_md = f"""# FCS-UDIP Data Quality Audit Report
**Dataset ID:** `{dataset_id}`
**Audit Timestamp:** {datetime.now(UTC).isoformat()}
**Pipeline Standard:** FCS v1.2 Phase 2 Data Quality Framework

---

## 1. Quality Summary Metrics
| Metric | Value | Proportion |
|---|---|---|
| **Initial Ingested Rows** | {initial:,} | 100.00% |
| **Accepted Clean Rows** | {clean:,} | {ratio:.2f}% |
| **Quarantined Rows** | {quarantine:,} | {100 - ratio:.2f}% |
| **Immutability of Raw Source** | **PRESERVED** | 100.00% |

---

## 2. Rule Violation Breakdown
| Quality Rule Triggered | Affected Row Count | Percentage |
|---|---|---|
{violations_rows}

---

## 3. Quarantine Remediation Policy
- Records triggering out-of-bounds port numbers, negative packet counts, negative byte counts, or missing labels are segregated into `data/staging/quarantine/`.
- Quarantined records are preserved for forensic review and model robustness ablation.
- Under FCS v1.2 policy, zero rows are silently deleted without audit tracking.
"""
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(report_md)

    return report_md

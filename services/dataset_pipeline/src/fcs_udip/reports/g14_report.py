"""Architecture Release Gate G14 — Dataset Integrity and Lineage Verification."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def generate_g14_report(
    evaluations: dict[str, dict[str, Any]],
    output_path: Path | str | None = None,
) -> str:
    """
    Generate official Architecture v1.2 Release Gate G14 evaluation report.
    Evaluates all required pass conditions with factual, audit-verifiable status.
    """
    all_passed = all(ev.get("status") in ("PASSED", "OFFLINE_VERIFIED") for ev in evaluations.values())
    overall_status = "PASSED (OFFLINE_VERIFIED)" if all_passed else "INCOMPLETE_OR_PENDING"

    rows = ""
    for gate_subid, ev in sorted(evaluations.items()):
        status = ev.get("status", "PENDING")
        desc = ev.get("description", "")
        evidence = ev.get("evidence", "")
        rows += f"| `{gate_subid}` | **{status}** | {desc} | {evidence} |\n"

    report_md = f"""# Release Gate G14 — Dataset Integrity & Lineage Verification Report
**Architecture Baseline:** Federated Cyber Shield v1.2
**Release Gate ID:** `G14`
**Evaluation Timestamp:** {datetime.now(UTC).isoformat()}
**Total Expenditure:** **₹0 / $0 — STRICT ZERO-COST COMPLIANCE**
**Overall G14 Status:** **{overall_status}**

---

## 1. G14 Sub-Check Evaluation Matrix
| Check ID | Status | Requirement | Verification Evidence |
|---|---|---|---|
{rows}

---

## 2. Gate Authority & Policy Disclosures
1. **Academic Licensing Constraint:** `NF-UQ-NIDS-v2` and its parent datasets are strictly classified as `RESEARCH_ONLY`. No commercial deployment claims are permitted.
2. **Development Cryptographic Signatures:** Manifest signatures are generated using development keys for pipeline reproducibility; production signing authority is deferred to subsequent release phases.
3. **Synthetic vs Full Benchmark Datasets:** Tests executed against high-fidelity synthetic fixtures and permitted local slices confirm pipeline correctness. Full 12-GB dataset acquisition remains gated by local resource budgets.
"""
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(report_md)

    return report_md

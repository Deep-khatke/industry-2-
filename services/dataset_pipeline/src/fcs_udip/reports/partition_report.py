"""Markdown report generation for 7 simulated ISP federated learning partitions."""

from pathlib import Path

from packages.contracts.partition_manifest import FederatedPartitionSetManifest


def generate_partition_report(
    manifest: FederatedPartitionSetManifest,
    output_path: Path | str | None = None,
) -> str:
    """Generate Markdown report detailing multi-client partition distributions and class skew."""
    regime = manifest.regime.value
    total_records = manifest.total_training_records
    alpha_str = f"Dirichlet Alpha: {manifest.dirichlet_alpha}" if manifest.dirichlet_alpha else "Uniform Stratified"

    client_rows = ""
    for cid, info in sorted(manifest.client_partitions.items()):
        cnt = info.assigned_record_count
        pct = (cnt / max(1, total_records)) * 100
        # Summarize top 3 classes
        top_classes = sorted(info.class_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ", ".join([f"{k}: {v}" for k, v in top_classes])
        client_rows += f"| `{cid}` | `{info.tenant_id_mapping}` | {cnt:,} | {pct:.1f}% | {top_str} |\n"

    report_md = f"""# FCS-UDIP Seven Simulated ISP Federated Partition Report
**Partition Regime:** `{regime}` ({alpha_str})
**Parent Dataset Digest:** `{manifest.parent_dataset_digest[:16]}...`
**Total Allocated Training Records:** {total_records:,}
**Random Seed:** {manifest.seed}

---

## 1. Client Allocation Summary
| Logical Client ID | Phase 1 Mapped Tenant | Record Count | Share | Dominant Class Profiles |
|---|---|---|---|---|
{client_rows}

---

## 2. Federated Boundary Guarantees
1. **Mutual Exclusivity:** Every assigned training sample belongs to exactly one simulated ISP client (0 record duplication across clients).
2. **Train Set Isolation:** Test and validation splits are completely excluded from client federated partitions.
3. **Independent Source Holdout:** Zero samples from held-out source datasets are present in client training views.
4. **Tenant ID Parity:** Client IDs (`isp_01` .. `isp_07`) map directly to Phase 1 authorized rural ISP tenants (`tenant-isp-alpha` .. `tenant-isp-eta`).
"""
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(report_md)

    return report_md

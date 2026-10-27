"""Model comparison engine for ranking and comparing candidate classifiers."""

import csv
from pathlib import Path
from typing import Any


class ModelComparator:
    """Aggregates and formats comparative benchmark tables across models and tracks."""

    def __init__(self, metrics_dir: Path | str = "artifacts/metrics") -> None:
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def generate_comparison_table(
        self,
        experiment_results: list[dict[str, Any]],
        output_csv: Path | str | None = None,
        output_md: Path | str | None = None,
    ) -> str:
        """
        Generate markdown and CSV model comparison tables.
        Columns: Model, Feature Track, PR-AUC, ROC-AUC, F1, Precision, Recall, FPR, ECE, Training Time.
        """
        headers = [
            "Model",
            "Track",
            "PR-AUC",
            "ROC-AUC",
            "F1 Score",
            "Precision",
            "Recall",
            "FPR",
            "ECE",
            "Train Time (s)",
        ]

        rows = []
        for res in experiment_results:
            m = res.get("metrics", {})
            rows.append([
                res.get("model_family", "Unknown"),
                res.get("feature_track", "RESEARCH"),
                f"{m.get('pr_auc', 0.0):.4f}",
                f"{m.get('roc_auc', 0.0):.4f}",
                f"{m.get('f1', 0.0):.4f}",
                f"{m.get('precision', 0.0):.4f}",
                f"{m.get('recall', 0.0):.4f}",
                f"{m.get('fpr', 0.0):.4f}",
                f"{m.get('expected_calibration_error', 0.0):.4f}",
                f"{m.get('training_time_seconds', 0.0):.2f}",
            ])

        # Generate Markdown Table
        md_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            md_lines.append("| " + " | ".join(str(c) for c in row) + " |")

        md_content = "\n".join(md_lines)

        if output_md:
            p_md = Path(output_md)
            p_md.parent.mkdir(parents=True, exist_ok=True)
            p_md.write_text(md_content, encoding="utf-8")

        if output_csv:
            p_csv = Path(output_csv)
            p_csv.parent.mkdir(parents=True, exist_ok=True)
            with p_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

        return md_content

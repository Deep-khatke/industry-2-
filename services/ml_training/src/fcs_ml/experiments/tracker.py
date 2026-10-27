"""Zero-cost file-based experiment tracker for local research logging."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ExperimentTracker:
    """Local JSON-based experiment tracking with zero cloud dependency."""

    def __init__(self, tracking_dir: Path | str = "artifacts/experiments") -> None:
        self.tracking_dir = Path(tracking_dir)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)

    def log_experiment(
        self,
        experiment_id: str,
        model_family: str,
        feature_track: str,
        hyperparameters: dict[str, Any],
        metrics: dict[str, Any],
        dataset_digest: str = "unknown",
        notes: str = "",
    ) -> Path:
        """Record experiment run to local JSON file."""
        run_file = self.tracking_dir / f"{experiment_id}.json"
        record = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "model_family": model_family,
            "feature_track": feature_track,
            "dataset_digest": dataset_digest,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
            "notes": notes,
        }
        run_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return run_file

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Retrieve a past experiment run."""
        p = self.tracking_dir / f"{experiment_id}.json"
        if not p.exists():
            raise FileNotFoundError(f"Experiment '{experiment_id}' not found.")
        return json.loads(p.read_text(encoding="utf-8"))

    def list_experiments(self) -> list[dict[str, Any]]:
        """List all logged experiments."""
        runs = []
        for f in self.tracking_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if "experiment_id" not in data:
                        data["experiment_id"] = f.stem
                    runs.append(data)
            except Exception:
                continue
        runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return runs

"""Candidate model registry for managing versioned, verified ML model artifacts."""

import hashlib
from pathlib import Path
from typing import Any

from fcs_ml.models.autoencoder import AutoencoderAnomalyModel
from fcs_ml.models.base import BaseFCSModel
from fcs_ml.models.baseline import DummyBaselineClassifier
from fcs_ml.models.botnet_specialist import BotnetSpecialistModel
from fcs_ml.models.ddos_specialist import DDoSSpecialistModel
from fcs_ml.models.isolation_forest import IsolationForestAnomalyModel
from fcs_ml.models.lightgbm_model import LightGBMModel
from fcs_ml.models.logistic import LogisticRegressionModel
from fcs_ml.models.mlp import PyTorchMLPModel
from fcs_ml.models.multiclass import MulticlassAttackClassifier
from fcs_ml.models.scanning_specialist import ScanningSpecialistModel

from .manifest import ModelManifest


class CandidateModelRegistry:
    """Stores, loads, and verifies versioned candidate ML models."""

    def __init__(self, registry_dir: Path | str = "artifacts/candidate-models") -> None:
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def register_model(
        self,
        model: BaseFCSModel,
        manifest: ModelManifest,
    ) -> Path:
        """Save model artifact and its signed manifest into the candidate registry."""
        model_dir = self.registry_dir / manifest.model_id
        model_dir.mkdir(parents=True, exist_ok=True)

        artifact_base = model_dir / "model"
        artifact_hash = model.save(artifact_base)

        manifest.artifact_hash = artifact_hash
        manifest.artifact_path = str(artifact_base)

        manifest_file = model_dir / "model_manifest.json"
        manifest_file.write_text(manifest.to_canonical_json(), encoding="utf-8")
        return model_dir

    def load_model(self, model_id: str) -> tuple[BaseFCSModel, ModelManifest]:
        """Load and verify a candidate model from registry."""
        model_dir = self.registry_dir / model_id
        if not model_dir.exists():
            raise FileNotFoundError(f"Model '{model_id}' not found in registry at {model_dir}")

        manifest_file = model_dir / "model_manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest missing for model '{model_id}'")

        manifest = ModelManifest.from_file(str(manifest_file))

        # Check artifact files exist
        artifact_base = Path(manifest.artifact_path)
        if not artifact_base.is_absolute() and not (
            artifact_base.with_suffix(".json").exists()
            or artifact_base.with_suffix(".joblib").exists()
            or artifact_base.with_suffix(".txt").exists()
            or artifact_base.with_suffix(".pt").exists()
            or artifact_base.exists()
        ):
            candidate = model_dir / artifact_base.name
            if (
                candidate.with_suffix(".json").exists()
                or candidate.with_suffix(".joblib").exists()
                or candidate.with_suffix(".txt").exists()
                or candidate.with_suffix(".pt").exists()
                or candidate.exists()
            ):
                artifact_base = candidate
            elif (model_dir / "model.json").exists() or (model_dir / "model.joblib").exists():
                artifact_base = model_dir / "model"
        family = manifest.model_family

        if family == "DummyBaseline":
            model: BaseFCSModel = DummyBaselineClassifier.load(artifact_base)
        elif family == "LogisticRegression":
            model = LogisticRegressionModel.load(artifact_base)
        elif family == "LightGBM":
            model = LightGBMModel.load(artifact_base)
        elif family == "PyTorchMLP":
            model = PyTorchMLPModel.load(artifact_base)
        elif family == "MulticlassAttackClassifier":
            model = MulticlassAttackClassifier.load(artifact_base)
        elif family == "IsolationForest":
            model = IsolationForestAnomalyModel.load(artifact_base)
        elif family == "Autoencoder":
            model = AutoencoderAnomalyModel.load(artifact_base)
        elif family == "DDoSSpecialist":
            model = DDoSSpecialistModel.load(artifact_base)
        elif family == "ScanningSpecialist":
            model = ScanningSpecialistModel.load(artifact_base)
        elif family == "BotnetSpecialist":
            model = BotnetSpecialistModel.load(artifact_base)
        else:
            raise ValueError(f"Unknown model family: {family}")

        return model, manifest

    def verify_model_artifact(self, model_id: str) -> dict[str, Any]:
        """Verify integrity of saved model artifact against recorded checksum."""
        model_dir = self.registry_dir / model_id
        manifest_file = model_dir / "model_manifest.json"
        manifest = ModelManifest.from_file(str(manifest_file))

        # Compute file hash
        p = Path(manifest.artifact_path)
        if not p.is_absolute() and not (
            p.with_suffix(".txt").exists()
            or p.with_suffix(".pt").exists()
            or p.with_suffix(".joblib").exists()
            or p.with_suffix(".json").exists()
            or p.exists()
        ):
            p = model_dir / p.name
        actual_hash = ""
        if p.with_suffix(".joblib").exists():
            # Joblib + json
            combined = p.with_suffix(".joblib").read_bytes() + p.with_suffix(".json").read_bytes()
            actual_hash = hashlib.sha256(combined).hexdigest()
        elif p.with_suffix(".txt").exists():
            # LightGBM txt + json
            combined = p.with_suffix(".txt").read_bytes() + p.with_suffix(".json").read_bytes()
            actual_hash = hashlib.sha256(combined).hexdigest()
        elif p.with_suffix(".pt").exists():
            # PyTorch pt + json
            combined = p.with_suffix(".pt").read_bytes() + p.with_suffix(".json").read_bytes()
            actual_hash = hashlib.sha256(combined).hexdigest()
        elif p.with_suffix(".json").exists():
            # JSON single file
            actual_hash = hashlib.sha256(p.with_suffix(".json").read_bytes()).hexdigest()
        elif p.exists():
            actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()

        hash_matches = (actual_hash == manifest.artifact_hash)
        return {
            "model_id": model_id,
            "recorded_hash": manifest.artifact_hash,
            "actual_hash": actual_hash,
            "integrity_verified": hash_matches,
            "feature_track": manifest.feature_track,
            "threshold": manifest.validation_threshold,
        }

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered candidate models."""
        models = []
        for d in self.registry_dir.iterdir():
            if d.is_dir() and (d / "model_manifest.json").exists():
                m = ModelManifest.from_file(str(d / "model_manifest.json"))
                models.append({
                    "model_id": m.model_id,
                    "model_family": m.model_family,
                    "feature_track": m.feature_track,
                    "threshold": m.validation_threshold,
                    "f1": m.test_metrics.get("f1", 0.0),
                    "pr_auc": m.test_metrics.get("pr_auc", 0.0),
                    "fpr": m.test_metrics.get("fpr", 0.0),
                })
        return models

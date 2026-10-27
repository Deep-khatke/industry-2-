"""Safe model artifact export and packaging engine."""

import hashlib
from pathlib import Path
from typing import Any

from fcs_ml.models.base import BaseFCSModel
from fcs_ml.registry.manifest import ModelManifest


class ModelExporter:
    """Exports model weights, configurations, and manifests using safe non-executable formats."""

    @staticmethod
    def export_model(
        model: BaseFCSModel,
        manifest: ModelManifest,
        export_dir: Path | str,
    ) -> dict[str, Any]:
        """Export candidate model and verified manifest to destination folder."""
        dest = Path(export_dir) / manifest.model_id
        dest.mkdir(parents=True, exist_ok=True)

        artifact_base = dest / "model"
        artifact_hash = model.save(artifact_base)

        manifest.artifact_hash = artifact_hash
        manifest.artifact_path = str(artifact_base)

        manifest_file = dest / "model_manifest.json"
        manifest_file.write_text(manifest.to_canonical_json(), encoding="utf-8")

        # Compute combined directory checksum
        hasher = hashlib.sha256()
        for f in sorted(dest.iterdir()):
            if f.is_file():
                hasher.update(f.read_bytes())
        bundle_digest = hasher.hexdigest()

        return {
            "model_id": manifest.model_id,
            "export_directory": str(dest),
            "manifest_file": str(manifest_file),
            "artifact_hash": artifact_hash,
            "bundle_digest": bundle_digest,
            "model_family": manifest.model_family,
            "feature_track": manifest.feature_track,
        }

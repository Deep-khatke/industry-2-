#!/usr/bin/env python3
"""Release Manifest Builder with Dual-Signatures for FCS (Phase 11).

Calculates SHA-384 digests of release artifacts (frontend build, model registry,
SBOM, configurations), builds an RFC 8785 canonical manifest, and dual-signs
using ECDSA P-256 and ML-DSA-65 post-quantum signatures.
"""

from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
GOV_SRC = ROOT_DIR / "services" / "governance" / "src"
if str(GOV_SRC) not in sys.path:
    sys.path.insert(0, str(GOV_SRC))

from fcs_governance.contracts.manifest import CanonicalManifestBody
from fcs_governance.crypto.dual_signer import DualSigner

OUTPUT_DIR = ROOT_DIR / "artifacts" / "phase11" / "release-manifests"


def compute_file_sha384(path: Path) -> str:
    hasher = hashlib.sha384()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_directory_sha384(directory: Path) -> dict[str, str]:
    digests = {}
    if not directory.exists():
        return digests
    for p in sorted(directory.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            rel = str(p.relative_to(ROOT_DIR)).replace("\\", "/")
            digests[rel] = compute_file_sha384(p)
    return digests


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[*] Collecting release artifacts and computing SHA-384 digests...")

    artifact_digests = {}
    artifact_digests.update(compute_directory_sha384(ROOT_DIR / "apps" / "security-dashboard" / "dist"))
    artifact_digests.update(compute_directory_sha384(ROOT_DIR / "artifacts" / "candidate-models"))
    artifact_digests.update(compute_directory_sha384(ROOT_DIR / "artifacts" / "phase11" / "sbom"))
    artifact_digests.update(compute_directory_sha384(ROOT_DIR / "configs" / "environments"))

    # Compute master aggregate artifact digest
    aggregate_hasher = hashlib.sha384()
    for rel_path, digest in sorted(artifact_digests.items()):
        aggregate_hasher.update(f"{rel_path}:{digest}".encode("utf-8"))
    master_artifact_digest = aggregate_hasher.hexdigest()

    now = datetime.now(UTC)
    body = CanonicalManifestBody(
        release_id="fcs-v1.2.0-rc1-phase11",
        schema_version="1.2.0",
        manifest_sequence=11,
        artifact_digest_sha384=master_artifact_digest,
        feature_schema_digest=hashlib.sha256(b"netflow_v9_ipfix_14_features").hexdigest(),
        model_lineage_reference="candidate-models-v1.2.0",
        evaluation_reference="phase4-phase9-eval-reports",
        validity_interval_start=now.isoformat(),
        validity_interval_end=(now + timedelta(days=90)).isoformat(),
    )

    print("[*] Generating dual ECDSA P-256 + ML-DSA-65 signatures...")
    signer, keys = DualSigner.create_ephemeral_dev_signer()
    manifest = signer.sign_manifest(body)

    print("[*] Verifying signed manifest integrity...")
    valid = DualSigner.verify_manifest(
        manifest,
        expected_artifact_digest=master_artifact_digest,
        trusted_ecdsa_key_hex=keys["ecdsa_public_key_hex"],
        trusted_mldsa_key_hex=keys["mldsa_public_key_hex"],
    )
    if not valid:
        print("[-] Dual signature verification FAILED!")
        return 1

    manifest_dict = manifest.model_dump()
    manifest_dict["artifact_inventory"] = artifact_digests
    manifest_dict["verification_metadata"] = {
        "status": "DUAL_SIGNATURES_VERIFIED",
        "verified_at": datetime.now(UTC).isoformat(),
        "trusted_keys": keys,
    }

    out_file = OUTPUT_DIR / "phase11_release_manifest.json"
    out_file.write_text(json.dumps(manifest_dict, indent=2), encoding="utf-8")
    print(f"[+] Verified Release Manifest saved to: {out_file}")
    print(f"[+] Total artifacts hashed: {len(artifact_digests)}")
    print(f"[+] Master SHA-384: {master_artifact_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

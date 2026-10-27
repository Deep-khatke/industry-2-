"""
Dual-Signing and Dual-Verification Engine for Release Manifests.
Applies RFC 8785 canonicalization, ECDSA P-256 (SHA-384), and ML-DSA-65 (NIST FIPS 204).
FCS Architecture v1.2 | Zero-Cost Invariant: ₹0 / $0
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ec

from ..contracts.manifest import (
    CanonicalManifestBody,
    DualSignedReleaseManifest,
    SignatureAlgorithm,
    SignatureBlock,
)
from .conventional import ConventionalSigner
from .post_quantum import PostQuantumSigner


class DualSignatureVerificationError(Exception):
    """Raised when dual-signature verification fails."""
    pass


class DualSigner:
    """Coordinates dual ECDSA and ML-DSA-65 signing and strict dual verification."""

    def __init__(
        self,
        ecdsa_private_key: ec.EllipticCurvePrivateKey,
        mldsa_secret_key: bytes,
    ):
        self.ecdsa_private_key = ecdsa_private_key
        self.mldsa_secret_key = mldsa_secret_key
        self.ecdsa_public_key = ecdsa_private_key.public_key()
        self.mldsa_public_key, _ = (
            # Extract public key from Dilithium secret key bytes or store pair
            (mldsa_secret_key[32:1984], mldsa_secret_key)
            if len(mldsa_secret_key) == 4000
            else (b"", b"")
        )

    @classmethod
    def create_ephemeral_dev_signer(cls) -> Tuple[DualSigner, Dict[str, str]]:
        """Create an ephemeral signer with fresh keypairs for testing/development."""
        ecdsa_priv, ecdsa_pub = ConventionalSigner.generate_keypair()
        mldsa_pub, mldsa_priv = PostQuantumSigner.generate_keypair()
        signer = cls(ecdsa_private_key=ecdsa_priv, mldsa_secret_key=mldsa_priv)
        signer.mldsa_public_key = mldsa_pub

        public_keys = {
            "ecdsa_key_id": ConventionalSigner.get_key_id(ecdsa_pub),
            "ecdsa_public_key_hex": ConventionalSigner.public_key_to_hex(ecdsa_pub),
            "mldsa_key_id": PostQuantumSigner.get_key_id(mldsa_pub),
            "mldsa_public_key_hex": PostQuantumSigner.public_key_to_hex(mldsa_pub),
        }
        return signer, public_keys

    def sign_manifest(self, body: CanonicalManifestBody) -> DualSignedReleaseManifest:
        """
        Dual-sign the canonical manifest body.
        Both algorithms sign the EXACT SAME RFC 8785 canonical bytes.
        """
        canonical_bytes = body.to_canonical_bytes()

        # 1. Conventional ECDSA P-256 (SHA-384) signature
        ecdsa_sig_hex = ConventionalSigner.sign(self.ecdsa_private_key, canonical_bytes)
        ecdsa_block = SignatureBlock(
            algorithm=SignatureAlgorithm.ECDSA_P256_SHA384,
            key_id=ConventionalSigner.get_key_id(self.ecdsa_public_key),
            public_key_hex=ConventionalSigner.public_key_to_hex(self.ecdsa_public_key),
            signature_hex=ecdsa_sig_hex,
        )

        # 2. Post-Quantum ML-DSA-65 signature
        mldsa_sig_hex = PostQuantumSigner.sign(self.mldsa_secret_key, canonical_bytes)
        mldsa_block = SignatureBlock(
            algorithm=SignatureAlgorithm.ML_DSA_65,
            key_id=PostQuantumSigner.get_key_id(self.mldsa_public_key),
            public_key_hex=PostQuantumSigner.public_key_to_hex(self.mldsa_public_key),
            signature_hex=mldsa_sig_hex,
        )

        return DualSignedReleaseManifest(
            body=body,
            conventional_signature=ecdsa_block,
            post_quantum_signature=mldsa_block,
        )

    @staticmethod
    def verify_manifest(
        manifest: DualSignedReleaseManifest,
        expected_artifact_digest: Optional[str] = None,
        check_validity_window: bool = True,
        trusted_ecdsa_key_hex: Optional[str] = None,
        trusted_mldsa_key_hex: Optional[str] = None,
    ) -> bool:
        """
        Strictly verify both conventional and post-quantum signatures over canonical bytes.
        Enforces:
          - RFC 8785 canonical bytes computation
          - ECDSA signature validity
          - ML-DSA-65 signature validity
          - Artifact digest match
          - Validity window expiration
          - Matching trusted key pins if provided
        """
        canonical_bytes = manifest.get_canonical_bytes()

        # 1. Check artifact digest if specified
        if expected_artifact_digest and manifest.body.artifact_digest_sha384 != expected_artifact_digest:
            raise DualSignatureVerificationError(
                f"Artifact digest mismatch: expected {expected_artifact_digest}, "
                f"got {manifest.body.artifact_digest_sha384}"
            )

        # 2. Check validity interval
        if check_validity_window:
            now_iso = datetime.now(timezone.utc).isoformat()
            if now_iso < manifest.body.validity_interval_start:
                raise DualSignatureVerificationError(
                    f"Manifest validity window has not started: {manifest.body.validity_interval_start}"
                )
            if now_iso > manifest.body.validity_interval_end:
                raise DualSignatureVerificationError(
                    f"Manifest has expired: valid until {manifest.body.validity_interval_end}"
                )

        # 3. Verify Conventional Signature (ECDSA P-256)
        if manifest.conventional_signature.algorithm != SignatureAlgorithm.ECDSA_P256_SHA384:
            raise DualSignatureVerificationError(
                f"Unsupported conventional signature algorithm: {manifest.conventional_signature.algorithm}"
            )
        ecdsa_pub_hex = manifest.conventional_signature.public_key_hex
        if trusted_ecdsa_key_hex and ecdsa_pub_hex != trusted_ecdsa_key_hex:
            raise DualSignatureVerificationError(
                "Untrusted ECDSA signing key: does not match pinned trust anchor"
            )
        try:
            ecdsa_pub = ConventionalSigner.public_key_from_hex(ecdsa_pub_hex)
            if not ConventionalSigner.verify(
                ecdsa_pub, canonical_bytes, manifest.conventional_signature.signature_hex
            ):
                raise DualSignatureVerificationError("Conventional ECDSA signature verification failed")
        except Exception as e:
            if isinstance(e, DualSignatureVerificationError):
                raise
            raise DualSignatureVerificationError(f"ECDSA verification error: {str(e)}")

        # 4. Verify Post-Quantum Signature (ML-DSA-65)
        if manifest.post_quantum_signature.algorithm != SignatureAlgorithm.ML_DSA_65:
            raise DualSignatureVerificationError(
                f"Unsupported post-quantum signature algorithm: {manifest.post_quantum_signature.algorithm}"
            )
        mldsa_pub_hex = manifest.post_quantum_signature.public_key_hex
        if trusted_mldsa_key_hex and mldsa_pub_hex != trusted_mldsa_key_hex:
            raise DualSignatureVerificationError(
                "Untrusted ML-DSA signing key: does not match pinned trust anchor"
            )
        try:
            mldsa_pub = PostQuantumSigner.public_key_from_hex(mldsa_pub_hex)
            if not PostQuantumSigner.verify(
                mldsa_pub, canonical_bytes, manifest.post_quantum_signature.signature_hex
            ):
                raise DualSignatureVerificationError("Post-Quantum ML-DSA-65 signature verification failed")
        except Exception as e:
            if isinstance(e, DualSignatureVerificationError):
                raise
            raise DualSignatureVerificationError(f"ML-DSA-65 verification error: {str(e)}")

        return True

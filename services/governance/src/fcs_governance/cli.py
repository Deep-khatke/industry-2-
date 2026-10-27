"""
CLI Tool for FCS Consortium Governance (fcs-gov).
FCS Architecture v1.2 | Phase 7 Consortium Governance.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .contracts.manifest import CanonicalManifestBody
from .contracts.models import ApprovalRole, EndorsementRecord, GovernanceOrg, RevocationReason
from .crypto.dual_signer import DualSigner
from .fabric.ledger_mock import MockFabricLedger
from .fabric.outbox import AuditOutboxRelay
from .fabric.topology import CONSORTIUM_ORGANIZATIONS
from .workflow.approval import ReleaseApprovalEngine
from .workflow.promotion import ModelPromotionPipeline
from .workflow.rollback import ModelRollbackEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fcs-gov",
        description="Federated Cyber Shield Consortium Governance & Post-Quantum Cryptography CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # inspect
    subparsers.add_parser("inspect", help="Display consortium topology, ledger status, and trust store")

    # verify-prerequisites
    subparsers.add_parser("verify-prerequisites", help="Verify cryptography and ledger libraries")

    # crypto
    crypto_parser = subparsers.add_parser("crypto", help="Cryptographic tools")
    crypto_sub = crypto_parser.add_subparsers(dest="crypto_command")
    crypto_sub.add_parser("test", help="Test dual-signing (ECDSA + ML-DSA-65) over canonical JSON")
    crypto_sub.add_parser("keygen", help="Generate fresh dual keypair")

    # releases
    rel_parser = subparsers.add_parser("releases", help="Release lifecycle management")
    rel_sub = rel_parser.add_subparsers(dest="release_command")
    rel_sub.add_parser("list", help="List releases on the consortium ledger")

    # outbox
    outbox_parser = subparsers.add_parser("outbox", help="Audit outbox management")
    outbox_sub = outbox_parser.add_subparsers(dest="outbox_command")
    outbox_sub.add_parser("status", help="Show pending outbox events")
    outbox_sub.add_parser("reconcile", help="Reconcile outbox events with ledger")

    return parser


def handle_inspect() -> int:
    print("=" * 60)
    print("FCS CONSORTIUM GOVERNANCE & SMARTBFT INSPECTION")
    print("=" * 60)
    print("Consortium Organizations (4 Governing Orgs):")
    for org_enum, topo in CONSORTIUM_ORGANIZATIONS.items():
        print(f"  - {org_enum.value:20} MSP: {topo.msp_id:10} Peers: {len(topo.peer_endpoints)}")

    ledger = MockFabricLedger()
    print("\nSmartBFT Ordering Cluster (N=4, F=1, Quorum=3):")
    for orderer, status in ledger.orderer_health.items():
        status_str = "ONLINE (Healthy)" if status else "OFFLINE (Faulty)"
        print(f"  - {orderer:22} Status: {status_str}")

    active = ledger.get_active_orderer_count()
    print(f"Active Orderers: {active}/4 | Quorum: {'SATISFIED' if active >= 3 else 'LOST'}")

    releases = ledger.list_releases()
    print(f"\nCommitted Releases on Ledger: {len(releases)}")
    for r in releases:
        rev_tag = " [REVOKED]" if r["is_revoked"] else ""
        print(f"  - Release: {r['release_id']:20} Status: {r['status']}{rev_tag} Block: {r['block_number']}")

    print("=" * 60)
    return 0


def handle_verify_prerequisites() -> int:
    print("=" * 60)
    print("FCS-GOV Prerequisites & Cryptographic Library Inspection")
    print("=" * 60)
    import cryptography
    import dilithium_py
    import rfc8785

    print(f"[+] Cryptography:    {cryptography.__version__} (ECDSA P-256 / SHA-384)")
    print(f"[+] Dilithium-py:    {dilithium_py.__file__} (ML-DSA-65 / NIST FIPS 204)")
    print(f"[+] RFC 8785 (JCS):  {rfc8785.__file__}")
    print("[+] Ledger Engine:   Embedded SQLite ACID Ledger (MockFabricLedger)")
    print("[+] Status:          ALL PREREQUISITES VERIFIED")
    print("=" * 60)
    return 0


def handle_crypto_test() -> int:
    print("Testing RFC 8785 Canonicalization & Dual-Signing (ECDSA + ML-DSA-65)...")
    body = CanonicalManifestBody(
        release_id="test-cli-rel-01",
        schema_version="1.2.0",
        manifest_sequence=1,
        artifact_digest_sha384="a" * 96,
        feature_schema_digest="b" * 64,
        model_lineage_reference="lineage-ref",
        evaluation_reference="eval-ref",
        validity_interval_start="2020-01-01T00:00:00Z",
        validity_interval_end="2099-01-01T00:00:00Z",
    )
    signer, keys = DualSigner.create_ephemeral_dev_signer()
    manifest = signer.sign_manifest(body)
    assert DualSigner.verify_manifest(manifest)
    print("[+] Canonical JSON generated successfully.")
    print(f"[+] ECDSA Signature (P-256): {manifest.conventional_signature.signature_hex[:32]}...")
    print(f"[+] ML-DSA-65 Signature:    {manifest.post_quantum_signature.signature_hex[:32]}...")
    print("[+] Dual verification PASSED over identical canonical bytes.")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        return handle_inspect()
    elif args.command == "verify-prerequisites":
        return handle_verify_prerequisites()
    elif args.command == "crypto":
        if args.crypto_command == "test":
            return handle_crypto_test()
    elif args.command == "releases":
        ledger = MockFabricLedger()
        releases = ledger.list_releases()
        print(f"Total Committed Releases: {len(releases)}")
        for r in releases:
            print(f"ID: {r['release_id']} | Status: {r['status']} | Tx: {r['ledger_tx_id']}")
        return 0
    elif args.command == "outbox":
        outbox = AuditOutboxRelay()
        if args.outbox_command == "status":
            pending = outbox.get_pending_events()
            print(f"Pending Outbox Events: {len(pending)}")
            for p in pending:
                print(f"Event: {p.event_id} | Type: {p.event_type} | Aggregate: {p.aggregate_id} | Status: {p.status.value}")
            return 0
        elif args.outbox_command == "reconcile":
            count = outbox.reconcile_and_relay()
            print(f"Reconciled and relayed {count} outbox events.")
            return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

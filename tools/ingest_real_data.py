#!/usr/bin/env python3
"""
FCS Real Telemetry Ingestion Tool.

Provides multiple ways to feed real or custom network telemetry into
the Federated Cyber Shield detection and monitoring pipeline:

Usage:
  # 1. Send sample live flow records (test connectivity and scoring)
  python tools/ingest_real_data.py --sample

  # 2. Simulate a live volumetric DDoS attack to test ML alerting
  python tools/ingest_real_data.py --attack ddos

  # 3. Simulate a stealthy port-scan reconnaissance attack
  python tools/ingest_real_data.py --attack portscan

  # 4. Ingest real flow records from a JSON or CSV file
  python tools/ingest_real_data.py --file path/to/my_flows.json
  python tools/ingest_real_data.py --file path/to/my_flows.csv
"""

import argparse
import csv
import json
import random
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

API_BASE = "http://127.0.0.1:8000"


def get_token(username: str = "admin_alpha", password: str = "FcsDemo2026!") -> str:
    """Acquire JWT token for authentication."""
    url = f"{API_BASE}/v1/auth/token"
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["access_token"]
    except Exception as e:
        print(f"[!] Authentication failed: {e}")
        print("    Ensure the FCS API server is running on port 8000 (run `start.bat`).")
        sys.exit(1)


def send_batch(records: list[dict], token: str, tenant_id: str = "rural-isp-alpha") -> dict:
    """Send a batch of flow records to the ingestion endpoint."""
    url = f"{API_BASE}/v1/dev/telemetry/ingest"
    payload = json.dumps({"tenant_id": tenant_id, "records": records}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[!] Ingestion failed HTTP {e.code}: {err}")
        sys.exit(1)


def generate_sample_flows(count: int = 5) -> list[dict]:
    """Generate realistic everyday internet traffic records."""
    flows = []
    services = [
        ("443", "TCP", 24, "HTTPS"),
        ("80", "TCP", 24, "HTTP"),
        ("53", "UDP", 0, "DNS"),
        ("853", "TCP", 24, "DNS-over-TLS"),
        ("123", "UDP", 0, "NTP"),
    ]
    for _ in range(count):
        port, proto, flags, _ = random.choice(services)
        flows.append({
            "src_ip": f"192.168.1.{random.randint(10, 250)}",
            "dst_ip": f"{random.randint(1, 200)}.{random.randint(1, 200)}.{random.randint(1, 200)}.{random.randint(1, 254)}",
            "src_port": random.randint(32768, 61000),
            "dst_port": int(port),
            "protocol": proto,
            "byte_count": random.randint(350, 4500),
            "packet_count": random.randint(4, 30),
            "flow_duration_ms": round(random.uniform(25.0, 450.0), 2),
            "tcp_flags": flags,
        })
    return flows


def generate_ddos_attack() -> list[dict]:
    """Generate a high-volume SYN flood DDoS pattern."""
    flows = []
    target_ip = "10.0.0.1"
    target_port = 443
    for _ in range(30):
        flows.append({
            "src_ip": f"{random.randint(11, 220)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "dst_ip": target_ip,
            "src_port": random.randint(1024, 65535),
            "dst_port": target_port,
            "protocol": "TCP",
            "byte_count": 64,
            "packet_count": 1,
            "flow_duration_ms": 1.5,
            "tcp_flags": 2,  # SYN flag only
        })
    return flows


def generate_portscan_attack() -> list[dict]:
    """Generate a sequential port scanning reconnaissance probe."""
    flows = []
    attacker_ip = "198.51.100.45"
    target_ip = "192.168.1.1"
    ports_to_probe = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 1433, 3306, 3389, 5432, 8080]
    for p in ports_to_probe:
        flows.append({
            "src_ip": attacker_ip,
            "dst_ip": target_ip,
            "src_port": random.randint(40000, 50000),
            "dst_port": p,
            "protocol": "TCP",
            "byte_count": 48,
            "packet_count": 1,
            "flow_duration_ms": 5.0,
            "tcp_flags": 2,  # SYN
        })
    return flows


def load_file(file_path: str) -> list[dict]:
    """Load flow records from a JSON or CSV file."""
    if file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "records" in data:
                return data["records"]
            raise ValueError("JSON file must be a list of records or contain a 'records' key.")

    elif file_path.endswith(".csv"):
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Type conversions
                rec = {}
                for k, v in row.items():
                    k_clean = k.strip()
                    try:
                        if "." in v:
                            rec[k_clean] = float(v)
                        else:
                            rec[k_clean] = int(v)
                    except (ValueError, TypeError):
                        rec[k_clean] = v
                records.append(rec)
        return records

    else:
        raise ValueError("Unsupported file format. Please use .json or .csv.")


def main():
    parser = argparse.ArgumentParser(description="Ingest real or custom network telemetry into FCS")
    parser.add_argument("--sample", action="store_true", help="Send 5 sample benign flows")
    parser.add_argument("--attack", choices=["ddos", "portscan"], help="Simulate a real DDoS or Port Scan attack")
    parser.add_argument("--file", help="Path to custom JSON or CSV flow file to ingest")
    parser.add_argument("--tenant", default="rural-isp-alpha", help="Tenant ID (default: rural-isp-alpha)")
    args = parser.parse_args()

    if not any([args.sample, args.attack, args.file]):
        parser.print_help()
        print("\n[*] Example: python tools/ingest_real_data.py --sample")
        return

    print("=" * 65)
    print("FEDERATED CYBER SHIELD (FCS) — REAL TELEMETRY INGESTION")
    print("=" * 65)

    print("[*] Authenticating with FCS API...")
    token = get_token()
    print("[+] Authenticated successfully.")

    if args.sample:
        records = generate_sample_flows(5)
        desc = "5 Sample Normal Traffic Flows"
    elif args.attack == "ddos":
        records = generate_ddos_attack()
        desc = "30-flow SYN Flood DDoS Attack"
    elif args.attack == "portscan":
        records = generate_portscan_attack()
        desc = "17-port TCP Reconnaissance Scan"
    elif args.file:
        records = load_file(args.file)
        desc = f"{len(records)} flows loaded from '{args.file}'"
    else:
        records = []
        desc = "Empty"

    print(f"[*] Ingesting {desc} into tenant '{args.tenant}'...")
    res = send_batch(records=records, token=token, tenant_id=args.tenant)

    print("\n" + "=" * 65)
    print("INGESTION & ML DETECTION SUMMARY:")
    print("=" * 65)
    print(f"  Status:             {res.get('status')}")
    print(f"  Records Ingested:   {res.get('records_ingested')}")
    print(f"  Incidents Created:  {res.get('incidents_created')}")

    threats = [r for r in res.get("results", []) if r.get("is_threat")]
    if threats:
        print(f"\n[!] THREAT DETECTED ({len(threats)} flagged records):")
        for t in threats[:5]:
            print(f"    - Event {t['event_id']}: Attack='{t['attack_category']}', Severity={t['severity']}, Risk={t['composite_risk']:.3f}, Incident Created={t['incident_created']}")
        if len(threats) > 5:
            print(f"    ... and {len(threats) - 5} more threats.")
    else:
        print("\n[+] No malicious threats detected in this batch (Benign/Normal traffic).")

    print("\n[✓] Telemetry live in dashboard: http://127.0.0.1:5173")


if __name__ == "__main__":
    main()


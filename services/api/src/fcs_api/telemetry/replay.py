"""Synthetic flow replay coordinator and scenario generator."""

import uuid
from datetime import UTC, datetime
from typing import Any

from .ingest import TelemetryIngestionPipeline


class ReplayCoordinator:
    """Manages reproducible demonstration traffic replays."""

    _active_scenario: str | None = None
    _replayed_count: int = 0
    _last_run_at: str | None = None

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        """Return status of synthetic replay coordinator."""
        return {
            "active_scenario": cls._active_scenario,
            "replayed_count": cls._replayed_count,
            "last_run_at": cls._last_run_at,
            "supported_scenarios": ["normal", "suspicious", "scanning", "mixed"],
        }

    @classmethod
    def run_scenario(
        cls,
        scenario: str,
        tenant_id: str = "rural-isp-alpha",
        pipeline: TelemetryIngestionPipeline | None = None,
    ) -> dict[str, Any]:
        """Execute a deterministic demonstration scenario."""
        pipe = pipeline or TelemetryIngestionPipeline()
        cls._active_scenario = scenario
        cls._last_run_at = datetime.now(UTC).isoformat()
        records: list[dict[str, Any]] = []

        now_str = datetime.now(UTC).isoformat()

        if scenario == "normal":
            # Normal HTTP, DNS, TLS traffic
            for i in range(25):
                records.append({
                    "event_id": f"flow_norm_{uuid.uuid4().hex[:10]}",
                    "tenant_id": tenant_id,
                    "exporter_id": "exp-alpha-core1",
                    "src_ip": f"192.168.1.{10 + (i % 15)}",
                    "dst_ip": "1.1.1.1" if i % 2 == 0 else "8.8.8.8",
                    "src_port": 40000 + i,
                    "dst_port": 443 if i % 2 == 0 else 53,
                    "protocol": "TCP" if i % 2 == 0 else "UDP",
                    "protocol_num": 6 if i % 2 == 0 else 17,
                    "byte_count": 850 + (i * 20),
                    "packet_count": 8 + (i % 4),
                    "flow_duration_ms": 320.0 + (i * 10),
                    "tcp_flags": 24,  # PSH-ACK
                    "event_time": now_str,
                })

        elif scenario in ("suspicious", "ddos"):
            # Volumetric DDoS burst against web service
            target_ip = "198.51.100.88"
            for i in range(40):
                records.append({
                    "event_id": f"flow_ddos_{uuid.uuid4().hex[:10]}",
                    "tenant_id": tenant_id,
                    "exporter_id": "exp-alpha-core1",
                    "src_ip": f"203.0.113.{50 + (i % 30)}",
                    "dst_ip": target_ip,
                    "src_port": 50000 + i,
                    "dst_port": 443,
                    "protocol": "TCP",
                    "protocol_num": 6,
                    "byte_count": 45_000 + (i * 1500),
                    "packet_count": 350 + (i * 10),
                    "flow_duration_ms": 450.0,
                    "tcp_flags": 16,  # ACK flood
                    "event_time": now_str,
                })

        elif scenario == "scanning":
            # SYN Port scanning from single malicious scanner
            scanner_ip = "198.51.100.199"
            target_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 1433, 3306, 3389, 5432, 8080, 8443]
            for i, p in enumerate(target_ports):
                records.append({
                    "event_id": f"flow_scan_{uuid.uuid4().hex[:10]}",
                    "tenant_id": tenant_id,
                    "exporter_id": "exp-alpha-edge2",
                    "src_ip": scanner_ip,
                    "dst_ip": "10.10.1.100",
                    "src_port": 61000 + i,
                    "dst_port": p,
                    "protocol": "TCP",
                    "protocol_num": 6,
                    "byte_count": 64,
                    "packet_count": 1,
                    "flow_duration_ms": 12.0,
                    "tcp_flags": 2,  # TCP SYN
                    "event_time": now_str,
                })

        else:  # Mixed
            # Normal + Suspicious
            norm_res = cls.run_scenario("normal", tenant_id, pipe)
            ddos_res = cls.run_scenario("suspicious", tenant_id, pipe)
            return {
                "scenario": "mixed",
                "processed_count": norm_res["processed_count"] + ddos_res["processed_count"],
                "incidents_created": norm_res["incidents_created"] + ddos_res["incidents_created"],
            }

        results = pipe.ingest_batch(records)
        cls._replayed_count += len(records)
        incidents_created = sum(1 for r in results if r.get("incident_created"))

        return {
            "scenario": scenario,
            "tenant_id": tenant_id,
            "replayed_flows": len(records),
            "processed_count": len(results),
            "incidents_created": incidents_created,
            "replayed_at": now_str,
        }

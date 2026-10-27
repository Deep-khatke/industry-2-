"""Durable event-time feature windowing engine."""

import json
import math
from datetime import UTC, datetime
from typing import Any

from ..database import get_db


class FeatureWindowEngine:
    """
    Assigns events to 30-second event-time windows, aggregates flow statistics,
    enforces 60-second allowed lateness, suppresses duplicates, and produces
    14-feature deployable vectors for ML inference.
    """

    def __init__(
        self,
        window_duration_seconds: float = 30.0,
        allowed_lateness_seconds: float = 60.0,
    ) -> None:
        self.window_duration = window_duration_seconds
        self.allowed_lateness = allowed_lateness_seconds

    def parse_event_time(self, event_time_str: str) -> datetime:
        """Parse ISO timestamp with fallback to current time."""
        try:
            return datetime.fromisoformat(event_time_str)
        except Exception:
            return datetime.now(UTC)

    def compute_window_bounds(self, event_dt: datetime) -> tuple[datetime, datetime, str]:
        """Compute window start, window end, and window ID based on event time."""
        ts = event_dt.timestamp()
        w_start_ts = math.floor(ts / self.window_duration) * self.window_duration
        w_end_ts = w_start_ts + self.window_duration
        w_start = datetime.fromtimestamp(w_start_ts, tz=UTC)
        w_end = datetime.fromtimestamp(w_end_ts, tz=UTC)
        window_id = f"w_{int(w_start_ts)}_{int(w_end_ts)}"
        return w_start, w_end, window_id

    def process_flow_event(self, flow: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a normalized FlowEvent record:
        1. Parse event time.
        2. Check allowed lateness.
        3. Insert flow_event record into database with duplicate suppression.
        4. Update or create the corresponding feature window.
        """
        tenant_id = flow.get("tenant_id", "rural-isp-alpha")
        event_id = flow.get("event_id")
        event_time_str = flow.get("event_time", datetime.now(UTC).isoformat())
        event_dt = self.parse_event_time(event_time_str)
        now_dt = datetime.now(UTC)

        # Lateness check: if event_time is older than (now - allowed_lateness)
        is_late = (now_dt - event_dt).total_seconds() > self.allowed_lateness
        if is_late:
            # Beyond allowed lateness: track as dropped / stale
            return None

        w_start, w_end, window_id_base = self.compute_window_bounds(event_dt)
        window_id = f"{tenant_id}_{window_id_base}"

        # Extract numerical flow attributes
        in_bytes = float(flow.get("byte_count") or flow.get("IN_BYTES") or 0.0)
        out_bytes = float(flow.get("OUT_BYTES") or 0.0)
        in_pkts = float(flow.get("packet_count") or flow.get("IN_PKTS") or 1.0)
        out_pkts = float(flow.get("OUT_PKTS") or 0.0)
        duration_ms = float(flow.get("flow_duration_ms") or flow.get("FLOW_DURATION_MILLISECONDS") or 100.0)
        src_port = int(flow.get("src_port") or flow.get("L4_SRC_PORT") or 0)
        dst_port = int(flow.get("dst_port") or flow.get("L4_DST_PORT") or 0)
        protocol = int(flow.get("protocol_num") or flow.get("PROTOCOL") or 6)
        tcp_flags = int(flow.get("tcp_flags") or flow.get("TCP_FLAGS") or 0)

        with get_db() as conn:
            # 1. Store raw flow event with duplicate avoidance (event_id primary key)
            conn.execute(
                """
                INSERT OR IGNORE INTO flow_events (
                    event_id, tenant_id, exporter_id, observation_domain, sequence,
                    event_time, ingest_time, protocol, src_port, dst_port,
                    byte_count, packet_count, flow_duration_ms, tcp_flags, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    tenant_id,
                    flow.get("exporter_id", "exp-default"),
                    flow.get("observation_domain", 0),
                    flow.get("sequence", 0),
                    event_time_str,
                    now_dt.isoformat(),
                    str(flow.get("protocol", "TCP")),
                    src_port,
                    dst_port,
                    int(in_bytes + out_bytes),
                    int(in_pkts + out_pkts),
                    duration_ms,
                    tcp_flags,
                    json.dumps(flow),
                ),
            )

            # 2. Update or create feature window
            existing = conn.execute(
                "SELECT * FROM feature_windows WHERE window_id = ?",
                (window_id,),
            ).fetchone()

            if existing:
                flow_count = existing["flow_count"] + 1
                byte_sum = existing["byte_sum"] + int(in_bytes + out_bytes)
                packet_sum = existing["packet_sum"] + int(in_pkts + out_pkts)
                avg_dur = ((existing["avg_duration_ms"] * existing["flow_count"]) + duration_ms) / flow_count
                features = json.loads(existing["feature_vector_json"])
                features["IN_BYTES"] = byte_sum
                features["OUT_BYTES"] = features.get("OUT_BYTES", 0) + int(out_bytes)
                features["IN_PKTS"] = packet_sum
                features["FLOW_DURATION_MILLISECONDS"] = avg_dur
                features["L4_SRC_PORT"] = src_port
                features["L4_DST_PORT"] = dst_port
                features["PROTOCOL"] = protocol
                features["TCP_FLAGS"] = tcp_flags

                conn.execute(
                    """
                    UPDATE feature_windows
                    SET flow_count = ?, byte_sum = ?, packet_sum = ?, avg_duration_ms = ?,
                        feature_vector_json = ?
                    WHERE window_id = ?
                    """,
                    (flow_count, byte_sum, packet_sum, avg_dur, json.dumps(features), window_id),
                )
            else:
                flow_count = 1
                byte_sum = int(in_bytes + out_bytes)
                packet_sum = int(in_pkts + out_pkts)
                avg_dur = duration_ms

                # Construct 14 deployable features vector
                features = {
                    "L4_SRC_PORT": src_port,
                    "L4_DST_PORT": dst_port,
                    "PROTOCOL": protocol,
                    "L7_PROTO": int(flow.get("L7_PROTO", 0)),
                    "IN_BYTES": byte_sum,
                    "OUT_BYTES": int(out_bytes),
                    "IN_PKTS": packet_sum,
                    "OUT_PKTS": int(out_pkts),
                    "FLOW_DURATION_MILLISECONDS": avg_dur,
                    "TCP_FLAGS": tcp_flags,
                    "CLIENT_TCP_FLAGS": int(flow.get("CLIENT_TCP_FLAGS", tcp_flags)),
                    "SERVER_TCP_FLAGS": int(flow.get("SERVER_TCP_FLAGS", 0)),
                    "DURATION_IN": float(flow.get("DURATION_IN", avg_dur / 2)),
                    "DURATION_OUT": float(flow.get("DURATION_OUT", avg_dur / 2)),
                }

                conn.execute(
                    """
                    INSERT INTO feature_windows (
                        window_id, tenant_id, window_start, window_end,
                        flow_count, byte_sum, packet_sum, avg_duration_ms,
                        feature_vector_json, is_complete, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        window_id,
                        tenant_id,
                        w_start.isoformat(),
                        w_end.isoformat(),
                        flow_count,
                        byte_sum,
                        packet_sum,
                        avg_dur,
                        json.dumps(features),
                        1,
                        now_dt.isoformat(),
                    ),
                )

        return {
            "window_id": window_id,
            "tenant_id": tenant_id,
            "flow_count": flow_count,
            "feature_vector": features,
            "window_start": w_start.isoformat(),
            "window_end": w_end.isoformat(),
        }

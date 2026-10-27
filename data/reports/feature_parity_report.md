# FCS-UDIP Feature Parity Matrix Report
**Architecture Baseline:** Federated Cyber Shield v1.2
**Canonical Benchmark Specification:** `fcs-netflow-v2-43-research` (43 features)
**Production Deployable Specification:** `fcs-deployable-flowevent-v1` (11 features)

---

## 1. Feature Parity Executive Summary
| Availability Status | Feature Count | Proportion | Interpretation |
|---|---|---|---|
| **DIRECTLY_AVAILABLE** | 7 | 16.3% | Natively captured in Phase 1 FlowEvent v1 |
| **DERIVABLE_WITH_VERIFIED_TRANSFORM** | 4 | 9.3% | Accurately computed from duration & bytes/packets |
| **REQUIRES_ADDITIONAL_EXPORT_FIELDS** | 28 | 65.1% | Requires router IPFIX template additions (Phase 4) |
| **UNAVAILABLE** | 4 | 9.3% | Payload deep inspection fields absent from router NetFlow |

---

## 2. Canonical 43 NetFlow v2 Feature Inventory
| Canonical Feature | Data Type | Unit | Production Status | FlowEvent v1 Mapping |
|---|---|---|---|---|
| `IPV4_SRC_ADDR` | `string` | `ip_address` | `DERIVABLE_WITH_VERIFIED_TRANSFORM` | `src_prefix_masked` |
| `IPV4_DST_ADDR` | `string` | `ip_address` | `DERIVABLE_WITH_VERIFIED_TRANSFORM` | `dst_prefix_masked` |
| `L4_SRC_PORT` | `int64` | `port_number` | `DIRECTLY_AVAILABLE` | `src_port` |
| `L4_DST_PORT` | `int64` | `port_number` | `DIRECTLY_AVAILABLE` | `dst_port` |
| `PROTOCOL` | `int64` | `protocol_id` | `DIRECTLY_AVAILABLE` | `protocol` |
| `L7_PROTO` | `float32` | `proto_id` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `IN_BYTES` | `int64` | `bytes` | `DIRECTLY_AVAILABLE` | `byte_count` |
| `OUT_BYTES` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `IN_PKTS` | `int64` | `packets` | `DIRECTLY_AVAILABLE` | `packet_count` |
| `OUT_PKTS` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `FLOW_DURATION_MILLISECONDS` | `int64` | `milliseconds` | `DIRECTLY_AVAILABLE` | `flow_duration_ms` |
| `TCP_FLAGS` | `int64` | `flags_mask` | `DIRECTLY_AVAILABLE` | `tcp_flags` |
| `CLIENT_TCP_FLAGS` | `int64` | `flags_mask` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `SERVER_TCP_FLAGS` | `int64` | `flags_mask` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `DURATION_IN` | `int64` | `milliseconds` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `DURATION_OUT` | `int64` | `milliseconds` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `MIN_TTL` | `int64` | `hops` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `MAX_TTL` | `int64` | `hops` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `LONGEST_FLOW_PKT` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `SHORTEST_FLOW_PKT` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `MIN_IP_PKT_LEN` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `MAX_IP_PKT_LEN` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `SRC_TO_DST_SECOND_BYTES` | `float32` | `bytes_per_sec` | `DERIVABLE_WITH_VERIFIED_TRANSFORM` | `byte_count / (flow_duration_ms / 1000)` |
| `DST_TO_SRC_SECOND_BYTES` | `float32` | `bytes_per_sec` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `RETRANSMITTED_IN_BYTES` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `RETRANSMITTED_IN_PKTS` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `RETRANSMITTED_OUT_BYTES` | `int64` | `bytes` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `RETRANSMITTED_OUT_PKTS` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `SRC_TO_DST_AVG_THROUGHPUT` | `float32` | `bps` | `DERIVABLE_WITH_VERIFIED_TRANSFORM` | `(byte_count * 8) / (flow_duration_ms / 1000)` |
| `DST_TO_SRC_AVG_THROUGHPUT` | `float32` | `bps` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `NUM_PKTS_UP_TO_128_BYTES` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `NUM_PKTS_128_TO_256_BYTES` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `NUM_PKTS_256_TO_512_BYTES` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `NUM_PKTS_512_TO_1024_BYTES` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `NUM_PKTS_1024_TO_1514_BYTES` | `int64` | `packets` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `TCP_WIN_MAX_IN` | `int64` | `window_size` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `TCP_WIN_MAX_OUT` | `int64` | `window_size` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `ICMP_TYPE` | `int64` | `icmp_encoded` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `ICMP_IPV4_TYPE` | `int64` | `icmp_type` | `REQUIRES_ADDITIONAL_EXPORT_FIELDS` | `*None (Unavailable)*` |
| `DNS_QUERY_ID` | `int64` | `query_id` | `UNAVAILABLE` | `*None (Unavailable)*` |
| `DNS_QUERY_TYPE` | `int64` | `query_type` | `UNAVAILABLE` | `*None (Unavailable)*` |
| `DNS_TTL_ANSWER` | `int64` | `seconds` | `UNAVAILABLE` | `*None (Unavailable)*` |
| `FTP_COMMAND_RET_CODE` | `float32` | `status_code` | `UNAVAILABLE` | `*None (Unavailable)*` |


---

## 3. Strict Boundary Rules
1. **Unavailable Features Excluded from Deployable View:** Features marked `REQUIRES_ADDITIONAL_EXPORT_FIELDS` or `UNAVAILABLE` must NEVER silently enter the deployable ML feature set.
2. **Privacy Protection:** Raw `IPV4_SRC_ADDR` and `IPV4_DST_ADDR` are strictly masked to `/24` network prefixes matching Phase 1 privacy rules.
3. **No Target Leakage:** Labels (`Label`, `Attack`) and metadata (`dataset_source`, `tenant_id`) are excluded from predictive inputs.

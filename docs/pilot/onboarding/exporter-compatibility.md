# Exporter Compatibility & Feature Parity Engineering Guide

## 1. Overview
FCS Phase 9 interfaces with router and firewall telemetry exporters using RFC 7011 (IPFIX) and RFC 3954 (NetFlow v9). To guarantee detection accuracy without introducing hallucinated or imputed values, the system enforces a strict **Zero-Imputation Policy**: if an exporter does not furnish a field required by a specific specialist detector, that specialist is cleanly decoupled while remaining models continue uninterrupted.

## 2. Supported Exporter Profiles
| Vendor | Family | Protocol | Default Port | Sampling | Tested Firmware |
|---|---|---|---|---|---|
| Cisco | ASR 1000 / ISR 4000 | IPFIX / NetFlow v9 | UDP 2055 | 1:1 or 1:N ASIC | IOS-XE 17.x |
| Juniper | MX Series (MX204/MX480) | IPFIX (J-Flow) | UDP 2055 | Inline Hardware | JunOS 21.x |
| MikroTik | CCR2004 / CCR2116 | NetFlow v9 / IPFIX | UDP 2055 | Software 1:1-1:1000 | RouterOS v7.x |
| Linux | softflowd / ipt_NETFLOW | IPFIX / NetFlow v9 | UDP 2055 | Kernel netfilter | Kernel 6.x |
| Huawei | NetEngine 8000 | IPFIX (NetStream) | UDP 2055 | Hardware sampling | VRP 8.x |
| VyOS | VyOS 1.4 / 1.5 SAGITTA | IPFIX (pmacct) | UDP 2055 | Software sampling | VyOS 1.4 |
| pfSense | pfSense Plus / CE | NetFlow v9 | UDP 2055 | FreeBSD bpf | pfSense 24.x |

## 3. Required NetFlow / IPFIX Information Elements
The following 10 canonical fields form the minimum deployable foundation:
1. `sourceIPv4Address` (IE 8) &rarr; `src_ip`
2. `destinationIPv4Address` (IE 12) &rarr; `dst_ip`
3. `sourceTransportPort` (IE 7) &rarr; `src_port`
4. `destinationTransportPort` (IE 11) &rarr; `dst_port`
5. `protocolIdentifier` (IE 4) &rarr; `protocol`
6. `octetDeltaCount` (IE 1) &rarr; `IN_BYTES`
7. `packetDeltaCount` (IE 2) &rarr; `IN_PKTS`
8. `tcpControlBits` (IE 6) &rarr; `TCP_FLAGS`
9. `flowStartMilliseconds` (IE 152) &rarr; `flow_start_ms`
10. `flowEndMilliseconds` (IE 153) &rarr; `flow_end_ms`

## 4. Derived Features & Imputation Invariants
- `FLOW_DURATION_MILLISECONDS = flow_end_ms - flow_start_ms`
- `SRC_TO_DST_AVG_THROUGHPUT = (IN_BYTES * 8) / (FLOW_DURATION_MILLISECONDS / 1000)`
- **Zero Imputation Invariant:** If `tcpControlBits` is omitted by the router, `syn_flood_specialist` is disabled. The feature vector is never zero-filled with false flags.
- **Sampling Correction:** When 1-in-N sampling is active (e.g. 1:10), packet and byte counts are scaled by $N$ for volume-based volumetric detectors.

## 5. Sequence Gap & Drift Handling
The collector tracks exporter sequence numbers per Observation Domain ID. If a sequence gap $\Delta > 0$ is detected, a degraded warning is logged. If sequence jumps backwards, exporter restart / reboot recovery is automatically triggered.

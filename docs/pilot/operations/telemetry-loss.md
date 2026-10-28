# Telemetry Loss, Intermittent Link & Degradation Runbook

## 1. Context
Rural ISP networks frequently experience upstream carrier flapping, wireless backhaul fading, and router exporter reboots. FCS is engineered to maintain detection continuity and recover backlogs gracefully under these conditions.

## 2. Operational Thresholds
- **Loss 0% - 1%:** Nominal rural operating conditions. Jitter buffer absorbs packet reordering.
- **Loss 1% - 5%:** Degraded conditions. Volumetric scaling adjusted; detection sensitivity remains $> 90\%$.
- **Loss > 5% - 15%:** Stress state. Alert banner displayed on SOC dashboard; optional specialists disabled; system alerts NOC of upstream backhaul degradation.
- **Stream Lag > 90 seconds:** Exporter marked `OFFLINE`. Sequence tracking frozen pending reconnect.

## 3. Exporter Reboot Recovery
When a router restarts, its flow export sequence number drops to 1.
1. The collector detects a backward sequence transition.
2. The sequence tracker realigns without throwing an unhandled exception.
3. Buffered flow records are committed to the outbox for replay reconciliation.

# ISP Pilot Decommissioning & Data Handling Plan

## 1. Overview
Upon pilot completion, expiration of observation agreements, or at the request of a participating ISP, the decommissioning protocol must be executed cleanly without leaving residual data or orphaned telemetry listeners.

## 2. Decommissioning Procedure
1. **Transition Pilot State:**
   Update onboarding status to `PILOT_CLOSED` via API:
   ```bash
   python -c "
   from fcs_pilot.onboarding.state_machine import OnboardingStateMachine
   from fcs_pilot.onboarding.models import OnboardingStatus
   sm = OnboardingStateMachine()
   sm.transition_state('pilot-001', OnboardingStatus.PILOT_CLOSED, 'admin', 'PLATFORM_ADMIN', 'Decommissioning complete')
   "
   ```
2. **Cease Telemetry Ingestion:**
   De-register exporter bindings in `TenantRegistry` to drop incoming NetFlow packets on arrival.
3. **Purge Ephemeral Telemetry:**
   Trigger automated deletion worker for raw flows ($t > 0$) and intermediate feature windows.
4. **Archive Cryptographic Audit Evidence:**
   Preserve immutable action journal and differential privacy receipts for legal compliance without retaining unmasked subscriber IP records.
5. **Issue Formal Data Destruction Certificate:**
   Provide participating ISP with cryptographic hash receipt verifying telemetry deletion.

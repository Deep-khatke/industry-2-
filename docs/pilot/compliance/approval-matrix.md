# Role & Action Approval Matrix

## 1. Role-Based Access Control (RBAC) Tiers
- `READ_ONLY`: Observational access to dashboards and incident lists.
- `SECURITY_ANALYST`: Incident investigation, evidence analysis, disposition feedback submission, and action recommendation.
- `SECURITY_RESPONDER`: Approval and simulated execution of defensive actions (temporary block / rate limit).
- `TENANT_ADMIN`: ISP tenant onboarding, exporter configuration, network scope definition, and response policy adjustments.
- `PLATFORM_ADMIN`: Global platform administration, readiness gate approval, emergency kill-switch activation.

## 2. Permission Matrix
| Operation | READ_ONLY | SECURITY_ANALYST | SECURITY_RESPONDER | TENANT_ADMIN | PLATFORM_ADMIN |
|---|:---:|:---:|:---:|:---:|:---:|
| View Incident Queue | &check; | &check; | &check; | &check; | &check; |
| Submit Triage Feedback | &cross; | &check; | &check; | &check; | &check; |
| Recommend Manual Action | &cross; | &check; | &check; | &check; | &check; |
| Approve Simulated Action | &cross; | &cross; | &check; | &check; | &check; |
| Rollback Active Rule | &cross; | &cross; | &check; | &check; | &check; |
| Update Onboarding State | &cross; | &cross; | &cross; | &check; | &check; |
| Activate Emergency Stop | &cross; | &cross; | &cross; | &check; | &check; |
| Modify Protected IP List | &cross; | &cross; | &cross; | &cross; | &check; |

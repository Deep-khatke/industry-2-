# Federated Cyber Shield (FCS) v1.2 — Future AWS Deployment Procedure

> [!WARNING]
> **CRITICAL ZERO-COST NOTICE: DO NOT EXECUTE WITHOUT APPROVED FUNDING**
> This procedure describes how to provision the production AWS environment in a future phase once dedicated cloud funding has been allocated.
> **Automated agents and developers must NOT execute this procedure during Phase 1.**
> All real cloud provisioning remains `BLOCKED_BY_ZERO_COST_POLICY`.

---

## 1. Prerequisites (For Future Funded Phase)
1. Approved cloud budget and authorized AWS master account.
2. AWS Organizations configured with dedicated accounts per tenant.
3. AWS CLI v2 and OpenTofu v1.8+ installed on a secure administrative bastion.
4. Pre-configured S3 backend with DynamoDB state locking (prohibited in Phase 1).

---

## 2. Step-by-Step Production Provisioning (Manual Execution)

### Step 2.1 — Configure Remote OpenTofu State Backend
Create `backend.tf` in `infrastructure/opentofu/environments/prod/`:
```hcl
terraform {
  backend "s3" {
    bucket         = "fcs-tf-state-secure-prod"
    key            = "fcs/prod/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "fcs-tf-state-locks"
    encrypt        = true
  }
}
```

### Step 2.2 — Initialize OpenTofu with Remote Backend
```bash
cd infrastructure/opentofu/environments/prod
tofu init
```

### Step 2.3 — Run Production Plan Inspection
```bash
tofu plan -out=tfplan.binary
# Perform four-eyes peer review on security groups, KMS policies, and IAM roles
```

### Step 2.4 — Execute Controlled Provisioning
```bash
tofu apply tfplan.binary
```

### Step 2.5 — Verify Ingress NLB & Kinesis Pipeline
1. Verify NLB DNS endpoint resolution:
   ```bash
   dig +short fcs-telemetry-nlb-prod.<region>.elb.amazonaws.com
   ```
2. Verify KMS encryption on S3 archive and Kinesis stream:
   ```bash
   aws kinesis describe-stream --stream-name fcs-telemetry-stream-prod
   ```
3. Deploy containerized `TelemetryCollector` task to private subnets using AWS ECS or EKS.

---

## 3. Rollback Procedure
If ingestion fails or configuration drift occurs:
```bash
tofu destroy -target=module.ingress
```

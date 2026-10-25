# CloudWatch Log Group for Security Audit & Ingestion Trails
resource "aws_cloudwatch_log_group" "security_audit_log_group" {
  name              = "/fcs/security/audit-trail-${var.environment}"
  retention_in_days = var.retention_days
  kms_key_id        = var.kms_key_arn

  tags = {
    Environment = var.environment
    Service     = "SecurityLogging"
    ManagedBy   = "OpenTofu"
  }
}

resource "aws_cloudwatch_log_group" "collector_application_logs" {
  name              = "/fcs/services/telemetry-collector-${var.environment}"
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn

  tags = {
    Environment = var.environment
    Service     = "CollectorApp"
  }
}

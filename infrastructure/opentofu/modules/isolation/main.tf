# Dedicated KMS Customer Managed Key per tenant to enforce cryptographic boundary
resource "aws_kms_key" "tenant_key" {
  for_each                = toset(var.tenant_ids)
  description             = "Dedicated cryptographic boundary KMS key for ${each.key} telemetry"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "fcs-kms-${each.key}-${var.environment}"
    TenantId    = each.key
    Environment = var.environment
    ManagedBy   = "OpenTofu"
  }
}

resource "aws_kms_alias" "tenant_key_alias" {
  for_each      = toset(var.tenant_ids)
  name          = "alias/fcs-${each.key}-${var.environment}"
  target_key_id = aws_kms_key.tenant_key[each.key].key_id
}

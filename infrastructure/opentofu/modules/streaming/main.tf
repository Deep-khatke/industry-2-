resource "aws_kinesis_stream" "telemetry_stream" {
  name             = "${var.stream_name}-${var.environment}"
  shard_count      = var.shard_count
  retention_period = var.retention_period_hours

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded"
  ]

  # Enforce encryption at rest
  encryption_type = "KMS"
  kms_key_id      = var.kms_key_arn != null ? var.kms_key_arn : "alias/aws/kinesis"

  tags = {
    Name        = "${var.stream_name}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "OpenTofu"
  }
}

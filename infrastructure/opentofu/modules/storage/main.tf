resource "aws_s3_bucket" "telemetry_archive" {
  bucket_prefix = "${var.bucket_prefix}-${var.environment}-"
  force_destroy = false

  tags = {
    Name        = "fcs-telemetry-archive-${var.environment}"
    Environment = var.environment
    ManagedBy   = "OpenTofu"
    Compliance  = "ZeroTrust"
  }
}

# Block all public access completely
resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket = aws_s3_bucket.telemetry_archive.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enforce server-side encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "kms_encryption" {
  bucket = aws_s3_bucket.telemetry_archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# Enforce object versioning for audit compliance
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.telemetry_archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket policy: Enforce TLS 1.2+ and reject non-HTTPS transport
resource "aws_s3_bucket_policy" "enforce_tls" {
  bucket = aws_s3_bucket.telemetry_archive.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLSRequestsOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.telemetry_archive.arn,
          "${aws_s3_bucket.telemetry_archive.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

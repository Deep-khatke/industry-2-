# AWS Provider Configuration for Definition-Only Offline Validation
# ZERO-COST POLICY: All credential checks and metadata API requests are bypassed
# so offline validation passes without an active AWS account or network access.

provider "aws" {
  region                      = var.aws_region
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  default_tags {
    tags = {
      Project     = "FederatedCyberShield"
      Environment = var.environment
      Phase       = "Phase1Foundation"
      ManagedBy   = "OpenTofu"
    }
  }
}

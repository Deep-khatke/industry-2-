terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOTE: Backend intentionally omitted or local for zero-cost Phase 1
  # Cloud backend prohibited during Phase 1
}

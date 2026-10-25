terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "ap-south-1"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}

module "single_tenant_isolation" {
  source      = "../../modules/isolation"
  environment = "example"
  tenant_ids  = ["tenant-isp-alpha"]
}

module "single_tenant_networking" {
  source      = "../../modules/networking"
  environment = "example"
}

output "example_tenant_kms_key" {
  value = module.single_tenant_isolation.tenant_kms_key_arns["tenant-isp-alpha"]
}

output "example_vpc_id" {
  value = module.single_tenant_networking.vpc_id
}

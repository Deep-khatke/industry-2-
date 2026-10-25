# FCS Phase 1 Architecture: Dev Environment Infrastructure Definition

module "isolation" {
  source      = "../../modules/isolation"
  environment = var.environment
  tenant_ids  = var.tenant_ids
}

module "networking" {
  source      = "../../modules/networking"
  environment = var.environment
}

module "storage" {
  source         = "../../modules/storage"
  environment    = var.environment
  kms_key_arn    = module.isolation.tenant_kms_key_arns["tenant-isp-alpha"]
  retention_days = 90
}

module "streaming" {
  source                 = "../../modules/streaming"
  environment            = var.environment
  kms_key_arn            = module.isolation.tenant_kms_key_arns["tenant-isp-alpha"]
  shard_count            = 2
  retention_period_hours = 24
}

module "ingress" {
  source            = "../../modules/ingress"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  telemetry_port    = 2055
}

module "iam" {
  source             = "../../modules/iam"
  environment        = var.environment
  kinesis_stream_arn = module.streaming.stream_arn
  s3_bucket_arn      = module.storage.bucket_arn
  kms_key_arns       = values(module.isolation.tenant_kms_key_arns)
}

module "monitoring" {
  source              = "../../modules/monitoring"
  environment         = var.environment
  kinesis_stream_name = module.streaming.stream_name
}

module "logging" {
  source         = "../../modules/logging"
  environment    = var.environment
  kms_key_arn    = module.isolation.tenant_kms_key_arns["tenant-isp-alpha"]
  retention_days = 90
}

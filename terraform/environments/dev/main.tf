terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = local.region
  default_tags {
    tags = local.tags
  }
}

module "vpc" {
  source      = "../../modules/vpc"
  prefix      = local.prefix
  names       = local.names
  tags        = local.tags
}

module "s3" {
  source     = "../../modules/s3"
  prefix     = local.prefix
  names      = local.names
  account_id = local.account_id
  tags       = local.tags
}

module "iam" {
  source        = "../../modules/iam"
  prefix        = local.prefix
  names         = local.names
  s3_bucket_arn = module.s3.bucket_arn
  tags          = local.tags
}

module "rds" {
  source             = "../../modules/rds"
  prefix             = local.prefix
  names              = local.names
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  app_security_group = module.vpc.app_security_group_id
  rds_security_group = module.vpc.rds_security_group_id
  tags               = local.tags
}

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
  source             = "../../modules/vpc"
  prefix             = local.prefix
  names              = local.names
  tags               = local.tags
  enable_nat_gateway = !var.cost_conscious_mode
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

module "ecs" {
  count                 = var.cost_conscious_mode ? 0 : 1
  source                = "../../modules/ecs"
  prefix                = local.prefix
  names                 = local.names
  tags                  = local.tags
  region                = local.region
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  private_subnet_ids    = module.vpc.private_subnet_ids
  app_security_group_id = module.vpc.app_security_group_id
  execution_role_arn    = module.iam.ecs_task_execution_role_arn
  task_role_arn         = module.iam.ecs_task_role_arn
  db_host               = module.rds.db_endpoint
  db_secret_arn         = module.rds.db_secret_arn
}

module "frontend" {
  source       = "../../modules/frontend"
  prefix       = local.prefix
  account_id   = local.account_id
  tags         = local.tags
  alb_dns_name = var.cost_conscious_mode ? "dummy.example.com" : module.ecs[0].alb_dns_name
}

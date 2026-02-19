data "aws_caller_identity" "current" {}

locals {
  project     = "mri"
  environment = "dev"
  prefix      = "mri-dev"
  region      = "ap-south-1"
  account_id  = data.aws_caller_identity.current.account_id

  names = {
    vpc                = "mri-dev-vpc"
    igw                = "mri-dev-igw"
    nat                = "mri-dev-nat"
    nat_eip            = "mri-dev-nat-eip"
    public_rt          = "mri-dev-public-rt"
    private_rt         = "mri-dev-private-rt"
    app_sg             = "mri-dev-app-sg"
    rds_sg             = "mri-dev-rds-sg"
    rds_instance       = "mri-dev-db"
    rds_subnet_group   = "mri-dev-db-subnet-group"
    db_secret          = "mri-dev-db-credentials"
    s3_outputs         = "mri-dev-outputs"
    iam_execution_role = "mri-dev-ecs-execution-role"
    iam_task_role      = "mri-dev-ecs-task-role"
    ecs_cluster        = "mri-dev-cluster"
    ecr_repo           = "mri-dev-quant-engine"
    log_group          = "/mri/dev/quant-engine"
  }

  tags = {
    Project     = "mri"
    Environment = "dev"
    ManagedBy   = "terraform"
    Owner       = "edwardjsi"
  }
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.db_endpoint
}

output "s3_bucket_name" {
  description = "S3 output bucket name"
  value       = module.s3.bucket_name
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for DB credentials"
  value       = module.rds.db_secret_arn
}

output "iam_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = module.iam.ecs_task_execution_role_arn
}

output "iam_task_role_arn" {
  description = "ECS task role ARN"
  value       = module.iam.ecs_task_role_arn
}

output "bastion_id" {
  description = "EC2 Bastion Host ID"
  value       = module.vpc.bastion_id
}

# --- ECS Outputs ---
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = var.cost_conscious_mode ? null : module.ecs[0].ecr_repository_url
}

output "alb_dns_name" {
  description = "ALB DNS name for API access"
  value       = var.cost_conscious_mode ? null : module.ecs[0].alb_dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = var.cost_conscious_mode ? null : module.ecs[0].ecs_cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = var.cost_conscious_mode ? null : module.ecs[0].ecs_service_name
}

# --- Frontend Outputs ---
output "cloudfront_domain" {
  description = "CloudFront URL for the frontend"
  value       = module.frontend.cloudfront_domain
}

output "frontend_bucket_name" {
  description = "S3 bucket for frontend static files"
  value       = module.frontend.frontend_bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.frontend.cloudfront_distribution_id
}

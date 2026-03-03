variable "prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "names" {
  description = "Map of resource names"
  type        = map(string)
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "app_security_group_id" {
  description = "Application security group ID"
  type        = string
}

variable "execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "db_host" {
  description = "RDS endpoint hostname"
  type        = string
}

variable "db_secret_arn" {
  description = "Secrets Manager ARN for DB credentials"
  type        = string
}

variable "ses_sender_email" {
  description = "SES verified sender email"
  type        = string
  default     = "edwardjsi@gmail.com"
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}

variable "alb_dns_name" {
  description = "ALB DNS name for API proxy origin"
  type        = string
}

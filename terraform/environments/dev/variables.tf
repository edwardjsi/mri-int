variable "cost_conscious_mode" {
  type        = bool
  default     = true
  description = "If true, skips creating expensive resources like NAT Gateway and ECS"
}
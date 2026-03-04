variable "prefix" {
  type = string
}

variable "names" {
  type = map(string)
}

variable "tags" {
  type = map(string)
}

variable "enable_nat_gateway" {
  description = "Whether to create a NAT gateway for private subnets to access the internet"
  type        = bool
  default     = true
}

variable "prefix" {
  type = string
}

variable "names" {
  type = map(string)
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "app_security_group" {
  type = string
}

variable "tags" {
  type = map(string)
}

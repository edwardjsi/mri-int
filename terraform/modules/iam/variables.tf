variable "prefix" {
  type = string
}

variable "names" {
  type = map(string)
}

variable "s3_bucket_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}

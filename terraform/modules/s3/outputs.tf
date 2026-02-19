output "bucket_name" {
  value = aws_s3_bucket.outputs.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.outputs.arn
}

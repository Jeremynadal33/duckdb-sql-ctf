output "db_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.ctf.endpoint
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.ctf.db_name
}

output "s3_bucket_name" {
  description = "CTF S3 bucket name"
  value       = aws_s3_bucket.ctf.bucket
}

output "iam_user_name" {
  description = "IAM user name"
  value       = aws_iam_user.ctf.name
}

output "iam_role_arn" {
  description = "IAM role ARN for S3 access"
  value       = aws_iam_role.ctf_s3_access.arn
}

output "iam_access_key_id" {
  description = "IAM user access key ID"
  value       = aws_iam_access_key.ctf.id
}

output "iam_secret_access_key" {
  description = "IAM user secret access key"
  value       = aws_iam_access_key.ctf.secret
  sensitive   = true
}

# Could use [managed password](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance#master_user_secret-1)
# To avoid having to use an env var to input the password
output "pg_user" {
  description = "PostgreSQL master username"
  value       = var.pg_user
}

output "pg_password" {
  description = "PostgreSQL master password"
  value       = var.pg_password
  sensitive   = true
}

output "pg_ro_user" {
  description = "PostgreSQL read-only username"
  value       = postgresql_role.readonly.name
}

output "pg_ro_password" {
  description = "PostgreSQL read-only password"
  value       = postgresql_role.readonly.password
  sensitive   = true
}

output "cloudfront_leaderboard_url" {
  description = "CloudFront URL for leaderboard results"
  value       = "https://${aws_cloudfront_distribution.leaderboard.domain_name}"
}


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

output "pg_user" {
  description = "PostgreSQL master username"
  value       = var.pg_user
}

output "pg_ro_user" {
  description = "PostgreSQL read-only username"
  value       = postgresql_role.readonly.name
}

output "ssm_pg_master_password" {
  description = "Chemin SSM du mot de passe master PostgreSQL"
  value       = aws_ssm_parameter.pg_master_password.name
}

output "ssm_pg_readonly_password" {
  description = "Chemin SSM du mot de passe read-only PostgreSQL"
  value       = aws_ssm_parameter.pg_readonly_password.name
}

output "s3_results_url" {
  description = "S3 URL for leaderboard results (for DuckDB httpfs)"
  value       = "s3://${aws_s3_bucket.ctf.bucket}/leaderboard/results"
}


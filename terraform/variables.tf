variable "pg_user" {
  description = "PostgreSQL master username"
  type        = string
}

variable "pg_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "pg_ro_user" {
  description = "PostgreSQL read-only username"
  type        = string
}

variable "pg_ro_password" {
  description = "PostgreSQL read-only password"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "bucket_name" {
  description = "S3 bucket name for CTF data"
  type        = string
  default     = "duckdb-sql-ctf"
}

variable "pg_user" {
  description = "PostgreSQL master username"
  type        = string
  default     = "ctfadmin"
}

variable "pg_ro_user" {
  description = "PostgreSQL read-only username"
  type        = string
  default     = "ctfplayer"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "bucket_name" {
  description = "S3 bucket name for CTF data"
  type        = string
  default     = "duckdb-sql-ctf-test"
}

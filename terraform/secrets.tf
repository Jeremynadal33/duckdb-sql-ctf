# ── Génération des mots de passe PostgreSQL ──────────────────────────────────

resource "random_password" "pg_master" {
  length           = 24
  special          = true
  override_special = "!#$%&*-_=+"
}

resource "random_password" "pg_readonly" {
  length           = 24
  special          = true
  override_special = "!#$%&*-_=+"
}

# ── Stockage dans SSM Parameter Store ────────────────────────────────────────

resource "aws_ssm_parameter" "pg_master_username" {
  name  = "/${var.bucket_name}/pg/master/username"
  type  = "String"
  value = var.pg_user

  tags = { Name = "${var.bucket_name}-pg-master-username" }
}

resource "aws_ssm_parameter" "pg_master_password" {
  name  = "/${var.bucket_name}/pg/master/password"
  type  = "SecureString"
  value = random_password.pg_master.result

  tags = { Name = "${var.bucket_name}-pg-master-password" }
}

resource "aws_ssm_parameter" "pg_readonly_username" {
  name  = "/${var.bucket_name}/pg/readonly/username"
  type  = "String"
  value = var.pg_ro_user

  tags = { Name = "${var.bucket_name}-pg-readonly-username" }
}

resource "aws_ssm_parameter" "pg_readonly_password" {
  name  = "/${var.bucket_name}/pg/readonly/password"
  type  = "SecureString"
  value = random_password.pg_readonly.result

  tags = { Name = "${var.bucket_name}-pg-readonly-password" }
}

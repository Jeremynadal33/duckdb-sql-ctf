resource "aws_db_subnet_group" "ctf" {
  name       = "ctf-db-subnet-group"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  tags = { Name = "ctf-db-subnet-group" }
}

resource "aws_db_instance" "ctf" {
  identifier     = "ctf-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = local.dbname
  username = var.pg_user
  password = random_password.pg_master.result

  db_subnet_group_name   = aws_db_subnet_group.ctf.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = true
  skip_final_snapshot    = true

  tags = { Name = "ctf-db" }
}

## PostgreSQL configuration for read-only user
resource "postgresql_role" "readonly" {
  name     = var.pg_ro_user
  login    = true
  password = random_password.pg_readonly.result

  depends_on = [
    aws_db_instance.ctf,
    aws_route_table_association.a,
    aws_route_table_association.b,
    aws_security_group.db,
  ]
}

# Not entirely understood why this works but only a grant did not work
resource "postgresql_grant" "readonly_table_permissions" {
  database    = local.dbname
  role        = postgresql_role.readonly.name
  schema      = "public"
  object_type = "table"
  objects     = []
  privileges  = ["SELECT"]

  depends_on = [
    postgresql_role.readonly
  ]
}

resource "postgresql_default_privileges" "read_only_tables" {
  database = local.dbname
  role     = postgresql_role.readonly.name
  schema   = "public"

  owner       = var.pg_user
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [
    postgresql_role.readonly,
    postgresql_grant.readonly_table_permissions
  ]
}
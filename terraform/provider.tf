terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.25"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket = "bg-lab-dev-tfstates-bucket"
    key    = "duckdb-sql-ctf/terraform.tfstate"
    region = "eu-west-1"
  }
}

provider "postgresql" {
  host      = aws_db_instance.ctf.address
  port      = aws_db_instance.ctf.port
  database  = aws_db_instance.ctf.db_name
  username  = var.pg_user
  password  = random_password.pg_master.result
  sslmode   = "require"
  superuser = false
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      "bg:owners"  = "p.farey@betclicgroup.com"
      "bg:project" = "duckdb-sql-ctf"
    }
  }
}

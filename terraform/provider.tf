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
  }

  backend "s3" {
    bucket = "ippon-data-dev-tfstates-bucket"
    key    = "duckdb-sql-ctf/terraform.tfstate"
    region = "eu-west-1"
  }
}

provider "postgresql" {
  host      = aws_db_instance.ctf.address
  port      = aws_db_instance.ctf.port
  database  = aws_db_instance.ctf.db_name
  username  = var.pg_user
  password  = var.pg_password
  sslmode   = "require"
  superuser = false
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      "ippon:owners"  = "jnadal@ippon.fr"
      "ippon:project" = "duckdb-sql-ctf"
    }
  }
}

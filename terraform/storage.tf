resource "aws_s3_bucket" "ctf" {
  bucket = var.bucket_name

  tags = { Name = var.bucket_name }
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "ctf" {
  bucket = aws_s3_bucket.ctf.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

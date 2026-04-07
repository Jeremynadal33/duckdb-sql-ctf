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
  block_public_policy     = false # Allow public-read policy on results prefix
  ignore_public_acls      = true
  restrict_public_buckets = false # Allow public access to results prefix
}

# ── CORS for browser-based DuckDB-WASM httpfs access ──
resource "aws_s3_bucket_cors_configuration" "ctf" {
  bucket = aws_s3_bucket.ctf.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag", "Content-Range", "Content-Length", "Accept-Ranges"]
    max_age_seconds = 3600
  }
}

# ── Public read-only access restricted to leaderboard/results/ ──
resource "aws_s3_bucket_policy" "public_results" {
  bucket = aws_s3_bucket.ctf.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadCtfEvents"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*"
      },
      {
        Sid       = "PublicListCtfEvents"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.ctf.arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["leaderboard/ctf-events/*"]
          }
        }
      }
    ]
  })
}

# ── Answer files for the Lambda checker ──
resource "aws_s3_object" "answer_scenario_1" {
  bucket  = aws_s3_bucket.ctf.id
  key     = "leaderboard/answers/scenario_1.txt"
  content = local.flag_scenario1
}

resource "aws_s3_object" "answer_scenario_2" {
  bucket  = aws_s3_bucket.ctf.id
  key     = "leaderboard/answers/scenario_2.txt"
  content = local.flag_scenario2
}

resource "aws_s3_object" "answer_scenario_3" {
  bucket  = aws_s3_bucket.ctf.id
  key     = "leaderboard/answers/scenario_3.txt"
  content = local.flag_scenario3
}

resource "aws_s3_object" "answer_scenario_4" {
  bucket  = aws_s3_bucket.ctf.id
  key     = "leaderboard/answers/scenario_4.txt"
  content = local.flag_scenario4
}

resource "aws_s3_bucket_notification" "user_inputs" {
  bucket = aws_s3_bucket.ctf.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.answer_checker.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "user-inputs/"
    filter_suffix       = ".parquet"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

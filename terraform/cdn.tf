# ── CloudFront distribution for public read access to leaderboard results ──

resource "aws_cloudfront_origin_access_control" "s3_results" {
  name                              = "duckdb-sql-ctf-results-oac"
  description                       = "OAC for leaderboard results"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "leaderboard" {
  enabled         = true
  comment         = "Public access to CTF leaderboard results"
  is_ipv6_enabled = true
  price_class     = "PriceClass_100" # US + Europe only (cheapest)

  origin {
    domain_name              = aws_s3_bucket.ctf.bucket_regional_domain_name
    origin_id                = "s3-results"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3_results.id
    origin_path              = "/leaderboard/results"
  }

  default_cache_behavior {
    target_origin_id       = "s3-results"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      headers      = ["Origin", "Access-Control-Request-Method", "Access-Control-Request-Headers"]

      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 60
    max_ttl     = 300

    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Name = "duckdb-sql-ctf-leaderboard" }
}

resource "aws_cloudfront_response_headers_policy" "cors" {
  name    = "duckdb-sql-ctf-cors-policy"
  comment = "CORS for GitHub Pages leaderboard"

  cors_config {
    access_control_allow_credentials = false

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET", "HEAD"]
    }

    access_control_allow_origins {
      items = ["*"]
    }

    access_control_max_age_sec = 3600
    origin_override            = true
  }
}

# ── S3 bucket policy to allow CloudFront OAC access to results ──

resource "aws_s3_bucket_policy" "cloudfront_access" {
  bucket = aws_s3_bucket.ctf.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontReadResults"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.ctf.arn}/leaderboard/results/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.leaderboard.arn
          }
        }
      },
      {
        Sid       = "AllowCloudFrontListResults"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.ctf.arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["leaderboard/results/*"]
          }
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.leaderboard.arn
          }
        }
      }
    ]
  })
}

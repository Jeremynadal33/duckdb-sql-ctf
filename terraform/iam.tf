resource "aws_iam_user" "ctf" {
  name = var.bucket_name

  tags = { Name = var.bucket_name }
}

resource "aws_iam_role" "ctf_s3_access" {
  name = "${var.bucket_name}-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::721665305066:root" }
        Action    = "sts:AssumeRole"
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::721665305066:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_*"
          }
        }
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-s3-access" }
}

resource "aws_iam_policy" "ctf_s3" {
  name        = "${var.bucket_name}-s3-policy"
  description = "Read-only on s3://${var.bucket_name}/data/*, read-write on s3://${var.bucket_name}/user-inputs/*"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.ctf.arn
      },
      {
        Sid      = "ReadData"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.ctf.arn}/data/*"
      },
      {
        Sid    = "ReadWriteUserInputs"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.ctf.arn}/user-inputs/*"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-s3-policy" }
}

resource "aws_iam_role_policy_attachment" "ctf_s3" {
  role       = aws_iam_role.ctf_s3_access.name
  policy_arn = aws_iam_policy.ctf_s3.arn
}

resource "aws_iam_user_policy_attachment" "ctf_s3" {
  user       = aws_iam_user.ctf.name
  policy_arn = aws_iam_policy.ctf_s3.arn
}

resource "aws_iam_access_key" "ctf" {
  user = aws_iam_user.ctf.name
}

# ──────────────────────────────────────────────
# Lambda Answer Checker
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_answer_checker" {
  name = "${var.bucket_name}-lambda-answer-checker"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-answer-checker" }
}

resource "aws_iam_policy" "lambda_answer_checker_s3" {
  name        = "${var.bucket_name}-lambda-answer-checker-s3"
  description = "S3 access for answer checker Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.ctf.arn
      },
      {
        Sid    = "ReadUserInputsAndEvents"
        Effect = "Allow"
        Action = "s3:GetObject"
        Resource = [
          "${aws_s3_bucket.ctf.arn}/user-inputs/*",
          "${aws_s3_bucket.ctf.arn}/leaderboard/answers/*",
          "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*",
        ]
      },
      {
        Sid      = "WriteCtfEvents"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-answer-checker-s3" }
}

resource "aws_iam_role_policy_attachment" "lambda_answer_checker_s3" {
  role       = aws_iam_role.lambda_answer_checker.name
  policy_arn = aws_iam_policy.lambda_answer_checker_s3.arn
}

resource "aws_iam_role_policy_attachment" "lambda_answer_checker_logs" {
  role       = aws_iam_role.lambda_answer_checker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ──────────────────────────────────────────────
# Lambda Pseudo Register
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_pseudo_register" {
  name = "${var.bucket_name}-lambda-pseudo-register"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-pseudo-register" }
}

resource "aws_iam_policy" "lambda_pseudo_register_s3" {
  name        = "${var.bucket_name}-lambda-pseudo-register-s3"
  description = "S3 access for pseudo registration Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.ctf.arn
      },
      {
        Sid    = "ReadWriteCtfEvents"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
        ]
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-pseudo-register-s3" }
}

resource "aws_iam_role_policy_attachment" "lambda_pseudo_register_s3" {
  role       = aws_iam_role.lambda_pseudo_register.name
  policy_arn = aws_iam_policy.lambda_pseudo_register_s3.arn
}

resource "aws_iam_role_policy_attachment" "lambda_pseudo_register_logs" {
  role       = aws_iam_role.lambda_pseudo_register.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ──────────────────────────────────────────────
# Lambda Mission Control
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_mission_control" {
  name = "${var.bucket_name}-lambda-mission-control"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-mission-control" }
}

resource "aws_iam_policy" "lambda_mission_control_s3" {
  name        = "${var.bucket_name}-lambda-mission-control-s3"
  description = "S3 access for mission control Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.ctf.arn
      },
      {
        Sid      = "WriteCtfEvents"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-mission-control-s3" }
}

resource "aws_iam_role_policy_attachment" "lambda_mission_control_s3" {
  role       = aws_iam_role.lambda_mission_control.name
  policy_arn = aws_iam_policy.lambda_mission_control_s3.arn
}

resource "aws_iam_role_policy_attachment" "lambda_mission_control_logs" {
  role       = aws_iam_role.lambda_mission_control.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ──────────────────────────────────────────────
# Lambda Hint Event
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_hint_event" {
  name = "${var.bucket_name}-lambda-hint-event"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-hint-event" }
}

resource "aws_iam_policy" "lambda_hint_event_s3" {
  name        = "${var.bucket_name}-lambda-hint-event-s3"
  description = "S3 access for hint event Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.ctf.arn
      },
      {
        Sid      = "WriteCtfEvents"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-hint-event-s3" }
}

resource "aws_iam_role_policy_attachment" "lambda_hint_event_s3" {
  role       = aws_iam_role.lambda_hint_event.name
  policy_arn = aws_iam_policy.lambda_hint_event_s3.arn
}

resource "aws_iam_role_policy_attachment" "lambda_hint_event_logs" {
  role       = aws_iam_role.lambda_hint_event.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ──────────────────────────────────────────────
# Lambda Compactor
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_compactor" {
  name = "${var.bucket_name}-lambda-compactor"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-compactor" }
}

resource "aws_iam_policy" "lambda_compactor_s3" {
  name        = "${var.bucket_name}-lambda-compactor-s3"
  description = "S3 access for the leaderboard compactor Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListCtfEvents"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.ctf.arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["leaderboard/ctf-events/*"]
          }
        }
      },
      {
        Sid      = "ReadCtfEvents"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/ctf-events/*"
      },
      {
        Sid      = "WriteSnapshot"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/snapshot.parquet"
      },
      {
        Sid    = "ManageTmpSnapshot"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "${aws_s3_bucket.ctf.arn}/leaderboard/snapshot.tmp.*.parquet"
      }
    ]
  })

  tags = { Name = "${var.bucket_name}-lambda-compactor-s3" }
}

resource "aws_iam_role_policy_attachment" "lambda_compactor_s3" {
  role       = aws_iam_role.lambda_compactor.name
  policy_arn = aws_iam_policy.lambda_compactor_s3.arn
}

resource "aws_iam_role_policy_attachment" "lambda_compactor_logs" {
  role       = aws_iam_role.lambda_compactor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

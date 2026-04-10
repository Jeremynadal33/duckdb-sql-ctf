resource "null_resource" "answer_checker_build" {
  triggers = {
    src_hash   = local.answer_checker_hash
    dockerfile = filesha1("${path.module}/../answer_checker/Dockerfile")
    pyproject  = filesha1("${path.module}/../answer_checker/pyproject.toml")
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.answer_checker.repository_url}
      docker build -t ${aws_ecr_repository.answer_checker.repository_url}:${local.answer_checker_hash} ${path.module}/../answer_checker
      docker push ${aws_ecr_repository.answer_checker.repository_url}:${local.answer_checker_hash}
    EOT
  }
}

resource "aws_cloudwatch_log_group" "answer_checker" {
  name              = "/aws/lambda/${var.bucket_name}-answer-checker"
  retention_in_days = 14

  tags = { Name = "${var.bucket_name}-answer-checker" }
}

resource "aws_lambda_function" "answer_checker" {
  function_name = "${var.bucket_name}-answer-checker"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.answer_checker.repository_url}:${local.answer_checker_hash}"
  role          = aws_iam_role.lambda_answer_checker.arn
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
    }
  }

  architectures = ["arm64"]

  depends_on = [
    null_resource.answer_checker_build,
    aws_cloudwatch_log_group.answer_checker,
  ]

  tags = { Name = "${var.bucket_name}-answer-checker" }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.answer_checker.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.ctf.arn
}

# ── Pseudo registration Lambda ──

resource "aws_cloudwatch_log_group" "pseudo_register" {
  name              = "/aws/lambda/${var.bucket_name}-pseudo-register"
  retention_in_days = 14

  tags = { Name = "${var.bucket_name}-pseudo-register" }
}

resource "aws_lambda_function" "pseudo_register" {
  function_name = "${var.bucket_name}-pseudo-register"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.answer_checker.repository_url}:${local.answer_checker_hash}"
  role          = aws_iam_role.lambda_pseudo_register.arn
  timeout       = 30
  memory_size   = 512

  image_config {
    command = ["answer_checker.register.register_handler"]
  }

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
    }
  }

  architectures = ["arm64"]

  depends_on = [
    null_resource.answer_checker_build,
    aws_cloudwatch_log_group.pseudo_register,
  ]

  tags = { Name = "${var.bucket_name}-pseudo-register" }
}

resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pseudo_register.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.pseudo.execution_arn}/*/*"
}

# ── Hint event Lambda ──

resource "aws_cloudwatch_log_group" "hint_event" {
  name              = "/aws/lambda/${var.bucket_name}-hint-event"
  retention_in_days = 14

  tags = { Name = "${var.bucket_name}-hint-event" }
}

resource "aws_lambda_function" "hint_event" {
  function_name = "${var.bucket_name}-hint-event"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.answer_checker.repository_url}:${local.answer_checker_hash}"
  role          = aws_iam_role.lambda_hint_event.arn
  timeout       = 30
  memory_size   = 512

  image_config {
    command = ["answer_checker.hint_event.hint_event_handler"]
  }

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
    }
  }

  architectures = ["arm64"]

  depends_on = [
    null_resource.answer_checker_build,
    aws_cloudwatch_log_group.hint_event,
  ]

  tags = { Name = "${var.bucket_name}-hint-event" }
}

resource "aws_lambda_permission" "allow_apigw_hint_event" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.hint_event.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.pseudo.execution_arn}/*/*"
}

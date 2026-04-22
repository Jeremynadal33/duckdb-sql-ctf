# ── HTTP API for pseudo registration ──

resource "aws_apigatewayv2_api" "pseudo" {
  name          = "${var.bucket_name}-pseudo-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 3600
  }

  tags = { Name = "${var.bucket_name}-pseudo-api" }
}

resource "aws_apigatewayv2_stage" "pseudo" {
  api_id      = aws_apigatewayv2_api.pseudo.id
  name        = "$default"
  auto_deploy = true

  tags = { Name = "${var.bucket_name}-pseudo-api-default" }
}

resource "aws_apigatewayv2_integration" "pseudo_register" {
  api_id                 = aws_apigatewayv2_api.pseudo.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.pseudo_register.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "pseudo_register" {
  api_id    = aws_apigatewayv2_api.pseudo.id
  route_key = "POST /register"
  target    = "integrations/${aws_apigatewayv2_integration.pseudo_register.id}"
}

# ── Mission control route ──

resource "aws_apigatewayv2_integration" "mission_control" {
  api_id                 = aws_apigatewayv2_api.pseudo.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.mission_control.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "mission_control" {
  api_id    = aws_apigatewayv2_api.pseudo.id
  route_key = "POST /mission-control"
  target    = "integrations/${aws_apigatewayv2_integration.mission_control.id}"
}

# ── Hint event route ──

resource "aws_apigatewayv2_integration" "hint_event" {
  api_id                 = aws_apigatewayv2_api.pseudo.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.hint_event.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "hint_event" {
  api_id    = aws_apigatewayv2_api.pseudo.id
  route_key = "POST /hint-event"
  target    = "integrations/${aws_apigatewayv2_integration.hint_event.id}"
}

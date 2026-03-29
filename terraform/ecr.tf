resource "aws_ecr_repository" "answer_checker" {
  name                 = "${var.bucket_name}-answer-checker"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = { Name = "${var.bucket_name}-answer-checker" }
}
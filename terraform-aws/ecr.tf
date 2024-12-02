resource "aws_ecr_repository" "ecg_inference" {
  name = local.ecr_docker_ecg_inference_name

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "ecg_inference_policy" {
  repository = aws_ecr_repository.ecg_inference.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1,
        description  = "Keep last 10 images",
        selection    = {
          tagStatus    = "any"
          countType    = "imageCountMoreThan"
          countNumber  = 5
        }
        action       = {
          type = "expire"
        }
      }
    ]
  })
}

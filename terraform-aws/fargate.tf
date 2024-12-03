resource "aws_ecs_cluster" "fargate_cluster" {
  name = local.fargate_cluster_name
}


resource "aws_vpc" "fargate_cluster_main_vpc" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "fargate_cluster_public_subnet" {
  count                   = 2
  vpc_id                  = aws_vpc.fargate_cluster_main_vpc.id
  cidr_block              = cidrsubnet(aws_vpc.fargate_cluster_main_vpc.cidr_block, 8, count.index)
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "fargate_igw" {
  vpc_id = aws_vpc.fargate_cluster_main_vpc.id
}

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.fargate_cluster_main_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.fargate_igw.id
  }
}

resource "aws_route_table_association" "public_route_assoc" {
  count          = 2
  subnet_id      = aws_subnet.fargate_cluster_public_subnet[count.index].id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_security_group" "fargate_sg" {
  vpc_id = aws_vpc.fargate_cluster_main_vpc.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = local.fargate_task_execution_role

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "ecs_task_execution_policy" {
  name = "${local.fargate_task_execution_role}-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:BatchGetImage"
        ],
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "${aws_cloudwatch_log_group.ecs_inference_log_group.arn}:log-stream:*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "logs:DescribeLogGroups"
        ],
        Resource = "*"
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "task_execution_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_task_execution_policy.arn
}


resource "aws_iam_role" "ecs_task_role" {
  name = "${local.fargate_ecg_task_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}


resource "aws_iam_policy" "ecs_task_policy" {
  name = "${local.fargate_ecg_task_name}-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:ListStreams"
        ],
        Resource = aws_kinesis_stream.ecg_aggregated_chunks_data.arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ],
        Resource = aws_dynamodb_table.ecg_abnormality_detection_results_table.arn
      }
    ]
  })
}



resource "aws_iam_role_policy_attachment" "task_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}


resource "aws_ecs_task_definition" "fargate_task" {
  family                   = local.fargate_ecg_task_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  cpu                      = "512"
  memory                   = "1024"

  container_definitions = jsonencode([
    {
      name      = local.fargate_task_container_name
      image     = local.fargate_task_image_uri
      essential = true
      environment = [
        { name = "STREAM_NAME", value = local.kinesis_ecg_chunks_stream_name },
        { name = "SHARD_ID", value = local.kinesis_shard_id_name },
        { name = "AWS_REGION", value = var.region },

      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_inference_log_group.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecg-inference"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "fargate_service" {
  name            = local.fargate_service_name
  cluster         = aws_ecs_cluster.fargate_cluster.id
  task_definition = aws_ecs_task_definition.fargate_task.arn
  desired_count   = 1 # Ensure only one task is running for single Kinesis shard
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.fargate_cluster_public_subnet[*].id
    security_groups = [aws_security_group.fargate_sg.id]
    assign_public_ip = true
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
}


resource "aws_cloudwatch_log_group" "ecs_inference_log_group" {
  name              = "/ecs/ecg-processing"
  retention_in_days = 3
}

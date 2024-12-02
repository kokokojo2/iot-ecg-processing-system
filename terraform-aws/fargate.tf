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

resource "aws_iam_policy_attachment" "ecs_task_execution_policy" {
  name       = "${local.fargate_task_execution_role}-policy"
  roles      = [aws_iam_role.ecs_task_execution_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}


resource "aws_ecs_task_definition" "fargate_task" {
  family                   = "ecg-fargate-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  cpu                      = "512"
  memory                   = "1024"

  container_definitions = jsonencode([
    {
      name      = local.fargate_task_container_name
      image     = local.fargate_task_image_uri
      essential = true
      environment = [
        { name = "KINESIS_STREAM", value = local.kinesis_ecg_chunks_stream_name },
        { name = "AWS_REGION", value = "eu-central-1" },
        # will be provided by lambda aggregation func
        { name = "SEQUENCE_NUMBER", value = "" },
        { name = "SHARD_ID", value = "" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ecg-inference"
          awslogs-region        = "eu-central-1"
          awslogs-stream-prefix = "ecg-inference"
        }
      }
    }
  ])
}

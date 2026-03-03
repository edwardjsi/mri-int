# --- ECR Repository ---
resource "aws_ecr_repository" "api" {
  name                 = var.names["ecr_repo"]
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# --- ECS Cluster ---
resource "aws_ecs_cluster" "main" {
  name = var.names["ecs_cluster"]

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# --- CloudWatch Log Group ---
resource "aws_cloudwatch_log_group" "api" {
  name              = var.names["log_group"]
  retention_in_days = 30
  tags              = var.tags
}

# --- ALB Security Group ---
resource "aws_security_group" "alb" {
  name        = "${var.prefix}-alb-sg"
  description = "Security group for API load balancer"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.prefix}-alb-sg"
  })
}

# Allow ALB to reach ECS tasks on port 8000
resource "aws_security_group_rule" "app_from_alb" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = var.app_security_group_id
  source_security_group_id = aws_security_group.alb.id
}

# --- Application Load Balancer ---
resource "aws_lb" "api" {
  name               = "${var.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.prefix}-alb"
  })
}

resource "aws_lb_target_group" "api" {
  name        = "${var.prefix}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/api/health"
    matcher             = "200"
  }

  tags = var.tags
}

resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# --- ECS Task Definition ---
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.prefix}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "DB_HOST", value = var.db_host },
      { name = "DB_PORT", value = "5432" },
      { name = "DB_NAME", value = "mri_db" },
      { name = "AWS_REGION", value = var.region },
      { name = "SES_SENDER_EMAIL", value = var.ses_sender_email },
    ]

    secrets = [
      { name = "DB_USER", valueFrom = "${var.db_secret_arn}:username::" },
      { name = "DB_PASSWORD", valueFrom = "${var.db_secret_arn}:password::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.names["log_group"]
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])

  tags = var.tags
}

# --- ECS Service ---
resource "aws_ecs_service" "api" {
  name            = "${var.prefix}-api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.api]

  tags = var.tags
}

# ============================================================
# DAILY PIPELINE — EventBridge Scheduled ECS Task
# Runs at 4PM IST (10:30 UTC) Mon-Fri
# ============================================================

# --- Pipeline Task Definition (heavier resources for data processing) ---
resource "aws_ecs_task_definition" "pipeline" {
  family                   = "${var.prefix}-pipeline"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "pipeline"
    image     = "${aws_ecr_repository.api.repository_url}:latest"
    essential = true

    command = ["python", "scripts/pipeline.py"]

    environment = [
      { name = "DB_HOST", value = var.db_host },
      { name = "DB_PORT", value = "5432" },
      { name = "DB_NAME", value = "mri_db" },
      { name = "AWS_REGION", value = var.region },
      { name = "SES_SENDER_EMAIL", value = var.ses_sender_email },
      { name = "PYTHONPATH", value = "/app" },
    ]

    secrets = [
      { name = "DB_USER", valueFrom = "${var.db_secret_arn}:username::" },
      { name = "DB_PASSWORD", valueFrom = "${var.db_secret_arn}:password::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.names["log_group"]
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "pipeline"
      }
    }
  }])

  tags = var.tags
}

# --- IAM Role for EventBridge to run ECS tasks ---
resource "aws_iam_role" "eventbridge_ecs" {
  name = "${var.prefix}-eventbridge-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "eventbridge_ecs_run" {
  name = "${var.prefix}-eventbridge-run-task"
  role = aws_iam_role.eventbridge_ecs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = aws_ecs_task_definition.pipeline.arn
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [var.execution_role_arn, var.task_role_arn]
      }
    ]
  })
}

# --- EventBridge Rule: 4PM IST Mon-Fri (10:30 UTC) ---
resource "aws_cloudwatch_event_rule" "daily_pipeline" {
  name                = "${var.prefix}-daily-pipeline"
  description         = "Run MRI daily pipeline at 4PM IST Mon-Fri"
  schedule_expression = "cron(30 10 ? * MON-FRI *)"
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "pipeline" {
  rule     = aws_cloudwatch_event_rule.daily_pipeline.name
  arn      = aws_ecs_cluster.main.arn
  role_arn = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.pipeline.arn
    task_count          = 1
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.app_security_group_id]
      assign_public_ip = false
    }
  }
}

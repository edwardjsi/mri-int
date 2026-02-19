resource "random_password" "db" {
  length  = 16
  special = false

  lifecycle {
    ignore_changes = [result]
  }
}

resource "aws_secretsmanager_secret" "db" {
  name                    = var.names["db_secret"]
  recovery_window_in_days = 0

  tags = merge(var.tags, {
    Name = var.names["db_secret"]
  })

  lifecycle {
    ignore_changes = [name]
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = "mri_admin"
    password = random_password.db.result
    dbname   = "mri_db"
    host     = aws_db_instance.main.address
    port     = 5432
  })
}

resource "aws_db_subnet_group" "main" {
  name       = var.names["rds_subnet_group"]
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = var.names["rds_subnet_group"]
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "main" {
  identifier        = var.names["rds_instance"]
  engine            = "postgres"
  engine_version    = "15.15"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "mri_db"
  username = "mri_admin"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_security_group]

  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
  publicly_accessible     = false
  apply_immediately       = true

  tags = merge(var.tags, {
    Name = var.names["rds_instance"]
  })

  lifecycle {
    ignore_changes = [password]
  }
}

# A database of its own rather than a second schema on teim-apps. It also keeps the subscriber list.

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "press" {
  name       = local.name
  subnet_ids = local.private_subnet_ids
}

resource "aws_db_instance" "press" {
  identifier     = local.name
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "cedar_press"
  username = "cedar_press"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.press.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period   = var.environment == "prod" ? 7 : 1
  deletion_protection       = var.environment == "prod"
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.name}-final" : null
  apply_immediately         = var.environment != "prod"

  lifecycle {
    ignore_changes = [password]
  }

  tags = { Name = local.name }
}

resource "aws_security_group" "app" {
  name_prefix = "${local.name}-app-"
  description = "Cedar Press API host"
  vpc_id      = local.vpc_id

  # Outbound reaches ECR, SSM, and the Cedar ALB. The Cedar ALB's own security
  # group (in the cedar repo) must allow this group on port 80.
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = { Name = "${local.name}-app-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "api" {
  for_each = toset(var.api_ingress_security_group_ids)

  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  description                  = "API from ${each.value}"
}

resource "aws_security_group" "db" {
  name_prefix = "${local.name}-db-"
  description = "Cedar Press database: PostgreSQL from the API host only"
  vpc_id      = local.vpc_id

  ingress {
    description     = "PostgreSQL from the Cedar Press API host"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = { Name = "${local.name}-db-sg" }
}

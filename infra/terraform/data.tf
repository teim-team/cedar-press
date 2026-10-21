data "aws_caller_identity" "current" {}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_vpc" "teim" {
  filter {
    name   = "tag:Name"
    values = ["teim-${var.environment}"]
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.teim.id]
  }
  filter {
    name   = "tag:Name"
    values = ["teim-${var.environment}-private", "teim-${var.environment}-private-b"]
  }
}

data "aws_lb" "cedar" {
  count = var.cedar_alb_name == null ? 0 : 1
  name  = var.cedar_alb_name
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  # The standard image only: the "minimal" and "ecs" variants lack the SSM agent.
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  vpc_id             = data.aws_vpc.teim.id
  private_subnet_ids = sort(data.aws_subnets.private.ids)
  account_id         = data.aws_caller_identity.current.account_id
  name               = "cedar-press-${var.environment}"
}

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket       = "teim-terraform-state-714933490822"
    key          = "cedar-press/dev.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  # Stops a dev plan from ever applying to the prod account, and the reverse.
  allowed_account_ids = [var.expected_account_id]

  default_tags {
    tags = {
      Project     = "cedar-press"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

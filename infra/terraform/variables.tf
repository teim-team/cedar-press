variable "environment" {
  type        = string
  description = "dev or prod. Selects the teim-<env> VPC."

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod."
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "expected_account_id" {
  type        = string
  description = "The only AWS account this stack may be applied to."
}

variable "github_repo" {
  type    = string
  default = "teim-team/cedar-press"
}

variable "app_instance_type" {
  type    = string
  default = "t3.small"
}

variable "app_ami_id" {
  type        = string
  default     = null
  description = "Pin an AMI."
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_engine_version" {
  type    = string
  default = "18.3"
}

variable "press_environment" {
  type        = string
  description = "CEDAR_PRESS_ENVIRONMENT"
  default     = "production"

  validation {
    condition     = contains(["staging", "production"], var.press_environment)
    error_message = "press_environment must be staging or production."
  }
}

variable "press_origins" {
  type        = list(string)
  default     = []
  description = "allowed to send credentialed requests (CEDAR_PRESS_ORIGINS)."
}

variable "proxy_hops" {
  type        = number
  default     = 1
  description = "trusted proxies that append to X-Forwarded-For (CEDAR_PRESS_PROXY_HOPS)."
}

variable "cedar_alb_name" {
  type        = string
  default     = null
  description = "internal Cedar ALB to call: Null leaves Cedar disabled for Press."
}

variable "api_ingress_security_group_ids" {
  type        = list(string)
  default     = []
  description = "sgs allowed to reach the API on port 8000. Empty means SSM port-forward only."
}

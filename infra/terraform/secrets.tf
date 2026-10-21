resource "random_password" "session_secret" {
  length  = 64
  special = false
}

locals {
  prefix = "/cedar-press/${var.environment}"
  cedar_enabled = var.cedar_alb_name != null
  cedar_base    = local.cedar_enabled ? "http://${data.aws_lb.cedar[0].dns_name}" : ""

  plain_config = {
    CEDAR_PRESS_ENVIRONMENT = var.press_environment
    CEDAR_PRESS_TRUST_PROXY = "1"
    CEDAR_PRESS_PROXY_HOPS  = tostring(var.proxy_hops)
    CEDAR_PRESS_ORIGINS     = join(",", var.press_origins)
    CEDAR_ENABLED           = tostring(local.cedar_enabled)
    CEDAR_BASE_URL          = local.cedar_base
  }
}

# unset means absent for SSM 
resource "aws_ssm_parameter" "plain" {
  for_each = { for key, value in local.plain_config : key => value if value != "" }
  name      = "${local.prefix}/${each.key}"
  type      = "String"
  value     = each.value
  overwrite = true
}

resource "aws_ssm_parameter" "database_url" {
  name = "${local.prefix}/DATABASE_URL"
  type = "SecureString"
  value = format(
    "postgresql://%s:%s@%s/%s?sslmode=require",
    aws_db_instance.press.username,
    random_password.db.result,
    aws_db_instance.press.endpoint,
    aws_db_instance.press.db_name,
  )
}

resource "aws_ssm_parameter" "session_secret" {
  name  = "${local.prefix}/CEDAR_PRESS_SECRET"
  type  = "SecureString"
  value = random_password.session_secret.result
}

# this param needs to be set by hand w/cedar dev key
resource "aws_ssm_parameter" "cedar_key" {
  name  = "${local.prefix}/CEDAR_INTERNAL_API_KEY"
  type  = "SecureString"
  value = "unset"

  lifecycle {
    ignore_changes = [value]
  }
}

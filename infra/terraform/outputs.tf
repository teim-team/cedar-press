output "instance_id" {
  value = aws_instance.app.id
}

output "private_ip" {
  value = aws_instance.app.private_ip
}

output "app_security_group_id" {
  description = "Allow this group on the Cedar ALB's security group (port 80)."
  value       = aws_security_group.app.id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "database_endpoint" {
  value = aws_db_instance.press.endpoint
}

output "ssm_prefix" {
  value = local.prefix
}

output "dev_site_url" {
  value = local.dev_site ? "https://${aws_cloudfront_distribution.dev_site[0].domain_name}" : null
}

output "dev_site_password" {
  description = "User name cedar."
  value       = local.dev_site ? random_password.dev_site[0].result : null
  sensitive   = true
}

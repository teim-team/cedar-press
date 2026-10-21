resource "aws_instance" "app" {
  ami                    = coalesce(var.app_ami_id, data.aws_ami.al2023.id)
  instance_type          = var.app_instance_type
  subnet_id              = local.private_subnet_ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e
    dnf update -y
    dnf install -y docker
    systemctl enable --now docker
    systemctl enable --now amazon-ssm-agent
    install -d -m 0755 /opt/cedar-press
  EOF

  # stateless 
  lifecycle {
    ignore_changes = [ami, user_data]
  }

  tags = { Name = "${local.name}-app" }
}

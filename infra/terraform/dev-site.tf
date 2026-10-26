# The dev site: the client build in S3 and the dev API behind one CloudFront
# address, so the client reaches the API same-origin at /api/* as it does in
# prod. A shared password covers the whole site. Prod's site is not managed here.

locals {
  dev_site = var.environment == "dev"
}

resource "random_password" "dev_site" {
  count   = local.dev_site ? 1 : 0
  length  = 24
  special = false
}

resource "aws_s3_bucket" "dev_site" {
  count  = local.dev_site ? 1 : 0
  bucket = "${local.name}-site-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "dev_site" {
  count                   = local.dev_site ? 1 : 0
  bucket                  = aws_s3_bucket.dev_site[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "dev_site" {
  count                             = local.dev_site ? 1 : 0
  name                              = "${local.name}-site"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "dev_site" {
  count  = local.dev_site ? 1 : 0
  bucket = aws_s3_bucket.dev_site[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.dev_site[0].arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.dev_site[0].arn } }
    }]
  })
}

resource "aws_cloudfront_vpc_origin" "api" {
  count = local.dev_site ? 1 : 0

  vpc_origin_endpoint_config {
    name                   = "${local.name}-api"
    arn                    = aws_instance.app.arn
    http_port              = 8000
    https_port             = 443
    origin_protocol_policy = "http-only"

    origin_ssl_protocols {
      items    = ["TLSv1.2"]
      quantity = 1
    }
  }
}

# CloudFront creates this group in the VPC when the first VPC origin deploys.
data "aws_security_group" "cloudfront_vpc_origins" {
  count      = local.dev_site ? 1 : 0
  name       = "CloudFront-VPCOrigins-Service-SG"
  vpc_id     = local.vpc_id
  depends_on = [aws_cloudfront_vpc_origin.api]
}

resource "aws_vpc_security_group_ingress_rule" "api_from_cloudfront" {
  count                        = local.dev_site ? 1 : 0
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = data.aws_security_group.cloudfront_vpc_origins[0].id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  description                  = "API from the dev site's CloudFront"
}

resource "aws_cloudfront_function" "dev_site" {
  count   = local.dev_site ? 1 : 0
  name    = "${local.name}-site"
  runtime = "cloudfront-js-2.0"
  publish = true

  # The API's routes sit at its root, so /api is removed before it. Paths with
  # no file extension are client routes and get the app shell; a blanket error
  # page would also turn API 404s into the app document.
  code = <<-EOF
    function handler(event) {
      var request = event.request;
      var auth = request.headers.authorization;
      if (!auth || auth.value !== "Basic ${base64encode("cedar:${random_password.dev_site[0].result}")}") {
        return {
          statusCode: 401,
          statusDescription: "Unauthorized",
          headers: { "www-authenticate": { value: 'Basic realm="Cedar Press dev"' } },
        };
      }
      delete request.headers.authorization;
      var uri = request.uri;
      if (uri === "/api" || uri.indexOf("/api/") === 0) {
        request.uri = uri.slice(4) || "/";
      } else if (uri.indexOf(".", uri.lastIndexOf("/")) === -1) {
        request.uri = "/index.html";
      }
      return request;
    }
  EOF
}

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_distribution" "dev_site" {
  count               = local.dev_site ? 1 : 0
  enabled             = true
  comment             = "${local.name}-site"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    origin_id                = "site"
    domain_name              = aws_s3_bucket.dev_site[0].bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.dev_site[0].id
  }

  origin {
    origin_id   = "api"
    domain_name = aws_instance.app.private_dns

    vpc_origin_config {
      vpc_origin_id = aws_cloudfront_vpc_origin.api[0].id
    }
  }

  default_cache_behavior {
    target_origin_id       = "site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.optimized.id
    compress               = true

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.dev_site[0].arn
    }
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "api"
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.dev_site[0].arn
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

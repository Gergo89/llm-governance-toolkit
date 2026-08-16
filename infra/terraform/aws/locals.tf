locals {
  name         = "${var.project}-${var.environment}"
  azs          = slice(data.aws_availability_zones.available.names, 0, 2)
  is_prod      = var.environment == "prod"
  tls_enabled  = var.domain_name != "" && var.route53_zone_id != ""
  min_capacity = local.is_prod ? 2 : 1
  max_capacity = local.is_prod ? 10 : 3

  tags = merge({
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  }, var.tags)
}


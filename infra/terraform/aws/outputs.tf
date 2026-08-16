output "application_url" {
  description = "Public application URL."
  value       = local.tls_enabled ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "ecr_repository_url" {
  description = "Repository for application images."
  value       = aws_ecr_repository.app.repository_url
}

output "assets_bucket" {
  description = "Private application assets bucket."
  value       = aws_s3_bucket.assets.id
}

output "runtime_secret_arn" {
  description = "Secrets Manager ARN injected into the application."
  value       = aws_secretsmanager_secret.runtime.arn
}

output "database_endpoint" {
  description = "Private database endpoint."
  value       = aws_db_instance.main.endpoint
}

output "redis_endpoint" {
  description = "Private Redis endpoint."
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}


project           = "app"
environment       = "prod"
aws_region        = "eu-central-1"
vpc_cidr          = "10.60.0.0/16"
desired_count     = 2
task_cpu          = 1024
task_memory       = 2048
db_instance_class = "db.t4g.medium"
redis_node_type   = "cache.t4g.small"

# Pin a tested application image by digest before applying production.
container_image   = "public.ecr.aws/docker/library/nginx:1.27-alpine"
container_port    = 80
health_check_path = "/"

# domain_name      = "app.example.com"
# route53_zone_id  = "Z0000000000000000000"
# alarm_email      = "on-call@example.com"


project           = "app"
environment       = "staging"
aws_region        = "eu-central-1"
vpc_cidr          = "10.50.0.0/16"
desired_count     = 1
task_cpu          = 512
task_memory       = 1024
db_instance_class = "db.t4g.small"
redis_node_type   = "cache.t4g.small"

container_image   = "public.ecr.aws/docker/library/nginx:1.27-alpine"
container_port    = 80
health_check_path = "/"


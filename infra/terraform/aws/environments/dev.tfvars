project           = "app"
environment       = "dev"
aws_region        = "eu-central-1"
vpc_cidr          = "10.40.0.0/16"
desired_count     = 1
task_cpu          = 512
task_memory       = 1024
db_instance_class = "db.t4g.micro"
redis_node_type   = "cache.t4g.micro"

# Replace after pushing the application image.
container_image   = "public.ecr.aws/docker/library/nginx:1.27-alpine"
container_port    = 80
health_check_path = "/"


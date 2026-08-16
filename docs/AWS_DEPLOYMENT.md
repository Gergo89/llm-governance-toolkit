# AWS Deployment Guide

This guide provides detailed instructions for deploying the AGI platform to Amazon Web Services using Terraform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Initial Setup](#initial-setup)
4. [Terraform Configuration](#terraform-configuration)
5. [Deployment Steps](#deployment-steps)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Monitoring and Alerts](#monitoring-and-alerts)
8. [Troubleshooting](#troubleshooting)
9. [Cost Optimization](#cost-optimization)

## Prerequisites

### Required Tools
- **Terraform** 1.10.5 or later
  ```bash
  terraform version
  ```
- **AWS CLI** v2
  ```bash
  aws --version
  ```
- **kubectl** v1.31.4 or later (for ECS/Kubernetes integration)
- **Docker** (optional, for building application images)

### AWS Permissions

Your AWS user or role needs permissions for:
- EC2 (VPC, Subnets, Security Groups, NAT Gateway, ALB)
- ECS (Cluster, Task Definition, Service)
- RDS (Database instance, subnet group)
- ElastiCache (Redis cluster)
- ECR (Container registry)
- S3 (State storage, logs)
- CloudWatch (Logs, metrics, alarms)
- IAM (Roles, policies)
- Secrets Manager

Create an IAM policy with these permissions or use `AdministratorAccess` for initial setup (not recommended for production).

### AWS Account Setup

1. **Create or select an AWS account**
2. **Set up AWS credentials**
   ```bash
   aws configure
   # or use environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ```
3. **Choose your AWS region** (default: eu-central-1)

## Architecture Overview

### Key Components

```
┌─────────────────────────────────────────────┐
│          Internet / ALB (Load Balancer)     │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────────────┐  ┌────▼──────────────┐
│   ECS Fargate      │  │   NAT Gateway     │
│   (Application)    │  │   (Egress)        │
└───┬────────────────┘  └────┬──────────────┘
    │                         │
    ├─────────────────────────┤
    │                         │
┌───▼──────────────┐  ┌──────▼───────────────┐
│  RDS PostgreSQL  │  │  ElastiCache Redis   │
│  (Data)          │  │  (Cache)             │
└──────────────────┘  └──────────────────────┘

Observability:
┌──────────────────────────────────────┐
│  CloudWatch Logs, Metrics, Alarms   │
│  OpenTelemetry / Prometheus Export  │
└──────────────────────────────────────┘
```

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Gergo89/llm-governance-toolkit.git
cd llm-governance-toolkit
```

### 2. Set Up Terraform State Backend (Optional)

For safe state management, create a remote backend:

```bash
cd infra/terraform/bootstrap
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Output: bucket name for backend configuration
cd ../aws
```

Store the S3 bucket name and DynamoDB table for the backend configuration.

### 3. Configure Environment Variables

```bash
# Region (default: eu-central-1)
export AWS_REGION=eu-central-1
export AWS_DEFAULT_REGION=eu-central-1

# Environment (dev, staging, prod)
export ENVIRONMENT=dev
```

## Terraform Configuration

### Backend Configuration

Create `infra/terraform/aws/backend.hcl`:

```hcl
bucket         = "your-terraform-state-bucket"
key            = "app/dev/terraform.tfstate"
region         = "eu-central-1"
encrypt        = true
dynamodb_table = "terraform-locks"
```

Or use command-line arguments:

```bash
terraform init \
  -backend-config="bucket=your-bucket" \
  -backend-config="key=app/dev/terraform.tfstate" \
  -backend-config="region=eu-central-1"
```

### Environment Variables

Update `infra/terraform/aws/environments/dev.tfvars`:

```hcl
environment             = "dev"
aws_region              = "eu-central-1"
vpc_cidr                = "10.0.0.0/16"
container_port          = 8080
container_image         = "123456789.dkr.ecr.eu-central-1.amazonaws.com/app:latest"
ecs_task_cpu            = 256
ecs_task_memory         = 512
ecs_desired_count       = 2
db_instance_class       = "db.t4g.micro"
redis_node_type         = "cache.t4g.micro"
enable_logging          = true
```

## Deployment Steps

### 1. Initialize Terraform

```bash
cd infra/terraform/aws

# Initialize with backend
terraform init -backend-config=backend.hcl

# Or without backend (local state only)
terraform init
```

### 2. Validate Configuration

```bash
# Validate Terraform syntax
terraform validate

# Format check
terraform fmt -check -recursive

# Lint with tflint (optional)
tflint
```

### 3. Build and Push Application Image

```bash
# Build Docker image
docker build -t app:latest .

# Tag for ECR
aws ecr describe-repositories --repository-names app \
  || aws ecr create-repository --repository-name app

ECR_URI=$(aws ecr describe-repositories \
  --query 'repositories[0].repositoryUri' -o text)

docker tag app:latest $ECR_URI:latest

# Authenticate with ECR
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# Push image
docker push $ECR_URI:latest

echo "Container image: $ECR_URI:latest"
```

### 4. Plan Deployment

```bash
# Plan for dev environment
terraform plan \
  -var-file=environments/dev.tfvars \
  -out=tfplan

# Review the plan output carefully
# Check for any unexpected resource changes
```

### 5. Apply Configuration

```bash
# Apply the plan
terraform apply tfplan

# Save outputs
terraform output -json > deployment.json
```

**Important:** The initial deployment may take 10-15 minutes for RDS and Redis provisioning.

### 6. Verify Deployment

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)

# Health check
curl http://$ALB_DNS/health

# View application logs
aws logs tail /ecs/app --follow

# Check ECS service status
aws ecs describe-services \
  --cluster app-dev \
  --services app-dev
```

## Post-Deployment Configuration

### 1. Database Initialization

```bash
# Get RDS endpoint
RDS_HOST=$(terraform output -raw rds_endpoint)
export PGPASSWORD=your_password

# Connect to database
psql -h $RDS_HOST -U postgres -d app

# Run migrations
psql -h $RDS_HOST -U postgres -d app -f migrations.sql
```

### 2. Secrets Management

Store sensitive values in AWS Secrets Manager:

```bash
# Create database credentials secret
aws secretsmanager create-secret \
  --name app/db \
  --secret-string '{"username":"postgres","password":"your_password"}'

# Create API keys secret
aws secretsmanager create-secret \
  --name app/api-keys \
  --secret-string '{"api_key":"your_key"}'
```

### 3. Configure SSL/TLS

Use AWS Certificate Manager:

```bash
# Request certificate (or use existing)
aws acm request-certificate \
  --domain-name yourdomain.com \
  --validation-method DNS \
  --region eu-central-1

# Update ALB listener to use HTTPS
# Edit tfvars and redeploy
```

### 4. Set Up DNS

```bash
# Get ALB address
ALB_DNS=$(terraform output -raw alb_dns_name)

# Create CNAME record in Route53 or your DNS provider
# yourdomain.com CNAME -> ALB_DNS
```

## Monitoring and Alerts

### CloudWatch Dashboards

Create a custom dashboard:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name app-dev \
  --dashboard-body file://dashboard.json
```

### CloudWatch Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name app-dev-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:region:account:topic

# Database connection pool alarm
aws cloudwatch put-metric-alarm \
  --alarm-name app-dev-db-connections \
  --alarm-description "Alert when DB connections high" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --threshold 80
```

### Application Logs

```bash
# Tail application logs
aws logs tail /ecs/app --follow

# Query logs with Insights
aws logs start-query \
  --log-group-name /ecs/app \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/'
```

## Troubleshooting

### ECS Tasks Not Starting

```bash
# Check task definition
aws ecs describe-task-definition \
  --task-definition app:1

# View task events
aws ecs describe-services \
  --cluster app-dev \
  --services app-dev \
  --query 'services[0].events[0:5]'

# Check container logs
aws logs tail /ecs/app --follow --filter-pattern ERROR
```

### Database Connection Issues

```bash
# Check security group
aws ec2 describe-security-groups \
  --filters Name=group-id,Values=sg-xxx

# Test connection
psql -h $RDS_HOST -U postgres -d app -c "SELECT version();"
```

### Terraform State Issues

```bash
# Back up state
cp terraform.tfstate terraform.tfstate.backup

# Refresh state
terraform refresh

# Force unlock (if needed)
terraform force-unlock LOCK_ID
```

## Cost Optimization

### Reduce Costs

1. **Right-size instances**
   - Use smaller ECS task sizes for dev
   - Use `db.t4g.micro` for non-production databases
   - Enable auto-scaling based on metrics

2. **Schedule-based scaling**
   ```hcl
   # Scale down outside business hours
   desired_count = 1  # for non-prod
   ```

3. **Spot instances** (for non-critical workloads)
   ```hcl
   launch_type = "SPOT"
   ```

4. **Reserved Capacity** (for prod)
   - Purchase RDS reserved instances
   - Purchase ElastiCache nodes

### Cost Monitoring

```bash
# Set up cost anomaly detection
aws ce put-anomaly-monitor \
  --anomaly-monitor '{"MonitorName":"app","MonitorType":"DIMENSIONAL"}'

# Get current costs
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=2026-08-16 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

## Destroying Infrastructure

**Warning:** This will delete all resources including the database.

```bash
# Back up database first
aws rds create-db-snapshot \
  --db-instance-identifier app-db \
  --db-snapshot-identifier app-backup-final

# Destroy infrastructure
terraform destroy -var-file=environments/dev.tfvars
```

## Next Steps

1. Configure auto-scaling policies
2. Set up multi-region failover
3. Implement backup and disaster recovery
4. Enable AWS Config for compliance monitoring
5. Review security best practices in docs/THREAT-MODEL.md

## Support

- Documentation: [docs/ARCHITECTURE.md](../ARCHITECTURE.md)
- Issues: [GitHub Issues](https://github.com/Gergo89/llm-governance-toolkit/issues)
- Discussions: [GitHub Discussions](https://github.com/Gergo89/llm-governance-toolkit/discussions)

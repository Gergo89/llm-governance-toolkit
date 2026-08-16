# Production Deployment Guide - AGI v0.1.0

**Date:** August 16, 2026  
**Version:** 0.1.0  
**Target:** Production Environment

## Overview

This guide walks through deploying AGI v0.1.0 to production. Choose your deployment platform:

- **[AWS/ECS Deployment](#aws-deployment-option-1)** - Managed AWS services (recommended for most teams)
- **[Kubernetes Deployment](#kubernetes-deployment-option-2)** - Self-managed or managed K8s (recommended for multi-cloud)

## Pre-Deployment Requirements

### Prerequisites Checklist

Before proceeding with ANY deployment:

- [ ] Read this guide completely
- [ ] Review `docs/PRODUCTION_CHECKLIST.md`
- [ ] Review `docs/THREAT-MODEL.md` for security architecture
- [ ] Team training completed on deployment procedures
- [ ] Disaster recovery plan documented and tested
- [ ] Monitoring and alerting configured
- [ ] Incident response plan in place
- [ ] Backups and snapshots tested
- [ ] Maintenance window scheduled and communicated
- [ ] Rollback procedure tested

### Tools Required

```bash
# AWS Deployment
terraform version        # 1.10+
aws --version           # v2+
aws sts get-caller-identity  # Verify credentials

# Kubernetes Deployment
kubectl version --client # v1.26+
kustomize version        # v5.0+
helm version            # v3+ (optional)

# Both
docker --version        # 20+
git --version          # 2.30+
```

### Credentials & Access

**AWS:**
- [ ] AWS credentials configured
- [ ] S3 bucket for Terraform state
- [ ] OIDC provider configured (for CI/CD)
- [ ] IAM role with appropriate permissions
- [ ] AWS region selected (default: eu-central-1)

**Kubernetes:**
- [ ] kubeconfig configured
- [ ] Cluster access verified: `kubectl cluster-info`
- [ ] Sufficient RBAC permissions
- [ ] Namespace created: `kubectl create namespace app`

**GitHub:**
- [ ] Repository access (for code)
- [ ] GitHub Secrets configured (PyPI token, AWS role, etc.)
- [ ] Branch protection enabled
- [ ] Signed commits (optional but recommended)

---

## AWS Deployment (Option 1)

### Phase 1: Preparation

#### Step 1.1: Set Environment Variables

```bash
# Set deployment environment
export ENVIRONMENT=prod
export AWS_REGION=eu-central-1
export AWS_DEFAULT_REGION=eu-central-1

# Terraform directory
export TF_DIR=infra/terraform/aws

# Verify
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
```

#### Step 1.2: Review Infrastructure Plan

```bash
cd infra/terraform/aws

# Initialize Terraform
terraform init -backend-config=backend.hcl

# Review plan (DO NOT APPLY YET)
terraform plan -var-file=environments/prod.tfvars -out=tfplan_prod

# This should show:
# - New VPC and networking
# - ECS cluster and services
# - RDS database
# - ElastiCache Redis
# - Application Load Balancer
# - Auto-scaling groups
# - CloudWatch logs and alarms
# - Security groups and network policies
```

**Review checklist:**
- [ ] All resources correct
- [ ] No unexpected deletions
- [ ] Resource sizes appropriate
- [ ] Costs estimated and approved
- [ ] Tags and naming conventions followed

#### Step 1.3: Build & Push Container Image

```bash
# Build application image
docker build -t app:0.1.0 .

# Tag for ECR
ECR_REPO=$(aws ecr describe-repositories --query 'repositories[0].repositoryUri' -o text)
docker tag app:0.1.0 $ECR_REPO:0.1.0
docker tag app:0.1.0 $ECR_REPO:latest

# Authenticate with ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Push images
docker push $ECR_REPO:0.1.0
docker push $ECR_REPO:latest

# Verify
aws ecr describe-images --repository-name app --query 'imageDetails[].imageTags'
```

#### Step 1.4: Run Full Testing

```bash
# Run all tests
cd llm-governance-toolkit
pytest -v --cov=llm_governance_toolkit

# Stress tests (optional)
python stress_test.py
python cage_stress_test.py

# Application health checks
cd ../
./scripts/test-cage.sh

# All tests must pass before proceeding
```

### Phase 2: Deployment

#### Step 2.1: Pre-Deployment Backup

```bash
# Create final backup
aws rds create-db-snapshot \
  --db-instance-identifier app-prod \
  --db-snapshot-identifier app-prod-backup-v0.1.0-$(date +%s)

# Tag the backup
SNAPSHOT_ID=$(aws rds describe-db-snapshots \
  --query 'DBSnapshots[0].DBSnapshotIdentifier' -o text)
echo "Backup created: $SNAPSHOT_ID"
```

#### Step 2.2: Apply Infrastructure

```bash
cd infra/terraform/aws

# Apply with explicit confirmation
echo "Applying Terraform plan for production environment..."
terraform apply tfplan_prod

# This will:
# - Create VPC with public/private subnets
# - Create NAT Gateway
# - Provision RDS PostgreSQL
# - Provision ElastiCache Redis
# - Create Application Load Balancer
# - Create ECS cluster and task definitions
# - Configure security groups
# - Set up CloudWatch logs and alarms
# - Enable auto-scaling

# Wait for completion (10-15 minutes typical)
# Monitor in AWS Console or via CLI
aws ecs describe-services \
  --cluster app-prod \
  --services app-prod \
  --query 'services[0].status'
```

**Save outputs:**
```bash
terraform output -json > deployment-outputs.json
echo "Outputs saved to deployment-outputs.json"
```

#### Step 2.3: Configure RDS Database

```bash
# Get RDS endpoint
RDS_HOST=$(terraform output -raw rds_endpoint)
RDS_PASS=$(aws secretsmanager get-secret-value \
  --secret-id app/db --query SecretString --output text | jq -r '.password')

# Connect to database
PGPASSWORD=$RDS_PASS psql -h $RDS_HOST -U postgres -d app

# Run initialization script
psql -h $RDS_HOST -U postgres -d app -f database-init.sql

# Verify schema created
psql -h $RDS_HOST -U postgres -d app -c "\dt"
```

#### Step 2.4: Configure Application Secrets

```bash
# Store database credentials
aws secretsmanager create-secret \
  --name app/db \
  --secret-string '{"username":"postgres","password":"your_prod_password"}' \
  --region $AWS_REGION

# Store API keys
aws secretsmanager create-secret \
  --name app/api-keys \
  --secret-string '{"api_key":"your_prod_key","api_secret":"your_prod_secret"}' \
  --region $AWS_REGION

# Verify
aws secretsmanager list-secrets --region $AWS_REGION
```

#### Step 2.5: Deploy Application

```bash
# Update ECS task definition with latest image
aws ecs register-task-definition \
  --family app \
  --container-definitions file://task-definition.json \
  --region $AWS_REGION

# Update service to use new task definition
aws ecs update-service \
  --cluster app-prod \
  --service app-prod \
  --task-definition app:1 \
  --region $AWS_REGION

# Monitor rollout
aws ecs describe-services \
  --cluster app-prod \
  --services app-prod \
  --query 'services[0].deployments' | jq '.'

# Wait for steady state
aws ecs wait services-stable \
  --cluster app-prod \
  --services app-prod \
  --region $AWS_REGION
```

### Phase 3: Verification

#### Step 3.1: Health Checks

```bash
# Get Load Balancer DNS
ALB_DNS=$(terraform output -raw alb_dns_name)

# Health check
curl -I http://$ALB_DNS/health

# Expected response: 200 OK

# Check logs
aws logs tail /ecs/app --follow --since 10m | grep ERROR
```

#### Step 3.2: Service Verification

```bash
# Check ECS tasks
aws ecs list-tasks --cluster app-prod --region $AWS_REGION
aws ecs describe-tasks \
  --cluster app-prod \
  --tasks $(aws ecs list-tasks --cluster app-prod --query taskArns --output text) \
  --region $AWS_REGION

# Check database connectivity
PGPASSWORD=$RDS_PASS psql -h $RDS_HOST -U postgres -d app -c "SELECT version();"

# Check Redis connectivity
aws ec2-instance-connect send-ssh-public-key \
  --instance-id i-xxx \
  --instance-os-user ec2-user \
  --ssh-public-key.s0 file://key.pub
redis-cli -h $REDIS_HOST -p 6379 PING
```

#### Step 3.3: Monitoring Verification

```bash
# Check CloudWatch dashboards
aws cloudwatch list-dashboards --region $AWS_REGION

# Check alarms
aws cloudwatch describe-alarms \
  --alarm-names app-prod-high-cpu app-prod-high-memory \
  --region $AWS_REGION

# Check logs
aws logs describe-log-groups | grep /ecs/app
aws logs tail /ecs/app --since 1h --follow
```

### Phase 4: Production Handoff

#### Step 4.1: Documentation

```bash
# Document deployment
cat > DEPLOYMENT_LOG_v0.1.0.md << EOF
# AGI v0.1.0 Production Deployment Log

**Date:** $(date)
**Status:** ✅ DEPLOYED
**Environment:** Production
**Region:** $AWS_REGION

## Infrastructure
- VPC: $VPC_ID
- RDS: $RDS_ENDPOINT
- Redis: $REDIS_ENDPOINT
- ALB: $ALB_DNS
- ECS Cluster: app-prod

## Credentials
- Secrets Manager: app/* secrets
- DB User: postgres
- API Keys: app/api-keys

## Monitoring
- CloudWatch Dashboard: app-prod
- Log Group: /ecs/app
- Alarms: app-prod-*

## Contacts
- On-call: [phone/email]
- Escalation: [phone/email]

## Rollback Plan
Run: terraform destroy -auto-approve
EOF

# Save outputs
terraform output -json > DEPLOYMENT_v0.1.0_outputs.json
```

#### Step 4.2: Monitoring Setup

Ensure monitoring is active:

```bash
# Start log monitoring
aws logs tail /ecs/app --follow &

# In another terminal, test application
curl http://$ALB_DNS/api/test

# Verify metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=app-prod \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

#### Step 4.3: On-call Handoff

```bash
# Create on-call runbooks
cat > RUNBOOK_PROD.md << 'EOF'
# Production On-Call Runbook - AGI v0.1.0

## Alert: High CPU Usage
1. Check running tasks
2. Review logs for errors
3. If legitimate spike: OK to proceed
4. If not: Check for runaway processes and terminate
5. Scale if needed: aws ecs update-service --service app-prod --desired-count 4

## Alert: High Memory Usage
Similar to CPU. Consider OOM killer.

## Alert: Database Connection Issues
1. Check RDS status: aws rds describe-db-instances
2. Verify security groups
3. Check connection pool limits in application

## Full System Restart
1. Stop ECS service: aws ecs update-service --service app-prod --desired-count 0
2. Wait 5 minutes for graceful shutdown
3. Restart service: aws ecs update-service --service app-prod --desired-count 3

## Rollback to Previous Version
1. terraform destroy -auto-approve
2. Restore from snapshot
3. Re-deploy with previous version tag
EOF
```

---

## Kubernetes Deployment (Option 2)

### Phase 1: Preparation

#### Step 1.1: Set Environment Variables

```bash
# Cluster configuration
export CLUSTER_NAME=production
export NAMESPACE=app
export ENVIRONMENT=prod

# Verify cluster access
kubectl cluster-info
kubectl get nodes
```

#### Step 1.2: Create Namespace and RBAC

```bash
# Create namespace
kubectl create namespace $NAMESPACE
kubectl label namespace $NAMESPACE environment=$ENVIRONMENT

# Apply RBAC
kubectl apply -f - << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-deployer
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-deployer
  namespace: $NAMESPACE
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets"]
  verbs: ["*"]
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-deployer
  namespace: $NAMESPACE
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: app-deployer
subjects:
- kind: ServiceAccount
  name: app-deployer
  namespace: $NAMESPACE
EOF
```

#### Step 1.3: Configure Secrets

```bash
# Create database credentials
kubectl create secret generic db-credentials \
  --from-literal=username=postgres \
  --from-literal=password=your_prod_password \
  -n $NAMESPACE

# Create API keys
kubectl create secret generic api-keys \
  --from-literal=api_key=your_prod_key \
  --from-literal=api_secret=your_prod_secret \
  -n $NAMESPACE

# Verify
kubectl get secrets -n $NAMESPACE
```

### Phase 2: Deployment

#### Step 2.1: Validate Kustomize Configuration

```bash
# Render manifests
kubectl kustomize infra/kubernetes/overlays/prod > manifests.yaml

# Validate syntax
kubectl apply --dry-run=client -f manifests.yaml

# Review output
cat manifests.yaml | head -100
```

#### Step 2.2: Deploy Application

```bash
# Apply configuration
kubectl apply -k infra/kubernetes/overlays/prod

# Verify deployment
kubectl get deployments -n $NAMESPACE
kubectl get pods -n $NAMESPACE --watch

# Wait for rollout
kubectl rollout status deployment/app -n $NAMESPACE --timeout=5m
```

#### Step 2.3: Configure Ingress

```bash
# Apply ingress (assuming ingress controller installed)
kubectl apply -f - << 'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: app
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - yourdomain.com
    secretName: app-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app
            port:
              number: 80
EOF
```

### Phase 3: Verification

#### Step 3.1: Pod Health

```bash
# Check pod status
kubectl get pods -n $NAMESPACE
kubectl describe pod -n $NAMESPACE <pod-name>

# Check logs
kubectl logs -n $NAMESPACE deployment/app --all-containers=true

# Check readiness
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}'
```

#### Step 3.2: Service Connectivity

```bash
# Test service
kubectl run -it -n $NAMESPACE --rm debug --image=nicolaka/netshoot --restart=Never -- \
  curl http://app/health

# Port forward for testing
kubectl port-forward -n $NAMESPACE svc/app 8080:80
curl http://localhost:8080/health
```

#### Step 3.3: Metrics & Logs

```bash
# Check resource usage
kubectl top pods -n $NAMESPACE
kubectl top nodes

# Check events
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'

# View logs with filters
kubectl logs -n $NAMESPACE deployment/app --grep=ERROR
kubectl logs -n $NAMESPACE deployment/app --tail=100 -f
```

---

## Post-Deployment (Both Options)

### Monitoring & Alerting

Ensure these are configured:

1. **Application Health**
   - [ ] Health check endpoint responding
   - [ ] Error rates normal (< 0.1%)
   - [ ] Response times within SLA

2. **Infrastructure**
   - [ ] CPU utilization < 70%
   - [ ] Memory utilization < 80%
   - [ ] Disk usage < 75%

3. **Database**
   - [ ] Connections normal
   - [ ] Query performance acceptable
   - [ ] Backups running on schedule

4. **Alerts Configured**
   - [ ] High CPU alert
   - [ ] High memory alert
   - [ ] Database connection issues
   - [ ] Application error rate

### Documentation

- [ ] Deployment log created
- [ ] Outputs saved
- [ ] Runbooks documented
- [ ] Contacts updated
- [ ] Escalation procedures documented

### Team Communication

- [ ] Deploy notification sent
- [ ] Status page updated
- [ ] Team briefed on changes
- [ ] On-call engineer prepared

---

## Verification Checklist (All Deployments)

```bash
# System Health
- [ ] Application responding to requests
- [ ] Health check endpoint: HTTP 200
- [ ] No error spikes in logs
- [ ] Database accessible
- [ ] Cache operational
- [ ] Metrics being collected
- [ ] Alarms not firing unexpectedly

# Functionality
- [ ] Core features working
- [ ] API endpoints operational
- [ ] Data persisting correctly
- [ ] Caching working
- [ ] Scheduled jobs running

# Performance
- [ ] Response times acceptable
- [ ] No memory leaks
- [ ] CPU stable
- [ ] Database query performance good

# Security
- [ ] HTTPS enforced
- [ ] Authentication working
- [ ] Authorization checks passing
- [ ] Secrets not exposed
- [ ] Network policies working
```

---

## Rollback Procedures

### AWS Rollback

```bash
# Option 1: Scale down service
aws ecs update-service --cluster app-prod --service app-prod --desired-count 0

# Option 2: Revert to previous task definition
PREVIOUS_REVISION=$((CURRENT_REVISION - 1))
aws ecs update-service \
  --cluster app-prod \
  --service app-prod \
  --task-definition app:$PREVIOUS_REVISION

# Option 3: Destroy infrastructure and restore from backup
cd infra/terraform/aws
terraform destroy -auto-approve
# Then restore database from snapshot
```

### Kubernetes Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/app -n app

# Or revert to specific revision
kubectl rollout history deployment/app -n app
kubectl rollout undo deployment/app -n app --to-revision=2

# Verify rollback
kubectl rollout status deployment/app -n app
```

---

## Success Criteria

✅ **Deployment is successful when:**

1. All pods/tasks are running and healthy
2. Application responds to health checks
3. Error rates are normal (< 0.1%)
4. Monitoring dashboards show stable metrics
5. No unexpected alerts firing
6. Database initialized and accessible
7. Caching layer operational
8. Backup procedures working
9. Logging and tracing functional
10. Team confirmed ready for traffic

---

## Post-Deployment Monitoring

```bash
# Watch metrics for 24 hours
aws logs tail /ecs/app --follow  # AWS
kubectl logs -n app -f deployment/app  # Kubernetes

# Track key metrics
- HTTP response times (p50, p95, p99)
- Error rate (4xx, 5xx)
- Application resource usage
- Database performance
- Cache hit rate
```

---

## Support & Troubleshooting

### If Deployment Fails

1. **Check logs immediately**
   - AWS: `aws logs tail /ecs/app --follow`
   - K8s: `kubectl logs -n app --all-containers=true -f`

2. **Review error messages**
   - Database connection errors?
   - Memory/CPU errors?
   - Configuration errors?

3. **Rollback if needed**
   - See [Rollback Procedures](#rollback-procedures)

4. **Investigate root cause**
   - Check Terraform state
   - Review application logs
   - Verify credentials

### Getting Help

- Review `docs/PRODUCTION_CHECKLIST.md`
- Check deployment guide for your platform
- Review threat model for security issues
- Contact support team

---

**Status: ✅ Ready for Production Deployment**

See [PUBLISHING.md](PUBLISHING.md) for complete publishing guide.

Choose your deployment option above and follow the steps carefully.

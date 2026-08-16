# Production Deployment Checklist

Use this checklist to ensure the AGI platform is production-ready before deploying to production environments.

## Table of Contents

- [Pre-Deployment](#pre-deployment)
- [Code and Build](#code-and-build)
- [Infrastructure](#infrastructure)
- [Security](#security)
- [Monitoring and Observability](#monitoring-and-observability)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Documentation](#documentation)
- [Deployment Execution](#deployment-execution)
- [Post-Deployment Verification](#post-deployment-verification)
- [Rollback Plan](#rollback-plan)

---

## Pre-Deployment

### Code Quality

- [ ] All tests pass in CI/CD pipeline
- [ ] Code coverage meets minimum threshold (>80%)
- [ ] No high-severity security vulnerabilities reported
- [ ] All TODOs and FIXMEs documented or resolved
- [ ] Code review approval from at least 2 team members
- [ ] Dependency versions locked in `requirements.txt`
- [ ] No hardcoded secrets or credentials
- [ ] Lint and format checks pass (`ruff`, `terraform fmt`)

### Version and Release

- [ ] Version number bumped appropriately (semantic versioning)
- [ ] CHANGELOG.md updated with release notes
- [ ] Git tag created: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] GitHub Release created with detailed notes
- [ ] Python package version matches all relevant files

### Testing

- [ ] Unit tests pass locally and in CI
- [ ] Integration tests pass with staging infrastructure
- [ ] Load testing completed (if applicable)
- [ ] Canary deployment tested in staging
- [ ] Rollback procedure tested

---

## Code and Build

### Container Image

- [ ] Docker image builds successfully
- [ ] Image size optimized (no unnecessary layers)
- [ ] Security scanning passed (no critical vulnerabilities)
- [ ] Image tagged with: `latest`, `vX.Y.Z`, and commit SHA
- [ ] Image pushed to ECR/registry
- [ ] Image digest verified: `docker inspect image_id`
- [ ] Dockerfile uses non-root user
- [ ] Multi-stage build used to reduce image size

### Dependencies

- [ ] All dependencies pinned to specific versions
- [ ] No unused dependencies included
- [ ] Development dependencies excluded from production image
- [ ] Supply chain security checks passed (SBOM generated)
- [ ] License compliance verified for all dependencies

### Application Configuration

- [ ] Environment variables documented in `.env.example`
- [ ] Configuration loaded from environment, not hardcoded
- [ ] No default secrets in code
- [ ] Feature flags configured for gradual rollout
- [ ] Graceful shutdown implemented (SIGTERM handling)
- [ ] Health check endpoint implemented and tested

---

## Infrastructure

### AWS Resources

- [ ] VPC and networking properly configured
- [ ] Subnets span at least 2 availability zones (high availability)
- [ ] NAT Gateway configured for private subnet egress
- [ ] Security groups follow principle of least privilege
- [ ] Network ACLs reviewed and properly configured
- [ ] S3 buckets have versioning enabled
- [ ] S3 buckets have encryption enabled (SSE-S3 or SSE-KMS)
- [ ] RDS database has automated backups enabled
- [ ] RDS database is Multi-AZ enabled (production)
- [ ] RDS parameter group reviewed and optimized
- [ ] ElastiCache Redis: cluster mode disabled for simplicity
- [ ] ElastiCache: automatic failover enabled
- [ ] ALB health check endpoints configured correctly
- [ ] ALB listener configured for HTTPS (SSL/TLS)
- [ ] ACM certificate valid and not expiring soon
- [ ] ECS task definition includes resource limits
- [ ] ECS service has auto-scaling policies configured
- [ ] CloudFormation/Terraform state stored in S3 with versioning
- [ ] AWS Config enabled for compliance monitoring

### High Availability

- [ ] Multi-AZ deployment configured
- [ ] Database replicas in multiple availability zones
- [ ] Load balancer configured to distribute traffic
- [ ] Connection draining configured on load balancer
- [ ] Auto-scaling policies configured with appropriate thresholds
- [ ] Minimum instance count set to >= 2

### Terraform/IaC

- [ ] Terraform code validated: `terraform validate`
- [ ] Terraform format checked: `terraform fmt -check`
- [ ] Terraform plan reviewed: `terraform plan -var-file=prod.tfvars`
- [ ] Terraform state locked: DynamoDB table enabled
- [ ] Terraform backend encrypted and replicated
- [ ] Version constraints specified for providers and modules
- [ ] Sensitive values marked as sensitive in outputs
- [ ] Variables have descriptions and type constraints

---

## Security

### Network Security

- [ ] VPC Flow Logs enabled for monitoring
- [ ] Network ACLs configured to deny unnecessary traffic
- [ ] Security groups follow least privilege principle
- [ ] SSH/RDP access restricted to bastion hosts
- [ ] All traffic to databases encrypted in transit (TLS)
- [ ] ALB enforces HTTPS (HTTP redirects to HTTPS)
- [ ] Security headers configured (HSTS, CSP, etc.)

### Access Control

- [ ] IAM roles follow least privilege principle
- [ ] Cross-account access reviewed (if applicable)
- [ ] Root account access disabled for day-to-day operations
- [ ] MFA enabled for all human users
- [ ] Service roles properly scoped
- [ ] Access keys rotated regularly
- [ ] Git repository permissions reviewed
- [ ] Secrets Manager credentials created for all secrets

### Secrets Management

- [ ] Database credentials stored in AWS Secrets Manager
- [ ] API keys and tokens stored securely
- [ ] Application retrieves secrets at runtime (not build-time)
- [ ] Secrets rotated on a schedule
- [ ] Secrets encrypted with KMS
- [ ] Secret access logged in CloudTrail
- [ ] No hardcoded secrets in Git history
- [ ] `.env` files excluded from Git

### Data Protection

- [ ] Database encryption enabled (RDS KMS)
- [ ] S3 buckets encrypted with KMS
- [ ] EBS volumes encrypted
- [ ] Automated backups configured with retention
- [ ] Backup encryption verified
- [ ] Data classification documented
- [ ] PII/sensitive data handling procedures documented

### Compliance

- [ ] Security controls documented in THREAT-MODEL.md
- [ ] Compliance requirements identified
- [ ] AWS Config rules enabled for compliance monitoring
- [ ] GuardDuty enabled for threat detection
- [ ] CloudTrail enabled for audit logging
- [ ] VPC Flow Logs enabled
- [ ] CloudWatch Logs retention configured

---

## Monitoring and Observability

### Logging

- [ ] CloudWatch Logs configured for all services
- [ ] Application structured logging implemented (JSON format)
- [ ] Log retention period configured (7-30 days)
- [ ] CloudWatch Logs Insights queries created for debugging
- [ ] Logs sent to centralized logging solution (if applicable)
- [ ] Sensitive data not logged (PII, passwords, tokens)
- [ ] Log levels set appropriately (INFO for prod)

### Metrics

- [ ] CloudWatch metrics enabled for all resources
- [ ] Application metrics exported (custom metrics)
- [ ] CPU, memory, disk utilization monitored
- [ ] Database connections and query performance monitored
- [ ] Cache hit rates monitored
- [ ] Request latency and error rates monitored
- [ ] Cost metrics tracked

### Alarms

- [ ] High CPU alarm configured (threshold: 80%)
- [ ] High memory alarm configured (threshold: 85%)
- [ ] Low disk space alarm configured
- [ ] Database connection pool alarm configured
- [ ] HTTP error rate alarm configured
- [ ] Request latency alarm configured
- [ ] Missing heartbeat alarm configured
- [ ] All alarms have SNS topics configured
- [ ] Alarm notifications tested
- [ ] On-call escalation policy defined

### Dashboards

- [ ] CloudWatch dashboard created
- [ ] Key metrics displayed (system health, business metrics)
- [ ] Dashboard shared with team
- [ ] Auto-refresh configured
- [ ] Custom widgets for critical systems

### Tracing and APM (if applicable)

- [ ] OpenTelemetry/X-Ray integrated
- [ ] Distributed tracing enabled
- [ ] Trace sampling configured (10-100%)
- [ ] Request correlation IDs implemented

---

## Backup and Disaster Recovery

### Backup Strategy

- [ ] RDS automated backups enabled (retention: 7+ days)
- [ ] Manual backup procedure documented
- [ ] Backup encryption verified
- [ ] Backup retention policy defined
- [ ] Test restore from backup completed
- [ ] Backup storage encrypted

### Disaster Recovery

- [ ] RTO (Recovery Time Objective) defined (< 1 hour)
- [ ] RPO (Recovery Point Objective) defined (< 15 minutes)
- [ ] Failover procedure documented
- [ ] Failover tested in non-production environment
- [ ] Data replication strategy implemented
- [ ] Database replication lag monitored
- [ ] Incident response plan reviewed

### Disaster Recovery Testing

- [ ] Simulated database failure tested
- [ ] Simulated region/AZ failure tested
- [ ] Restore from backup tested
- [ ] Failover failback procedure tested
- [ ] Recovery procedures documented and tested

---

## Documentation

### Architecture Documentation

- [ ] Architecture diagram created (docs/ARCHITECTURE.md)
- [ ] Data flow documented
- [ ] Security architecture documented (docs/THREAT-MODEL.md)
- [ ] Infrastructure components documented
- [ ] Deployment architecture documented

### Operational Documentation

- [ ] AWS deployment guide completed (docs/AWS_DEPLOYMENT.md)
- [ ] Runbooks created for common operations
- [ ] Troubleshooting guide created
- [ ] On-call guide created
- [ ] Escalation procedures documented
- [ ] Maintenance windows documented

### API Documentation

- [ ] API endpoints documented
- [ ] Authentication/authorization documented
- [ ] Rate limits documented
- [ ] Error handling documented
- [ ] Example requests/responses provided

### Change Management

- [ ] Change control procedure defined
- [ ] Change log maintained
- [ ] Deployment procedure documented
- [ ] Rollback procedure documented
- [ ] Communication plan for outages

---

## Deployment Execution

### Pre-Deployment

- [ ] Deployment window scheduled
- [ ] Team members notified and confirmed availability
- [ ] Monitoring dashboard open and watched
- [ ] Backup created immediately before deployment
- [ ] Change request approved
- [ ] Communication channels open (Slack, war room, etc.)

### Deployment Steps

- [ ] Feature flags disabled for safe rollout
- [ ] Canary deployment to 10-20% of traffic
- [ ] Health checks passing on canary instances
- [ ] Metrics stable on canary instances (5-15 minutes)
- [ ] Gradual rollout to remaining instances (25%, 50%, 100%)
- [ ] Health checks passing on all instances
- [ ] Smoke tests passing

### Post-Deployment Validation

- [ ] Application responding on health endpoint
- [ ] Error rates within normal range (< 0.1%)
- [ ] Latency within SLA (< 500ms p99)
- [ ] Database connectivity verified
- [ ] Cache working correctly
- [ ] External API calls working
- [ ] Logging working correctly

---

## Post-Deployment Verification

### Functional Testing

- [ ] Critical user journeys tested manually
- [ ] API endpoints tested (curl, Postman)
- [ ] Database queries working correctly
- [ ] Cache working as expected
- [ ] Scheduled jobs executing on time
- [ ] Notifications/alerts working
- [ ] Search/filtering working correctly

### Performance Testing

- [ ] Response times acceptable
- [ ] No memory leaks observed
- [ ] CPU utilization stable
- [ ] Database query performance acceptable
- [ ] No connection pool exhaustion
- [ ] Rate limiting working correctly

### Security Testing

- [ ] HTTPS enforced
- [ ] Security headers present
- [ ] Authentication working
- [ ] Authorization checks working
- [ ] No exposed secrets in logs
- [ ] API authentication working

### Monitoring

- [ ] All metrics collected and visible
- [ ] Alarms functioning correctly
- [ ] Logs being aggregated
- [ ] Traces being collected
- [ ] No anomalies detected
- [ ] Dashboard showing expected data

---

## Rollback Plan

### Trigger Conditions

- [ ] Error rate exceeds 5%
- [ ] Response time exceeds SLA
- [ ] Critical functionality unavailable
- [ ] Database corruption detected
- [ ] Security incident detected
- [ ] Out of memory errors
- [ ] Unresolvable runtime errors

### Rollback Steps

1. [ ] Alert team to issue
2. [ ] Create incident channel
3. [ ] Initiate rollback decision (within 5 minutes of detection)
4. [ ] Revert to previous version in ECS task definition
5. [ ] Monitor rollback progression
6. [ ] Verify all instances healthy
7. [ ] Post-incident review
8. [ ] Document lessons learned

### Rollback Validation

- [ ] Application responding
- [ ] Error rates returned to normal
- [ ] Performance metrics normal
- [ ] No data corruption
- [ ] All systems healthy
- [ ] Incident report created

---

## Sign-Off

**Deployment Manager:** _________________________ Date: _________

**Team Lead:** _________________________ Date: _________

**Operations Lead:** _________________________ Date: _________

---

## Notes

Use this section for deployment notes:

```
[Space for deployment-specific notes]
```

---

## Useful Commands

### Deployment
```bash
# Create and apply Terraform plan
make terraform-plan ENV=prod
terraform apply infra/terraform/aws/tfplan

# Monitor ECS deployment
aws ecs describe-services --cluster app-prod --services app-prod --query 'services[0].deployments'

# View logs
aws logs tail /ecs/app --follow --filter-pattern ERROR
```

### Rollback
```bash
# Revert to previous task definition
aws ecs update-service --cluster app-prod --service app-prod --task-definition app:N
```

### Verification
```bash
# Health check
curl -I https://yourdomain.com/health

# Database check
psql -h $RDS_HOST -U postgres -d app -c "SELECT version();"

# Metrics check
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization
```

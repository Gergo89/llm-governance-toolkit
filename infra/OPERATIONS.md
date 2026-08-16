# Operations guide

## Provisioning order

1. Create and secure remote Terraform state using the bootstrap stack.
2. Initialize the AWS stack with the backend configuration.
3. Apply a reviewed environment plan.
4. Build, scan, and push the application image using an immutable digest.
5. Update the ECS task or Kubernetes overlay to use that digest.
6. Verify `/healthz`, logs, metrics, alarms, and a database migration smoke test.

## Secrets

Terraform generates database and Redis credentials and stores them in AWS Secrets Manager. Never commit `.env`, Terraform state, kubeconfig, or rendered Kubernetes secrets. Rotate credentials by updating the secret, rolling the workload, and retiring the previous credential after active connections drain.

## Backups and recovery

RDS automated backups are enabled; production also retains a final snapshot on deletion. Test a point-in-time restore at least quarterly. Enable S3 versioning (already configured) and define lifecycle retention suitable for the data classification. Infrastructure state must use the versioned, encrypted bootstrap bucket.

## Deployment safety

- Pin images by digest in production.
- Run database migrations as a separate, backward-compatible job before workload rollout.
- Require approval on the GitHub `production` environment.
- Review Terraform replacements, public ingress changes, IAM changes, and deletion-protection changes manually.
- Roll back by restoring the previous image digest; do not roll back a destructive schema migration.
- After installing or changing the Cage policy, run `make cage-test` against a non-production cluster context.

## Incident checklist

1. Confirm scope from ALB target health, ECS events or Kubernetes events, application logs, and CloudWatch alarms.
2. Stop the change stream and preserve logs.
3. Roll back the most recent deploy when safe.
4. Scale only after identifying whether the dependency or application is saturated.
5. Record timeline, impact, mitigation, and follow-up controls.

# Infrastructure baseline

This repository contains a complete starting platform for a containerized HTTP service. It deliberately keeps the application image and domain configurable.

The platform is organized around two named layers: **the Cage**, an enforced workload containment boundary, and **the Cathedral**, the service-governance and telemetry plane around it. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Included

- Local PostgreSQL, Redis, Prometheus, and Grafana with Docker Compose.
- AWS infrastructure as code: VPC, public/private subnets, NAT, ECR, ECS Fargate, an ALB, PostgreSQL RDS, Redis, Secrets Manager, S3, logs, alarms, and autoscaling.
- Provider-neutral Kubernetes manifests with Kustomize overlays for development and production.
- Native Kubernetes Cage controls and an HA OpenTelemetry Cathedral gateway with a machine-readable service/SLO contract.
- GitHub Actions for infrastructure validation and opt-in AWS deployment.
- Security defaults: private workloads and databases, encrypted storage, non-root containers, network policies, secrets outside Git, and deletion protection in production.

The AWS/ECS and Kubernetes directories are alternative production deployment targets; use one for an application rather than deploying both by accident.

## Local environment

1. Copy `.env.example` to `.env` and replace the local-only passwords.
2. Run `docker compose up -d`.
3. PostgreSQL is available on `localhost:5432`, Redis on `localhost:6379`, Prometheus on `localhost:9090`, and Grafana on `localhost:3000`.

## AWS deployment

Prerequisites: Terraform 1.10+, AWS credentials, and an application container image.

1. Optionally create remote-state storage from `infra/terraform/bootstrap`.
2. Configure the backend using `infra/terraform/aws/backend.hcl.example`.
3. Review `infra/terraform/aws/environments/dev.tfvars`.
4. Run `terraform -chdir=infra/terraform/aws init` and `terraform -chdir=infra/terraform/aws plan -var-file=environments/dev.tfvars`.
5. Push the application image to the output ECR repository, then set `container_image` to that immutable image digest and apply again.

Terraform creates billable AWS resources. In particular, NAT Gateway, RDS, Redis, ALB, and Fargate incur charges. Review the plan before applying.

## Kubernetes deployment

Build and publish the application image, replace `ghcr.io/example/app` in the selected overlay, create the runtime secret from `secret.example.yaml`, then run:

```sh
kubectl apply -k infra/kubernetes/overlays/dev
```

The cluster must already have an ingress controller, Metrics Server, and a TLS secret matching the overlay (or cert-manager configured to create it). Production should use External Secrets or a comparable secret manager instead of applying a plaintext Secret.

## CI/CD setup

Validation runs without cloud credentials. AWS deployment is manual and expects a GitHub environment named `production` with an `AWS_ROLE_ARN` variable. Configure GitHub's OIDC provider in AWS and restrict the role trust policy to this repository and environment.

See [infra/OPERATIONS.md](infra/OPERATIONS.md) for provisioning order, recovery, and day-two operations.

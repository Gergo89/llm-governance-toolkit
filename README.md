# 🎉 AGI Platform v0.1.0 - NOW AVAILABLE

**Status:** ✅ Public Release · **Version:** 0.1.0 · **Date:** August 16, 2026

The **AGI Platform** (LLM Governance Toolkit + Infrastructure) is now publicly available! 

📦 **Install:** `pip install llm-governance-toolkit`  
📖 **Learn:** Start with [QUICK_RELEASE_GUIDE.md](QUICK_RELEASE_GUIDE.md)  
🚀 **Deploy:** Follow [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)  
📚 **Docs:** See [PUBLISHING_INDEX.md](PUBLISHING_INDEX.md) for navigation

---

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

## Publishing & Releases

### Python Package (PyPI)

The `llm-governance-toolkit` Python package is published to PyPI automatically on GitHub releases.

**Installation:**
```bash
pip install llm-governance-toolkit
```

**Publishing a new release:**
1. Update version: `make version-bump BUMP_TYPE=minor`
2. Update [CHANGELOG.md](CHANGELOG.md)
3. Commit changes: `git commit -am "chore: bump version"`
4. Create git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. Push: `git push && git push --tags`
6. GitHub Actions automatically publishes to PyPI

See [Makefile](Makefile) for version management commands.

### GitHub Releases

Each release includes:
- Release notes with highlights
- Installation instructions
- Migration guides (if applicable)
- Link to full changelog

Create releases at: [GitHub Releases](https://github.com/Gergo89/llm-governance-toolkit/releases)

## Deployment Guides

### AWS Deployment

Complete guide with prerequisites, architecture, and step-by-step instructions:

**[→ AWS Deployment Guide](docs/AWS_DEPLOYMENT.md)**

- Terraform configuration and backend setup
- Building and pushing container images
- Infrastructure provisioning and validation
- Post-deployment configuration
- Monitoring and cost optimization

### Kubernetes Deployment

Deployment using Kubernetes with Kustomize:

**[→ Kubernetes Deployment Guide](docs/KUBERNETES_DEPLOYMENT.md)**

- Cluster setup and prerequisites
- Kustomize configuration and overlays
- Secrets and configuration management
- Networking and Ingress setup
- Auto-scaling and resource management

### Production Deployment Checklist

Comprehensive checklist for production deployments:

**[→ Production Deployment Checklist](docs/PRODUCTION_CHECKLIST.md)**

- Code and build verification
- Infrastructure requirements
- Security compliance
- Monitoring and observability
- Disaster recovery planning
- Deployment execution procedures

## Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Terraform 1.10+
- kubectl (for Kubernetes)

### Local Development

```bash
# Install development dependencies
cd llm-governance-toolkit
pip install -e ".[dev]"

# Run tests
pytest

# Run stress tests
python stress_test.py

# Code formatting
ruff check .
ruff format .
```

### Available Commands

```bash
# Show all available commands
make help

# Local services
make local-up      # Start PostgreSQL, Redis, Prometheus, Grafana
make local-down    # Stop local services
make local-logs    # View logs

# Infrastructure validation
make validate      # Validate Terraform, Docker Compose, Kubernetes YAML

# AWS deployment
make terraform-plan ENV=dev    # Plan deployment
make terraform-init            # Initialize Terraform

# Kubernetes
make k8s-render ENV=dev        # Render Kubernetes manifests

# Testing
make cage-test                 # Test Cage admission controls
```

## Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[Threat Model](docs/THREAT-MODEL.md)** - Security analysis and mitigations
- **[Operations Guide](infra/OPERATIONS.md)** - Day-to-day operations

### Research Papers

The `llm-governance-toolkit/papers/` directory contains comprehensive research on:
- AI Safety case studies
- LLM governance frameworks  
- Assurance case integrity
- Epistemic governance
- And more

See [llm-governance-toolkit/README.md](llm-governance-toolkit/README.md) for the full toolkit documentation.

## Contributing

We welcome contributions! Please see [llm-governance-toolkit/CONTRIBUTING.md](llm-governance-toolkit/CONTRIBUTING.md).

## License

MIT License - see [LICENSE](llm-governance-toolkit/LICENSE) for details.

## Support

- **Issues:** [GitHub Issues](https://github.com/Gergo89/llm-governance-toolkit/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Gergo89/llm-governance-toolkit/discussions)
- **PyPI Package:** [llm-governance-toolkit on PyPI](https://pypi.org/project/llm-governance-toolkit/)


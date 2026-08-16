# Changelog

All notable changes to the AGI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-16 🎉 PUBLIC RELEASE

### Added
- **LLM Governance Toolkit** - Deterministic reference implementations for applied LLM governance
  - Epistemic linter (goodhart_auditor) for metric verification claims
  - Deterministic evidence-maturity classifier (knowledge_maturity)
  - Fail-closed containment guard (containment_guard) for agent authorization
  - Optimal-stopping timing layer (optimal_timing) for decision boundaries
  - Goodhart-in-the-wild monitor (decoupling_monitor) for metric gaming detection
  - Ground-truth independence auditor (ground_truth_auditor) for signal validation
  - Defensive eval-gaming detector (eval_gaming_detector) for capability assessment integrity

- **Infrastructure Platform** - Complete containerized HTTP service platform
  - Docker Compose setup for local PostgreSQL, Redis, Prometheus, and Grafana
  - AWS infrastructure as code: VPC, ECS Fargate, RDS, Redis, ECR, ALB, auto-scaling
  - Kubernetes manifests with Kustomize overlays for dev/prod environments
  - Cage (workload containment) and Cathedral (governance/telemetry) architecture
  - GitHub Actions for CI/CD: infrastructure validation and AWS deployment
  - Security defaults: private workloads, encrypted storage, non-root containers, network policies

- **Documentation**
  - Architecture guide (docs/ARCHITECTURE.md)
  - Threat model (docs/THREAT-MODEL.md)
  - Operations manual (infra/OPERATIONS.md)
  - AI Safety case studies and governance frameworks
  - Comprehensive research papers on LLM governance

- **Development Tools**
  - Makefile with common tasks (local-up, validate, terraform-plan, k8s-render, cage-test)
  - Stress testing suite for governance components
  - Pre-configured linting and formatting (ruff, Terraform fmt)
  - Comprehensive test suite with pytest

### Infrastructure
- Python 3.11+ support with setuptools build system
- MIT License
- GitHub-based CI/CD with Actions workflows
- OIDC-based AWS authentication for secure deployments
- Support for dev, staging, and production environments

---

For detailed information about releases and how to publish, see:
- [PyPI Releases](https://pypi.org/project/llm-governance-toolkit/)
- [GitHub Releases](https://github.com/Gergo89/llm-governance-toolkit/releases)
- [Contributing Guide](llm-governance-toolkit/CONTRIBUTING.md)

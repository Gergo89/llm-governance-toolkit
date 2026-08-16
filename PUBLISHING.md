# Publishing Guide

This guide explains how to publish the AGI project to multiple channels: PyPI, GitHub Releases, AWS, Kubernetes, and Documentation.

## Table of Contents

1. [Overview](#overview)
2. [Before You Start](#before-you-start)
3. [Step-by-Step Publishing](#step-by-step-publishing)
4. [PyPI Publishing](#pypi-publishing)
5. [GitHub Release](#github-release)
6. [AWS Deployment](#aws-deployment)
7. [Kubernetes Deployment](#kubernetes-deployment)
8. [Documentation Publishing](#documentation-publishing)
9. [Post-Release Tasks](#post-release-tasks)
10. [Troubleshooting](#troubleshooting)

## Overview

The AGI project has multiple publishing channels:

| Channel | Purpose | Automation | Target Users |
|---------|---------|-----------|--------------|
| **PyPI** | Python package distribution | ✅ GitHub Actions | Python developers |
| **GitHub Releases** | Version releases & notes | Manual (automated from git tag) | All users |
| **AWS** | Cloud infrastructure deployment | Manual via Terraform | DevOps / SRE |
| **Kubernetes** | Container orchestration | Manual via kubectl/Kustomize | DevOps / SRE |
| **Documentation** | User guides & API docs | ✅ GitHub Actions on push | All users |

## Before You Start

### Prerequisites

1. **Local Development Environment**
   - Python 3.11+
   - Git configured with GPG signing (recommended)
   - Terraform 1.10+ (for AWS)
   - kubectl (for Kubernetes)
   - Docker (for container images)

2. **Repository Permissions**
   - Push access to main branch
   - Ability to create tags and releases
   - Admin access for configuring GitHub Pages

3. **PyPI Account**
   - Create account at [pypi.org](https://pypi.org/account/register/)
   - Generate API token in account settings
   - Add token to GitHub Secrets as `PYPI_API_TOKEN`

4. **AWS Account** (for AWS deployment)
   - AWS credentials configured
   - S3 bucket for Terraform state
   - OIDC provider configured for GitHub
   - IAM role for deployments

5. **Kubernetes Cluster** (for K8s deployment)
   - Access to production cluster
   - kubectl configured and authenticated
   - Sufficient permissions (RBAC)

### Environment Setup

```bash
# Clone repository
git clone https://github.com/Gergo89/llm-governance-toolkit.git
cd llm-governance-toolkit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
cd llm-governance-toolkit
pip install -e ".[dev]"
cd ..

# Verify tools
python --version  # 3.11+
terraform version  # 1.10+
kubectl version --client  # v1.26+
docker --version
```

## Step-by-Step Publishing

### Phase 1: Preparation (1-2 weeks before release)

#### 1.1 Create Release Branch

```bash
# Create feature branch for release preparation
git checkout -b release/v1.1.0

# Make any final fixes and documentation updates
# Run all tests
make validate
cd llm-governance-toolkit
pytest
cd ..
```

#### 1.2 Update Version

```bash
# Bump version (choose: major, minor, or patch)
make version-bump BUMP_TYPE=minor

# This updates:
# - llm-governance-toolkit/pyproject.toml
# - Any other version files
```

#### 1.3 Update Changelog

Edit [CHANGELOG.md](CHANGELOG.md):

```markdown
## [1.1.0] - 2026-08-20

### Added
- New feature X
- Improvement Y

### Fixed
- Bug fix Z

### Security
- Security patch A
```

#### 1.4 Commit and Push

```bash
# Stage changes
git add CHANGELOG.md llm-governance-toolkit/pyproject.toml

# Commit with meaningful message
git commit -m "chore: release v1.1.0

- Bump version
- Update changelog
- Final documentation updates"

# Push branch
git push origin release/v1.1.0
```

#### 1.5 Create Pull Request

1. Go to GitHub repository
2. Create Pull Request from `release/v1.1.0` to `main`
3. Add description using [RELEASE_TEMPLATE.md](.github/RELEASE_TEMPLATE.md)
4. Request reviews from team members
5. Merge after approval

### Phase 2: Release Publication

#### 2.1 Create Git Tag

After PR is merged to main:

```bash
# Ensure you're on main branch
git checkout main
git pull origin main

# Create annotated tag (recommended)
git tag -a v1.1.0 -m "Release v1.1.0 - Add new governance patterns"

# Or with GPG signing
git tag -s -a v1.1.0 -m "Release v1.1.0 - Add new governance patterns"

# Verify tag
git tag -n5
git show v1.1.0

# Push tags
git push origin v1.1.0
# Or push all tags
git push origin --tags
```

#### 2.2 GitHub Actions Triggers

When you push the tag, these automated workflows trigger:

1. **publish-pypi.yml** - Builds and publishes to PyPI
2. **publish-docs.yml** - Updates documentation site

Monitor the workflows:
```bash
# Open in browser
https://github.com/Gergo89/llm-governance-toolkit/actions

# Or use GitHub CLI
gh run list --workflow=publish-pypi.yml
gh run view <run-id>
```

#### 2.3 Create GitHub Release

```bash
# Using GitHub CLI
gh release create v1.1.0 \
  --title "Release v1.1.0" \
  --notes-file release-notes.md \
  --draft  # Keep as draft until ready

# Then edit and publish:
gh release edit v1.1.0 --draft=false

# Or create from browser
https://github.com/Gergo89/llm-governance-toolkit/releases/new
```

**Release Notes Template** (release-notes.md):

```markdown
# AGI Platform v1.1.0

## Highlights

- ✨ New governance patterns for agent containment
- 🚀 Enhanced monitoring and observability
- 🔒 Improved security controls
- 📚 Comprehensive documentation

## Installation

### PyPI
\`\`\`bash
pip install --upgrade llm-governance-toolkit==1.1.0
\`\`\`

### From Source
\`\`\`bash
git clone https://github.com/Gergo89/llm-governance-toolkit.git
cd llm-governance-toolkit
git checkout v1.1.0
pip install -e .
\`\`\`

## What's New

### Features
- Governance pattern X: [description]
- Enhanced monitoring for Y: [description]

### Breaking Changes
- None

### Deprecations
- [Any deprecations]

### Bug Fixes
- Fixed issue #123
- Fixed issue #456

### Security
- Patched vulnerability CVE-XXXX-XXXXX
- Enhanced encryption for Z

## Acknowledgments

Thank you to all contributors:
- @contributor1
- @contributor2

## Full Changelog
See [CHANGELOG.md](../CHANGELOG.md) for complete details.
```

#### 2.4 Verify Automated Publishing

```bash
# Check PyPI publication
curl https://pypi.org/pypi/llm-governance-toolkit/json | jq '.info.version'

# Verify package
pip install --upgrade llm-governance-toolkit

# Check documentation
# Visit: https://yourusername.github.io/llm-governance-toolkit/

# Check GitHub Release
# Visit: https://github.com/Gergo89/llm-governance-toolkit/releases
```

### Phase 3: Infrastructure Deployment

This is optional and depends on your deployment strategy.

#### 3.1 AWS Deployment

See [AWS Deployment Guide](docs/AWS_DEPLOYMENT.md) for detailed instructions.

```bash
# Initialize Terraform
cd infra/terraform/aws
terraform init -backend-config=backend.hcl

# Plan deployment
terraform plan -var-file=environments/prod.tfvars -out=tfplan

# Review plan carefully
# Check for any unexpected changes

# Apply configuration
terraform apply tfplan
```

#### 3.2 Kubernetes Deployment

See [Kubernetes Deployment Guide](docs/KUBERNETES_DEPLOYMENT.md) for detailed instructions.

```bash
# Update image tag in kustomization
# Edit infra/kubernetes/overlays/prod/kustomization.yaml

# Validate manifests
kubectl kustomize infra/kubernetes/overlays/prod | kubectl apply --dry-run=client -f -

# Deploy
kubectl apply -k infra/kubernetes/overlays/prod

# Verify deployment
kubectl rollout status deployment/app -n app --timeout=5m
```

## PyPI Publishing

### Automatic Publishing

When you push a git tag, GitHub Actions automatically:

1. Builds Python package (sdist + wheel)
2. Verifies package with twine
3. Publishes to PyPI using OIDC token
4. Uploads artifacts to GitHub Actions

### Manual Publishing (if needed)

```bash
# Build package locally
cd llm-governance-toolkit
python -m build --sdist --wheel .

# Verify package
python -m pip install twine
twine check dist/*

# Publish to TestPyPI first (optional)
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*
```

### Verify Publication

```bash
# Check package on PyPI
pip search llm-governance-toolkit  # Deprecated
# Or visit https://pypi.org/project/llm-governance-toolkit/

# Install and verify
pip install --upgrade llm-governance-toolkit
python -c "import llm_governance_toolkit; print(llm_governance_toolkit.__version__)"
```

## GitHub Release

### Automated Release Creation

GitHub Actions creates releases when you:
1. Push a version tag
2. Create release with `gh release create`

### Manual Release Updates

```bash
# Edit existing release
gh release edit v1.1.0 --notes-file new-release-notes.md

# Delete release (if needed)
gh release delete v1.1.0 --yes

# List all releases
gh release list
```

## AWS Deployment

### Pre-Deployment Checklist

- [ ] Read [AWS Deployment Guide](docs/AWS_DEPLOYMENT.md)
- [ ] Terraform state backend configured
- [ ] AWS credentials configured
- [ ] Container image built and pushed to ECR
- [ ] Production checklist items reviewed
- [ ] Team notified of deployment window

### Deployment Steps

1. Follow [AWS Deployment Guide](docs/AWS_DEPLOYMENT.md)
2. Use [Production Checklist](docs/PRODUCTION_CHECKLIST.md) before go-live
3. Monitor deployment progress
4. Verify health checks and metrics
5. Perform smoke tests

### Rollback

```bash
# Get previous deployment
terraform show

# Rollback to previous state
terraform apply -var container_image=old_image:tag
```

## Kubernetes Deployment

### Pre-Deployment Checklist

- [ ] Read [Kubernetes Deployment Guide](docs/KUBERNETES_DEPLOYMENT.md)
- [ ] Cluster access verified
- [ ] Container image pushed to registry
- [ ] Kustomize manifests validated
- [ ] Secrets configured in cluster
- [ ] Production checklist items reviewed

### Deployment Steps

1. Follow [Kubernetes Deployment Guide](docs/KUBERNETES_DEPLOYMENT.md)
2. Use [Production Checklist](docs/PRODUCTION_CHECKLIST.md)
3. Monitor rollout
4. Verify running pods and services
5. Test application endpoints

### Rollback

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/app -n app

# Verify rollback
kubectl rollout status deployment/app -n app
```

## Documentation Publishing

### Automatic Publishing

When changes are pushed to main branch:

1. GitHub Actions triggers `publish-docs.yml`
2. Builds MkDocs documentation
3. Publishes to GitHub Pages
4. Available at: `https://yourusername.github.io/llm-governance-toolkit/`

### Manual Publishing

```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Build locally
mkdocs build

# Preview
mkdocs serve  # Open http://localhost:8000

# Deploy
mkdocs gh-deploy
```

## Post-Release Tasks

### 1. Announcements

- [ ] Post on social media
- [ ] Email newsletter (if applicable)
- [ ] Update project website
- [ ] Notify stakeholders

### 2. Monitoring

- [ ] Monitor PyPI statistics
- [ ] Track GitHub release downloads
- [ ] Monitor deployment health
- [ ] Watch for issues and feedback

### 3. Documentation Updates

- [ ] Update README with new features
- [ ] Add migration guides if needed
- [ ] Update FAQ with common questions
- [ ] Archive old documentation versions

### 4. Issue Management

- [ ] Create issues for known limitations
- [ ] Tag issues appropriately
- [ ] Plan next release features
- [ ] Update project roadmap

## Troubleshooting

### PyPI Publishing Issues

**Problem:** Package fails to publish

```bash
# Check token
# Verify PyPI_API_TOKEN is set in GitHub Secrets

# Check package
cd llm-governance-toolkit
twine check dist/*

# Check version
grep "version =" pyproject.toml
```

**Solution:**
1. Fix issues locally
2. Rebuild: `python -m build`
3. Test with TestPyPI
4. Create new release tag

### GitHub Actions Failures

```bash
# View workflow logs
gh run view <run-id>

# Re-run failed job
gh run rerun <run-id>

# View specific workflow
gh run list --workflow=publish-pypi.yml
```

### Deployment Issues

See specific deployment guides:
- [AWS Troubleshooting](docs/AWS_DEPLOYMENT.md#troubleshooting)
- [Kubernetes Troubleshooting](docs/KUBERNETES_DEPLOYMENT.md#troubleshooting)

### Tag/Release Issues

```bash
# Delete local tag (if wrong)
git tag -d v1.1.0

# Delete remote tag
git push origin --delete v1.1.0

# Recreate tag
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

## Release Schedule

Suggested release cadence:

- **Patch releases (v1.0.x):** Weekly if needed
- **Minor releases (v1.x.0):** Monthly
- **Major releases (vX.0.0):** Quarterly or as needed

Communicate schedule to users via:
- GitHub Issues
- CHANGELOG.md
- Release notes
- Documentation

## Versioning

Following [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: Backward-compatible features
- **PATCH**: Backward-compatible bug fixes

Examples:
- `v1.0.0` → `v1.1.0` (new feature)
- `v1.0.0` → `v1.0.1` (bug fix)
- `v1.0.0` → `v2.0.0` (breaking change)

## Security

### Secret Management

- **PyPI Token:** Store in GitHub Secrets as `PYPI_API_TOKEN`
- **AWS Credentials:** Use OIDC federation (no static credentials)
- **Registry Credentials:** Use managed registries (ECR, GHCR)
- **Kubernetes Secrets:** Use External Secrets or similar

### GPG Signing

For additional security, sign releases:

```bash
# Configure GPG
gpg --list-secret-keys --keyid-format LONG

# Sign tag
git tag -s -a v1.1.0 -m "Release v1.1.0"

# Verify signature
git verify-tag v1.1.0
```

## Support

For issues or questions:
- GitHub Issues: [Report problems](https://github.com/Gergo89/llm-governance-toolkit/issues)
- Discussions: [Ask questions](https://github.com/Gergo89/llm-governance-toolkit/discussions)
- Documentation: [Read guides](docs/)

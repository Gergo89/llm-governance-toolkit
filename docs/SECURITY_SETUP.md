# Security Setup & Verification Guide

This guide ensures all security and compliance configurations are properly set up for the AGI project.

## Table of Contents

1. [GitHub Repository Security](#github-repository-security)
2. [Secrets Management](#secrets-management)
3. [CI/CD Security](#cicd-security)
4. [Dependency Security](#dependency-security)
5. [Code Security](#code-security)
6. [Infrastructure Security](#infrastructure-security)
7. [Compliance Checklist](#compliance-checklist)

## GitHub Repository Security

### 1. Branch Protection

Enable branch protection for main branch:

1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable these settings:
   - [ ] Require a pull request before merging
   - [ ] Require approvals (minimum: 2)
   - [ ] Dismiss stale pull request approvals
   - [ ] Require status checks to pass (CI/CD)
   - [ ] Require branches to be up to date
   - [ ] Require conversation resolution
   - [ ] Include administrators

```bash
# Verify with GitHub CLI
gh api repos/:owner/:repo/branches/main/protection
```

### 2. Require Signed Commits

Require GPG signatures for commits to main:

1. Settings → Branches → main
2. Enable "Require signed commits"

```bash
# Configure local Git
git config --global commit.gpgSign true
git config --global user.signingkey YOUR_GPG_KEY_ID
```

### 3. Enable Code Scanning

Set up GitHub code scanning:

1. Settings → Code security & analysis
2. Enable:
   - [ ] Secret scanning
   - [ ] Secret scanning push protection
   - [ ] Dependabot alerts
   - [ ] Dependabot security updates
   - [ ] Code scanning (CodeQL)

### 4. CODEOWNERS

Create `.github/CODEOWNERS`:

```
# Repository owners
* @primary-maintainer @secondary-maintainer

# Infrastructure team
infra/ @infra-team
.github/workflows/ @infra-team

# Security team
docs/THREAT-MODEL.md @security-team
SECURITY.md @security-team

# LLM Governance team
llm-governance-toolkit/ @governance-team
```

### 5. Repository Permissions

- [ ] Manage access in Settings → Collaborators
- [ ] Give minimum necessary permissions
- [ ] Use teams for group permissions
- [ ] Audit access quarterly

```bash
# List collaborators
gh api repos/:owner/:repo/collaborators

# Remove specific access
gh api repos/:owner/:repo/collaborators/username -X DELETE
```

## Secrets Management

### 1. GitHub Secrets

Set up required secrets for CI/CD:

1. Settings → Secrets & variables → Actions
2. Create these secrets:

```bash
# PyPI publishing
PYPI_API_TOKEN="your-pypi-token"  # From https://pypi.org/account/

# AWS deployment (use OIDC instead)
# AWS_ROLE_ARN="arn:aws:iam::ACCOUNT:role/github-actions"

# Container registry
REGISTRY_USERNAME="your-registry-user"
REGISTRY_PASSWORD="your-registry-password"
```

### 2. OIDC Configuration (AWS)

Set up OpenID Connect for secure AWS deployments:

```bash
# 1. Create OIDC provider in AWS IAM
aws iam create-openid-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com

# 2. Create IAM role with trust policy
# Trust GitHub repository:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:Gergo89/llm-governance-toolkit:ref:refs/heads/main"
        }
      }
    }
  ]
}

# 3. Store role ARN in GitHub
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::ACCOUNT:role/github-actions"
```

### 3. Secrets Rotation

- [ ] Rotate PyPI token yearly
- [ ] Rotate AWS credentials every 90 days
- [ ] Rotate registry passwords every 6 months
- [ ] Audit access logs monthly

```bash
# Check GitHub secrets (count only, can't list values)
gh secret list
```

### 4. Encrypted Secrets in Commits

Ensure no secrets are committed:

```bash
# Install git-secrets
brew install git-secrets

# Configure for repository
git secrets --install
git secrets --register-aws
git secrets --add-provider -- git secrets --aws-provider

# Verify
git secrets --scan

# For CI/CD
echo 'git secrets --scan' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## CI/CD Security

### 1. Workflow Permissions

Set repository-level workflow permissions:

1. Settings → Actions → General
2. Enable:
   - [ ] Actions permissions: "Allow all actions and reusable workflows"
   - [ ] Workflow permissions: "Read repository contents and packages permissions"
   - [ ] Default: "Restrict permissions to the minimum required"

### 2. Workflow Secrets

Review all workflows for secure secret handling:

**Good Example:**
```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    packages-dir: ./dist/
```

**Bad Example (Don't do this):**
```yaml
- name: Publish to PyPI
  env:
    PYPI_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
  run: |
    pip install twine
    twine upload --password $PYPI_TOKEN dist/*  # ❌ Never pass token in command
```

### 3. Third-party Actions

Review dependencies in `.github/workflows/*.yml`:

```bash
# List all action versions
grep -r "uses:" .github/workflows/ | grep "@"

# Pin actions to specific commit SHA (most secure):
# ❌ Don't use: actions/checkout@main
# ❌ Don't use: actions/checkout@v4
# ✅ Do use:   actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675 # v4.1.1
```

### 4. Audit Logs

Enable GitHub audit logs:

```bash
# View organization audit log
gh api orgs/:org/audit-log --paginate

# Monitor for:
# - Deleted secrets
# - Changed permissions
# - Modified workflows
# - Token access
```

## Dependency Security

### 1. Python Dependency Scanning

```bash
# Generate SBOM (Software Bill of Materials)
pip install pip-audit cyclonedx-bom
pip-audit

# Check for vulnerabilities
pip install safety
safety check

# Update requirements.txt with pinned versions
pip freeze > llm-governance-toolkit/requirements.txt
```

### 2. Dependabot Configuration

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/llm-governance-toolkit"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
    open-pull-requests-limit: 5
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
    commit-message:
      prefix: "chore(deps):"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
    commit-message:
      prefix: "chore(actions):"

  # Docker images (if applicable)
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    reviewers:
      - "security-team"
```

### 3. Security Advisories

- [ ] Subscribe to Python package advisories
- [ ] Monitor GitHub Security Advisories
- [ ] Set up alerts for dependencies
- [ ] Review advisories monthly

```bash
# Check for vulnerabilities
pip-audit
```

## Code Security

### 1. Secret Scanning

Enable GitHub secret scanning:

1. Settings → Code security & analysis
2. Enable "Secret scanning"
3. Enable "Push protection"

This prevents commits with secrets.

### 2. Static Code Analysis

Set up CodeQL for continuous analysis:

Create `.github/workflows/codeql.yml`:

```yaml
name: CodeQL Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '30 1 * * 0'

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest

    strategy:
      fail-fast: false
      matrix:
        language: ['python']

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: ${{ matrix.language }}

      - name: Autobuild
        uses: github/codeql-action/autobuild@v2

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
```

### 3. Code Linting

Ensure linting in CI:

```yaml
# In validate.yml or similar
- name: Lint with ruff
  run: |
    cd llm-governance-toolkit
    ruff check .
    ruff format --check .
```

### 4. Security Policy

Create `SECURITY.md`:

```markdown
# Security Policy

## Reporting Security Issues

**Do not** open a public GitHub issue for security vulnerabilities.

Instead, email security@example.com with:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response Timeline

- Acknowledgment: Within 24 hours
- Assessment: Within 48 hours
- Fix and patch: Within 7 days (for critical)

## Responsible Disclosure

We follow responsible disclosure practices and request a 90-day embargo before public disclosure.

## Security Best Practices

See docs/THREAT-MODEL.md for security architecture and mitigations.
```

## Infrastructure Security

### 1. AWS Security

Verify AWS security settings:

- [ ] Enable CloudTrail logging
- [ ] Enable GuardDuty
- [ ] Enable Security Hub
- [ ] Rotate credentials every 90 days
- [ ] Use IAM roles, not access keys
- [ ] Enable MFA for humans
- [ ] Encrypt data at rest and in transit

### 2. Kubernetes Security

Verify Kubernetes security:

- [ ] Pod Security Policies enforced
- [ ] Network Policies configured
- [ ] RBAC properly scoped
- [ ] Secrets encrypted at rest
- [ ] Audit logging enabled
- [ ] Regular security scans

### 3. Container Images

Secure container images:

```bash
# Scan image for vulnerabilities
docker scan app:latest

# Or use Trivy
trivy image app:latest

# Best practices:
# - Use minimal base images
# - Don't run as root
# - Use read-only filesystem
# - Scan before pushing to registry
```

## Compliance Checklist

### OWASP Top 10 Mitigations

- [ ] **A01:2021 - Broken Access Control**
  - RBAC configured
  - Least privilege enforced
  - See: docs/THREAT-MODEL.md

- [ ] **A02:2021 - Cryptographic Failures**
  - All data encrypted in transit (TLS)
  - Secrets stored securely (Secrets Manager)
  - See: docs/THREAT-MODEL.md

- [ ] **A03:2021 - Injection**
  - Input validation implemented
  - Parameterized queries used
  - No SQL/shell injection vulnerabilities

- [ ] **A04:2021 - Insecure Design**
  - Security architecture documented
  - Threat model completed
  - Design reviewed by security team

- [ ] **A05:2021 - Security Misconfiguration**
  - Security checklist followed
  - Default configurations hardened
  - Regular security audits scheduled

- [ ] **A06:2021 - Vulnerable Components**
  - Dependabot enabled
  - Dependencies scanned regularly
  - Updates applied promptly

- [ ] **A07:2021 - Authentication Failures**
  - Strong authentication enforced
  - MFA implemented for admins
  - Session management secure

- [ ] **A08:2021 - Software/Data Integrity Failures**
  - Commits signed
  - Code review required
  - SBOM generated

- [ ] **A09:2021 - Logging & Monitoring Failures**
  - CloudWatch logs configured
  - Audit logging enabled
  - Alarms configured for suspicious activity

- [ ] **A10:2021 - SSRF**
  - Network policies configured
  - External API calls validated
  - No server-side request forgery vulnerabilities

### Compliance Standards

- [ ] **SOC 2 Type II** (if applicable)
  - Audit logging enabled
  - Access controls documented
  - Encryption implemented
  - Monitoring configured

- [ ] **HIPAA** (if handling health data)
  - Data encryption (AES-256)
  - Audit logs retention (6 years)
  - Access controls strict
  - Incident response plan

- [ ] **GDPR** (if handling EU personal data)
  - Data retention policies
  - Right to deletion implemented
  - Data breach notification plan
  - DPA with cloud providers

- [ ] **PCI DSS** (if handling payment data)
  - Network segmentation
  - Strong encryption
  - Access control logging
  - Regular security testing

## Security Audit Checklist

Run this quarterly:

```bash
#!/bin/bash
echo "=== GitHub Repository Security Audit ==="

# Branch protection
echo "✓ Branch protection enabled on main"
gh api repos/:owner/:repo/branches/main/protection

# Secrets
echo "✓ Checking for exposed secrets"
git secrets --scan

# Dependencies
echo "✓ Checking for vulnerable dependencies"
pip-audit

# Permissions
echo "✓ Auditing repository permissions"
gh api repos/:owner/:repo/collaborators

# Audit logs
echo "✓ Checking audit logs"
gh api orgs/:org/audit-log | tail -20

echo "=== Audit Complete ==="
```

## Security Contact

For security issues, contact:
- **Email:** security@example.com
- **PGP Key:** [Include if applicable]
- **Response Time:** 24 hours

## Additional Resources

- [OWASP Top 10](https://owasp.org/Top10/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Threat Model](docs/THREAT-MODEL.md)

# Security policy

Do not report vulnerabilities in public issues. Send reports to the repository security contact and include affected components, reproduction steps, and impact. Rotate any credential that was ever committed, even if the commit is later removed.

## Baseline controls

- Use short-lived OIDC credentials in CI; never store AWS access keys as repository secrets.
- Require reviews and protected environments for production applies.
- Keep Terraform state encrypted, versioned, locked, and access-restricted.
- Pin production containers by digest and review image scan findings.
- Use Secrets Manager or External Secrets for runtime credentials.
- Periodically review public ingress, IAM policies, dependency versions, logs, backups, and restore tests.


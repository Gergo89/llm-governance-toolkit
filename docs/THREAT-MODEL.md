# Threat model

## Protected assets

- Customer and application data in PostgreSQL, Redis, and object storage.
- Runtime credentials and cloud identities.
- Infrastructure state and the production deployment path.
- Telemetry, which can itself contain sensitive data.

## Principal threats and controls

| Threat | Primary controls | Residual risk |
|---|---|---|
| Compromised application container | Non-root restricted pods, no privilege escalation, read-only root filesystem, default-deny network, no API token | Kernel or runtime escape; use sandboxed runtimes for hostile code |
| Credential theft | External secret stores, scoped task/service identity, no committed secrets | Secrets remain readable inside the process that needs them |
| Lateral movement | Namespace isolation and explicit egress ports | Port-based policy cannot authenticate an arbitrary external destination |
| Resource exhaustion | Requests, limits, quota, HPA, database storage alarms | Distributed traffic can still exhaust shared dependencies |
| Supply-chain compromise | Immutable production images, ECR scanning, reviewed CI | Tag examples must be replaced by verified digests |
| Malicious infrastructure change | Terraform review, remote-state locking, protected environments, OIDC | Cloud administrators remain a high-trust role |
| Sensitive telemetry leakage | Dedicated gateway and explicit exporter configuration | Applications must avoid recording secrets and personal data |

## Required production hardening

- Pin all container images and GitHub Actions by digest or commit SHA.
- Put a WAF and rate limits at the edge based on the application threat model.
- Use External Secrets and workload identity; prohibit manual long-lived credentials.
- Export Cathedral signals to a durable authenticated backend and define retention/redaction.
- Add a sandboxed runtime and isolated node pool before executing untrusted code.
- Test admission rejection, NetworkPolicy enforcement, backup restoration, and credential rotation.


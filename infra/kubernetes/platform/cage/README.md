# The Cage

The Cage is the workload containment boundary. A namespace opts in with the label `agi.internal/security-tier: cage`.

It enforces:

- Kubernetes Restricted Pod Security admission.
- Deny-by-default ingress and egress, with workload-specific allow rules.
- No host namespaces, host paths, host ports, privileged containers, or privilege escalation.
- Required CPU and memory requests and limits.
- Namespace quotas that prevent accidental cluster exhaustion and public Service creation.
- Service accounts without ambient API credentials unless explicitly required.

The admission policy requires Kubernetes 1.30 or newer. A CNI that enforces NetworkPolicy is required. Namespace administrators must not be able to alter the Cage label, policy bindings, or cluster admission policies; enforce that separation through cluster RBAC and cloud IAM.

The Cage reduces blast radius. It does not make untrusted code safe by itself. For hostile multi-tenancy, additionally select a sandboxed runtime such as gVisor or Kata Containers and isolate nodes and cloud identities.


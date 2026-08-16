# The Cathedral

The Cathedral is the operability and service-governance layer around Cage workloads. It gives every service one contract for ownership, health, dependencies, telemetry, and reliability objectives.

The deployed OpenTelemetry gateway accepts OTLP over gRPC or HTTP, enriches signals with Kubernetes metadata, exposes metrics in Prometheus format, and sends traces and logs to the debug exporter until a production backend is selected. Replace the debug exporters with authenticated OTLP exporters for the chosen observability system before production.

The `cathedral-service-contract` ConfigMap is intentionally machine-readable. It can become the input to a service catalog, documentation generator, deployment checks, and SLO alert generation without changing the application contract.

The collector is pinned to an official release verified when this baseline was authored. Production should pin the image by digest and update it through dependency automation.

Because native NetworkPolicy cannot portably select the Kubernetes API service, the collector's egress rule permits TCP 443 so metadata enrichment works across managed clusters. Tighten that rule to the control-plane CIDR or use the CNI's service/FQDN policy once the target cluster is known.

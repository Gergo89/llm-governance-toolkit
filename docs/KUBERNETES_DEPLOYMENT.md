# Kubernetes Deployment Guide

This guide provides comprehensive instructions for deploying the AGI platform to Kubernetes clusters.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Cluster Setup](#cluster-setup)
4. [Kustomize Configuration](#kustomize-configuration)
5. [Deployment Process](#deployment-process)
6. [Configuration Management](#configuration-management)
7. [Storage and Persistence](#storage-and-persistence)
8. [Networking and Ingress](#networking-and-ingress)
9. [Security](#security)
10. [Monitoring and Logging](#monitoring-and-logging)
11. [Scaling and Auto-scaling](#scaling-and-auto-scaling)
12. [Troubleshooting](#troubleshooting)
13. [Upgrade Procedures](#upgrade-procedures)

## Prerequisites

### Required Tools

- **kubectl** v1.31.4 or later
  ```bash
  kubectl version --client
  ```
- **Kustomize** v5.0+
  ```bash
  kustomize version
  ```
- **Helm** (optional, for package management)
- **Docker** (for building application images)

### Kubernetes Cluster

- **Cluster version:** 1.26+ (EKS, GKE, AKS, or self-managed)
- **Node count:** 3+ for HA
- **Node type:** At least 2 CPU, 4GB RAM per node
- **Storage:** Persistent volume provisioner configured
- **Ingress Controller:** NGINX, Traefik, or similar
- **Cluster DNS:** CoreDNS or equivalent
- **RBAC:** Enabled
- **Network Policy:** Supported and enabled

### Cluster Roles and Permissions

Ensure your user/service account has permissions to:
- Create/update/delete Deployments, Services, Ingress
- Manage ConfigMaps and Secrets
- Create PersistentVolumeClaims
- Manage Namespaces
- View cluster resources and logs

```bash
# Verify cluster access
kubectl cluster-info
kubectl auth can-i create deployments --as=system:serviceaccount:default:deployer
```

## Architecture Overview

### Kubernetes Resources

```
┌─────────────────────────────────────────────────┐
│           Ingress (TLS Termination)             │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼─────────────────┐  ┌────▼──────────────────┐
│  Service (ClusterIP)│  │  Service (LoadBalancer)
└───┬─────────────────┘  └────┬──────────────────┘
    │                         │
┌───▼──────────────────────────▼────────────────┐
│          Deployment (Replicas)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Pod      │  │ Pod      │  │ Pod      │   │
│  │ (App)    │  │ (App)    │  │ (App)    │   │
│  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────────────────────────────┘

External Databases:
┌──────────────────────────────────────────┐
│  ConfigMaps (configuration)              │
│  Secrets (credentials)                   │
│  PersistentVolumeClaims (if needed)      │
└──────────────────────────────────────────┘
```

## Cluster Setup

### 1. Create Namespace

```bash
# Create application namespace
kubectl create namespace app

# Set default namespace
kubectl config set-context --current --namespace=app

# Label namespace
kubectl label namespace app environment=production
```

### 2. Set Up RBAC

Create service account for deployment:

```yaml
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-deployer
  namespace: app
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-deployer
  namespace: app
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["services", "pods", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-deployer
  namespace: app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: app-deployer
subjects:
- kind: ServiceAccount
  name: app-deployer
  namespace: app
```

### 3. Configure Storage Classes

```bash
# Verify storage class available
kubectl get storageclass

# Create custom storage class if needed
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: app-storage
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
allowVolumeExpansion: true
EOF
```

### 4. Set Up Network Policies

Enable network policies:

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-network-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # For external APIs
    - protocol: TCP
      port: 5432 # PostgreSQL
    - protocol: TCP
      port: 6379 # Redis
  - to:
    - podSelector: {}  # Allow DNS
    ports:
    - protocol: UDP
      port: 53
```

## Kustomize Configuration

### Directory Structure

```
infra/kubernetes/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secret.yaml
├── overlays/
│   ├── dev/
│   │   └── kustomization.yaml
│   └── prod/
│       ├── kustomization.yaml
│       ├── replicas.yaml
│       ├── resources.yaml
│       └── hpa.yaml
└── platform/
    └── ingress.yaml
```

### Base Configuration

Example `infra/kubernetes/base/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: app

resources:
- deployment.yaml
- service.yaml
- configmap.yaml

commonLabels:
  app: app
  managed-by: kustomize

commonAnnotations:
  description: "AGI Application Platform"
```

### Environment Overlays

Example `infra/kubernetes/overlays/prod/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
- ../../base

namespace: app

replicas:
- name: app
  count: 3

patchesStrategicMerge:
- replicas.yaml
- resources.yaml

patchesJson6902:
- target:
    group: apps
    version: v1
    kind: Deployment
    name: app
  patch: |-
    - op: replace
      path: /spec/strategy/type
      value: RollingUpdate

resources:
- hpa.yaml
- ../../platform/ingress.yaml

commonLabels:
  environment: production

configMapGenerator:
- name: app-config
  literals:
  - ENVIRONMENT=production
  - LOG_LEVEL=info
  files:
  - config.properties

secretGenerator:
- name: app-secrets
  envs:
  - .env.prod
  options:
    annotations:
      kustomize.config.k8s.io/needs-hash: "true"
```

## Deployment Process

### 1. Build and Push Container Image

```bash
# Build image
docker build -t app:v1.0.0 .

# Tag for registry
docker tag app:v1.0.0 your-registry.azurecr.io/app:v1.0.0

# Push to registry
docker push your-registry.azurecr.io/app:v1.0.0
```

### 2. Validate Kustomize Configuration

```bash
# Render dev environment
kubectl kustomize infra/kubernetes/overlays/dev

# Render production environment
kubectl kustomize infra/kubernetes/overlays/prod

# Validate YAML syntax
kubectl kustomize infra/kubernetes/overlays/prod | kubectl apply --dry-run=client -f -
```

### 3. Create Secrets

```bash
# Create database credentials secret
kubectl create secret generic db-credentials \
  --from-literal=username=postgres \
  --from-literal=password=your-password \
  -n app \
  --dry-run=client \
  -o yaml | kubectl apply -f -

# Create image pull secret (if using private registry)
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.azurecr.io \
  --docker-username=username \
  --docker-password=password \
  -n app
```

### 4. Deploy Application

```bash
# Dry run to verify
kubectl apply -k infra/kubernetes/overlays/prod --dry-run=client -o wide

# Apply configuration
kubectl apply -k infra/kubernetes/overlays/prod

# Verify deployment
kubectl rollout status deployment/app -n app --timeout=5m

# Check pods
kubectl get pods -n app -o wide
```

### 5. Verify Deployment

```bash
# Check pod status
kubectl get pods -n app --watch

# View pod logs
kubectl logs -n app deployment/app --tail=100 -f

# Describe deployment
kubectl describe deployment app -n app

# Port forward for testing
kubectl port-forward -n app svc/app 8080:8080

# Test endpoint
curl http://localhost:8080/health
```

## Configuration Management

### ConfigMaps

Store non-sensitive configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: app
data:
  application.properties: |
    server.port=8080
    server.servlet.context-path=/api
    spring.profiles.active=production
    logging.level.root=INFO
  database.url: "postgresql://postgres-service:5432/app"
  redis.url: "redis://redis-service:6379"
```

### Secrets

Store sensitive data:

```bash
# Create from files
kubectl create secret generic app-secrets \
  --from-file=tls.crt=./certs/tls.crt \
  --from-file=tls.key=./certs/tls.key \
  -n app

# Create from literal
kubectl create secret generic api-keys \
  --from-literal=api-key=your-api-key \
  --from-literal=api-secret=your-secret \
  -n app
```

### Environment Variables in Pods

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: database.url
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        - name: ENVIRONMENT
          value: "production"
```

## Storage and Persistence

### PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
  namespace: app
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: app-storage
  resources:
    requests:
      storage: 10Gi
```

### Volume Mounts

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - name: app
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /etc/app
          readOnly: true
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: app-data
      - name: config
        configMap:
          name: app-config
```

## Networking and Ingress

### Service Configuration

```yaml
apiVersion: v1
kind: Service
metadata:
  name: app
  namespace: app
spec:
  type: ClusterIP
  selector:
    app: app
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
  sessionAffinity: None
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: app
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - yourdomain.com
    secretName: app-tls-cert
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app
            port:
              number: 80
```

## Security

### Security Context

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: app
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
```

### Pod Security Policies/Standards

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
  - ALL
  volumes:
  - 'configMap'
  - 'emptyDir'
  - 'projected'
  - 'secret'
  - 'downwardAPI'
  - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'MustRunAs'
```

## Monitoring and Logging

### Resource Requests and Limits

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Liveness and Readiness Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - name: app
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

### Logging

```bash
# View pod logs
kubectl logs -n app deployment/app

# View logs with filtering
kubectl logs -n app deployment/app --grep=ERROR

# View logs from all pods in deployment
kubectl logs -n app -l app=app --all-containers=true -f

# Get logs for previous pod instance
kubectl logs -n app pod-name --previous
```

### Metrics

```bash
# View pod resource usage
kubectl top pods -n app

# View node resource usage
kubectl top nodes

# Describe resource usage
kubectl describe pod -n app pod-name
```

## Scaling and Auto-scaling

### Manual Scaling

```bash
# Scale deployment to 5 replicas
kubectl scale deployment app -n app --replicas=5

# Verify scaling
kubectl get deployment app -n app
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 15
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
```

## Troubleshooting

### Pod Issues

```bash
# Check pod status and events
kubectl describe pod -n app pod-name

# View pod logs
kubectl logs -n app pod-name --tail=100

# Execute command in pod
kubectl exec -it -n app pod-name -- /bin/sh

# Check pod YAML
kubectl get pod -n app pod-name -o yaml
```

### Deployment Issues

```bash
# Check deployment status
kubectl describe deployment -n app app

# View deployment rollout history
kubectl rollout history deployment/app -n app

# Rollback to previous deployment
kubectl rollout undo deployment/app -n app --to-revision=2

# Check deployment replicas
kubectl get deployment -n app app -o wide
```

### Network Issues

```bash
# Test DNS
kubectl exec -n app pod-name -- nslookup app

# Test service connectivity
kubectl run -it -n app --rm debug --image=nicolaka/netshoot --restart=Never -- bash
# Inside: curl http://app:80

# Check service endpoints
kubectl get endpoints -n app

# Check ingress status
kubectl describe ingress -n app app-ingress
```

## Upgrade Procedures

### Rolling Update

```bash
# Update image in deployment
kubectl set image deployment/app \
  -n app \
  app=your-registry/app:v1.1.0

# Monitor rollout
kubectl rollout status deployment/app -n app --timeout=5m

# Check rollout history
kubectl rollout history deployment/app -n app
```

### Kustomize-based Update

```bash
# Update image reference in kustomization.yaml
# Then apply
kubectl apply -k infra/kubernetes/overlays/prod

# Verify rollout
kubectl rollout status deployment/app -n app
```

### Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/app -n app

# Rollback to specific revision
kubectl rollout undo deployment/app -n app --to-revision=3

# Verify rollback
kubectl get deployment app -n app
```

## Useful Commands

```bash
# Namespace operations
kubectl get namespace
kubectl describe namespace app

# Resource operations
kubectl get all -n app
kubectl describe pod,svc,deployment -n app

# Debugging
kubectl get events -n app --sort-by='.lastTimestamp'
kubectl logs -n app deployment/app --all-containers=true --tail=200

# Configuration
kubectl get configmap -n app
kubectl get secret -n app
kubectl edit configmap app-config -n app
```

## Next Steps

1. Set up Prometheus/Grafana for monitoring
2. Configure log aggregation (ELK, Loki, etc.)
3. Implement CI/CD pipeline for automatic deployments
4. Set up GitOps workflow (ArgoCD, Flux)
5. Configure certificate management (cert-manager)
6. Implement service mesh (Istio, Linkerd)

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Ingress-NGINX Documentation](https://kubernetes.github.io/ingress-nginx/)
- [AGI Architecture Guide](../ARCHITECTURE.md)
- [AGI Threat Model](../THREAT-MODEL.md)

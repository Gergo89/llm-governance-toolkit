#!/usr/bin/env bash
set -euo pipefail

test_namespace="cage-contract-test"

if ! kubectl get validatingadmissionpolicy cage-pod-boundary >/dev/null 2>&1; then
  echo "Cage admission policy is not installed in the current cluster." >&2
  exit 1
fi

cleanup() {
  kubectl delete namespace "${test_namespace}" --ignore-not-found --wait=false >/dev/null
}
trap cleanup EXIT

kubectl create namespace "${test_namespace}" >/dev/null
kubectl label namespace "${test_namespace}" \
  agi.internal/security-tier=cage \
  pod-security.kubernetes.io/enforce=restricted >/dev/null

kubectl apply --dry-run=server -f tests/cage/allowed.yaml >/dev/null

if kubectl apply --dry-run=server -f tests/cage/denied-privileged.yaml >/dev/null 2>&1; then
  echo "FAIL: Cage admitted a privileged pod." >&2
  exit 1
fi

if kubectl apply --dry-run=server -f tests/cage/denied-hostpath.yaml >/dev/null 2>&1; then
  echo "FAIL: Cage admitted a hostPath pod." >&2
  exit 1
fi

echo "PASS: Cage accepted the compliant pod and rejected both escape attempts."


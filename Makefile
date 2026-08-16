.PHONY: help local-up local-down local-logs validate fmt terraform-init terraform-plan k8s-render cage-test

TF_DIR := infra/terraform/aws
ENV ?= dev

help:
	@echo "local-up       Start local data and observability services"
	@echo "local-down     Stop local services"
	@echo "validate       Validate Terraform, Compose, and Kubernetes YAML"
	@echo "terraform-plan Plan AWS infrastructure (ENV=dev|staging|prod)"
	@echo "k8s-render     Render the Kubernetes overlay (ENV=dev|prod)"
	@echo "cage-test      Test Cage admission against the current cluster"

local-up:
	docker compose up -d

local-down:
	docker compose down

local-logs:
	docker compose logs -f

fmt:
	terraform -chdir=$(TF_DIR) fmt -recursive

terraform-init:
	terraform -chdir=$(TF_DIR) init

terraform-plan: terraform-init
	terraform -chdir=$(TF_DIR) plan -var-file=environments/$(ENV).tfvars

k8s-render:
	kubectl kustomize infra/kubernetes/overlays/$(ENV)

cage-test:
	bash scripts/test-cage.sh

validate:
	docker compose config --quiet
	terraform -chdir=$(TF_DIR) fmt -check -recursive
	terraform -chdir=$(TF_DIR) init -backend=false
	terraform -chdir=$(TF_DIR) validate
	kubectl kustomize infra/kubernetes/overlays/dev > /dev/null
	kubectl kustomize infra/kubernetes/overlays/prod > /dev/null

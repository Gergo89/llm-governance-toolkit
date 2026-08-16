.PHONY: help local-up local-down local-logs validate fmt terraform-init terraform-plan k8s-render cage-test version-current version-bump build-pkg test-pkg publish-release

TF_DIR := infra/terraform/aws
ENV ?= dev

help:
	@echo "Local Development"
	@echo "  local-up       Start local data and observability services"
	@echo "  local-down     Stop local services"
	@echo "  validate       Validate Terraform, Compose, and Kubernetes YAML"
	@echo ""
	@echo "Infrastructure"
	@echo "  terraform-plan Plan AWS infrastructure (ENV=dev|staging|prod)"
	@echo "  k8s-render     Render the Kubernetes overlay (ENV=dev|prod)"
	@echo "  cage-test      Test Cage admission against the current cluster"
	@echo ""
	@echo "Publishing & Release"
	@echo "  version-current       Show current version"
	@echo "  version-bump [type]   Bump version: major, minor, or patch"
	@echo "  build-pkg             Build Python package distribution"
	@echo "  test-pkg              Verify built package with twine"
	@echo "  publish-release       Create GitHub release (requires tag)"

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

# Version management
version-current:
	@python scripts/manage-version.py current

version-bump:
	@python scripts/manage-version.py bump $(BUMP_TYPE)

# Package building and publishing
build-pkg:
	cd llm-governance-toolkit && python -m build --sdist --wheel .

test-pkg: build-pkg
	python -m pip install --upgrade twine
	cd llm-governance-toolkit && twine check dist/*

publish-release:
	@echo "To publish a release:"
	@echo "1. Update version: make version-bump BUMP_TYPE=minor"
	@echo "2. Update CHANGELOG.md"
	@echo "3. Commit and tag: git tag -a v<version> -m 'Release v<version>'"
	@echo "4. Push: git push && git push --tags"
	@echo "5. GitHub Actions will automatically publish to PyPI"
	@echo ""
	@echo "Visit: https://github.com/Gergo89/llm-governance-toolkit/actions/workflows/publish-pypi.yml"

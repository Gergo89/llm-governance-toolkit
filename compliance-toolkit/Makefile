PY ?= python3
export PYTHONPATH := src

.PHONY: help install test lint validate report crosswalks eval clean

help:
	@echo "install     install the package with dev extras"
	@echo "test        run the test suite"
	@echo "lint        run ruff if available"
	@echo "validate    run schema + policy-as-code checks over the registry"
	@echo "report      write reports/portfolio.md"
	@echo "crosswalks  regenerate the generated crosswalk tables"
	@echo "eval        run the probe suite against the reference stubs"

install:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q || $(PY) -m unittest discover -s tests -t .

lint:
	-$(PY) -m ruff check src tests

validate:
	$(PY) -m llm_governance.cli validate

report:
	@mkdir -p reports
	$(PY) -m llm_governance.cli report -o reports/portfolio.md

crosswalks:
	$(PY) -m llm_governance.cli crosswalk eu_ai_act  -o compliance/eu-ai-act/generated-crosswalk.md
	$(PY) -m llm_governance.cli crosswalk nist_ai_rmf -o compliance/nist-ai-rmf/generated-crosswalk.md
	$(PY) -m llm_governance.cli crosswalk iso_42001   -o compliance/iso-42001/generated-crosswalk.md

eval:
	$(PY) -m llm_governance.cli eval --stub compliant

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ build dist *.egg-info

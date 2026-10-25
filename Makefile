.PHONY: help install lint typecheck test test-unit test-integration test-security test-fault iac-fmt iac-validate verify-all clean

PYTHON ?= python

help:
	@echo "Federated Cyber Shield (FCS) v1.2 - Phase 1 Foundation"
	@echo "Zero-Cost Build and Verification Commands:"
	@echo "  make lint           - Run ruff linter"
	@echo "  make typecheck      - Run mypy strict type checker"
	@echo "  make test           - Run all offline pytest test suites"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-security  - Run tenant isolation and security tests"
	@echo "  make test-fault     - Run fault-injection and resilience tests"
	@echo "  make iac-fmt        - Check OpenTofu code formatting"
	@echo "  make iac-validate   - Validate OpenTofu modules statically"
	@echo "  make verify-all     - Run full offline zero-cost verification suite"
	@echo "  make clean          - Remove temporary test/cache files"

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check --fix .

typecheck:
	$(PYTHON) -m mypy packages services adapters tools tests

test:
	$(PYTHON) -m pytest tests/

test-unit:
	$(PYTHON) -m pytest -m unit tests/

test-integration:
	$(PYTHON) -m pytest -m integration tests/

test-security:
	$(PYTHON) -m pytest -m security tests/

test-fault:
	$(PYTHON) -m pytest -m fault_injection tests/

iac-fmt:
	tofu fmt -check -recursive infrastructure/opentofu/

iac-validate:
	cd infrastructure/opentofu/environments/dev && tofu init -backend=false && tofu validate

verify-all: lint typecheck test iac-fmt iac-validate
	$(PYTHON) scripts/verify_all.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Makefile for Smart Contract Testing and Development

# Python and pip commands
PYTHON := python3
PIP := pip3

# Test directories
TESTS_DIR := tests
UNIT_TESTS := tests/unit
INTEGRATION_TESTS := tests/integration  
EMULATOR_TESTS := tests/emulator
VALIDATION_TESTS := tests/validation

# Coverage settings
COVERAGE_MIN := 35
COVERAGE_REPORT := htmlcov

.PHONY: help install install-dev test test-unit test-integration test-emulator test-validation test-property test-all coverage clean lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  install       - Install production dependencies"
	@echo "  install-dev   - Install development dependencies" 
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-emulator - Run emulator tests only"
	@echo "  test-validation - Run validation tests only"
	@echo "  test-property - Run property-based tests only"
	@echo "  coverage      - Run tests with coverage report"
	@echo "  lint          - Run code linting"
	@echo "  format        - Format code with black"
	@echo "  clean         - Clean up generated files"

# Install dependencies
install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

# Test commands
test: test-all

test-unit:
	@echo "Running unit tests..."
	pytest $(UNIT_TESTS)/test_simple_contract.py -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/test_simple_integration.py -v

test-emulator:
	@echo "Running emulator tests..."
	pytest $(EMULATOR_TESTS) -v -m "emulator or not slow"

test-validation:
	@echo "Running validation tests..."
	pytest $(VALIDATION_TESTS) -v

test-property:
	@echo "Running property-based tests..."
	pytest $(UNIT_TESTS)/test_property_based.py -v -m "property"

test-all:
	@echo "Running all working tests..."
	pytest $(UNIT_TESTS)/test_simple_contract.py tests/integration/test_simple_integration.py $(VALIDATION_TESTS) $(EMULATOR_TESTS) $(UNIT_TESTS)/test_property_based.py -v

# Test with coverage
coverage:
	@echo "Running tests with coverage..."
	pytest $(UNIT_TESTS)/test_simple_contract.py tests/integration/test_simple_integration.py $(VALIDATION_TESTS) $(EMULATOR_TESTS) $(UNIT_TESTS)/test_property_based.py \
		--cov=onchain --cov-report=html --cov-report=term-missing \
		--cov-fail-under=$(COVERAGE_MIN)
	@echo "Coverage report generated in $(COVERAGE_REPORT)/"

# Code quality
lint:
	@echo "Running code linting..."
	flake8 onchain/ offchain/ model-inference/ --max-line-length=100 --ignore=E203,W503
	mypy onchain/ offchain/ model-inference/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	black onchain/ offchain/ model-inference/ tests/ --line-length=100

# Cleanup
clean:
	@echo "Cleaning up..."
	rm -rf $(COVERAGE_REPORT)/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage
	rm -rf tests/validation_artifacts/

# Quick validation check
check: lint test-unit
	@echo "Quick validation passed!"

# Full CI pipeline
ci: install-dev lint test coverage
	@echo "CI pipeline completed!"

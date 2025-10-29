## Convenience Makefile for stac-mcp development and integration testing

COMPOSE_FILE ?= docker-compose.stac.yml

# Detect virtual environment directory (prefer .venv then venv). This repo uses 'uv' to create a venv
VENV_DIR ?= $(shell if [ -d ".venv" ]; then echo ".venv"; elif [ -d "venv" ]; then echo "venv"; else echo ".venv"; fi)

# Prefer venv-provided python/pip when available, otherwise fall back to system
PYTHON := $(if $(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python,python3)
PIP := $(PYTHON) -m pip

# Tool binaries: prefer venv-installed CLI, fallback to python -m <module> or system binary
UVICORN := $(if $(wildcard $(VENV_DIR)/bin/uvicorn),$(VENV_DIR)/bin/uvicorn,$(PYTHON) -m uvicorn)
PYTEST := $(if $(wildcard $(VENV_DIR)/bin/pytest),$(VENV_DIR)/bin/pytest,pytest)
RUFF := $(if $(wildcard $(VENV_DIR)/bin/ruff),$(VENV_DIR)/bin/ruff,$(PYTHON) -m ruff)
COVERAGE := $(if $(wildcard $(VENV_DIR)/bin/coverage),$(VENV_DIR)/bin/coverage,coverage)

.PHONY: help install install-editable install-dev run-package stac-run stac-up stac-load stac-test stac-down format lint test coverage stac-validate clean

help:
	@echo "Available targets:"
	@echo "  install           Install package (pip install .)"
	@echo "  install-editable  Install package in editable mode (pip install -e .)"
	@echo "  install-dev       Install dev dependencies (editable with dev extras)."
	@echo "  run-package       Run the installed package (python -m stac_mcp)."
	@echo "  stac-run          Run the lightweight in-repo STAC test server (uvicorn)."
	@echo "  stac-up           Start integration stack (PostGIS + stac-fastapi) via docker-compose."
	@echo "  stac-load         Load test-data into the running integration server."
	@echo "  stac-test         Run integration tests (uses in-repo server tests by default)."
	@echo "  stac-down         Tear down the integration stack."
	@echo "  format            Run ruff format on repository files."
	@echo "  lint              Run ruff check and try to fix auto-fixable issues."
	@echo "  test              Run the full test suite (pytest)."
	@echo "  coverage          Run coverage report for tests."
	@echo "  stac-validate     Run stac-api-validator against http://localhost:8080 (docker image)."
	@echo "  clean             Remove common build/test artifacts."

install:
	@echo "Installing package..."
	$(PIP) install .

install-editable:
	@echo "Installing package in editable mode..."
	$(PIP) install -e .

install-dev:
	@echo "Installing dev dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run-package:
	@echo "Running stac-mcp package (python -m stac_mcp)"
	$(PYTHON) -m stac_mcp

stac-run:
	@echo "Starting lightweight in-repo STAC test server on http://localhost:8080"
	$(UVICORN) tests.support.stac_test_server:app --reload --port 8080

stac-up:
	@echo "Bringing up integration stack (PostGIS + stac-fastapi)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "Waiting for stac-api to be ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
	  if curl -fsS http://localhost:8080/ >/dev/null 2>&1; then \
	    echo "stac-api ready" && break; \
	  fi; \
	  echo "waiting..." && sleep 2; \
	done

stac-load:
	@echo "Loading test-data into integration server"
	$(PYTHON) scripts/load_test_data.py

stac-test:
	@echo "Running integration tests (in-repo server tests)"
	$(PYTEST) -q tests/integration -k "stac_server"

stac-down:
	@echo "Tearing down integration stack"
	docker-compose -f $(COMPOSE_FILE) down -v

format:
	@echo "Formatting source with ruff"
	$(RUFF) format stac_mcp/ tests/ examples/ || true

lint:
	@echo "Running ruff checks and attempting to auto-fix"
	$(RUFF) check stac_mcp/ tests/ examples/ --fix || true

test:
	@echo "Running full test suite"
	$(PYTEST) -v

coverage:
	@echo "Running tests with coverage"
	$(COVERAGE) run -m pytest && $(COVERAGE) report -m

stac-validate:
	@echo "Running stac-api-validator against http://localhost:8080"
	docker run --rm stacutils/stac-api-validator --url http://localhost:8080 || true

clean:
	@echo "Cleaning build/test artifacts"
	rm -rf build/ dist/ .pytest_cache/ $(VENV_DIR)/ __pycache__/ .cache/ .ruff_cache/ .coverage
## Convenience Makefile for stac-mcp development and integration testing

COMPOSE_FILE ?= docker-compose.stac.yml

# Detect virtual environment directory (prefer .venv then venv). This repo uses 'uv' to create a venv
VENV_DIR ?= $(shell if [ -d ".venv" ]; then echo ".venv"; elif [ -d "venv" ]; then echo "venv"; else echo ".venv"; fi)

# Prefer venv-provided python/pip when available, otherwise fall back to system
PYTHON := $(if $(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python,python3)
PIP := $(PYTHON) -m pip

# Tool binaries: prefer venv-installed CLI, fallback to python -m <module> or system binary
UVICORN := $(if $(wildcard $(VENV_DIR)/bin/uvicorn),$(VENV_DIR)/bin/uvicorn,$(PYTHON) -m uvicorn)
PYTEST := $(if $(wildcard $(VENV_DIR)/bin/pytest),$(VENV_DIR)/bin/pytest,pytest)
RUFF := $(if $(wildcard $(VENV_DIR)/bin/ruff),$(VENV_DIR)/bin/ruff,$(PYTHON) -m ruff)
COVERAGE := $(if $(wildcard $(VENV_DIR)/bin/coverage),$(VENV_DIR)/bin/coverage,coverage)

.PHONY: help install install-editable install-dev run-package stac-run stac-up stac-load stac-test stac-down format lint test coverage stac-validate clean

help:
	@echo "Available targets:"
	@echo "  install           Install package (pip install .)"
	@echo "  install-editable  Install package in editable mode (pip install -e .)"
	@echo "  install-dev       Install dev dependencies (editable with dev extras)."
	@echo "  run-package       Run the installed package (python -m stac_mcp)."
	@echo "  stac-run          Run the lightweight in-repo STAC test server (uvicorn)."
	@echo "  stac-up           Start integration stack (PostGIS + stac-fastapi) via docker-compose."
	@echo "  stac-load         Load test-data into the running integration server."
	@echo "  stac-test         Run integration tests (uses in-repo server tests by default)."
	@echo "  stac-down         Tear down the integration stack."
	@echo "  format            Run ruff format on repository files."
	@echo "  lint              Run ruff check and try to fix auto-fixable issues."
	@echo "  test              Run the full test suite (pytest)."
	@echo "  coverage          Run coverage report for tests."
	@echo "  stac-validate     Run stac-api-validator against http://localhost:8080 (docker image)."
	@echo "  clean             Remove common build/test artifacts."

install:
	@echo "Installing package..."
	$(PIP) install .

install-editable:
	@echo "Installing package in editable mode..."
	$(PIP) install -e .

install-dev:
	@echo "Installing dev dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run-package:
	@echo "Running stac-mcp package (python -m stac_mcp)"
	$(PYTHON) -m stac_mcp

stac-run:
	@echo "Starting lightweight in-repo STAC test server on http://localhost:8080"
	$(PYTHON) -m uvicorn tests.support.stac_test_server:app --reload --port 8080

stac-up:
	@echo "Bringing up integration stack (PostGIS + stac-fastapi)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "Waiting for stac-api to be ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
	  if curl -fsS http://localhost:8080/ >/dev/null 2>&1; then \
	    echo "stac-api ready" && break; \
	  fi; \
	  echo "waiting..." && sleep 2; \
	done

stac-load:
	@echo "Loading test-data into integration server"
	$(PYTHON) scripts/load_test_data.py

stac-test:
	@echo "Running integration tests (in-repo server tests)"
	pytest -q tests/integration -k "stac_server"

stac-down:
	@echo "Tearing down integration stack"
	docker-compose -f $(COMPOSE_FILE) down -v

format:
	@echo "Formatting source with ruff"
	ruff format stac_mcp/ tests/ examples/ || true

lint:
	@echo "Running ruff checks and attempting to auto-fix"
	ruff check stac_mcp/ tests/ examples/ --fix || true

test:
	@echo "Running full test suite"
	pytest -v

coverage:
	@echo "Running tests with coverage"
	coverage run -m pytest && coverage report -m

stac-validate:
	@echo "Running stac-api-validator against http://localhost:8080"
	docker run --rm stacutils/stac-api-validator --url http://localhost:8080 || true

clean:
	@echo "Cleaning build/test artifacts"
	rm -rf build/ dist/ .pytest_cache/ .venv/ __pycache__/ .cache/ .ruff_cache/ .coverage

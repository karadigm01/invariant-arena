.PHONY: bootstrap check test smoke kb-check all-report all-report-fix-status resolver-report component-report status status-check summary-check coverage-snapshot refresh-artifacts

PYTHONPATH_SRC := $(CURDIR)/src
SYSTEM_PYTHON := /usr/bin/python3
VENV_PYTHON := $(CURDIR)/.venv/bin/python
PYTHON := $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(SYSTEM_PYTHON))
TEST_FILES := tests/test_core_reference.py tests/test_workspace_health.py tests/test_metadata_integrity.py tests/test_kb_integrity.py tests/test_rules.py tests/test_system_status.py tests/test_cli_entrypoints.py tests/test_resolver_registry.py

bootstrap:
	$(SYSTEM_PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest $(TEST_FILES)

smoke:
	$(PYTHON) -m inf_work workspace . --pretty

kb-check:
	$(PYTHON) -m inf_work kb . --pretty

all-report:
	$(PYTHON) -m inf_work all . --pretty

all-report-fix-status:
	$(PYTHON) -m inf_work all . --pretty --fix-status

resolver-report:
	$(PYTHON) -m inf_work all . --pretty --profile resolver-only

component-report:
	$(PYTHON) -m inf_work all . --pretty --profile component-governance

status:
	$(PYTHON) -m inf_work status . --pretty

status-check:
	$(PYTHON) -m inf_work status-check . --pretty

summary-check:
	$(PYTHON) -m inf_work summary-check . --pretty

coverage-snapshot:
	$(PYTHON) -m inf_work coverage-snapshot . --pretty

refresh-artifacts:
	$(PYTHON) -m inf_work refresh-artifacts . --pretty

check:
	$(MAKE) test
	$(MAKE) smoke
	$(MAKE) kb-check
	$(MAKE) status
	$(MAKE) status-check

default: check

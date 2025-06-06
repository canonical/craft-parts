SOURCES=$(wildcard *.py) craft_parts tests

UV_FROZEN:=true

.PHONY: help
help: ## Show this help.
	@printf "%-30s %s\n" "Target" "Description"
	@printf "%-30s %s\n" "------" "-----------"
	@fgrep " ## " $(MAKEFILE_LIST) | fgrep -v grep | awk -F ': .*## ' '{$$1 = sprintf("%-30s", $$1)} 1'

.PHONY: autoformat
autoformat: ## Run automatic code formatters.
	autoflake --remove-all-unused-imports --ignore-init-module-imports -ri $(SOURCES)
	ruff check --fix $(SOURCES)
	ruff format $(SOURCES)

.PHONY: clean
clean: ## Clean artifacts from building, testing, etc.
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	rm -rf docs/_build/
	rm -f docs/craft_parts.*
	rm -f docs/modules.rst
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
	rm -rf .tox/
	rm -f .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache

.PHONY: coverage
coverage: ## Run pytest with coverage report.
	coverage run --source craft_parts -m pytest tests/unit
	coverage report -m
	coverage xml

.PHONY: preparedocs
preparedocs: ## move file from the sphinx-starter-pack to docs folder
	cp docs/sphinx-resources/.sphinx/_static/* docs/_static
	mkdir -p docs/_templates
	cp -R docs/sphinx-resources/.sphinx/_templates/* docs/_templates
	cp docs/sphinx-resources/.sphinx/spellingcheck.yaml docs/spellingcheck.yaml

.PHONY: installdocs
installdocs: preparedocs ## install documentation dependencies.
	$(MAKE) -C docs install

.PHONY: docs
docs: ## Generate documentation.
	rm -f docs/craft_parts.rst
	rm -f docs/modules.rst
	pip install -r docs/requirements.txt
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

.PHONY: dist
dist: clean ## Build python package.
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

.PHONY: install
install: clean ## Install python package.
	python setup.py install

.PHONY: lint
lint: test-codespell test-ruff test-mypy test-pydocstyle test-pyright ## Run all linting tests

.PHONY: release
release: dist ## Release with twine.
	twine upload dist/*

.PHONY: test-black
test-black: test-ruff
	@echo "\033[0;31mWARNING\033[0m: Switched from black to ruff"

.PHONY: test-codespell
test-codespell:
	codespell $(SOURCES) --ignore-words-list crate

.PHONY: test-flake8
test-flake8:
	echo "\033[0;31mWARNING\033[0m: Did you mean to run \`make ruff\`?"
	flake8 $(SOURCES)

.PHONY: test-ruff lint-ruff
test-ruff lint-ruff:
	ruff check $(SOURCES)
	ruff format --diff $(SOURCES)

.PHONY: test-integrations
test-integrations: ## Run integration tests.
	pytest tests/integration

.PHONY: test-mypy
test-mypy:
	mypy $(SOURCES)

.PHONY: test-pydocstyle
test-pydocstyle:
	pydocstyle craft_parts

.PHONY: test-pyright
test-pyright:
	pyright $(SOURCES)

.PHONY: test-units
test-units: ## Run unit tests.
	pytest tests/unit

.PHONY: test-docs
test-docs: installdocs ## Run docs tests.
	$(MAKE) -C docs linkcheck
	$(MAKE) -C docs woke
	$(MAKE) -C docs spelling

.PHONY: tests
tests: lint test-units test-integrations ## Run all tests.

# This target exists for compatibility with the Starflow TICS workflow.
# https://github.com/canonical/starflow/blob/main/.github/workflows/tics.yaml
.PHONY: setup-tics
setup-tics:
ifneq ($(shell which uv),)
else ifneq ($(shell which snap),)
	sudo snap install --classic astral-uv
else ifneq ($(shell which brew),)
	brew install uv
else ifeq ($(OS),Windows_NT)
	pwsh -c "irm https://astral.sh/uv/install.ps1 | iex"
else
	curl -LsSf https://astral.sh/uv/install.sh | sh
endif

include /etc/os-release
.ONESHELL:
.PHONY: test-coverage
test-coverage:
	uv sync --extra apt-$(VERSION_CODENAME) --extra tics --extra dev
	uv run coverage run --source craft_parts,tests -m pytest
	uv run coverage xml -o results/coverage.xml
	uv run coverage report -m
	uv run coverage html

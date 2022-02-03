SOURCES=$(wildcard *.py) craft_parts tests

.PHONY: help
help: ## Show this help.
	@printf "%-30s %s\n" "Target" "Description"
	@printf "%-30s %s\n" "------" "-----------"
	@fgrep " ## " $(MAKEFILE_LIST) | fgrep -v grep | awk -F ': .*## ' '{$$1 = sprintf("%-30s", $$1)} 1'

.PHONY: autoformat
autoformat: ## Run automatic code formatters.
	isort $(SOURCES)
	autoflake --remove-all-unused-imports --ignore-init-module-imports -ri $(SOURCES)
	black $(SOURCES)

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
	coverage run --source craft_parts -m pytest
	coverage report -m
	coverage html

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
lint: test-black test-codespell test-flake8 test-isort test-mypy test-pydocstyle test-pylint test-pyright ## Run all linting tests

.PHONY: release
release: dist ## Release with twine.
	twine upload dist/*

.PHONY: test-black
test-black:
	black --check --diff $(SOURCES)

.PHONY: test-codespell
test-codespell:
	codespell $(SOURCES)

.PHONY: test-flake8
test-flake8:
	flake8 $(SOURCES)

.PHONY: test-integrations
test-integrations: ## Run integration tests.
	pytest tests/integration

.PHONY: test-isort
test-isort:
	isort --check $(SOURCES)

.PHONY: test-mypy
test-mypy:
	mypy $(SOURCES)

.PHONY: test-pydocstyle
test-pydocstyle:
	pydocstyle craft_parts

.PHONY: test-pylint
test-pylint:
	pylint craft_parts
	pylint tests --disable=invalid-name,missing-module-docstring,missing-function-docstring,no-self-use,duplicate-code,protected-access,consider-using-with

.PHONY: test-pyright
test-pyright:
	pyright $(SOURCES)

.PHONY: test-units
test-units: ## Run unit tests.
	pytest tests/unit

.PHONY: tests
tests: lint test-units test-integrations ## Run all tests.

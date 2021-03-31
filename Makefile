.PHONY: help
help: ## Show this help.
	@printf "%-30s %s\n" "Target" "Description"
	@printf "%-30s %s\n" "------" "-----------"
	@fgrep " ## " $(MAKEFILE_LIST) | fgrep -v grep | awk -F ': .*## ' '{$$1 = sprintf("%-30s", $$1)} 1'

.PHONY: autoformat
autoformat: ## Run automatic code formatters.
	isort .
	autoflake --remove-all-unused-imports --ignore-init-module-imports -ri .
	black .

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
	sphinx-apidoc -o docs/ craft_parts --no-toc --ext-githubpages
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
lint: test-black test-codespell test-flake8 test-isort test-mypy test-pydocstyle test-pyright test-pylint ## Run all linting tests

.PHONY: release
release: dist ## Release with twine.
	twine upload dist/*

.PHONY: test-black
test-black:
	black --check --diff .

.PHONY: test-codespell
test-codespell:
	codespell craft_parts tests

.PHONY: test-flake8
test-flake8:
	flake8 craft_parts tests

.PHONY: test-integrations
test-integrations: ## Run integration tests.
	pytest tests/integration

.PHONY: test-isort
test-isort:
	isort --check craft_parts tests

.PHONY: test-mypy
test-mypy:
	mypy craft_parts tests

.PHONY: test-pydocstyle
test-pydocstyle:
	pydocstyle craft_parts

.PHONY: test-pylint
test-pylint:
	pylint --fail-under=9.0 craft_parts
	pylint tests --fail-under=9.0 --disable=invalid-name,missing-module-docstring,missing-function-docstring,redefined-outer-name,no-self-use,duplicate-code,protected-access,too-few-public-methods

.PHONY: test-pyright
test-pyright:
	pyright craft_parts tests

.PHONY: test-units
test-units: ## Run unit tests.
	pytest tests/unit

.PHONY: tests
tests: lint test-units test-integrations ## Run all tests.

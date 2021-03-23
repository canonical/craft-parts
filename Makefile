.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

.PHONY: autoformat
autoformat:
	isort .
	autoflake --remove-all-unused-imports --ignore-init-module-imports -ri .
	black .

.PHONY: clean
clean: clean-build clean-docs clean-pyc clean-test

.PHONY: clean-build
clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-docs
clean-docs:
	rm -rf docs/_build/
	rm -f docs/craft_parts.*
	rm -f docs/modules.rst

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

.PHONY: clean-tests
clean-test:
	rm -rf .tox/
	rm -f .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache

.PHONY: coverage
coverage:
	coverage run --source craft_parts -m pytest
	coverage report -m
	coverage html

.PHONY: docs
docs:
	rm -f docs/craft_parts.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ craft_parts --no-toc --ext-githubpages
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

.PHONY: docs-browse
docs-browse: docs
	$(BROWSER) docs/_build/html/index.html

.PHONY: dist
dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: install
install: clean
	python setup.py install

.PHONY: lint
lint: test-black test-flake8 test-isort test-mypy test-pyright test-pylint

.PHONY: release
release: dist
	twine upload dist/*

.PHONY: servedocs
servedocs: docs
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

.PHONY: test-black
test-black:
	black --check --diff .

.PHONY: test-codespell
test-codespell:
	codespell .

.PHONY: test-flake8
test-flake8:
	flake8 .

.PHONY: test-integrations
test-integrations:
	pytest tests/integration

.PHONY: test-isort
test-isort:
	isort --check craft_parts tests

.PHONY: test-mypy
test-mypy:
	mypy .

.PHONY: test-pylint
test-pylint:
	pylint --fail-under=9.0 craft_parts
	pylint tests --fail-under=9.0 --disable=invalid-name,missing-module-docstring,missing-function-docstring,redefined-outer-name,no-self-use,duplicate-code,protected-access,too-few-public-methods

.PHONY: test-pyright
test-pyright:
	pyright .

.PHONY: test-units
test-units:
	pytest tests/unit

.PHONY: tests
tests: lint test-integrations test-units

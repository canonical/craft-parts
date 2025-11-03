# GitHub Copilot Instructions for craft-parts

## Project Overview

Craft Parts is a Python library that supports the _parts_ mechanism common to all craft applications. It provides a declarative way to obtain, process, and organize data from different sources before it is packaged into the final artifact. This library is most useful for app developers in the Starcraft family.

## Development Environment

### Setup

Use the following commands to set up your development environment:

```bash
make setup      # Set up full development environment
make setup-lint # Set up linting-only environment
make setup-docs # Set up documentation-only environment
```

### Python Version

- **Minimum Python version**: 3.10
- **Supported versions**: 3.10, 3.11, 3.12
- **Target version for tooling**: 3.10

## Code Style and Standards

### Formatting and Linting

This project uses:

- **Ruff** for linting and formatting (primary tool)
- **mypy** for type checking
- **pyright** for additional type checking
- **codespell** for spell checking
- **prettier** for non-Python files

Run linters with:

```bash
make lint           # Run all linters
make lint-ruff      # Run ruff only
make lint-mypy      # Run mypy only
make lint-pyright   # Run pyright only
make format         # Auto-format code
```

### Code Formatting Rules

- **Line length**: 88 characters
- **Quote style**: Double quotes
- **Line endings**: LF (Unix-style)
- **Docstring format**: Follow pydocstyle conventions with code formatting enabled

### Type Annotations

- All functions in `craft_parts` module should have type annotations
- Use `typing` module for complex types
- Mypy is configured with strict settings for the `craft_parts` module
- Tests can be less strict with types but should still be typed when practical

### Naming Conventions

Follow PEP8 naming conventions:

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: prefix with `_`

### Import Ordering

Use isort-compatible import ordering (configured in ruff):

1. Standard library imports
2. Third-party imports
3. Local application imports

Group them with blank lines between sections.

## Testing

### Test Structure

- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/`
- Test framework: **pytest**

### Running Tests

```bash
make test           # Run all tests (can take ~1 hour)
make test-fast      # Run fast tests only
make test-slow      # Run slow tests only
make test-coverage  # Generate coverage report
```

#### Running Relevant Tests

When making changes, run only the relevant tests first before running linters:

```bash
# Run tests for a specific module
uv run pytest tests/unit/test_module.py

# Run tests for a specific file or directory
uv run pytest tests/unit/executor/

# Run tests matching a pattern
uv run pytest -k "test_pattern"

# Run fast tests for a specific area
uv run pytest -m 'not slow' tests/unit/plugins/
```

**Important**: Always run relevant tests locally before linting to catch issues early.

### Test Markers

Tests can be marked with:

- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.java` - Tests requiring Java build tools
- `@pytest.mark.python` - Tests requiring Python build tools
- `@pytest.mark.plugin` - Tests requiring plugin dependencies

### Test Dependencies

Available in tests:

- `pytest-mock` for mocking
- `pytest-cov` for coverage
- `pyfakefs` for filesystem mocking
- `pytest-subprocess` for subprocess mocking
- `requests-mock` for HTTP mocking
- `hypothesis` for property-based testing

### Writing Tests

- All nontrivial code changes should include tests
- Tests should be descriptive and follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common setup
- Mock external dependencies
- Avoid flaky tests

### Development Workflow

When making code changes:

1. **Run relevant tests first** - Use `uv run pytest` with specific paths or patterns
2. **Fix any test failures** - Ensure all relevant tests pass
3. **Run linters** - Use `make lint` or specific linters like `make lint-ruff`
4. **Run broader tests** - Use `make test-fast` before committing

## Documentation

### Documentation Framework

- Uses **Sphinx** with **Read the Docs theme**
- Follows **Diátaxis** framework (tutorials, how-to guides, reference, explanation)

### Building Documentation

```bash
make docs           # Build documentation
make docs-auto      # Build and auto-reload docs
make lint-docs      # Lint documentation
```

### Documentation Style

- Keep documentation app-agnostic for common features
- Place shared documentation in `docs/common/`
- Update changelog in `docs/reference/changelog.rst` for notable changes

## Commit Conventions

Follow **Conventional Commits** specification:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, no logic change)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test additions or modifications
- `build:` - Build system changes
- `ci:` - CI/CD changes
- `chore:` - Other changes (dependencies, etc.)

Use imperative mood: "add feature" not "added feature"

## Project Structure

```
craft_parts/
├── actions.py           # Action definitions
├── callbacks.py         # Callback mechanisms
├── constraints.py       # Build constraints
├── ctl.py              # Control interface (craftctl command)
├── dirs.py             # Directory management
├── errors.py           # Exception definitions
├── executor/           # Execution engine
├── features.py         # Feature flags
├── infos.py           # Information containers
├── lifecycle_manager.py # Main lifecycle orchestration
├── overlays/          # Overlay functionality
├── packages/          # Package management
├── parts.py           # Part definitions
├── permissions.py     # Permission handling
├── plugins/           # Plugin system
├── sources/           # Source handlers
├── state_manager/     # State management
├── steps.py           # Build steps
└── utils/             # Utility functions
```

## Key Dependencies

- **pydantic**: Data validation and settings management (v2.0+)
- **PyYAML**: YAML processing
- **requests**: HTTP client
- **lxml**: XML processing
- **semver**: Semantic versioning

## Plugin Development

When working with plugins:

- Plugins live in `craft_parts/plugins/`
- Each plugin inherits from `Plugin` base class
- Plugins define how to build specific types of sources (e.g., make, cmake, python)
- Test plugins thoroughly with both unit and integration tests

## Common Patterns

### Error Handling

Use custom exceptions from `craft_parts.errors`:

- Inherit from `CraftError` for library errors
- Provide clear error messages
- Include context in error messages

### Pydantic Models

- Use Pydantic v2 for all data models
- Define validators for complex validation
- Use `Field` for metadata and constraints

### State Management

- Parts maintain state through the state manager
- States track what steps have been executed
- Clean state when dependencies change

## Security Considerations

- Avoid using `shell=True` in subprocess calls
- Sanitize user inputs
- Use timeouts for network requests
- Be careful with file permissions
- Don't hardcode credentials or secrets

## License

This project uses **LGPL-3.0** license. All contributions must be compatible with this license.

## Getting Help

- Review `CONTRIBUTING.md` for contribution guidelines
- Check `README.md` for project overview
- Refer to the [documentation](https://canonical-craft-parts.readthedocs-hosted.com/en/latest/)
- Join the [Starcraft Development Matrix space](https://matrix.to/#/#starcraft-development:ubuntu.com)

## Code Review Guidelines

- Keep changes focused and minimal
- Write descriptive commit messages
- Update tests for behavior changes
- Update documentation for user-facing changes
- Respond to review feedback promptly
- Don't force-push after approval

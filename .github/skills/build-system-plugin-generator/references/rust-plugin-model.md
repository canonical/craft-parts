# Rust Plugin Model

Use these files as the baseline pattern when generating a new build-system plugin:

- Implementation: craft_parts/plugins/rust_plugin.py
- Unit tests: tests/unit/plugins/test_rust_plugin.py
- Integration tests: tests/integration/plugins/test_rust.py

## Implementation Pattern

1. Define `PluginProperties` subclass with:
    - Fixed `plugin` literal keyword.
    - Plugin-specific properties and defaults.
    - Field validators for stricter user input validation.
2. Define `PluginEnvironmentValidator` subclass for dependency checks:
    - Validate dependency tool availability.
    - Raise `PluginEnvironmentValidationError` for invalid configurations.
3. Define plugin class methods:
    - `get_build_snaps`
    - `get_build_packages`
    - `get_build_environment`
    - `get_pull_commands`
    - `get_build_commands`

## Unit Test Pattern

1. `part_info` fixture using `PartInfo`, `ProjectInfo`, `Part`.
2. Use `pytest_subprocess.FakeProcess` for command probing (`--version`).
3. Validate:
    - property validators
    - build snaps/packages
    - build environment changes
    - pull/build command generation
    - validator success/failure paths

## Integration Test Pattern

1. Build sample source tree in temporary directory with `Path(...).write_text()`.
2. Create YAML part definition with plugin keyword and required options.
3. Run `LifecycleManager(...).plan(Step.PRIME)` and execute actions.
4. Assert final binary/artifact path and behavior.

## Naming Pattern

- Module: craft_parts/plugins/<plugin-key>\_plugin.py
- Unit tests: tests/unit/plugins/test\_<plugin-key>\_plugin.py
- Integration tests: tests/integration/plugins/test\_<plugin-key>.py
- Docs: docs/common/craft-parts/reference/plugins/<plugin-key>\_plugin.rst

## Deterministic Validation Commands

Use these fixed commands and paths directly; avoid ad-hoc test discovery with `ls` or
`find`.

1. Unit tests for the new plugin:
    - `pytest tests/unit/plugins/test_<plugin-key>_plugin.py`
2. Plugin registry coverage:
    - `pytest tests/unit/plugins/test_plugins.py -k '<plugin-key> or get_plugin'`
3. Integration test for the new plugin:
    - `pytest tests/integration/plugins/test_<plugin-key>.py -m plugin`
4. Ensure docs page is linked in `docs/reference/plugins.rst`.
5. Add an `Example` section in plugin docs that explains what the example does and
   includes the exact `parts.yaml` from `examples/.local-tests/<plugin-key>/parts.yaml`.

## Additional Checks

1. CLI invocation sanity:
    - Validate expected command shape with `uv run python3 -m craft_parts --help`.
    - Use `python3` and `--verbose` with an explicit lifecycle command (`prime`, `build`, etc.).
2. Plugin registry coverage:
    - Add the new plugin in `craft_parts/plugins/plugins.py` and `tests/unit/plugins/test_plugins.py`.
3. Tool provenance check:
    - Verify the install source corresponds to the actual build system tool.
    - Prefer wrapper scripts; otherwise install the official binary in plugin pull/build commands.
    - Avoid `override-build` in example parts when plugin-level bootstrap can handle tool installation.
4. Example execution check:
    - Put validation example files under `examples/.local-tests/<plugin-key>/` to avoid committing temporary build assets.
    - Run `uv run python3 -m craft_parts --verbose --dry-run prime` first.
    - Only run full `prime` after dry-run confirms expected actions and no unexpected build-snaps.
    - After `prime` succeeds, run `uv run python3 -m craft_parts --verbose clean`.

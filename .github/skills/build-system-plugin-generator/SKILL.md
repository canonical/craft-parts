---
name: build-system-plugin-generator
description: "Generate a new craft-parts build-system plugin and matching unit/integration tests. Use when adding plugin support for a new build system, or when you want a scaffold that follows the Rust plugin patterns in craft_parts/plugins/rust_plugin.py and tests/unit/plugins/test_rust_plugin.py plus tests/integration/plugins/test_rust.py."
argument-hint: "<plugin-key> <build-system-name> [property-prefix]"
user-invocable: true
---

# Build System Plugin Generator

Create a new plugin implementation plus unit and integration tests that match the project conventions used by the Rust plugin.

## When To Use

- Add support for a new build system plugin under craft_parts/plugins.
- Scaffold unit tests under tests/unit/plugins for plugin properties, commands, and environment validation.
- Scaffold integration tests under tests/integration/plugins that perform an end-to-end PRIME build.

## Required Inputs

- Plugin keyword (example: `zig`)
- Build system display name (example: `Zig`)
- Optional property prefix for plugin-specific options (default: plugin keyword)

## Before Executing

- Use `python3`, not `python`, for local script invocations.
- Confirm CLI syntax before running builds with `uv run python3 -m craft_parts --help`.
- Use `--verbose` (not misspelled variants) and include a lifecycle command such as `prime`.
- Expect non-dry-run `prime` to download packages and take time on first run.
- Validate build-tool provenance early: do not assume similarly named packages/snaps are the right tool.
- Use deterministic file targets and command paths below; do not use ad-hoc `ls`/`find` to discover where plugin tests/docs should live.

## Procedure

1. Read [Rust plugin model](./references/rust-plugin-model.md) and mirror its structure.
2. Run the scaffold script to generate the initial files:
    - `python .github/skills/build-system-plugin-generator/scripts/scaffold_plugin.py <plugin-key> <build-system-name> --property-prefix <property-prefix>`
    - Generated files:
        - `craft_parts/plugins/<plugin-key>_plugin.py`
        - `tests/unit/plugins/test_<plugin-key>_plugin.py`
        - `tests/integration/plugins/test_<plugin-key>.py`
    - `docs/common/craft-parts/reference/plugins/<plugin-key>_plugin.rst`
3. Refine plugin module from [plugin template](./assets/plugin_template.py.tmpl):
    - Add `<BuildSystem>PluginProperties` class with `plugin: Literal["<plugin-key>"]`.
    - Implement `<BuildSystem>PluginEnvironmentValidator` if toolchain checks are required.
    - Implement `<BuildSystem>Plugin` methods: `get_build_snaps`, `get_build_packages`, `get_build_environment`, `get_pull_commands`, `get_build_commands`.
4. Register the plugin in craft_parts/plugins/plugins.py:
    - Import the new class.
    - Add an entry in plugin map keyed by plugin keyword.
5. Refine unit tests from [unit test template](./assets/unit_test_template.py.tmpl):
    - Validate properties parsing and defaults.
    - Verify pull/build command rendering.
    - Verify environment-validator success/failure behavior.
    - Verify out-of-source build behavior.
6. Refine integration tests from [integration test template](./assets/integration_test_template.py.tmpl):
    - Build a minimal sample project with generated build-system config files.
    - Run lifecycle through `Step.PRIME`.
    - Assert expected binary/artifact exists and is executable/contains expected output.
7. Finalize plugin docs from `docs/common/craft-parts/reference/plugins/<plugin-key>_plugin.rst` and register it in `docs/reference/plugins.rst` toctree.
    - Add an `Example` section that explains what the example does.
    - Include the exact `parts.yaml` used for this plugin example.
    - Keep the example consistent with the git-ignored file at `examples/.local-tests/<plugin-key>/parts.yaml`.
8. Run deterministic plugin test commands (no discovery commands required):
    - `pytest tests/unit/plugins/test_<plugin-key>_plugin.py`
    - `pytest tests/unit/plugins/test_plugins.py -k '<plugin-key> or get_plugin'`
    - `pytest tests/integration/plugins/test_<plugin-key>.py -m plugin`
9. Validate CLI invocation, real-world example wiring, and plugin registration coverage:
    - Confirm the command form with `uv run python3 -m craft_parts --help`.
    - Create a simple real-world `parts.yaml` example that exercises the target build system.
    - Place it in the git-ignored validation directory: `examples/.local-tests/<plugin-key>/parts.yaml`.
    - The example must not rely on `override-build` commands.
    - Add plugin registration checks in `tests/unit/plugins/test_plugins.py`.
10. Validate build-tool provenance and installation path:

- Do not assume a package/snap name matches the intended build tool.
- Prefer project wrapper when available.
- If wrapper is unavailable, prefer plugin-managed installation of the official tool binary in pull/build commands instead of `override-build` in example parts.
- Use a dedicated `<tool>-deps` part only when plugin-level bootstrap is not feasible.

11. Validate the generated example project with dry-run before full execution:

- `uv run python3 -m craft_parts --verbose --dry-run prime`
- Verify planned pull/build/stage/prime actions and confirm no unexpected build-snaps.

12. Run full example build only after dry-run checks pass:

- `uv run python3 -m craft_parts --verbose prime`

13. Run cleanup after a successful full prime run:

- `uv run python3 -m craft_parts --verbose clean`

## Acceptance Checklist

- New plugin is registered and loadable by keyword.
- Unit tests cover property validation, command generation, and environment validation.
- Integration tests build a real sample and assert final artifact behavior.
- Registry tests include the new plugin keyword in `test_plugins` coverage.
- Plugin docs file is created at `docs/common/craft-parts/reference/plugins/<plugin-key>_plugin.rst` and linked from `docs/reference/plugins.rst`.
- Plugin docs include an `Example` section with explanation and the plugin's `parts.yaml`.
- Tool installation method is verified to match the real build system (wrapper or official binary), not just similarly named packages/snaps.
- CLI validation includes a simple real-world `parts.yaml` example in `examples/.local-tests/` with no `override-build` usage.
- Example project passes `--dry-run prime` and shows expected lifecycle actions.
- Example project runs `clean` after successful `prime`.
- No regressions in existing plugin tests.

## Notes

- Keep option names kebab-case in YAML (for example `<prefix>-channel`) and snake_case in Python fields (`<prefix>_channel`).
- Prefer the same fixture and assertion style used by the Rust plugin tests.

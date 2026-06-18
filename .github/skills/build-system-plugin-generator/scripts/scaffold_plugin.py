#!/usr/bin/env python3
"""Generate a new build-system plugin and tests from templates."""

from __future__ import annotations

import argparse
from pathlib import Path


def _to_class_prefix(value: str) -> str:
    return "".join(piece.capitalize() for piece in value.replace("_", "-").split("-"))


def _render_template(template_path: Path, replacements: dict[str, str]) -> str:
    text = template_path.read_text()
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _write_new_file(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main() -> None:
    """Entrypoint for the plugin scaffolding script."""
    parser = argparse.ArgumentParser(
        description="Generate plugin and tests from skill templates."
    )
    parser.add_argument("plugin_key", help="Plugin keyword, for example zig")
    parser.add_argument(
        "build_system_name", help="Build system display name, for example Zig"
    )
    parser.add_argument(
        "--property-prefix",
        default=None,
        help="Prefix for plugin properties (defaults to plugin_key)",
    )
    parser.add_argument(
        "--build-tool",
        default=None,
        help="Command used to build (defaults to plugin_key)",
    )
    parser.add_argument(
        "--build-tool-binary",
        default=None,
        help="Binary used for environment validation (defaults to build-tool)",
    )
    parser.add_argument(
        "--artifact-name",
        default="sample-app",
        help="Output artifact name for integration test template",
    )
    parser.add_argument(
        "--project-config-file",
        default="build.config",
        help="Primary project config file for integration test template",
    )
    parser.add_argument(
        "--source-file",
        default="src/main.txt",
        help="Source file path used in integration test template",
    )
    parser.add_argument(
        "--expected-output",
        default="hello world",
        help="Expected output for integration test assertion",
    )

    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parent.parent
    repo_root = skill_root.parent.parent.parent

    plugin_key = args.plugin_key
    build_system_name = args.build_system_name
    prefix = args.property_prefix or plugin_key.replace("-", "_")
    build_tool = args.build_tool or plugin_key
    build_tool_binary = args.build_tool_binary or build_tool

    replacements = {
        "<plugin-key>": plugin_key,
        "<plugin_key>": plugin_key.replace("-", "_"),
        "<BuildSystem>": _to_class_prefix(build_system_name),
        "<build-tool>": build_tool,
        "<build-tool-binary>": build_tool_binary,
        "<prefix>": prefix,
        "<artifact-name>": args.artifact_name,
        "<project-config-file>": args.project_config_file,
        "<source-file>": args.source_file,
        "<expected-output>": args.expected_output,
        "<artifact-path>": f"{args.project_config_file}.artifact",
    }

    outputs = {
        repo_root / "craft_parts" / "plugins" / f"{plugin_key}_plugin.py": (
            skill_root / "assets" / "plugin_template.py.tmpl"
        ),
        repo_root / "tests" / "unit" / "plugins" / f"test_{plugin_key}_plugin.py": (
            skill_root / "assets" / "unit_test_template.py.tmpl"
        ),
        repo_root / "tests" / "integration" / "plugins" / f"test_{plugin_key}.py": (
            skill_root / "assets" / "integration_test_template.py.tmpl"
        ),
        repo_root
        / "docs"
        / "common"
        / "craft-parts"
        / "reference"
        / "plugins"
        / f"{plugin_key}_plugin.rst": (
            skill_root / "assets" / "plugin_doc_template.rst.tmpl"
        ),
    }

    for out_path, template_path in outputs.items():
        rendered = _render_template(template_path, replacements)
        _write_new_file(out_path, rendered)
        print(f"created {out_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()

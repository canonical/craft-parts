# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2023,2024,2025 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The gradle plugin validator."""

import dataclasses
import os
import re
import subprocess
from pathlib import Path


@dataclasses.dataclass
class CraftDirs:
    """Craft dir mappings.

    build_dir: CRAFT_PART_BUILD
    src_dir: CRAFT_PART_SRC
    """

    build_dir: Path
    src_dir: Path


GRADLE_EXECUTABLE = "gradle"
GRADLEW_EXECUTABLE = "./gradlew"


def _get_craft_parts_dirs() -> CraftDirs:
    build_dir = os.environ.get("CRAFT_PART_BUILD")
    if not build_dir:
        raise RuntimeError("CRAFT_PART_BUILD not set.")
    src_dir = os.environ.get("CRAFT_PART_SRC")
    if not src_dir:
        raise RuntimeError("CRAFT_PART_SRC not set.")
    return CraftDirs(
        build_dir=Path(build_dir),
        src_dir=Path(src_dir),
    )


def _get_system_java_version() -> int:
    java_version = os.environ.get("JAVA_VERSION")
    if not java_version:
        raise RuntimeError("JAVA_VERSION not set")
    try:
        return int(java_version)
    except ValueError as err:
        raise RuntimeError("invalid JAVA_VERSION") from err


def _validate_project_java_version(
    build_dir: Path, src_dir: Path, system_java_major_version: int
) -> None:
    gradlew_path = src_dir / GRADLEW_EXECUTABLE
    gradle_executable = (
        GRADLE_EXECUTABLE if not gradlew_path.exists() else GRADLEW_EXECUTABLE
    )
    if not gradlew_path.exists():
        raise RuntimeError("gradlew file not found in project")

    try:
        project_java_major_versions = _get_project_java_major_version(
            build_dir=build_dir
        )
    except subprocess.CalledProcessError as exc:
        # We ignore errors while executing project version check when using gradle because
        # Ubuntu package provided gradlew version is too low to execute the init script.
        if gradle_executable == GRADLE_EXECUTABLE:
            pass
        raise RuntimeError(
            f"something went wrong while executing {GRADLEW_EXECUTABLE}"
        ) from exc
    if not all(
        system_java_major_version >= project_java_major_version
        for project_java_major_version in project_java_major_versions
    ):
        raise RuntimeError("some project Java version higher than build Java version")


def _get_project_java_major_version(build_dir: Path) -> list[int]:
    """Return the project major version for all projects and subprojects."""
    init_script_path = Path(f"{build_dir}/gradle-plugin-init-script.gradle")
    search_term = "gradle-plugin-java-version-print"
    init_script_path.write_text(
        f"""allprojects {{ project ->
afterEvaluate {{
    if (project.hasProperty('java') && \
project.java.toolchain.languageVersion.getOrElse(false)) {{
        println "{search_term}: ${{project.java.toolchain.languageVersion.get().asInt()}}"
    }} else if (project.plugins.hasPlugin('java')) {{
        def javaVersion = project.targetCompatibility?: project.sourceCompatibility
        println "{search_term}: ${{javaVersion}}"
    }} else {{
        println "version not detected"
    }}
}}
}}
""",
        encoding="utf-8",
    )

    try:
        version_output = subprocess.check_output(
            [f"{build_dir}/gradlew", "--init-script", f"{init_script_path}"],
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as err:
        raise RuntimeError("failed to run version check init script") from err

    matches = re.findall(rf"{search_term}: (\d+)", version_output)
    if not matches:
        raise RuntimeError("project using ")

    try:
        return [int(match) for match in matches]
    except ValueError as err:
        raise RuntimeError("invalid java version detected") from err


if __name__ == "__main__":
    craft_dirs = _get_craft_parts_dirs()
    system_java_version = _get_system_java_version()
    _validate_project_java_version(
        build_dir=craft_dirs.build_dir,
        src_dir=craft_dirs.src_dir,
        system_java_major_version=system_java_version,
    )

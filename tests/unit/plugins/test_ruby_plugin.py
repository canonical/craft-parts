# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

import subprocess

import pytest
import pytest_subprocess
from craft_parts.errors import PluginEnvironmentValidationError
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.ruby_plugin import RubyPlugin
from craft_parts.plugins.validator import PluginEnvironmentValidator


def exec_fail(x):
    raise subprocess.CalledProcessError(127, x)


@pytest.fixture
def mock_validator(monkeypatch):
    def fake_execute(self, cmd: str):
        return subprocess.check_output(  # noqa: S602
            cmd,
            shell=True,
        )

    monkeypatch.setattr(PluginEnvironmentValidator, "_execute", fake_execute)


@pytest.fixture
def part_info_with_dependency(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"after": ["ruby-deps"]}),
    )


@pytest.fixture
def part_info_without_dependency(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_get_build_packages_after_ruby_deps(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)
    assert plugin.get_build_packages() == set()


def test_get_build_packages_no_ruby_deps(part_info_without_dependency):
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": ".", "ruby-flavor": "ruby", "ruby-version": "3.4"}
    )
    plugin = RubyPlugin(properties=properties, part_info=part_info_without_dependency)
    assert "curl" in plugin.get_build_packages()


@pytest.mark.parametrize(
    "properties_dict",
    [
        {"source": ".", "ruby-flavor": "mruby"},
        {"source": ".", "ruby-version": "3.2"},
    ],
)
def test_validate_environment_flavor_version(properties_dict):
    """If either ruby-flavor or ruby-version is specified, the other must be too."""
    properties = RubyPlugin.properties_class.unmarshal(properties_dict)
    validator = RubyPlugin.validator_class(
        part_name="my-part", properties=properties, env=""
    )
    with pytest.raises(PluginEnvironmentValidationError) as exc:
        validator.validate_environment()
    assert "ruby-version and ruby-flavor must both be specified" in exc.value.brief


@pytest.mark.parametrize("missing_command", ["ruby", "gem"])
def test_validate_environment(
    missing_command, fake_process: pytest_subprocess.FakeProcess, mock_validator
):
    """Omitting ruby-deps and ruby-flavor should trigger checks for dependencies."""
    if missing_command != "gem":
        fake_process.register(["gem", "--version"])
    if missing_command != "ruby":
        fake_process.register(["ruby", "--version"])
    fake_process.register([missing_command, "--version"], callback=exec_fail)

    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    validator = RubyPlugin.validator_class(
        part_name="my-part", properties=properties, env=""
    )
    with pytest.raises(PluginEnvironmentValidationError) as exc:
        validator.validate_environment()
    assert f"'{missing_command}' not found" in exc.value.brief


def test_validate_environment_ruby_deps(
    fake_process: pytest_subprocess.FakeProcess, mock_validator
):
    """Specifying ruby-deps should skip environment checks"""
    for exe in ["ruby", "gem"]:
        fake_process.register([exe, "--version"], callback=exec_fail)

    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    validator = RubyPlugin.validator_class(
        part_name="my-part", properties=properties, env=""
    )
    validator.validate_environment(part_dependencies=["ruby-deps"])


def test_validate_environment_custom_flavor():
    """Specifying ruby-flavor should skip environment checks"""
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": ".", "ruby-flavor": "mruby", "ruby-version": "3.2"}
    )
    validator = RubyPlugin.validator_class(
        part_name="my-part", properties=properties, env=""
    )
    validator.validate_environment()


def test_validate_environment_deps_and_custom():
    """Specifying both ruby-flavor and ruby-deps should raise an exception."""
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": ".", "ruby-flavor": "mruby", "ruby-version": "3.2"}
    )
    validator = RubyPlugin.validator_class(
        part_name="my-part", properties=properties, env=""
    )
    with pytest.raises(PluginEnvironmentValidationError) as exc:
        validator.validate_environment(part_dependencies=["ruby-deps"])
    assert "ruby-deps cannot be used" in exc.value.brief


def test_get_build_environment(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)

    env = plugin.get_build_environment()
    assert "${CRAFT_PART_INSTALL}/usr/bin" in env["PATH"]
    assert "${CRAFT_STAGE}/usr/lib/${CRAFT_ARCH_TRIPLET}" in env["LD_LIBRARY_PATH"]
    assert "${CRAFT_PART_INSTALL}/var/lib/gems/all" in env["GEM_HOME"]
    assert "${CRAFT_PART_INSTALL}/var/lib/gems/all" in env["GEM_PATH"]
    assert env["BUNDLE_PATH__SYSTEM"] == "true"


def test_pull_build_commands_after_ruby_deps(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)

    pull_commands = plugin.get_pull_commands()
    assert len(pull_commands) == 0

    build_commands = plugin.get_build_commands()
    assert build_commands == ["uname -a", "env"]


def test_pull_build_commands_no_ruby_deps(part_info_without_dependency):
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": ".", "ruby-flavor": "ruby", "ruby-version": "3.4"}
    )
    plugin = RubyPlugin(properties=properties, part_info=part_info_without_dependency)

    pull_commands = plugin.get_pull_commands()
    assert len(pull_commands) > 0
    assert (
        "curl -L --proto '=https' --tlsv1.2 "
        "https://github.com/postmodern/ruby-install/archive/refs/tags/v0.10.1.tar.gz "
        "-o ruby-install.tar.gz"
    ) in pull_commands

    build_commands = plugin.get_build_commands()
    assert len(build_commands) > 0
    assert (
        "ruby-install-0.10.1/bin/ruby-install --src-dir ${CRAFT_PART_SRC} "
        "--install-dir ${CRAFT_PART_INSTALL}/usr --no-install-deps "
        "--jobs=${CRAFT_PARALLEL_BUILD_COUNT} ruby-3.4 -- "
        "--without-baseruby --enable-load-relative --disable-install-doc"
    ) in build_commands


def test_ruby_gem_install(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": ".", "ruby-gems": ["mygem1", "mygem2"]}
    )
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)

    build_commands = plugin.get_build_commands()
    assert build_commands[-1] == "gem install --env-shebang --no-document mygem1 mygem2"

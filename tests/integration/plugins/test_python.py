# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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

import os
import sys
import textwrap
from pathlib import Path

import craft_parts.plugins.plugins
import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors, plugins
from overrides import override


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


def test_python_plugin(new_dir, partitions):
    """Prime a simple python source."""
    source_location = Path(__file__).parent / "test_python"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: python
            source: {source_location}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "bin", "mytest")
    assert primed_script.exists()
    assert primed_script.open().readline().rstrip() == "#!/usr/bin/env python3"


def test_python_plugin_with_pyproject_toml(new_dir, partitions):
    """Prime a simple python source."""
    source_location = Path(__file__).parent / "test_python_pyproject_toml"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: python
            source: {source_location}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_python_pyproject_toml",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "bin", "mytestpyprojecttoml")
    assert primed_script.exists()
    assert primed_script.open().readline().rstrip() == "#!/usr/bin/env python3"


def test_python_plugin_symlink(new_dir, partitions):
    """Run in the standard scenario with no overrides."""
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: python
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.is_symlink()

    # In regular Ubuntu this would be /usr/bin/python3.* but in GH this can be
    # something like /opt/hostedtoolcache/Python/3.9.16/x64/bin/python3.9
    assert os.path.isabs(python_link)
    assert os.path.basename(python_link).startswith("python3")


def test_python_plugin_override_get_system_interpreter(new_dir, partitions):
    """Override the system interpreter, link should use it."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            return "use-this-python"

    plugins.register({"python": MyPythonPlugin})

    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: python
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.is_symlink()
    assert os.readlink(python_link) == "use-this-python"


@pytest.mark.parametrize("remove_symlinks", [(True), (False)])
def test_python_plugin_no_system_interpreter(
    new_dir, partitions, remove_symlinks: bool  # noqa: FBT001
):
    """Check that the build fails if a payload interpreter is needed but not found."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            return None

        @override
        def _should_remove_symlinks(self) -> bool:
            # Parametrize this to make sure that the build fails even if the
            # venv symlinks will be removed.
            return remove_symlinks

    plugins.register({"python": MyPythonPlugin})

    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: python
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx, pytest.raises(errors.PluginBuildError):
        ctx.execute(actions)


def test_python_plugin_remove_symlinks(new_dir, partitions):
    """Override symlink removal."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _should_remove_symlinks(self) -> bool:
            return True

    plugins.register({"python": MyPythonPlugin})

    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: python
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.exists() is False


def test_python_plugin_fix_shebangs(new_dir, partitions):
    """Check if shebangs are properly fixed in scripts."""
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: python
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "bin/pip")
    assert primed_script.open().readline().rstrip() == "#!/usr/bin/env python3"


def test_python_plugin_override_shebangs(new_dir, partitions):
    """Override what we want in script shebang lines."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_script_interpreter(self) -> str:
            return "#!/my/script/interpreter"

    plugins.register({"python": MyPythonPlugin})

    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: python
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "bin/pip")
    assert primed_script.open().readline().rstrip() == "#!/my/script/interpreter"


# A part whose override-build copies the system's Python interpreter into the
# payload
PART_WITH_PAYLOAD_PYTHON = """\
parts:
  foo:
    plugin: python
    source: .
    override-build: |
      # Put a binary called "{payload_python}" in the payload
      mkdir -p ${{CRAFT_PART_INSTALL}}/usr/bin
      cp {real_python} ${{CRAFT_PART_INSTALL}}/usr/bin/{payload_python}
      craftctl default
"""


def test_find_payload_python_bad_version(new_dir, partitions):
    """Test that the build fails if a payload interpreter is needed but it's the
    wrong Python version."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_system_python_interpreter(self) -> str | None:
            # To have the build fail after failing to find the payload interpreter
            return None

    plugins.register({"python": MyPythonPlugin})

    real_python = Path(sys.executable).resolve()
    real_basename = real_python.name

    # Copy the "real" binary into the payload before calling the plugin's build,
    # but name it "python3.3".
    parts_yaml = PART_WITH_PAYLOAD_PYTHON.format(
        real_python=real_python, payload_python="python3.3"
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    out = Path("out.txt")
    with out.open(mode="w") as outfile, pytest.raises(errors.ScriptletRunError):
        with lf.action_executor() as ctx:
            ctx.execute(actions, stdout=outfile)

    output = out.read_text()
    expected_text = textwrap.dedent(
        f"""\
        Looking for a Python interpreter called "{real_basename}" in the payload...
        Python interpreter not found in payload.
        No suitable Python interpreter found, giving up.
        """
    )
    assert expected_text in output


def test_find_payload_python_good_version(new_dir, partitions):
    """Test that the build succeeds if a payload interpreter is needed, and it's
    the right Python version."""

    real_python = Path(sys.executable).resolve()
    real_basename = real_python.name
    install_dir = Path("parts/foo/install")

    # Copy the "real" binary into the payload before calling the plugin's build.
    parts_yaml = PART_WITH_PAYLOAD_PYTHON.format(
        real_python=real_python, payload_python=real_basename
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    out = Path("out.txt")
    with out.open(mode="w") as outfile:
        with lf.action_executor() as ctx:
            ctx.execute(actions, stdout=outfile)

    output = out.read_text()
    payload_python = (install_dir / f"usr/bin/{real_basename}").resolve()
    expected_text = textwrap.dedent(
        f"""\
        Found interpreter in payload: "{payload_python}"
        """
    )
    assert expected_text in output


def test_no_shebangs(new_dir, partitions):
    """Test that building a Python part with no scripts works."""

    class ScriptlessPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_package_install_commands(self) -> list[str]:
            return [
                *super()._get_package_install_commands(),
                f"rm {self._part_info.part_install_dir}/bin/pip*",
                f"rm {self._part_info.part_install_dir}/bin/mytest",
            ]

    plugins.register({"python": ScriptlessPlugin})

    source_location = Path(__file__).parent / "test_python"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: python
            source: {source_location}
            python-packages: [] # to remove default wheel, setuptools, etc
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_python", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = lf.project_info.prime_dir / "bin/mytest"
    assert not primed_script.exists()

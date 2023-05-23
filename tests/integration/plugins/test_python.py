# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
import textwrap
from pathlib import Path
from typing import Optional

import pytest
import yaml
from overrides import override

import craft_parts.plugins.plugins
from craft_parts import LifecycleManager, Step, errors, plugins


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


def test_python_plugin(new_dir):
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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "bin", "mytest")
    assert primed_script.exists()
    assert primed_script.open().readline().rstrip() == "#!/usr/bin/env python3"


def test_python_plugin_symlink(new_dir):
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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.is_symlink()

    # In regular Ubuntu this would be /usr/bin/python3.* but in GH this can be
    # something like /opt/hostedtoolcache/Python/3.9.16/x64/bin/python3.9
    assert os.path.isabs(python_link)
    assert os.path.basename(python_link).startswith("python3")


def test_python_plugin_override_get_system_interpreter(new_dir):
    """Override the system interpreter, link should use it."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_system_python_interpreter(self) -> Optional[str]:
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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.is_symlink()
    assert os.readlink(python_link) == "use-this-python"


def test_python_plugin_no_system_interpreter(new_dir):
    """Override the system interpreter, link should use it."""

    class MyPythonPlugin(craft_parts.plugins.plugins.PythonPlugin):
        @override
        def _get_system_python_interpreter(self) -> Optional[str]:
            return None

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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx, pytest.raises(errors.PluginBuildError):
        ctx.execute(actions)


def test_python_plugin_remove_symlinks(new_dir):
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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    python_link = Path(lf.project_info.prime_dir, "bin", "python3")
    assert python_link.exists() is False


def test_python_plugin_fix_shebangs(new_dir):
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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path("prime/bin/pip")
    assert primed_script.open().readline().rstrip() == "#!/usr/bin/env python3"


def test_python_plugin_override_shebangs(new_dir):
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

    lf = LifecycleManager(parts, application_name="test_python", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path("prime/bin/pip")
    assert primed_script.open().readline().rstrip() == "#!/my/script/interpreter"

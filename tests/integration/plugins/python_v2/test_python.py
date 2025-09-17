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
import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step, plugins
from craft_parts.errors import PluginBuildError
from craft_parts.plugins.python_v2.python_plugin import PythonPlugin

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def setup_function():
    plugins.unregister_all()
    yield
    plugins.unregister_all()


def _run_lifecycle(parts_yaml, new_dir, partitions) -> LifecycleManager:
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_python",
        cache_dir=new_dir,
        partitions=partitions,
        usrmerged_by_default=True,
    )
    actions = lf.plan(Step.PRIME)

    original_path = ""
    try:
        # This test might be running in a virtual environment; as such, the "pip"
        # executable that the plugin picks up will be the one in the venv, which cannot
        # install things in the user base dir. So make sure "/usr/bin/pip" is found
        # first.
        original_path = os.environ["PATH"]
        os.environ["PATH"] = os.pathsep.join(["/usr/bin", original_path])

        with lf.action_executor() as ctx:
            ctx.execute(actions)
    finally:
        if original_path:
            os.environ["PATH"] = original_path

    return lf


def _check_binaries(prime_dir, expected_prefix):
    python3 = prime_dir / "usr/bin/python3"

    # Check the "mytest" package, both the console script and the module
    primed_script = prime_dir / "bin/mytest"
    assert primed_script.exists()
    assert (
        primed_script.open().readline().rstrip()
        == f"#!{expected_prefix}/usr/bin/python3"
    )

    for args in ([primed_script], [python3, "-m", "mytest"]):
        assert subprocess.check_output(args) == b"it works!\n"

    black = prime_dir / "bin/black"
    assert black.exists()

    # Check "black", installed via python-packages
    # (both the console script and the module)
    for args in ([black], [python3, "-m", "black"]):
        output = subprocess.check_output([*args, "--help"])
        assert b"The uncompromising code formatter" in output

    flask = prime_dir / "bin/flask"
    assert flask.exists()

    # Check "flask", installed via python-requirements
    # (both the console script and the module)
    for args in ([flask], [python3, "-m", "flask"]):
        output = subprocess.check_output([*args, "--help"])
        assert b"A general utility script for Flask applications." in output


def test_python_plugin_no_bundled_python(new_dir, partitions):
    """Prime a simple python source."""
    source_location = Path(__file__).parent / "test_python"

    plugins.register({"python": PythonPlugin})

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: python
            source: {source_location}
        """
    )

    expected = re.escape("Using the system Python interpreter is not supported.")
    with pytest.raises(PluginBuildError, match=expected):
        _run_lifecycle(parts_yaml, new_dir, partitions)


def test_python_plugin_bundled_in_part(new_dir, partitions):
    source_location = Path(__file__).parent / "test_python"

    plugins.register({"python": PythonPlugin})

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: python
            source: {source_location}
            stage-packages: [python3]
            python-packages: [black]
            python-requirements: [requirements.txt]
        """
    )

    lifecycle = _run_lifecycle(parts_yaml, new_dir, partitions)
    prime_dir = lifecycle.project_info.prime_dir
    part_install = new_dir / "parts/foo/install"

    _check_binaries(prime_dir, part_install)


def test_python_plugin_staged(new_dir, partitions):
    source_location = Path(__file__).parent / "test_python"

    plugins.register({"python": PythonPlugin})

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          interpreter:
            plugin: nil
            stage-packages: [python3]

          foo:
            after: [interpreter]
            plugin: python
            source: {source_location}
            python-packages: [black]
            python-requirements: [requirements.txt]
        """
    )

    lifecycle = _run_lifecycle(parts_yaml, new_dir, partitions)
    prime_dir = lifecycle.project_info.prime_dir
    stage_dir = new_dir / "stage"

    _check_binaries(prime_dir, stage_dir)

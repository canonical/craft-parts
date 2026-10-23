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
from craft_parts import LifecycleManager, Step, errors, plugins
from craft_parts.errors import PluginBuildError
from craft_parts.plugins.python_v2.python_plugin import PythonPlugin
from craft_parts.utils import os_utils


def is_ubuntu_jammy() -> bool:
    release = os_utils.OsRelease()
    try:
        return release.id() == "ubuntu" and release.version_id() == "22.04"
    except errors.OsReleaseIdError:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.python,
    pytest.mark.skipif(
        is_ubuntu_jammy(), reason="Needs new enough pip provided by the system."
    ),
]


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


def _check_binaries(prime_dir):
    python3 = prime_dir / "usr/bin/python3"

    # Check the "mytest" package, both the console script and the module.
    # The console script's shebang must have been rewritten from the
    # build-time interpreter path to the runtime one. Note that executing the
    # script directly only works if the host has a /usr/bin/python3 with the
    # script's dependencies; run it through the payload interpreter instead.
    primed_script = prime_dir / "bin/mytest"
    assert primed_script.exists()
    assert primed_script.open().readline().rstrip() == "#!/usr/bin/python3"

    for args in ([python3, primed_script], [python3, "-m", "mytest"]):
        assert subprocess.check_output(args) == b"it works!\n"

    black = prime_dir / "bin/black"
    assert black.exists()

    # Check "black", installed via python-packages
    # (both the console script and the module)
    for args in ([python3, black], [python3, "-m", "black"]):
        output = subprocess.check_output([*args, "--help"])
        assert b"The uncompromising code formatter" in output

    flask = prime_dir / "bin/flask"
    assert flask.exists()

    # Check "flask", installed via python-requirements
    # (both the console script and the module)
    for args in ([python3, flask], [python3, "-m", "flask"]):
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
            python-packages: [black~=26.0]
            python-requirements: [requirements.txt]
        """
    )

    lifecycle = _run_lifecycle(parts_yaml, new_dir, partitions)
    prime_dir = lifecycle.project_info.prime_dir

    _check_binaries(prime_dir)


def test_python_plugin_staged(new_dir, partitions):
    source_location = Path(__file__).parent / "test_python"

    plugins.register({"python": PythonPlugin})

    # Note: the 'enable-usrmerge' build attribute is needed because when running this
    # test on Jammy the 'python3' stage-package has bin/python3 (usr/bin/python3 started
    # with Noble).
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

    _check_binaries(prime_dir)


def test_python_plugin_long_build_path(new_dir, partitions):
    """Rewrite pip's polyglot shebang for build paths over the shebang limit.

    When the interpreter path that pip embeds is longer than the kernel's
    ~127-byte shebang limit, pip writes a 3-line ``#!/bin/sh`` polyglot header
    instead of a plain ``#!`` line. The rewrite must collapse the whole header.
    """
    source_location = Path(__file__).parent / "test_python"

    plugins.register({"python": PythonPlugin})

    # Stage python3 at a path that is deep enough to push the interpreter's
    # shebang over the kernel limit, then have the python part find it first
    # in PATH.
    deep_dir = "d" * 100
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          interpreter:
            plugin: nil
            source: {source_location}
            override-build: |
              mkdir -p ${{CRAFT_PART_INSTALL}}/{deep_dir}
              cp $(readlink -f $(which python3)) ${{CRAFT_PART_INSTALL}}/{deep_dir}/python3

          foo:
            after: [interpreter]
            plugin: python
            source: {source_location}
            python-packages: [black]
            python-requirements: [requirements.txt]
            build-environment:
              - PATH: "$CRAFT_STAGE/{deep_dir}:$PATH"
              - PIP_PYTHON: "$CRAFT_STAGE/{deep_dir}/python3"
        """
    )

    lifecycle = _run_lifecycle(parts_yaml, new_dir, partitions)
    prime_dir = lifecycle.project_info.prime_dir

    # The polyglot header must have been collapsed into the runtime shebang.
    for script in ("mytest", "black", "blackd", "flask"):
        primed_script = prime_dir / "bin" / script
        assert primed_script.exists()
        assert primed_script.open().readline().rstrip() == "#!/usr/bin/python3"


def test_python_plugin_package_conflicts(new_dir, partitions):
    """Specified packages and requirements have a conflict."""
    source_location = Path(__file__).parent / "test_python"

    plugins.register({"python": PythonPlugin})

    # requirements-black.txt declares black==26.3.1, but python-packages declares
    # black==25.1.0
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: python
            source: {source_location}
            stage-packages: [python3]
            python-packages: [black==25.1.0]
            python-requirements: [requirements-black.txt]
        """
    )

    # pip orders the two conflicting pins differently depending on their versions,
    # so allow either order.
    expected = (
        r"Cannot install (black==26\.3\.1 and black==25\.1\.0|black==25\.1\.0 "
        r"and black==26\.3\.1) because these package versions have conflicting "
        r"dependencies\."
    )
    with pytest.raises(PluginBuildError, match=expected):
        _run_lifecycle(parts_yaml, new_dir, partitions)

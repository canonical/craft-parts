# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Build real Zig projects and check their installed payloads."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from craft_parts import ActionType, LifecycleManager, Step
from craft_parts.errors import PluginBuildError

pytestmark = [pytest.mark.plugin]

_FIXTURES = Path(__file__).parent / "test_zig"


def _manager(part, work_dir, partitions, *, usrmerged=False):
    return LifecycleManager(
        {
            "parts": {
                "hello": {
                    "plugin": "zig",
                    "source": str(_FIXTURES / "payload"),
                    **part,
                }
            }
        },
        application_name="test_zig",
        cache_dir=work_dir / "cache",
        work_dir=work_dir,
        partitions=partitions,
        parallel_build_count=2,
        usrmerged_by_default=usrmerged,
    )


def _prime(manager):
    actions = manager.plan(Step.PRIME)
    with manager.action_executor() as executor:
        executor.execute(actions)
    return manager.project_info.prime_dir


def _output(binary):
    return subprocess.check_output([str(binary)], text=True, stderr=subprocess.STDOUT)


@pytest.mark.parametrize(
    ("prefix", "usrmerged", "binary_directory", "data_directory"),
    [
        (None, False, "bin", "share"),
        (None, True, "usr/bin", "share"),
        ("/usr", False, "usr/bin", "usr/share"),
        ("/usr", True, "usr/bin", "usr/share"),
    ],
)
def test_zig_installs_complete_payload(
    new_path, partitions, prefix, usrmerged, binary_directory, data_directory
):
    properties = {} if prefix is None else {"zig-install-prefix": prefix}
    manager = _manager(properties, new_path, partitions, usrmerged=usrmerged)

    prime = _prime(manager)

    assert _output(prime / binary_directory / "hello") == "Hello from Zig!\n"
    library_directory = "usr/lib" if prefix == "/usr" or usrmerged else "lib"
    header_directory = "usr/include" if prefix == "/usr" else "include"
    assert (prime / library_directory / "libanswer.a").is_file()
    assert (prime / header_directory / "answer.h").read_text() == (
        _FIXTURES / "payload/answer.h"
    ).read_text()
    assert (prime / data_directory / "hello/message.txt").read_text() == (
        "Zig application data\n"
    )
    assert not (prime / "build.zig").exists()
    assert not list(prime.rglob("zig"))
    assert not list(prime.rglob(".zig-cache"))
    assert not list(prime.rglob("zig-out"))
    if usrmerged and prefix is None:
        assert (prime / "bin").is_symlink()


def test_zig_source_subdir_override_and_literal_parameters(new_path, partitions):
    source = new_path / "source"
    shutil.copytree(_FIXTURES / "payload", source / "nested project")
    message = "hello with spaces; $(touch injected)"
    manager = _manager(
        {
            "source": str(source),
            "source-subdir": "nested project",
            "zig-build-parameters": [f"-Dmessage={message}"],
            "override-build": (
                'test "$PWD" = "$CRAFT_PART_BUILD"\n'
                "craftctl default\n"
                'printf override > "$CRAFT_PART_INSTALL/override-marker"\n'
            ),
        },
        new_path,
        partitions,
    )

    prime = _prime(manager)

    assert _output(prime / "bin/hello") == f"{message}\n"
    assert (prime / "override-marker").read_text() == "override"
    assert not list(new_path.rglob("injected"))
    assert not (source / "nested project/.zig-cache").exists()


def test_zig_finds_staged_c_library(new_path, partitions):
    manager = LifecycleManager(
        {
            "parts": {
                "answer": {
                    "plugin": "zig",
                    "source": str(_FIXTURES / "c-library"),
                    "zig-install-prefix": "/usr",
                },
                "hello": {
                    "plugin": "zig",
                    "source": str(_FIXTURES / "c-consumer"),
                    "after": ["answer"],
                },
            }
        },
        application_name="test_zig",
        cache_dir=new_path / "cache",
        work_dir=new_path,
        partitions=partitions,
        parallel_build_count=2,
    )

    prime = _prime(manager)

    assert _output(prime / "bin/hello") == "C answer: 42\n"
    assert (prime / "usr/lib/libanswer.a").is_file()
    assert (prime / "usr/include/answer.h").is_file()


def test_zig_organizes_payload_into_partition(new_path, partitions):
    if partitions is None:
        pytest.skip("This case exercises named partitions.")
    manager = _manager(
        {"organize": {"bin/hello": "(mypart)/bin/hello"}}, new_path, partitions
    )

    prime = _prime(manager)

    assert not (prime / "bin/hello").exists()
    binary = new_path / "partitions/mypart/prime/bin/hello"
    assert _output(binary) == "Hello from Zig!\n"


def test_zig_build_failure_does_not_commit_build_state(new_path, partitions):
    source = new_path / "source"
    shutil.copytree(_FIXTURES / "payload", source)
    (source / "main.zig").write_text('@compileError("intentional build failure");\n')
    manager = _manager({"source": str(source)}, new_path, partitions)

    with pytest.raises(PluginBuildError):
        _prime(manager)

    state_dir = new_path / "parts/hello/state"
    assert (state_dir / "pull").is_file()
    assert not (state_dir / "build").exists()
    assert not (state_dir / "stage").exists()
    assert not (state_dir / "prime").exists()


def test_zig_build_parameters_invalidate_build_state(new_path, partitions):
    _prime(_manager({}, new_path, partitions))
    unchanged = _manager({}, new_path, partitions).plan(Step.PRIME)
    assert all(action.action_type == ActionType.SKIP for action in unchanged)

    changed = _manager(
        {"zig-build-parameters": ["-Dmessage=Changed"]}, new_path, partitions
    )
    actions = changed.plan(Step.PRIME)
    assert actions[0].step == Step.PULL
    assert actions[0].action_type == ActionType.SKIP
    assert actions[1].step == Step.BUILD
    assert actions[1].action_type == ActionType.RERUN
    with changed.action_executor() as executor:
        executor.execute(actions)
    assert _output(changed.project_info.prime_dir / "bin/hello") == "Changed\n"


def test_zig_external_supplier_part(new_path, partitions, monkeypatch):
    # The dependency stages a wrapper around the real compiler, which must be
    # the only zig in PATH.
    zig = shutil.which("zig")
    assert zig is not None
    monkeypatch.setenv(
        "PATH", f"{Path(sys.executable).parent}:/usr/local/bin:/usr/bin:/bin"
    )
    manager = LifecycleManager(
        {
            "parts": {
                "zig-deps": {
                    "plugin": "nil",
                    "override-build": (
                        'mkdir -p "$CRAFT_PART_INSTALL/bin"\n'
                        "cat > \"$CRAFT_PART_INSTALL/bin/zig\" <<'EOF'\n"
                        "#!/bin/sh\n"
                        'printf called >> "$CRAFT_PART_BUILD/zig-wrapper-used"\n'
                        f'exec "{zig}" "$@"\n'
                        "EOF\n"
                        'chmod +x "$CRAFT_PART_INSTALL/bin/zig"\n'
                    ),
                    "prime": ["-bin/zig"],
                },
                "hello": {
                    "plugin": "zig",
                    "source": str(_FIXTURES / "payload"),
                    "after": ["zig-deps"],
                },
            }
        },
        application_name="test_zig",
        cache_dir=new_path / "cache",
        work_dir=new_path,
        partitions=partitions,
        parallel_build_count=2,
    )

    prime = _prime(manager)

    assert _output(prime / "bin/hello") == "Hello from Zig!\n"
    assert not (prime / "bin/zig").exists()
    assert (new_path / "parts/hello/build/zig-wrapper-used").is_file()

# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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
import runpy
import sys
import textwrap
from pathlib import Path

import craft_parts
import pytest
from craft_parts import main

parts_yaml = textwrap.dedent(
    """
    parts:
      foo:
        plugin: nil
      bar:
        after: [foo]
        plugin: nil
"""
)

plan_steps = [
    "Pull foo\nPull bar\n",
    "Overlay foo\nOverlay bar\n",
    "Build foo\nStage foo (required to build 'bar')\nBuild bar\n",
    "Stage bar\n",
    "Prime foo\nPrime bar\n",
]

plan_result = ["".join(plan_steps[0:n]) for n in range(1, len(plan_steps) + 1)]


# pylint: disable=line-too-long

execute_steps = [
    "Execute: Pull foo\nExecute: Pull bar\n",
    "Execute: Overlay foo\nExecute: Overlay bar\n",
    "Execute: Build foo\nExecute: Stage foo (required to build 'bar')\nExecute: Build bar\n",
    "Execute: Stage bar\n",
    "Execute: Prime foo\nExecute: Prime bar\n",
]

execute_result = ["".join(execute_steps[0:n]) for n in range(1, len(execute_steps) + 1)]

skip_steps = [
    "Skip pull foo (already ran)\nSkip pull bar (already ran)\n",
    "Skip overlay foo (already ran)\nSkip overlay bar (already ran)\n",
    "Skip build foo (already ran)\nSkip build bar (already ran)\n",
    "Skip stage foo (already ran)\nSkip stage bar (already ran)\n",
    "Skip prime foo (already ran)\nSkip prime bar (already ran)\n",
]

skip_result = ["".join(skip_steps[0:n]) for n in range(1, len(skip_steps) + 1)]


@pytest.fixture(autouse=True)
def setup_new_dir(new_dir):  # pylint: disable=unused-argument
    pass


def setup_function():
    craft_parts.Features.reset()


def teardown_function():
    craft_parts.Features.reset()


def test_main_no_args(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == execute_result[4]
    assert Path("parts").is_dir()
    assert Path("parts/foo").is_dir()
    assert Path("parts/bar").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()


def test_main_missing_parts_file(mocker, capfd):
    mocker.patch.object(sys, "argv", ["cmd"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: parts.yaml: No such file or directory.\n"
    assert out == ""


def test_main_unreadable_parts_file(mocker, capfd):
    Path("parts.yaml").touch()
    Path("parts.yaml").chmod(0o111)

    mocker.patch.object(sys, "argv", ["cmd"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: parts.yaml: Permission denied.\n"
    assert out == ""


def test_main_invalid_parts_file(mocker, capfd):
    Path("parts.yaml").write_text("not yaml data")

    mocker.patch.object(sys, "argv", ["cmd"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 4

    out, err = capfd.readouterr()
    assert err == "Error: parts definition must be a dictionary\n"
    assert out == ""


def test_main_missing_parts_entry(mocker, capfd):
    Path("parts.yaml").write_text("name: file")

    mocker.patch.object(sys, "argv", ["cmd"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 4

    out, err = capfd.readouterr()
    assert err == "Error: parts definition is missing\n"
    assert out == ""


def test_main_version(mocker, capfd):
    mocker.patch.object(sys, "argv", ["cmd", "--version"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == f"craft-parts {craft_parts.__version__}\n"


def test_main_dry_run(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == plan_result[4]
    assert Path("parts").is_dir() is False
    assert Path("stage").is_dir() is False
    assert Path("prime").is_dir() is False


def test_main_invalid_application_name(mocker):
    Path("parts.yaml").write_text(parts_yaml)
    Path("work_dir").mkdir()

    mocker.patch.object(
        sys, "argv", ["cmd", "--dry-run", "--application-name", "snap-craft", "clean"]
    )
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3


def test_main_alternative_work_dir(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)
    Path("work_dir").mkdir()

    mocker.patch.object(sys, "argv", ["cmd", "--work-dir", "work_dir"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == execute_result[4]

    # work dirs are in the new location
    assert Path("work_dir/parts").is_dir()
    assert Path("work_dir/stage").is_dir()
    assert Path("work_dir/prime").is_dir()

    # no new entries in the current dir
    assert sorted(os.listdir(".")) == [".cache", "parts.yaml", "work_dir"]


@pytest.mark.parametrize("opt", ["--f", "--file"])
def test_main_alternative_parts_file(mocker, capfd, opt):
    Path("other.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", opt, "other.yaml"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == plan_result[4]


def test_main_alternative_parts_invalid_file(mocker, capfd):
    Path("other.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "-f", "missing.yaml"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 1

    out, err = capfd.readouterr()
    assert err == "Error: missing.yaml: No such file or directory.\n"
    assert out == ""


@pytest.mark.parametrize(
    ("step", "result"),
    [
        ("pull", execute_result[0]),
        ("overlay", execute_result[1]),
        ("build", execute_result[2]),
        ("stage", execute_result[3]),
        ("prime", execute_result[4]),
    ],
)
def test_main_step(mocker, capfd, step, result):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", step])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == result
    assert Path("parts").is_dir()


@pytest.mark.parametrize(
    ("step", "result"),
    [
        ("pull", plan_result[0]),
        ("overlay", plan_result[1]),
        ("build", plan_result[2]),
        ("stage", plan_result[3]),
        ("prime", plan_result[4]),
    ],
)
def test_main_step_dry_run(mocker, capfd, step, result):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", step])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == result
    assert Path("parts").is_dir() is False


def test_main_step_dry_run_skip(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""

    # run it again on the existing state
    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "prime"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "No actions to execute.\n"


def test_main_step_dry_run_show_skip(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""

    # run it again on the existing state
    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "--show-skip", "prime"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == skip_result[4]


def test_main_step_specify_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "prime", "foo"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert out == (
        "Execute: Pull foo\nExecute: Overlay foo\nExecute: Build foo\n"
        "Execute: Stage foo\nExecute: Prime foo\n"
    )


def test_main_step_specify_part_dry_run(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "prime", "foo"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Pull foo\nOverlay foo\nBuild foo\nStage foo\nPrime foo\n"

    assert Path("parts").is_dir() is False


@pytest.mark.parametrize(
    ("step", "result"),
    [
        ("pull", plan_result[0]),
        ("overlay", plan_result[1]),
        ("build", plan_result[2]),
        (
            "stage",
            (
                "Pull foo\n"
                "Pull bar\n"
                "Overlay foo\n"
                "Overlay bar\n"
                "Build foo\n"
                "Stage foo (required to build 'bar')\n"
                "Build bar\n"
                "Stage bar\n"
            ),
        ),
        ("prime", plan_result[4]),
    ],
)
def test_main_step_specify_multiple_parts(mocker, capfd, step, result):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", step, "foo", "bar"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == result
    assert Path("parts").is_dir() is False


def test_main_step_invalid_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "pull", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3

    out, err = capfd.readouterr()
    assert err == (
        "Error: A part named 'invalid' is not defined in the parts list.\n"
        "Review the parts definition and make sure it's correct.\n"
    )
    assert out == ""


def test_main_step_invalid_multiple_parts(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "pull", "foo", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3

    out, err = capfd.readouterr()
    assert err == (
        "Error: A part named 'invalid' is not defined in the parts list.\n"
        "Review the parts definition and make sure it's correct.\n"
    )
    assert out == ""
    assert Path("parts").is_dir() is False


def test_main_step_invalid_part_dry_run(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "pull", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3

    out, err = capfd.readouterr()
    assert err == (
        "Error: A part named 'invalid' is not defined in the parts list.\n"
        "Review the parts definition and make sure it's correct.\n"
    )
    assert out == ""
    assert Path("parts").is_dir() is False


def test_main_step_invalid_multiple_parts_dry_run(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "pull", "foo", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3

    out, err = capfd.readouterr()
    assert err == (
        "Error: A part named 'invalid' is not defined in the parts list.\n"
        "Review the parts definition and make sure it's correct.\n"
    )
    assert out == ""
    assert Path("parts").is_dir() is False


def test_main_clean(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "clean"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Clean all parts.\n"
    assert Path("parts").is_dir() is False
    assert Path("stage").is_dir() is False
    assert Path("prime").is_dir() is False

    # clean again should not fail
    mocker.patch.object(sys, "argv", ["cmd", "clean"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None
    assert err == ""
    assert out == "Clean all parts.\n"


def test_main_clean_workdir(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)
    Path("work_dir").mkdir()

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "--work-dir", "work_dir"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("work_dir/parts").is_dir()
    assert Path("work_dir/stage").is_dir()
    assert Path("work_dir/prime").is_dir()

    assert sorted(os.listdir(".")) == [".cache", "parts.yaml", "work_dir"]

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "--work-dir", "work_dir", "clean"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == "Clean all parts.\n"
    assert Path("work_dir/parts").is_dir() is False
    assert Path("work_dir/stage").is_dir() is False
    assert Path("work_dir/prime").is_dir() is False

    assert sorted(os.listdir(".")) == [".cache", "parts.yaml", "work_dir"]


def test_main_clean_dry_run(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    Path("parts").mkdir()
    Path("stage").mkdir()
    Path("prime").mkdir()

    mocker.patch.object(sys, "argv", ["cmd", "--dry-run", "clean"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    # work dirs are not removed
    assert set(os.listdir(".")).issuperset({"parts", "prime", "stage"})


def test_main_clean_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == ""
    assert Path("parts/foo/state/pull").is_file() is False
    assert Path("parts/foo/state/build").is_file() is False
    assert Path("parts/foo/state/state").is_file() is False
    assert Path("parts/foo/state/prime").is_file() is False
    assert Path("parts/bar/state/pull").is_file()
    assert Path("parts/bar/state/build").is_file()
    assert Path("parts/bar/state/stage").is_file()
    assert Path("parts/bar/state/prime").is_file()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the again should not fail
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None
    assert err == ""
    assert out == ""


def test_main_clean_multiple_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd"])
    main.main()

    out, err = capfd.readouterr()
    assert err == ""
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()

    # clean the existing work dirs
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo", "bar"])
    craft_parts.Features.reset()
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code is None

    out, err = capfd.readouterr()
    assert err == ""
    assert out == ""
    assert Path("parts/foo/state/pull").is_file() is False
    assert Path("parts/foo/state/build").is_file() is False
    assert Path("parts/foo/state/state").is_file() is False
    assert Path("parts/foo/state/prime").is_file() is False
    assert Path("parts/bar/state/pull").is_file() is False
    assert Path("parts/bar/state/build").is_file() is False
    assert Path("parts/bar/state/stage").is_file() is False
    assert Path("parts/bar/state/prime").is_file() is False


def test_main_clean_invalid_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "clean", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3

    out, err = capfd.readouterr()
    assert err == (
        "Error: A part named 'invalid' is not defined in the parts list.\n"
        "Review the parts definition and make sure it's correct.\n"
    )
    assert out == ""


def test_main_clean_invalid_multiple_part(mocker, capfd):
    Path("parts.yaml").write_text(parts_yaml)

    # run it once to build state
    mocker.patch.object(sys, "argv", ["cmd", "clean", "foo", "invalid"])
    with pytest.raises(SystemExit) as raised:
        main.main()
    assert raised.value.code == 3

    out, err = capfd.readouterr()
    assert err == (
        "Error: A part named 'invalid' is not defined in the parts list.\n"
        "Review the parts definition and make sure it's correct.\n"
    )
    assert out == ""


def test_main_import(mocker, capfd):
    mocker.patch.object(sys, "argv", ["cmd", "--version"])
    with pytest.raises(SystemExit):
        runpy.run_module("craft_parts", run_name="__main__")

    out, err = capfd.readouterr()
    assert out == f"craft-parts {craft_parts.__version__}\n"
    assert err == ""


def test_main_strict(mocker):
    """Test passing "--strict" on the command line."""
    Path("parts.yaml").write_text(parts_yaml)
    mocker.patch.object(sys, "argv", ["cmd", "--strict"])

    spied_lcm = mocker.spy(craft_parts.LifecycleManager, name="__init__")
    main.main()

    kwargs = spied_lcm.call_args[1]
    assert kwargs == {
        "application_name": "craft_parts",
        "base": "",
        "base_layer_dir": None,
        "base_layer_hash": b"",
        "cache_dir": mocker.ANY,
        "strict_mode": True,
        "work_dir": ".",
    }

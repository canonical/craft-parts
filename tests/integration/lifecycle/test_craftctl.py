# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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

import craft_parts
import pytest
import yaml
from craft_parts import Action, ActionType, Step, errors

from tests import TESTS_DIR


@pytest.fixture(autouse=True)
def setup_feature(enable_overlay_feature):
    return


@pytest.fixture(autouse=True)
def setup_fixture(new_dir, mocker):
    craftctl = Path("craftctl")
    craftctl.write_text(f"#!{sys.executable}\nfrom craft_parts import ctl\nctl.main()")
    craftctl.chmod(0o755)

    mocker.patch.dict(
        os.environ,
        {
            "PATH": "/bin" + os.pathsep + str(new_dir),
            "PYTHONPATH": str(TESTS_DIR.parent),
        },
    )

    mocker.patch("craft_parts.utils.os_utils.mount")
    mocker.patch("craft_parts.utils.os_utils.mount_overlayfs")
    mocker.patch("craft_parts.utils.os_utils.umount")


def test_craftctl_default(new_dir, partitions, capfd, mocker):
    mocker.patch("craft_parts.lifecycle_manager._ensure_overlay_supported")
    mocker.patch("craft_parts.overlays.OverlayManager.refresh_packages_list")

    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: dump
            source: foo
            override-pull: |
              echo "pull step"
              craftctl default
            overlay-script: |
              echo "overlay step"
            override-build: |
              echo "build step"
              craftctl default
            override-stage: |
              echo "stage step"
              craftctl default
            override-prime: |
              echo "prime step"
              craftctl default
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("foo").mkdir()
    Path("foo/foo.txt").touch()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_ctl",
        cache_dir=new_dir,
        base_layer_dir=new_dir,
        base_layer_hash=b"hash",
        partitions=partitions,
    )

    # Check if planning resulted in the correct list of actions.
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.OVERLAY),
        Action("foo", Step.BUILD),
        Action("foo", Step.STAGE),
        Action("foo", Step.PRIME),
    ]

    # Execute each step and verify if scriptlet and built-in handler
    # ran as expected.

    with lf.action_executor() as ctx:
        # Execute the pull step. The source file must have been
        # copied to the part src directory.
        ctx.execute(actions[0])
        captured = capfd.readouterr()
        assert captured.out == "pull step\n"
        assert Path("parts/foo/src/foo.txt").exists()
        assert Path("parts/foo/install/foo.txt").exists() is False
        assert Path("stage/foo.txt").exists() is False
        assert Path("prime/foo.txt").exists() is False

        # Execute the overlay step and add a file to the overlay
        # directory to track file migration.
        ctx.execute(actions[1])
        captured = capfd.readouterr()
        Path("parts/foo/layer/ovl.txt").touch()
        assert captured.out == "overlay step\n"

        # Execute the build step. The source file must have been
        # copied to the part install directory.
        ctx.execute(actions[2])
        captured = capfd.readouterr()
        assert captured.out == "build step\n"
        assert Path("parts/foo/install/foo.txt").exists()
        assert Path("stage/foo.txt").exists() is False
        assert Path("stage/ovl.txt").exists() is False
        assert Path("prime/foo.txt").exists() is False
        assert Path("prime/ovl.txt").exists() is False

        # Execute the stage step. Both source and overlay files
        # must be in the stage directory.
        ctx.execute(actions[3])
        captured = capfd.readouterr()
        assert captured.out == "stage step\n"
        assert Path("stage/foo.txt").exists()
        assert Path("stage/ovl.txt").exists()
        assert Path("prime/foo.txt").exists() is False
        assert Path("prime/ovl.txt").exists() is False

        # Execute the prime step. Both source and overlay files
        # must be in the prime directory.
        ctx.execute(actions[4])
        captured = capfd.readouterr()
        assert captured.out == "prime step\n"
        assert Path("prime/foo.txt").exists()
        assert Path("prime/ovl.txt").exists()


def test_craftctl_default_arguments(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: craftctl default argument
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_ctl",
        cache_dir=new_dir,
        base_layer_dir=new_dir,
        base_layer_hash=b"hash",
        partitions=partitions,
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert "invalid arguments to command 'default'" in captured.err


def test_craftctl_set(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=myvalue
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": ""},
        partitions=partitions,
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
    assert lf.project_info.get_project_var("myvar") == "myvalue"


def test_craftctl_set_multiple(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=myvalue myvar2=myvalue2
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": "", "myvar2": ""},
        partitions=partitions,
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert "invalid arguments to command 'set'" in captured.err


def test_craftctl_set_bad_part_name(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=myvalue
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="bar",
        project_vars={"myvar": "x"},
        partitions=partitions,
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert "variable 'myvar' can only be set in part 'bar'" in captured.err


def test_craftctl_set_no_part_name(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=myvalue
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars={"myvar": "x"},
        partitions=partitions,
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert (
        "variable 'myvar' can only be set in a part that adopts external metadata"
        in captured.err
    )


def test_craftctl_set_multiple_parts(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=myvalue
          bar:
            plugin: nil
            override-pull: |
              craftctl set myvar2=myvalue2
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": "x", "myvar2": "y"},
        partitions=partitions,
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        expected = "override-pull' in part 'bar' failed with code 1"
        with pytest.raises(errors.ScriptletRunError, match=expected):
            ctx.execute(Action("bar", Step.PULL))

    assert lf.project_info.get_project_var("myvar") == "myvalue"
    assert lf.project_info.get_project_var("myvar2") == "y"

    captured = capfd.readouterr()
    assert "variable 'myvar2' can only be set in part 'foo'" in captured.err


def test_craftctl_set_error(new_dir, partitions, capfd, mocker):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=myvalue
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        partitions=partitions,
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert "'myvar' not in project variables" in captured.err


def test_craftctl_set_only_once(new_dir, partitions, capfd, mocker):  # see LP #1831135
    parts_yaml = textwrap.dedent(
        """\
        parts:
          part1:
            plugin: nil
            override-pull: |
              craftctl default
              craftctl set version=xx

          part2:
            plugin: nil
            after: [part1]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="part1",
        project_vars={"version": ""},
        partitions=partitions,
    )

    assert lf.project_info.get_project_var("version", raw_read=True) == ""

    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert lf.project_info.get_project_var("version") == "xx"

    # change something in part1 to make it dirty
    parts["parts"]["part1"]["override-pull"] += "\necho foo"

    # now build only part2 so that pull order will be reversed
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="part1",
        project_vars={"version": ""},
        partitions=partitions,
    )

    assert lf.project_info.get_project_var("version", raw_read=True) == ""

    # execution of actions must succeed
    actions = lf.plan(Step.BUILD, part_names=["part2"])
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert lf.project_info.get_project_var("version") == "xx"


def test_craftctl_update_project_vars(new_dir, partitions, capfd, mocker):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          part1:
            plugin: nil
            override-pull: |
              craftctl default
              craftctl set version=xx

          part2:
            plugin: nil
            after: [part1]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="part1",
        project_vars={"version": ""},
        partitions=partitions,
    )

    assert lf.project_info.get_project_var("version", raw_read=True) == ""

    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert lf.project_info.get_project_var("version") == "xx"

    # re-execute the lifecycle with no changes
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="part1",
        project_vars={"version": ""},
        partitions=partitions,
    )

    assert lf.project_info.get_project_var("version", raw_read=True) == ""

    actions = lf.plan(Step.BUILD)

    # all actions should be skipped
    for action in actions:
        assert action.action_type == ActionType.SKIP

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert lf.project_info.get_project_var("version") == "xx"


def test_craftctl_get_error(new_dir, partitions, capfd, mocker):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl get myvar
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_set", cache_dir=new_dir, partitions=partitions
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert "'myvar' not in project variables" in captured.err


def test_craftctl_set_argument_error(new_dir, partitions, capfd, mocker):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        partitions=partitions,
    )

    expected = "override-pull' in part 'foo' failed with code 1"
    with pytest.raises(errors.ScriptletRunError, match=expected):
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    captured = capfd.readouterr()
    assert "invalid arguments to command 'set' (want key=value)" in captured.err


def test_craftctl_set_consume(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=val1
            override-build: |
              craftctl get myvar
              craftctl set myvar=val2
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": ""},
        partitions=partitions,
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        assert lf.project_info.get_project_var("myvar", raw_read=True) == "val1"

        expected = "override-build' in part 'foo' failed with code 1"
        with pytest.raises(errors.ScriptletRunError, match=expected):
            ctx.execute(Action("foo", Step.BUILD))

        captured = capfd.readouterr()
        assert captured.out == "val1\n"
        assert "variable 'myvar' can be set only once" in captured.err


def test_craftctl_project_vars_from_state(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=val1
        """
    )
    parts = yaml.safe_load(parts_yaml)

    # run the lifecycle and execute pull. The pull scriptlet sets
    # a project variable to "val1"

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": ""},
        partitions=partitions,
    )

    actions = lf.plan(Step.PULL)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # run the lifecycle again and execute build. The pull step is
    # skipped because it already ran, but the variable value set
    # in the previous execution must be

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": ""},
        partitions=partitions,
    )

    actions = lf.plan(Step.BUILD)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert lf.project_info.get_project_var("myvar") == "val1"


def test_craftctl_project_vars_write_once_from_state(new_dir, partitions, capfd):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              craftctl set myvar=val1
            override-prime: |
              craftctl set myvar2=val2
              craftctl set myvar=val2
        """
    )
    parts = yaml.safe_load(parts_yaml)

    # run the lifecycle. The pull scriptlet sets a project variable
    # to "val1". Plan for more than one step to generate multiple skipped
    # steps in the second run.

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": "", "myvar2": ""},
        partitions=partitions,
    )

    actions = lf.plan(Step.STAGE)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # run the lifecycle again and execute prime. Previous steps are
    # skipped because they already ran, and setting the variable again
    # in the prime step must fail.

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_set",
        cache_dir=new_dir,
        project_vars_part_name="foo",
        project_vars={"myvar": "", "myvar2": ""},
        partitions=partitions,
    )

    actions = lf.plan(Step.PRIME)

    expected = "override-prime' in part 'foo' failed with code 1"
    with lf.action_executor() as ctx:
        with pytest.raises(errors.ScriptletRunError, match=expected):
            ctx.execute(actions)

    captured = capfd.readouterr()
    assert "variable 'myvar' can be set only once" in captured.err
    assert lf.project_info.get_project_var("myvar2") == "val2"

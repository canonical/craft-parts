# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import pytest
import yaml

import craft_parts
from craft_parts import Action, Step, errors
from tests import TESTS_DIR


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


def test_craftctl_default(new_dir, capfd, mocker):
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
    )
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.OVERLAY),
        Action("foo", Step.BUILD),
        Action("foo", Step.STAGE),
        Action("foo", Step.PRIME),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions[0])
        captured = capfd.readouterr()
        assert captured.out == "pull step\n"
        assert Path("parts/foo/src/foo.txt").exists()
        assert Path("parts/foo/install/foo.txt").exists() is False
        assert Path("stage/foo.txt").exists() is False
        assert Path("prime/foo.txt").exists() is False

        ctx.execute(actions[1])
        captured = capfd.readouterr()
        Path("parts/foo/layer/ovl.txt").touch()
        assert captured.out == "overlay step\n"

        ctx.execute(actions[2])
        captured = capfd.readouterr()
        assert captured.out == "build step\n"
        assert Path("parts/foo/install/foo.txt").exists()
        assert Path("stage/foo.txt").exists() is False
        assert Path("stage/ovl.txt").exists() is False
        assert Path("prime/foo.txt").exists() is False
        assert Path("prime/ovl.txt").exists() is False

        ctx.execute(actions[3])
        captured = capfd.readouterr()
        assert captured.out == "stage step\n"
        assert Path("stage/foo.txt").exists()
        assert Path("stage/ovl.txt").exists()
        assert Path("prime/foo.txt").exists() is False
        assert Path("prime/ovl.txt").exists() is False

        ctx.execute(actions[4])
        captured = capfd.readouterr()
        assert captured.out == "prime step\n"
        assert Path("prime/foo.txt").exists()
        assert Path("prime/ovl.txt").exists()


def test_craftctl_default_argments(new_dir):
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
    )
    with pytest.raises(errors.InvalidControlAPICall) as raised:
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    assert raised.value.message == "invalid arguments to command 'default'"


def test_craftctl_set(new_dir):
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
        project_vars={"myvar": ""},
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
    assert lf.project_info.get_project_var("myvar") == "myvalue"


def test_craftctl_set_multiple(new_dir):
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
        project_vars={"myvar": "", "myvar2": ""},
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
    assert lf.project_info.get_project_var("myvar") == "myvalue"
    assert lf.project_info.get_project_var("myvar2") == "myvalue2"


def test_craftctl_set_part_name(new_dir):
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
        project_vars={"myvar": "x"},
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
    assert lf.project_info.get_project_var("myvar") == "myvalue"


def test_craftctl_set_bad_part_name(new_dir):
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
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
    assert lf.project_info.get_project_var("myvar") == "x"


def test_craftctl_set_multiple_parts(new_dir):
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
        project_vars={"myvar": "x", "myvar2": "y"},
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        ctx.execute(Action("bar", Step.PULL))

    assert lf.project_info.get_project_var("myvar") == "myvalue"
    assert lf.project_info.get_project_var("myvar2") == "myvalue2"


def test_craftctl_set_multiple_parts_restricted(new_dir):
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
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        ctx.execute(Action("bar", Step.PULL))

    assert lf.project_info.get_project_var("myvar") == "myvalue"
    assert lf.project_info.get_project_var("myvar2") == "y"


def test_craftctl_set_error(new_dir, capfd, mocker):
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
        parts, application_name="test_set", cache_dir=new_dir
    )
    with pytest.raises(errors.InvalidControlAPICall) as raised:
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    assert raised.value.part_name == "foo"
    assert raised.value.scriptlet_name == "override-pull"
    assert raised.value.message == "'myvar' not in project variables"


def test_craftctl_get_error(new_dir, capfd, mocker):
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
        parts, application_name="test_set", cache_dir=new_dir
    )
    with pytest.raises(errors.InvalidControlAPICall) as raised:
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    assert raised.value.part_name == "foo"
    assert raised.value.scriptlet_name == "override-pull"
    assert raised.value.message == "'myvar' not in project variables"


def test_craftctl_set_argument_error(new_dir, capfd, mocker):
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
        parts, application_name="test_set", cache_dir=new_dir
    )
    with pytest.raises(errors.InvalidControlAPICall) as raised:
        with lf.action_executor() as ctx:
            ctx.execute(Action("foo", Step.PULL))

    assert raised.value.part_name == "foo"
    assert raised.value.scriptlet_name == "override-pull"
    assert raised.value.message == "invalid arguments to command 'set'"


def test_craftctl_set_consume(new_dir, capfd):
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
        project_vars={"myvar": ""},
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        assert lf.project_info.get_project_var("myvar") == "val1"

        with pytest.raises(errors.InvalidControlAPICall) as raised:
            ctx.execute(Action("foo", Step.BUILD))

        captured = capfd.readouterr()
        assert captured.out == "val1\n"

        err = raised.value

        assert err.part_name == "foo"
        assert err.scriptlet_name == "override-build"
        assert err.message == (
            "cannot set variable 'myvar', it has already been consumed"
        )

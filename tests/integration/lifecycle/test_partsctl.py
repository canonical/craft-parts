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
    partsctl = Path("partsctl")
    partsctl.write_text(f"#!{sys.executable}\nfrom craft_parts import ctl\nctl.main()")
    partsctl.chmod(0o755)

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


def test_ctl_client_steps(new_dir, capfd, mocker):
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
              partsctl pull
            overlay-script: |
              echo "overlay step"
            override-build: |
              echo "build step"
              partsctl build
            override-stage: |
              echo "stage step"
              partsctl stage
            override-prime: |
              echo "prime step"
              partsctl prime
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


@pytest.mark.parametrize("step", [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME])
def test_ctl_client_step_argments(new_dir, step):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: partsctl pull argument
            override-build: partsctl build argument
            override-stage: partsctl stage argument
            override-prime: partsctl prime argument
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
            ctx.execute(Action("foo", step))

    assert raised.value.message == (
        "invalid arguments to function {!r}".format(step.name.lower())
    )


def test_ctl_client_set(new_dir):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              partsctl set myvar myvalue
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_set", cache_dir=new_dir, myvar=""
    )
    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
    assert lf.project_info.myvar == "myvalue"


def test_ctl_client_set_var_error(new_dir, capfd, mocker):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              partsctl set myvar myvalue
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
    assert raised.value.message == "'myvar' not in project custom arguments"


def test_ctl_client_set_argument_error(new_dir, capfd, mocker):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            override-pull: |
              partsctl set myvar myvalue anothervalue
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
    assert raised.value.message == "invalid number of arguments to function 'set'"

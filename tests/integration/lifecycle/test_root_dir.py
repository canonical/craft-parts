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
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Integration tests for LifecycleManager root_dir parameter.

These tests simulate a monorepo layout where a charm subdir has a sibling
package directory (e.g. ../common), mirroring what the mysql-operators
monorepo does with poetry path dependencies.
"""

from pathlib import Path

import craft_parts
import pytest
from craft_parts import Step


@pytest.fixture
def monorepo(tmp_path, monkeypatch):
    """Create a monorepo layout and cd into the charm subdir.

    Layout:
        root/
            charm/          <- CWD / work_dir
                src/
                    hello.py
            common/
                shared.py
    """
    charm = tmp_path / "charm"
    common = tmp_path / "common"
    (charm / "src").mkdir(parents=True)
    (charm / "src" / "hello.py").write_text("# charm code\n")
    common.mkdir()
    (common / "shared.py").write_text("# shared library\n")

    monkeypatch.chdir(charm)
    return tmp_path


def _make_lf(root, work_dir, cache_dir, **kwargs):
    parts = {"parts": {"my-part": {"plugin": "dump", "source": "."}}}
    return craft_parts.LifecycleManager(
        parts,
        application_name="test_root_dir",
        cache_dir=str(cache_dir),
        work_dir=str(work_dir),
        **kwargs,
    )


def _pull(lf):
    actions = lf.plan(Step.PULL)
    with lf.action_executor() as ctx:
        ctx.execute(actions)


class TestRootDir:
    def test_sibling_dirs_visible_with_root_dir(self, monorepo):
        """With root_dir set, the full git root is staged so ../common is accessible."""
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        lf = _make_lf(root, charm, cache, root_dir=root)
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "charm" / "src" / "hello.py").exists()
        assert (src_dir / "common" / "shared.py").exists()

    def test_without_root_dir_sibling_not_visible(self, monorepo):
        """Without root_dir, only the charm subdir is staged."""
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        lf = _make_lf(root, charm, cache)
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "src" / "hello.py").exists()
        assert not (src_dir / "common").exists()

    def test_existing_source_subdir_is_preserved(self, monorepo):
        """An existing source-subdir gets prepended with the charm subdir.

        The full root is staged and the original subdir is appended so the
        build still runs in charm/src/ as the user intended.
        """
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        parts = {"parts": {"my-part": {"plugin": "dump", "source": ".", "source-subdir": "src"}}}
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_root_dir",
            cache_dir=str(cache),
            work_dir=str(charm),
            root_dir=root,
        )
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "charm" / "src" / "hello.py").exists()
        assert (src_dir / "common" / "shared.py").exists()
        assert lf._part_list[0].spec.source_subdir == "charm/src"

    def test_work_dir_not_under_root_dir_raises(self, tmp_path):
        """root_dir must be an ancestor of work_dir."""
        root = tmp_path / "root"
        work = tmp_path / "other"
        root.mkdir()
        work.mkdir()

        parts = {"parts": {"my-part": {"plugin": "nil", "source": "."}}}
        with pytest.raises(ValueError, match="must be the same as or a subdirectory"):
            craft_parts.LifecycleManager(
                parts,
                application_name="test_root_dir",
                cache_dir=str(tmp_path),
                work_dir=str(work),
                root_dir=root,
            )

    def test_work_dir_equal_to_root_dir_is_valid(self, tmp_path, monkeypatch):
        """work_dir == root_dir is a valid configuration (no source rewriting needed)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "file.txt").write_text("hello\n")

        lf = _make_lf(tmp_path, tmp_path, tmp_path / ".cache", root_dir=tmp_path)
        _pull(lf)

        src_dir = tmp_path / "parts" / "my-part" / "src"
        assert (src_dir / "file.txt").exists()

    def test_root_dir_none_is_backward_compatible(self, monorepo):
        """root_dir=None (default) behaves exactly as before."""
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        lf = _make_lf(root, charm, cache, root_dir=None)
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "src" / "hello.py").exists()
        assert not (src_dir / "common").exists()

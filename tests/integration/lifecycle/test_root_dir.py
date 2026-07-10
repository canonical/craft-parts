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
from craft_parts import Features, Step


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


def _make_lf(work_dir, cache_dir, **kwargs):
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

        lf = _make_lf(charm, cache, root_dir=root)
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "charm" / "src" / "hello.py").exists()
        assert (src_dir / "common" / "shared.py").exists()

    def test_without_root_dir_sibling_not_visible(self, monorepo):
        """Without root_dir, only the charm subdir is staged."""
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        lf = _make_lf(charm, cache)
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
        part = lf._part_list[0]
        assert part._effective_source_subdir() == "charm/src"

    def test_work_dir_outside_root_dir_is_valid(self, tmp_path, monkeypatch):
        """work_dir does not need to be inside root_dir.

        In managed mode, work_dir=/root and root_dir=/root/project — work_dir
        is a parent of root_dir, not a child.  Sources that don't resolve
        inside root_dir are simply left unrewritten.
        """
        # CWD = root_dir; work_dir is a parent
        root = tmp_path / "project"
        work = tmp_path  # parent of root
        root.mkdir()
        (root / "file.txt").write_text("hello\n")
        monkeypatch.chdir(root)

        parts = {"parts": {"my-part": {"plugin": "dump", "source": "."}}}
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_root_dir",
            cache_dir=str(work / ".cache"),
            work_dir=str(work),
            root_dir=root,
        )
        _pull(lf)

        src_dir = work / "parts" / "my-part" / "src"
        assert (src_dir / "file.txt").exists()

    def test_work_dir_equal_to_root_dir_is_valid(self, tmp_path, monkeypatch):
        """work_dir == root_dir is a valid configuration (no source rewriting needed)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "file.txt").write_text("hello\n")

        lf = _make_lf(tmp_path, tmp_path / ".cache", root_dir=tmp_path)
        _pull(lf)

        src_dir = tmp_path / "parts" / "my-part" / "src"
        assert (src_dir / "file.txt").exists()

    def test_root_dir_none_is_backward_compatible(self, monorepo):
        """root_dir=None (default) behaves exactly as before."""
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        lf = _make_lf(charm, cache, root_dir=None)
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "src" / "hello.py").exists()
        assert not (src_dir / "common").exists()


class TestRootDirWithNonLocalSources:
    """root_dir must not rewrite non-local or absolute sources."""

    def test_absolute_source_not_rewritten(self, monorepo):
        """A part whose source is an absolute path is left unchanged."""
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        parts = {"parts": {"my-part": {"plugin": "dump", "source": str(root / "common")}}}
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_root_dir",
            cache_dir=str(cache),
            work_dir=str(charm),
            root_dir=root,
        )
        _pull(lf)

        src_dir = charm / "parts" / "my-part" / "src"
        # Only common/ contents (shared.py) should be staged, not the full root
        assert (src_dir / "shared.py").exists()
        assert not (src_dir / "charm").exists()

    def test_multiple_parts_only_local_source_rewritten(self, monorepo):
        """With multiple parts, only the relative-source part is rewritten.

        A second part with an absolute source should be staged without
        source-subdir injection from root_dir.
        """
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        parts = {
            "parts": {
                "local-part": {"plugin": "dump", "source": "."},
                "abs-part": {"plugin": "dump", "source": str(root / "common")},
            }
        }
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_root_dir",
            cache_dir=str(cache),
            work_dir=str(charm),
            root_dir=root,
        )
        _pull(lf)

        # local-part: full root staged, sibling visible
        local_src = charm / "parts" / "local-part" / "src"
        assert (local_src / "charm" / "src" / "hello.py").exists()
        assert (local_src / "common" / "shared.py").exists()

        # abs-part: only common/ contents, no root rewrite
        abs_src = charm / "parts" / "abs-part" / "src"
        assert (abs_src / "shared.py").exists()
        assert not (abs_src / "charm").exists()


class TestRootDirWithOverlay:
    """root_dir works correctly with overlays enabled.

    The overlay/ output dir lives inside work_dir (which is inside root_dir)
    and must not be captured by the source pull.
    """

    def test_overlay_dir_excluded_from_staged_source(self, monorepo, mocker):
        """When overlay feature is on, the overlay/ dir is not staged."""
        Features.reset()
        Features(enable_overlay=True)
        try:
            import sys

            mocker.patch("os.geteuid", return_value=0)
            mocker.patch.object(sys, "platform", "linux")
            mocker.patch(
                "craft_parts.overlays.OverlayManager.refresh_packages_list"
            )

            root = monorepo
            charm = root / "charm"
            cache = charm / ".cache"

            lf = craft_parts.LifecycleManager(
                {"parts": {"my-part": {"plugin": "dump", "source": "."}}},
                application_name="test_root_dir",
                cache_dir=str(cache),
                work_dir=str(charm),
                root_dir=root,
                base_layer_dir=charm / "base",
                base_layer_hash=b"hash",
            )
            _pull(lf)

            src_dir = charm / "parts" / "my-part" / "src"
            assert (src_dir / "common" / "shared.py").exists()
            overlay_dir_name = lf._project_info.dirs.overlay_dir.name
            assert not (src_dir / overlay_dir_name).exists()
        finally:
            Features.reset()


class TestRootDirWithPartitions:
    """root_dir works correctly with partitions enabled."""

    def test_root_dir_with_partitions_source_rewritten(self, monorepo):
        """root_dir source rewriting works when partitions are enabled."""
        Features.reset()
        Features(enable_partitions=True)
        try:
            root = monorepo
            charm = root / "charm"
            cache = charm / ".cache"

            lf = craft_parts.LifecycleManager(
                {"parts": {"my-part": {"plugin": "dump", "source": "."}}},
                application_name="test_root_dir",
                cache_dir=str(cache),
                work_dir=str(charm),
                root_dir=root,
                partitions=["default", "mypart"],
            )
            _pull(lf)

            src_dir = charm / "parts" / "my-part" / "src"
            assert (src_dir / "charm" / "src" / "hello.py").exists()
            assert (src_dir / "common" / "shared.py").exists()
        finally:
            Features.reset()


class TestRootDirEdgeCases:
    """Edge cases for root_dir source rewriting."""

    def test_work_dir_equals_root_dir_no_subdir_set(self, tmp_path, monkeypatch):
        """When work_dir == root_dir, no source_subdir is injected."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "file.txt").write_text("hello\n")

        parts = {"parts": {"my-part": {"plugin": "dump", "source": "."}}}
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_root_dir",
            cache_dir=str(tmp_path / ".cache"),
            work_dir=str(tmp_path),
            root_dir=tmp_path,
        )
        # No source-subdir should be set (resolved source is already root_dir)
        assert lf._part_list[0].spec.source_subdir == ""

        _pull(lf)

        src_dir = tmp_path / "parts" / "my-part" / "src"
        assert (src_dir / "file.txt").exists()

    def test_relative_source_pointing_to_sibling(self, monorepo):
        """A relative source that resolves inside root_dir is handled correctly.

        source: ../common resolves to root/common; LocalSource uses root_dir as
        the copy source and _effective_source_subdir() returns "common" so the
        build dir is set to root/common/.
        """
        root = monorepo
        charm = root / "charm"
        cache = charm / ".cache"

        parts = {"parts": {"my-part": {"plugin": "dump", "source": "../common"}}}
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_root_dir",
            cache_dir=str(cache),
            work_dir=str(charm),
            root_dir=root,
        )
        _pull(lf)

        # Full root is staged (source-subdir only affects the build directory, not pull)
        src_dir = charm / "parts" / "my-part" / "src"
        assert (src_dir / "common" / "shared.py").exists()
        assert lf._part_list[0]._effective_source_subdir() == "common"

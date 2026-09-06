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

import os
import stat
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step, overlays
from craft_parts.executor import collisions
from craft_parts.overlays import overlay_fs
from craft_parts.overlays.errors import OverlayMountError


SCENARIOS = {
    "file": {
        "target": Path("conflict.txt"),
        "yaml": textwrap.dedent(
            """
            parts:
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  rm $CRAFT_OVERLAY/conflict.txt
            """
        ),
    },
    "dir": {
        "target": Path("conflict"),
        "yaml": textwrap.dedent(
            """
            parts:
              B:
                plugin: nil
                overlay-script: |
                  mkdir $CRAFT_OVERLAY/conflict
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  rm -r $CRAFT_OVERLAY/conflict
            """
        ),
    },
}


def _collect_tree(root: Path) -> tuple[set[Path], set[Path]]:
    files: set[Path] = set()
    dirs: set[Path] = set()

    for current_root, directories, file_names in os.walk(root, topdown=True):
        current_path = Path(current_root)
        for file_name in file_names:
            files.add((current_path / file_name).relative_to(root))

        for directory in directories:
            path = current_path / directory
            relpath = path.relative_to(root)
            if path.is_symlink():
                files.add(relpath)
            else:
                dirs.add(relpath)

    return files, dirs


def _describe_path(path: Path) -> str:
    if not path.exists() and not path.is_symlink():
        return f"{path}:missing"

    mode = stat.S_IFMT(path.lstat().st_mode)
    if path.is_symlink():
        kind = f"symlink->{path.readlink()}"
    elif stat.S_ISCHR(mode):
        kind = "char-device"
    elif path.is_dir():
        kind = "dir"
    elif path.is_file():
        kind = "file"
    else:
        kind = f"mode={oct(mode)}"

    description = [
        f"{path}:{kind}",
        f"overlay_whiteout={overlay_fs.is_whiteout_file(path)}",
        f"oci_whiteout={overlays.is_oci_whiteout_file(path)}",
        f"overlay_opaque={overlay_fs.is_opaque_dir(path)}",
        f"oci_opaque={overlays.is_oci_opaque_dir(path)}",
    ]
    if stat.S_ISCHR(mode):
        rdev = path.stat().st_rdev
        description.append(f"major={os.major(rdev)}")
        description.append(f"minor={os.minor(rdev)}")

    return " ".join(description)


def _describe_tree(root: Path) -> list[str]:
    entries: list[str] = []

    for current_root, directories, file_names in os.walk(root, topdown=True):
        current_path = Path(current_root)
        for name in sorted(directories + file_names):
            entries.append(_describe_path(current_path / name))

    return entries


def _format_diagnostics(
    *,
    target: Path,
    lower_dir: Path,
    upper_dir: Path,
    visible_files: set[Path],
    visible_dirs: set[Path],
    lower_files: set[Path],
    lower_dirs: set[Path],
    upper_files: set[Path],
    upper_dirs: set[Path],
    overlay_candidates: dict[str, set[Path]],
    merged_files: set[Path] | None = None,
    merged_dirs: set[Path] | None = None,
) -> str:
    lines = [
        f"target={target}",
        f"lower_dir={lower_dir}",
        f"upper_dir={upper_dir}",
        f"visible_in_layer.files={sorted(map(str, visible_files))}",
        f"visible_in_layer.dirs={sorted(map(str, visible_dirs))}",
        f"collisions._get_overlay_layer_contents(lower).files={sorted(map(str, lower_files))}",
        f"collisions._get_overlay_layer_contents(lower).dirs={sorted(map(str, lower_dirs))}",
        f"collisions._get_overlay_layer_contents(upper).files={sorted(map(str, upper_files))}",
        f"collisions._get_overlay_layer_contents(upper).dirs={sorted(map(str, upper_dirs))}",
        f"overlay_candidates={{{', '.join(f'{name}: {sorted(map(str, contents))}' for name, contents in sorted(overlay_candidates.items()))}}}",
    ]
    if merged_files is not None and merged_dirs is not None:
        lines.extend(
            [
                f"mounted_overlay.files={sorted(map(str, merged_files))}",
                f"mounted_overlay.dirs={sorted(map(str, merged_dirs))}",
            ]
        )
    lines.extend(["lower_tree:", *_describe_tree(lower_dir), "upper_tree:", *_describe_tree(upper_dir)])
    return "\n".join(lines)


class TestOverlayDiagnostics:
    @staticmethod
    def _mount_overlay(lower_dir: Path, upper_dir: Path, mount_dir: Path, work_dir: Path):
        overlay = overlay_fs.OverlayFS(
            lower_dirs=[lower_dir],
            upper_dir=upper_dir,
            work_dir=work_dir,
        )
        mount_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        overlay.mount(mount_dir)
        return overlay

    @staticmethod
    def _run_overlay(parts_yaml: str, new_dir: Path, partitions: list[str] | None):
        base_dir = new_dir / "base"
        base_dir.mkdir()

        lifecycle = LifecycleManager(
            yaml.safe_load(parts_yaml),
            application_name="overlay_diagnostics",
            cache_dir=new_dir,
            base_layer_dir=base_dir,
            base_layer_hash=b"hash",
            partitions=partitions,
        )

        with lifecycle.action_executor() as executor:
            executor.execute(lifecycle.plan(Step.OVERLAY))

        parts_by_name = {part.name: part for part in lifecycle._part_list}
        return lifecycle, parts_by_name

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    def test_runner_supports_overlay_mounts_and_whiteouts(self, new_dir):
        new_dir = Path(new_dir)
        lower_dir = new_dir / "lower"
        upper_dir = new_dir / "upper"
        mount_dir = new_dir / "mount"
        work_dir = new_dir / "work"

        lower_dir.mkdir()
        upper_dir.mkdir()
        (lower_dir / "victim.txt").write_text("from lower")

        mknod_error = None
        whiteout_path = upper_dir / "victim.txt"
        try:
            os.mknod(whiteout_path, stat.S_IFCHR, os.makedev(0, 0))
        except OSError as err:
            mknod_error = repr(err)

        mount_error = None
        merged_files: set[Path] | None = None
        merged_dirs: set[Path] | None = None
        try:
            overlay = self._mount_overlay(lower_dir, upper_dir, mount_dir, work_dir)
        except OverlayMountError as err:
            mount_error = str(err)
        else:
            try:
                merged_files, merged_dirs = _collect_tree(mount_dir)
            finally:
                overlay.unmount()

        assert mknod_error is None and mount_error is None, "\n".join(
            [
                f"mknod_error={mknod_error}",
                f"mount_error={mount_error}",
                f"whiteout_path_exists={whiteout_path.exists() or whiteout_path.is_symlink()}",
                f"whiteout_description={_describe_path(whiteout_path)}",
                f"merged_files={sorted(map(str, merged_files or set()))}",
                f"merged_dirs={sorted(map(str, merged_dirs or set()))}",
            ]
        )
        assert Path("victim.txt") not in merged_files

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    @pytest.mark.parametrize("scenario", ["file", "dir"])
    def test_overlay_delete_is_hidden_from_collision_candidates(
        self, new_dir, partitions, scenario
    ):
        new_dir = Path(new_dir)
        data = SCENARIOS[scenario]
        try:
            lifecycle, parts = self._run_overlay(data["yaml"], new_dir, partitions)
        except OverlayMountError as err:
            pytest.skip(f"overlay lifecycle unavailable: {err}")
        target = data["target"]
        partition = partitions[0] if partitions else None
        lower_dir = parts["B"].part_layer_dirs[partition]
        upper_dir = parts["C"].part_layer_dirs[partition]

        lower_files, lower_dirs = collisions._get_overlay_layer_contents(lower_dir)
        upper_files, upper_dirs = collisions._get_overlay_layer_contents(upper_dir)
        visible_files, visible_dirs = overlays.visible_in_layer(lower_dir, upper_dir)
        overlay_candidates = {
            candidate.part_name: candidate.contents
            for candidate in collisions._get_candidates_from_overlay(
                lifecycle._part_list, partition
            )
        }
        diagnostics = _format_diagnostics(
            target=target,
            lower_dir=lower_dir,
            upper_dir=upper_dir,
            visible_files=visible_files,
            visible_dirs=visible_dirs,
            lower_files=lower_files,
            lower_dirs=lower_dirs,
            upper_files=upper_files,
            upper_dirs=upper_dirs,
            overlay_candidates=overlay_candidates,
        )

        assert target not in visible_files, diagnostics
        assert target not in visible_dirs, diagnostics
        assert target not in overlay_candidates["B"], diagnostics
        assert target not in overlay_candidates["C"], diagnostics

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    @pytest.mark.parametrize("scenario", ["file", "dir"])
    def test_overlay_mount_view_matches_visibility_helpers(
        self, new_dir, partitions, scenario
    ):
        new_dir = Path(new_dir)
        data = SCENARIOS[scenario]
        try:
            lifecycle, parts = self._run_overlay(data["yaml"], new_dir, partitions)
        except OverlayMountError as err:
            pytest.skip(f"overlay lifecycle unavailable: {err}")
        target = data["target"]
        partition = partitions[0] if partitions else None
        lower_dir = parts["B"].part_layer_dirs[partition]
        upper_dir = parts["C"].part_layer_dirs[partition]

        lower_files, lower_dirs = collisions._get_overlay_layer_contents(lower_dir)
        upper_files, upper_dirs = collisions._get_overlay_layer_contents(upper_dir)
        visible_files, visible_dirs = overlays.visible_in_layer(lower_dir, upper_dir)
        overlay_candidates = {
            candidate.part_name: candidate.contents
            for candidate in collisions._get_candidates_from_overlay(
                lifecycle._part_list, partition
            )
        }

        mount_dir = new_dir / f"mounted-{scenario}"
        work_dir = new_dir / f"work-{scenario}"
        try:
            overlay = self._mount_overlay(lower_dir, upper_dir, mount_dir, work_dir)
        except OverlayMountError as err:
            pytest.skip(f"overlay mount unavailable: {err}")

        try:
            merged_files, merged_dirs = _collect_tree(mount_dir)
        finally:
            overlay.unmount()

        diagnostics = _format_diagnostics(
            target=target,
            lower_dir=lower_dir,
            upper_dir=upper_dir,
            visible_files=visible_files,
            visible_dirs=visible_dirs,
            lower_files=lower_files,
            lower_dirs=lower_dirs,
            upper_files=upper_files,
            upper_dirs=upper_dirs,
            overlay_candidates=overlay_candidates,
            merged_files=merged_files,
            merged_dirs=merged_dirs,
        )

        assert (target in merged_files) == (target in visible_files), diagnostics
        assert (target in merged_dirs) == (target in visible_dirs), diagnostics

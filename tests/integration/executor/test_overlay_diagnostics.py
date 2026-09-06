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
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path
from platform import platform, python_version

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
                  python3 - <<'PY'
                  import os
                  from pathlib import Path

                  root = Path(os.environ["CRAFT_OVERLAY"])
                  entries = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
                  print("DIAG_B_RUNTIME=" + repr(entries))
                  PY
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  rm $CRAFT_OVERLAY/conflict.txt
                  python3 - <<'PY'
                  import os
                  from pathlib import Path

                  root = Path(os.environ["CRAFT_OVERLAY"])
                  entries = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
                  print("DIAG_C_RUNTIME=" + repr(entries))
                  PY
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
                  python3 - <<'PY'
                  import os
                  from pathlib import Path

                  root = Path(os.environ["CRAFT_OVERLAY"])
                  entries = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
                  print("DIAG_B_RUNTIME=" + repr(entries))
                  PY
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  rm -r $CRAFT_OVERLAY/conflict
                  python3 - <<'PY'
                  import os
                  from pathlib import Path

                  root = Path(os.environ["CRAFT_OVERLAY"])
                  entries = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
                  print("DIAG_C_RUNTIME=" + repr(entries))
                  PY
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
        entries.extend(
            _describe_path(current_path / name)
            for name in sorted(directories + file_names)
        )

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
    part_overlay_dirs: dict[str, Path] | None = None,
    merged_files: set[Path] | None = None,
    merged_dirs: set[Path] | None = None,
) -> str:
    lines = [
        f"runner.platform={platform()}",
        f"runner.python={python_version()}",
        f"runner.fuse_overlayfs={_fuse_overlayfs_version()}",
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
    if part_overlay_dirs:
        for part_name, overlay_dir in sorted(part_overlay_dirs.items()):
            lines.extend([f"overlay_dir[{part_name}]={overlay_dir}", *_describe_tree(overlay_dir)])
    return "\n".join(lines)


def _fuse_overlayfs_version() -> str:
    binary = shutil.which("fuse-overlayfs")
    if not binary:
        return "missing"

    result = subprocess.run(
        [binary, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or result.stderr).strip().replace("\n", " | ")
    return output or f"present at {binary}"


def _runner_details() -> list[str]:
    return [
        f"runner.platform={platform()}",
        f"runner.python={python_version()}",
        f"runner.fuse_overlayfs={_fuse_overlayfs_version()}",
    ]


class TestOverlayDiagnostics:
    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    def test_runner_mknod_whiteout_capability(self, new_dir):
        new_dir = Path(new_dir)
        whiteout_path = new_dir / "whiteout"

        error = None
        try:
            os.mknod(whiteout_path, stat.S_IFCHR, os.makedev(0, 0))
        except OSError as err:
            error = repr(err)

        diagnostics = "\n".join(
            [
                *_runner_details(),
                f"mknod_error={error}",
                f"whiteout_exists={whiteout_path.exists() or whiteout_path.is_symlink()}",
                f"whiteout_description={_describe_path(whiteout_path)}",
            ]
        )

        if error is not None:
            pytest.skip(diagnostics)
        assert overlay_fs.is_whiteout_file(whiteout_path), diagnostics

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    def test_runner_overlay_opaque_xattr_capability(self, new_dir):
        new_dir = Path(new_dir)
        opaque_dir = new_dir / "opaque-dir"
        opaque_dir.mkdir()

        setxattr_error = None
        getxattr_error = None
        clearxattr_error = None
        value = None
        try:
            os.setxattr(opaque_dir, "trusted.overlay.opaque", b"y")
        except OSError as err:
            setxattr_error = repr(err)
        else:
            try:
                value = os.getxattr(opaque_dir, "trusted.overlay.opaque")
            except OSError as err:
                getxattr_error = repr(err)

            try:
                os.removexattr(opaque_dir, "trusted.overlay.opaque")
            except OSError as err:
                clearxattr_error = repr(err)

        diagnostics = "\n".join(
            [
                *_runner_details(),
                f"setxattr_error={setxattr_error}",
                f"getxattr_error={getxattr_error}",
                f"removexattr_error={clearxattr_error}",
                f"opaque_value={value!r}",
                f"overlay_opaque_detected={overlay_fs.is_opaque_dir(opaque_dir)}",
                "opaque_tree=",
                *_describe_tree(new_dir),
            ]
        )

        if any(
            error is not None
            for error in (setxattr_error, getxattr_error, clearxattr_error)
        ):
            pytest.skip(diagnostics)
        assert value == b"y", diagnostics

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    @pytest.mark.parametrize("scenario", ["file", "dir"])
    def test_overlay_delete_records_expected_upperdir_artifacts(self, new_dir, scenario):
        new_dir = Path(new_dir)
        lower_dir = new_dir / f"lower-artifacts-{scenario}"
        upper_dir = new_dir / f"upper-artifacts-{scenario}"
        mount_dir = new_dir / f"mount-artifacts-{scenario}"
        work_dir = new_dir / f"work-artifacts-{scenario}"

        lower_dir.mkdir()
        upper_dir.mkdir()
        if scenario == "file":
            (lower_dir / "victim.txt").write_text("from lower")
            target = Path("victim.txt")
        else:
            (lower_dir / "victim").mkdir()
            (lower_dir / "victim" / "nested.txt").write_text("from lower")
            target = Path("victim")

        try:
            overlay = self._mount_overlay(lower_dir, upper_dir, mount_dir, work_dir)
        except OverlayMountError as err:
            pytest.skip(f"overlay mount unavailable: {err}")

        try:
            if scenario == "file":
                (mount_dir / target).unlink()
            else:
                shutil.rmtree(mount_dir / target)
            merged_files, merged_dirs = _collect_tree(mount_dir)
        finally:
            overlay.unmount()

        upper_files, upper_dirs = _collect_tree(upper_dir)
        target_path = upper_dir / target
        diagnostics = "\n".join(
            [
                *_runner_details(),
                f"scenario={scenario}",
                f"mounted_overlay.files={sorted(map(str, merged_files))}",
                f"mounted_overlay.dirs={sorted(map(str, merged_dirs))}",
                f"upperdir.files={sorted(map(str, upper_files))}",
                f"upperdir.dirs={sorted(map(str, upper_dirs))}",
                f"target_description={_describe_path(target_path)}",
                f"target_oci_whiteout_description={_describe_path(overlays.oci_whiteout(target_path))}",
                f"target_oci_opaque_description={_describe_path(overlays.oci_opaque_dir(target_path))}",
                "upper_tree=",
                *_describe_tree(upper_dir),
            ]
        )

        assert target not in merged_files, diagnostics
        assert target not in merged_dirs, diagnostics
        if scenario == "file":
            assert overlay_fs.is_whiteout_file(target_path), diagnostics
        else:
            assert target in upper_dirs, diagnostics
            assert overlay_fs.is_opaque_dir(target_path), diagnostics

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
    @pytest.mark.parametrize("scenario", ["file", "dir"])
    def test_overlay_delete_persists_across_remounts(self, new_dir, scenario):
        new_dir = Path(new_dir)
        lower_dir = new_dir / f"lower-{scenario}"
        upper_dir = new_dir / f"upper-{scenario}"
        mount_dir = new_dir / f"mount-{scenario}"
        mount_dir_second = new_dir / f"mount-remount-{scenario}"
        work_dir = new_dir / f"work-{scenario}"
        work_dir_second = new_dir / f"work-remount-{scenario}"

        lower_dir.mkdir()
        upper_dir.mkdir()
        if scenario == "file":
            (lower_dir / "victim.txt").write_text("from lower")
            target = Path("victim.txt")
        else:
            (lower_dir / "victim").mkdir()
            (lower_dir / "victim" / "nested.txt").write_text("from lower")
            target = Path("victim")

        try:
            overlay = self._mount_overlay(lower_dir, upper_dir, mount_dir, work_dir)
        except OverlayMountError as err:
            pytest.skip(f"overlay mount unavailable: {err}")

        try:
            if scenario == "file":
                (mount_dir / target).unlink()
            else:
                shutil.rmtree(mount_dir / target)
            live_files, live_dirs = _collect_tree(mount_dir)
        finally:
            overlay.unmount()

        remount_error = None
        remounted_files: set[Path] | None = None
        remounted_dirs: set[Path] | None = None
        try:
            overlay = self._mount_overlay(
                lower_dir, upper_dir, mount_dir_second, work_dir_second
            )
        except OverlayMountError as err:
            remount_error = str(err)
        else:
            try:
                remounted_files, remounted_dirs = _collect_tree(mount_dir_second)
            finally:
                overlay.unmount()

        diagnostics = "\n".join(
            [
                *_runner_details(),
                f"scenario={scenario}",
                "lower_tree_before=",
                *_describe_tree(lower_dir),
                "upper_tree_after_first_unmount=",
                *_describe_tree(upper_dir),
                f"first_mount.files={sorted(map(str, live_files))}",
                f"first_mount.dirs={sorted(map(str, live_dirs))}",
                f"remount_error={remount_error}",
                f"second_mount.files={sorted(map(str, remounted_files or set()))}",
                f"second_mount.dirs={sorted(map(str, remounted_dirs or set()))}",
            ]
        )

        assert target not in live_files, diagnostics
        assert target not in live_dirs, diagnostics
        assert remount_error is None, diagnostics
        assert target not in (remounted_files or set()), diagnostics
        assert target not in (remounted_dirs or set()), diagnostics

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

        diagnostics = "\n".join(
            [
                *_runner_details(),
                f"mknod_error={mknod_error}",
                f"mount_error={mount_error}",
                f"whiteout_path_exists={whiteout_path.exists() or whiteout_path.is_symlink()}",
                f"whiteout_description={_describe_path(whiteout_path)}",
                f"merged_files={sorted(map(str, merged_files or set()))}",
                f"merged_dirs={sorted(map(str, merged_dirs or set()))}",
            ]
        )

        if mknod_error is not None:
            pytest.skip(diagnostics)
        if mount_error is not None:
            pytest.skip(diagnostics)
        assert mount_error is None, diagnostics
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
        part_overlay_dirs = {
            "B": parts["B"].overlay_dirs[partition],
            "C": parts["C"].overlay_dirs[partition],
        }

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
            part_overlay_dirs=part_overlay_dirs,
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
        part_overlay_dirs = {
            "B": parts["B"].overlay_dirs[partition],
            "C": parts["C"].overlay_dirs[partition],
        }

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
            part_overlay_dirs=part_overlay_dirs,
            merged_files=merged_files,
            merged_dirs=merged_dirs,
        )

        assert (target in merged_files) == (target in visible_files), diagnostics
        assert (target in merged_dirs) == (target in visible_dirs), diagnostics

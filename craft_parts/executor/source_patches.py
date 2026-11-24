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

"""Helpers to apply source patches declared in part definitions."""

import logging
from pathlib import Path
from typing import TextIO

from craft_parts import errors
from craft_parts.parts import Part
from craft_parts.utils import process

logger = logging.getLogger(__name__)

Stream = TextIO | int | None


def apply_source_patches(part: Part, *, stdout: Stream, stderr: Stream) -> None:
    """Apply all patches configured for a part to its source tree."""
    if not part.spec.patches:
        return

    for patch in part.spec.patches:
        patch_path = Path(patch).expanduser()
        if not patch_path.is_absolute():
            patch_path = part.dirs.project_dir / patch_path

        if not patch_path.is_file():
            raise errors.PatchApplyError(
                part_name=part.name,
                patch=patch,
                message=f"patch file not found: {patch_path}",
            )

        command = [
            "patch",
            "--strip",
            "1",
            "--forward",
            "--batch",
            "--input",
            str(patch_path),
        ]

        logger.debug("Applying patch %r for part %r", patch_path, part.name)
        try:
            process.run(
                command,
                cwd=part.part_src_dir,
                stdout=stdout,
                stderr=stderr,
            )
        except process.ProcessError as process_error:
            output = process_error.result.combined.decode("utf-8", errors="replace")
            output_lower = output.lower()

            # `patch --forward` reports already-applied patches as non-zero.
            if "previously applied" in output_lower:
                logger.debug(
                    "Patch %r was already applied for part %r, skipping.",
                    patch_path,
                    part.name,
                )
                continue

            details = output.strip() or (
                f"command {command!r} exited with code "
                f"{process_error.result.returncode}"
            )
            raise errors.PatchApplyError(
                part_name=part.name,
                patch=patch,
                message=details,
            ) from process_error
        except OSError as err:
            raise errors.PatchApplyError(
                part_name=part.name,
                patch=patch,
                message=str(err),
            ) from err

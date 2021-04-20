# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Source handler error definitions."""

from craft_parts import errors


class SourceError(errors.PartsError):
    """Base class for source handler errors."""


class ChecksumMismatch(SourceError):
    """A checksum doesn't match the expected value."""

    def __init__(self, *, expected: str, obtained: str):
        self.expected = expected
        self.obtained = obtained
        brief = f"Expected digest {expected}, obtained {obtained}."

        super().__init__(brief=brief)

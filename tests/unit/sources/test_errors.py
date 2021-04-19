# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

from craft_parts.sources import errors


def test_checksum_mismatch():
    err = errors.ChecksumMismatch(expected="1234", obtained="5678")
    assert err.expected == "1234"
    assert err.obtained == "5678"
    assert err.brief == "Expected digest 1234, obtained 5678."
    assert err.details is None
    assert err.resolution is None

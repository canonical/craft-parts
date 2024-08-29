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

from typing import Any

import pytest


@pytest.fixture
def properties() -> dict[str, Any]:
    return {
        "plugin": "nil",
        "source": "http://example.com/hello-2.3.tar.gz",
        "source-checksum": "md5/d9210476aac5f367b14e513bdefdee08",
        "source-branch": "release",
        "source-commit": "2514f9533ec9b45d07883e10a561b248497a8e3c",
        "source-depth": 3,
        "source-subdir": "src",
        "source-tag": "v2.3",
        "source-type": "tar",
        "disable-parallel": True,
        "after": ["bar"],
        "stage-snaps": ["stage-snap1", "stage-snap2"],
        "stage-packages": ["stage-pkg1", "stage-pkg2"],
        "build-snaps": ["build-snap1", "build-snap2"],
        "build-packages": ["build-pkg1", "build-pkg2"],
        "build-environment": [{"ENV1": "on"}, {"ENV2": "off"}],
        "build-attributes": ["attr1", "attr2"],
        "organize": {"src1": "dest1", "src2": "dest2"},
        "stage": ["-usr/docs"],
        "prime": ["*"],
        "override-pull": "override-pull",
        "override-build": "override-build",
        "override-stage": "override-stage",
        "override-prime": "override-prime",
    }


@pytest.fixture
def project_options() -> dict[str, Any]:
    return {
        "application-name": "test",
        "target-arch": "amd64",
    }

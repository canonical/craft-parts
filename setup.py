#!/usr/bin/env python
#
# Copyright 2021-2022 Canonical Ltd.
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

"""The setup script."""

import os
import re

from setuptools import find_packages, setup  # type: ignore

VERSION = "1.22.0"

with open("README.md") as readme_file:
    readme = readme_file.read()


def is_ubuntu() -> bool:
    """Verify if running on Ubuntu."""
    try:
        with open("/etc/os-release") as release_file:
            os_release = release_file.read()
        if re.search(r"^ID(?:_LIKE)?=.*\bubuntu\b.*$", os_release, re.MULTILINE):
            return True
        return False
    except FileNotFoundError:
        return False


def is_rtd() -> bool:
    """Verify if running on ReadTheDocs."""
    return "READTHEDOCS" in os.environ


install_requires = [
    "overrides",
    "PyYAML",
    "pydantic>=1.9.0",
    "pydantic-yaml[pyyaml]",
    "pyxdg",
    "requests",
    "requests-unixsocket",
    "urllib3<2",  # keep compatible API
]

dev_requires = [
    "autoflake",
    "twine",
]

docs_require = [
    "sphinx",
    "sphinx-autodoc-typehints",
    "sphinx-lint",
    "sphinx-pydantic",
    "sphinx-rtd-theme",
    "sphinxcontrib-details-directive==0.1.0",
]

types_requires = [
    "mypy[reports]==0.991",
    "types-colorama",
    "types-docutils",
    "types-Pillow",
    "types-Pygments",
    "types-pytz",
    "types-PyYAML",
    "types-requests",
    "types-setuptools",
]

test_requires = [
    "black",
    "codespell",
    "coverage",
    "isort",
    "pydocstyle",
    "pylint",
    "pylint-fixme-info",
    "pylint-pytest",
    "pyright",
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "requests-mock",
    "ruff==0.0.239",
    "tox",
    "yamllint==1.29.0",
]

extras_requires = {
    "dev": dev_requires + docs_require + test_requires + types_requires,
    "docs": docs_require,
    "test": test_requires + types_requires,
    "types": types_requires,
    # Python-apt bindings for specific Ubuntu versions.
    # Up to date package links can be found at https://launchpad.net/ubuntu/+source/python-apt
    # Note: These extras can break requirements from other packages, so
    # do not use them in dependencies unless you know what you're doing.
    "focal-dev": [
        "python-apt@https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.0.1ubuntu0.20.04.1/python-apt_2.0.1ubuntu0.20.04.1.tar.xz"
    ],
    "jammy-dev": [
        "python-apt@https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.4.0ubuntu1/python-apt_2.4.0ubuntu1.tar.xz"
    ],
    "lunar-dev": [
        "python-apt@https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.5.3ubuntu1/python-apt_2.5.3ubuntu1.tar.xz"
    ],
    # Generic "apt" extra for handling any apt-based platforms (e.g. Debian, Ubuntu)
    "apt": ["python-apt"],
}


setup(
    name="craft-parts",
    version=VERSION,
    description="Craft parts tooling",
    long_description=readme,
    author="Canonical Ltd.",
    author_email="snapcraft@lists.snapcraft.io",
    url="https://github.com/canonical/craft-parts",
    license="GNU General Public License v3",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    entry_points={
        "console_scripts": [
            "craftctl=craft_parts.ctl:main",
        ],
    },
    install_requires=install_requires,
    extras_require=extras_requires,
    packages=find_packages(include=["craft_parts", "craft_parts.*"])
    + ["craft_parts_docs"],
    # todo: can we make the docs optional?
    package_dir={"craft_parts_docs": "docs/base"},
    package_data={
        "craft_parts": ["py.typed"],
        "craft_parts_docs": ["**"],
    },
    include_package_data=True,
    zip_safe=False,
)

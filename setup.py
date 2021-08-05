#!/usr/bin/env python
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

"""The setup script."""

from setuptools import find_packages, setup  # type: ignore


with open("README.md") as readme_file:
    readme = readme_file.read()

install_requires = [
    "PyYAML",
    "progressbar",
    "pydantic",
    "pydantic-yaml",
    "pyxdg",
    "requests",
    "requests-unixsocket",
]

try:
    os_release = open("/etc/os-release").read()
    ubuntu = "ID=ubuntu" in os_release
except FileNotFoundError:
    ubuntu = False

if ubuntu:
    install_requires += [
        "python-apt",
    ]

dev_requires = [
    "autoflake",
    "twine",
]

doc_requires = [
    "sphinx",
    "sphinx-autodoc-typehints",
    "sphinx-pydantic",
    "sphinx-rtd-theme",
]

test_requires = [
    "black",
    "codespell",
    "coverage",
    "flake8",
    "isort",
    "mypy",
    "pydocstyle",
    "pylint",
    "pylint-fixme-info",
    "pylint-pytest",
    "pytest",
    "pytest-mock",
    "requests-mock",
    "tox",
    "types-PyYAML",
    "types-requests",
]

extras_requires = {
    "dev": dev_requires + doc_requires + test_requires,
    "doc": doc_requires,
    "test": test_requires,
}

setup(
    name="craft-parts",
    version="1.0.0",
    description="Craft parts tooling",
    long_description=readme,
    author="Canonical Ltd.",
    author_email="snapcraft@lists.snapcraft.io",
    url="https://github.com/canonical/craft_parts",
    license="GNU General Public License v3",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "console_scripts": [
            "partsctl=craft_parts.ctl:main",
        ],
    },
    install_requires=install_requires,
    extras_require=extras_requires,
    packages=find_packages(include=["craft_parts", "craft_parts.*"]),
    package_data={"craft_parts": ["py.typed"]},
    include_package_data=True,
    zip_safe=False,
)

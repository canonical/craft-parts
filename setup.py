#!/usr/bin/env python
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

"""The setup script."""

from setuptools import find_packages, setup  # type: ignore


with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = [
    "pyyaml",
]

setup_requirements = [
    "pytest-runner",
]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Canonical Ltd",
    author_email="Canonical Ltd",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Craft parts tooling",
    entry_points={
        "console_scripts": [
            "partsctl=craft_parts.ctl:main",
        ],
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme,
    include_package_data=True,
    keywords="craft_parts",
    name="craft-parts",
    package_data={"craft_parts": ["py.typed", "data/schema"]},
    packages=find_packages(include=["craft_parts", "craft_parts.*"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/canonical/craft_parts",
    version="0.0.1",
    zip_safe=False,
)

#!/usr/bin/env python3

from setuptools import setup

setup(
    name="package_python",
    version="0.1",
    entry_points={"console_scripts": ["mytest=mytest:main"]},
)

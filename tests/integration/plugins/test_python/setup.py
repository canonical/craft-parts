#!/usr/bin/env python3

from setuptools import setup

setup(
    name="plugin_test",
    version="0.1",
    entry_points={"console_scripts": ["mytest=mytest:main"]},
)

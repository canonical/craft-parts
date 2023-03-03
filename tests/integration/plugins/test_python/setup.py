#!/usr/bin/env python3

from distutils.core import setup

setup(
    name="plugin_test",
    version="0.1",
    entry_points={"console_scripts": ["mytest=mytest:main"]},
)

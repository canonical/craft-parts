# Craft Parts

[![Documentation Status](https://readthedocs.com/projects/canonical-craft-parts/badge/?version=latest)](https://canonical-craft-parts.readthedocs-hosted.com/en/latest/?badge=latest)

Craft-parts provides a mechanism to obtain data from different sources,
process it in various ways, and prepare a filesystem subtree suitable for
deployment. The components used in its project specification are called
*parts*, which can be independently downloaded, built and installed, and
also depend on each other in order to assemble the subtree containing the
final artifacts.


# License

Free software: GNU Lesser General Public License v3


# Documentation

https://canonical-craft-parts.readthedocs-hosted.com/en/latest/

# Contributing

A `Makefile` is provided for easy interaction with the project. To see
all available options run:

```
make help
```

## Development Environment

In order to develop any `apt` related items, the `python-apt` package is needed.
The `apt` extra will require this package in general.

> Ubuntu 22.04 is assumed in the rest of this setup

Development packages, such as those to build the Apt Python package are required:

```bash
sudo apt install libapt-pkg-dev intltool fuse-overlayfs python3.10-venv python3-dev gcc g++ make
```

The following are required to run integration tests (it is a default target for `make tests`):
```bash
sudo snap install chisel --candidate
sudo apt install ninja-build cmake scons qt5-qmake p7zip rpm \
                 autoconf automake autopoint gcc git gperf help2man libtool texinfo \
                 pkg-config
```

Create virtual environment to develop in and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required Python packages

```bash
pip install -e .[dev,docs]
pip install https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.4.0ubuntu1/python-apt_2.4.0ubuntu1.tar.xz
```

### Python Apt across Ubuntu series
* focal (20.04): https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.0.1ubuntu0.20.04.1/python-apt_2.0.1ubuntu0.20.04.1.tar.xz
* jammy (22.04): https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.4.0ubuntu1/python-apt_2.4.0ubuntu1.tar.xz
* lunar (23.04): https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.5.3ubuntu1/python-apt_2.5.3ubuntu1.tar.xz
* noble (24.04): https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.7.7ubuntu1/python-apt_2.7.7ubuntu1.tar.xz

## Running tests

To run all tests in the suite run:

```bash
make tests
```

To get coverage information for Craft Parts from the unit tests:

```bash
make coverage
```
## Adding new requirements

If a new dependency is added to the project run:

```bash
make freeze-requirements
```

## Verifying documentation changes

To locally verify documentation changes run:

```bash
make docs
```

After running, newly generated documentation shall be available at
`./docs/_build/html/`.


## Committing code

Please follow these guidelines when committing code for this project:

- Use a topic with a colon to start the subject
- Separate subject from body with a blank line
- Limit the subject line to 50 characters
- Do not capitalize the subject line
- Do not end the subject line with a period
- Use the imperative mood in the subject line
- Wrap the body at 72 characters
- Use the body to explain what and why (instead of how)

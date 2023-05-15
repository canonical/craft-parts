#!/bin/bash -eux

venv_dir="$(mktemp -d)"

python3 -m venv "$venv_dir"
# shellcheck source=/dev/null
. "$venv_dir/bin/activate"

# Pull in host python3-apt site package to avoid installation.
site_pkgs="$(readlink -f "$venv_dir"/lib/python3.*/site-packages/)"
temp_dir="$(mktemp -d)"
pushd "$temp_dir"
apt download python3-apt
dpkg -x ./*.deb .
cp -r usr/lib/python3/dist-packages/* "$site_pkgs"
popd

pip install -e .
pip freeze --exclude-editable | grep -v ^python-apt== > requirements.txt

pip install -e .[dev]
pip freeze --exclude-editable | grep -v ^python-apt== > requirements-dev.txt

rm -rf "$venv_dir"

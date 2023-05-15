Python plugin
-------------

The Python plugin can be used for Python projects where you would want to do
any of the following things:

- Import Python modules with a :file:`requirements.txt` file.
- Build a Python project that has a :file:`setup.py` or
  :file:`pyproject.toml` file.
- Install packages using :command:`pip`.

This plugin uses the common plugin keywords as well as those for "sources".
For more information check the 'plugins' topic for the former and the
'sources' topic for the latter.

Additionally, this plugin uses the following plugin-specific keywords:

- ``python-requirements``
  (list of strings)
  List of paths to requirements files.

- ``python-constraints``
  (list of strings)
  List of paths to constraint files.

- ``python-packages``
  (list)
  A list of dependencies to get from PyPI. If needed, pip,
  setuptools and wheel can be upgraded here.

This plugin also interprets these specific build-environment entries:

- ``PARTS_PYTHON_INTERPRETER``
  (default: python3)
  The interpreter binary to search for in PATH.

- ``PARTS_PYTHON_VENV_ARGS``
  Additional arguments for venv.

By default this plugin uses Python from the base. If a different
interpreter is desired, it must be bundled (including the ``venv`` module)
and must be in the PATH.

Use of python3-<python-package> in stage-packages will force the
inclusion of the python interpreter.

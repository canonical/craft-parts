Python plugin
-------------

The Python It can be used for python projects where you would want to do:

- import python modules with a requirements.txt
- build a python project that has a setup.py
- install packages straight from pip

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

By default this plugin uses python from the base. If a different
interpreter is desired, it must be bundled (including venv) and must
be in PATH.

Use of python3-<python-package> in stage-packages will force the
inclusion of the python interpreter.

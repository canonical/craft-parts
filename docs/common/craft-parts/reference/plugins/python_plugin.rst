.. _craft_parts_python_plugin:

Python plugin
=============

The Python plugin can be used for Python projects where you would want to do
any of the following things:

- Import Python modules with a :file:`requirements.txt` file.
- Build a Python project that has a :file:`setup.py` or
  :file:`pyproject.toml` file.
- Install packages using :command:`pip`.


Keywords
--------

This plugin uses the common :ref:`plugin <part-properties-plugin>` keywords as
well as those for :ref:`sources <part-properties-sources>`.

Additionally, this plugin provides the plugin-specific keywords defined in the
following sections.

python-requirements
~~~~~~~~~~~~~~~~~~~
**Type:** list of strings

List of paths to requirements files.

python-constraints
~~~~~~~~~~~~~~~~~~
**Type:** list of strings

List of paths to constraint files.

python-packages
~~~~~~~~~~~~~~~
**Type:** list

A list of dependencies to install from PyPI. If needed, :command:`pip`,
:command:`setuptools` and :command:`wheel` can be upgraded here.


Environment variables
---------------------

This plugin also sets environment variables in the build environment. These are
defined in the following sections.

PARTS_PYTHON_INTERPRETER
~~~~~~~~~~~~~~~~~~~~~~~~
**Default value:** python3

The interpreter binary to search for in ``PATH``.

PARTS_PYTHON_VENV_ARGS
~~~~~~~~~~~~~~~~~~~~~~
**Default value:** (empty string)

Additional arguments for venv.

.. _python-details-begin:

Dependencies
------------

By default this plugin uses Python from the base when it is available and
appropriate to use. This depends on the tool and format in use.

* The bases used by Rockcraft do not contain Python, so it will need to be
  supplied in rocks that use it.
* Snaps that use strict confinement will use the version of Python in the
  base. Snaps that use classic confinement will use the host system's Python.

If a different interpreter is desired, it must be bundled (including the
``venv`` module) and its path must be included in the ``PATH`` environment
variable.

Use of ``python3-<python-package>`` in stage-packages will force the
inclusion of the Python interpreter.

.. _python-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

* It creates a virtual environment directly into the ``${CRAFT_PART_INSTALL}``
  directory.
* It uses :command:`pip` to install the required Python packages as configured
  in the ``python-requirements``, ``python-constraints`` and
  ``python-packages`` keywords.
* If the source contains a ``setup.py`` or ``pyproject.toml`` file, those
  files are used to install the dependencies specified by the package itself.


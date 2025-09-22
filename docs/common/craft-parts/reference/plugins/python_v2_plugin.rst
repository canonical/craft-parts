.. _python_v2_plugin:

Python plugin (v2)
==================

The Python plugin (v2) is the successor to the :ref:`craft_parts_python_plugin`. It can
be used for Python projects where you would want to do any of the following things:

- Import Python modules with a ``requirements.txt`` file.
- Build a Python project that has a ``setup.py`` or ``pyproject`` file.
- Install packages using ``pip``.

.. _python_v2_plugin-keywords:

Keys
----

This plugin provides the following unique keys.

python-requirements
~~~~~~~~~~~~~~~~~~~
**Type:** list of strings

List of paths to requirements files.

python-packages
~~~~~~~~~~~~~~~
**Type:**

A list of dependencies to install from PyPI. If needed, ``pip``, ``setuptools``, and
``wheel`` can be upgraded here.

.. _python_plugin_v2-environment_variables:

Environment variables
---------------------

This plugin also sets environment variables in the build environment. These are defined
in the following sections.

PIP_PYTHON
~~~~~~~~~~
**Default value:** The first instance of ``python3`` on the ``PATH``.

The Python interpreter for pip to use.

.. _python_plugin_v2-details-begin:

Dependencies
------------

The Python plugin needs the ``python3`` executable, but it does not provision it itself
and will refuse to use the base system-installed executable.

The recommended way of providing ``python3`` is to install it as a ``stage-package``.
Alternatively, a part can be added to build ``python3`` from source and stage the
binary. Then, the consuming part can declare its dependence on the binary by using the
``after`` key.

.. _python_plugin_v2-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

* It sets ``PIP_USER`` to ``1``, equivalent to passing ``--user``. For more information
  on this flag, see `the pip documentation
  <https://pip.pypa.io/en/stable/cli/pip_install/#install-user>`_. Then,
  ``PYTHONUSERBASE`` is set to the part's install directory, causing pip to install all
  packages to that location.
* Pip is used to install all of the requirements from the ``PIP_PYTHON`` environment
  variable, as well as any dependencies in a ``setup.py`` or ``pyproject.toml`` file,
  if present.
* A `sitecustomize <https://docs.python.org/3/library/site.html>`_ file is created,
  which adds the files from the part's install directory to Python's runtime import
  path.

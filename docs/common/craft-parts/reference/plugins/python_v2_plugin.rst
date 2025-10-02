.. _python_v2_plugin:

Python plugin (v2)
==================

The Python plugin (v2) is the successor to the :ref:`craft_parts_python_plugin`. It can
be used for Python projects where you would want to do any of the following things:

- Import Python modules with a ``requirements.txt`` file.
- Build a Python project that has a ``setup.py`` or ``pyproject.toml`` file.
- Install packages with pip.

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
**Type:** list of strings

Additional Python packages to install with pip.

.. _python_plugin_v2-environment_variables:

Environment variables
---------------------

This plugin also sets environment variables in the build environment. These are defined
in the following sections.


PIP_PYTHON
~~~~~~~~~~

**Default:** The first instance of ``python3`` in the ``PATH``.

The Python interpreter for pip to use.

.. _python_plugin_v2-details-begin:

Dependencies
------------

The Python plugin (v2) needs the ``python3`` executable, but it does not provision it
itself and won't use a system-wide executable.

The recommended way of providing ``python3`` is to install it as a ``stage-package``.
The recommended way of providing a Python executable to the plugin is to install it as
a ``stage-package``. Alternatively, a part can be added to build ``python3`` from
source and stage the binary. Then, the consuming part can declare its dependence on the
binary by using the ``after`` key, like so:

.. code-block:: yaml

    parts:
      python-bin:
        plugin: autotools
        source: https://github.com/python/cpython.git
        stage:
          - ./python

      python-app:
        plugin: python
        source: .
        after:
          - python-bin

.. _python_plugin_v2-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

* It sets ``PIP_USER`` to ``1``, equivalent to the ``--user`` argument.
  The `the pip documentation
  <https://pip.pypa.io/en/stable/cli/pip_install/#install-user>`_ describes this
  argument in detail.
* The ``PYTHONUSERBASE`` is set to the part's install directory, which pip uses as a
  destination.
* Pip is used to install all of the requirements from ``python-requirements`` and
  packages from ``python-packages``. This step will also install the project described
  in the ``setup.py`` or ``pyproject.toml`` file, if present.
* A `sitecustomize <https://docs.python.org/3/library/site.html>`_ file is created,
  which adds the files from the part's install directory to Python's runtime import
  path.

.. _craft_parts_poetry_plugin:

Poetry plugin
=============

The Poetry plugin can be used for Python projects that use the `Poetry
<https://python-poetry.org>`_ build system.

.. _craft_parts_poetry_plugin-keywords:

Keywords
--------

This plugin uses the common :ref:`plugin <part-properties-plugin>` keywords as
well as those for :ref:`sources <part-properties-sources>`.

Additionally, this plugin provides the plugin-specific keywords defined in the
following sections.

poetry-export-extra-args:
~~~~~~~~~~~~~~~~~~~~~~~~~
**Type:** list of strings

Extra arguments to pass at the end of the poetry `export command
<https://python-poetry.org/docs/cli/#export>`_.

poetry-pip-extra-args:
~~~~~~~~~~~~~~~~~~~~~~
**Type:** list of strings

Extra arguments to pass to ``pip install`` when installing dependencies.

poetry-with:
~~~~~~~~~~~~
**Type:** list of strings

`Dependency groups
<https://python-poetry.org/docs/managing-dependencies#dependency-groups>`_ to include.
By default, only the main dependencies are included.

.. _craft_parts_poetry_plugin-environment_variables:

Environment variables
---------------------

This plugin also sets environment variables in the build environment. User-set
environment variables will override these values. Users may also set `environment
variables to configure Poetry
<https://python-poetry.org/docs/configuration/#using-environment-variables>`_ using the
:ref:`build-environment <build_environment>` key.

PARTS_PYTHON_INTERPRETER
~~~~~~~~~~~~~~~~~~~~~~~~
**Default value:** python3

Either the interpreter binary to search for in ``PATH`` or an absolute path to
the interpreter (e.g. ``${CRAFT_STAGE}/bin/python``).

PARTS_PYTHON_VENV_ARGS
~~~~~~~~~~~~~~~~~~~~~~
**Default value:** (empty string)

Additional arguments passed to ``python -m venv``.

.. _poetry-details-begin:

Dependencies
------------

Python
~~~~~~

By default this plugin uses the system Python when available and appropriate to
use, using the same logic as the
:ref:`Python plugin <craft_parts_python_plugin>`. If a different interpreter is
desired, it must be made available in the build environment (including the ``venv``
module) and its path must be included in the ``PATH`` environment variable.
Use of ``python3-<python-package>`` in stage-packages will force the inclusion
of the Python interpreter.

Poetry
~~~~~~

By default, this plugin gets Poetry from the ``python3-poetry`` package on the build
system. If that is not desired (for example, if a newer version  of Poetry is
required), a ``poetry-deps`` part can install poetry in the build system. Any parts
that use the Poetry plugin must run ``after`` the ``poetry-deps`` part:

.. code-block:: yaml

  parts:
    poetry-deps:
      plugin: nil
      build-packages:
        - curl
        - python3
      build-environment:
        - POETRY_VERSION: "1.8.0"
      override-pull: |
        curl -sSL https://install.python-poetry.org | python3 -
    my-project:
      plugin: poetry
      source: .
      after: [poetry-deps]

.. _poetry-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

1. It creates a virtual environment directly into the ``${CRAFT_PART_INSTALL}``
   directory.
2. It uses :command:`poetry export` to create a ``requirements.txt`` file in the
   project's build directory.
3. It uses :command:`pip` to install the packages referenced in ``requirements.txt``
   into the virtual environment, without any additional dependencies.
4. It uses :command:`pip` to install the source package without any additional
   dependencies.
5. It runs :command:`pip check` to ensure the virtual environment is consistent.

.. _craft_parts_poetry_links:

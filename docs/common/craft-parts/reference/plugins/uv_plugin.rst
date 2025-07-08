.. _craft_parts_uv_plugin:

uv plugin
=========

The uv plugin can be used for Python projects that use the uv build tool.

.. _craft_parts_uv_plugin-keywords:

Keys
----

This plugin provides the following unique keys.

uv-extras
~~~~~~~~~
**Type:** list of strings

Extra dependencies to build with. Each element of the list is passed
exactly as ``--extra EXTRA``.

uv-groups
~~~~~~~~~
**Type:** list of strings

Extra dependency groups to build with. Each element of the list is passed
exactly as ``--group GROUP``.

.. _craft_parts_uv_plugin-environment_variables:

Environment variables
---------------------

Along with the variables defined by the Python plugin, this plugin responds to its
own special variables.

.. note::

  This section describes how this plugin uses uv-specific environment
  variables. For more information, as well as a complete list of environment
  variables for uv, see the `uv environment documentation 
  <https://docs.astral.sh/uv/configuration/environment/>`_.

UV_FROZEN
~~~~~~~~~
**Default value:** true

Whether or not to update the :file:`uv.lock` file. If true, :file:`uv.lock`
must exist and will be used as the single source of truth for dependency
versions, with no attempt made to update them before installation.

UV_PROJECT_ENVIRONMENT
~~~~~~~~~~~~~~~~~~~~~~
**Default value:** See below

A path to the Python virtual environment to build with. By default, this
variable populates itself with the directory in which this plugin will create
the virtual environment.

UV_PYTHON_DOWNLOADS
~~~~~~~~~~~~~~~~~~~
**Default value:** "never"

Whether or not to automatically download Python if the requested version is
missing.

UV_PYTHON
~~~~~~~~~
**Default value:** ``${PARTS_PYTHON_INTERPRETER}``

The version of Python that uv should use.

UV_PYTHON_PREFERENCE
~~~~~~~~~~~~~~~~~~~~
**Default value:** "only-system"

**Possible values:** only-system, only-managed, system, managed

Whether uv should prefer (or exclusively use) system or uv-managed Python
versions.

.. _uv-details-begin:

Dependencies
------------

The uv plugin needs the ``uv`` executable but does not provision it by itself, to allow
flexibility in the choice of version.

One way of providing ``uv`` is the ``astral-uv`` snap, declared as a ``build-snap`` from
the desired channel.

An alternative method is to define a part with the name ``uv-deps``, and declare that
the part using the ``uv`` plugin comes after the ``uv-deps`` part with the ``after``
key. In this case, the plugin will assume that this new part will stage the ``uv``
executable to be used in the build step. For installation instructions, see `uv
documentation <https://docs.astral.sh/uv/getting-started/installation/>`_.

.. _uv-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

* It creates a virtual environment in the ``${CRAFT_PART_INSTALL}`` directory.
* It uses :command:`uv sync` to install the required Python packages from
  the provided :file:`uv.lock` file.

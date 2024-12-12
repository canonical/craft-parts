.. _craft_parts_uv_plugin:

uv plugin
=========

The uv plugin can be used for Python projects that use the uv build tool.


Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the
following plugin-specific keywords:

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


Environment variables
---------------------

Along with the variables defined by the :ref:`Python plugin
<craft_parts_python_plugin-environment_variables>`, this plugin responds to its
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

The version of Python that uv should use. See :ref:`Python plugin environment
variables <craft_parts_python_plugin-environment_variables>` for more
information.

UV_PYTHON_PREFERENCE
~~~~~~~~~~~~~~~~~~~~
**Default value:** "only-system"

**Possible values:** only-system, only-managed, system, managed

Whether uv should prefer (or exclusively use) system or uv-managed Python
versions.


Dependencies
------------

uv must already be installed on the build system in order to use this plugin.
For installation instructions, see `uv documentation
<https://docs.astral.sh/uv/getting-started/installation/>`_.


How it works
------------

During the build step, the plugin performs the following actions:

* It creates a virtual environment in the ``${CRAFT_PART_INSTALL}`` directory.
* It uses :command:`uv sync` to install the required Python packages from
  the provided :file:`uv.lock` file.


See also
--------

:ref:`Python plugin <craft_parts_python_plugin>`

:ref:`Poetry plugin <craft_parts_poetry_plugin>`

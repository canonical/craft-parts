.. _craft_parts_pnpm_plugin:

Pnpm plugin
===========

Pnpm plugin is a plugin that simplifies building projects that use pnpm. By
default, it is equivalent to running:

.. code-block:: shell

    ./pnpm install --frozen-lockfile
    ./pnpm run build

When wrapper mode is disabled, this plugin bootstraps an official pnpm release
from GitHub and then runs:

.. code-block:: shell

    pnpm install --frozen-lockfile
    pnpm run build

Keys
----

This plugin provides the following unique keys.


pnpm-task
~~~~~~~~~

**Type:** string

Task to execute with pnpm. Default is ``run build``.


pnpm-parameters
~~~~~~~~~~~~~~~

**Type:** list of strings

Additional command-line arguments passed to the pnpm task command.


pnpm-use-wrapper
~~~~~~~~~~~~~~~~

**Type:** boolean

Whether to use a project-provided ``pnpm`` wrapper at
``<project-root>/pnpm``. Default is ``True``.


pnpm-version
~~~~~~~~~~~~

**Type:** string

Pnpm release version to bootstrap from official releases when
``pnpm-use-wrapper`` is ``False``. Default is ``10.12.1``.


Dependencies
------------

When ``pnpm-use-wrapper`` is ``False``, the plugin downloads the official pnpm
release binary from GitHub and makes it available in the build environment.

The pnpm plugin does not make a Node.js runtime available in the target
environment. This must be handled by the developer when defining the part,
according to each application's runtime requirements.


Example
-------

This example builds the pino-pretty project with pnpm and disables wrapper mode
so the plugin bootstraps pnpm from an official release.

.. code-block:: yaml

    parts:
      pino-pretty:
        plugin: pnpm
        source: https://github.com/pinojs/pino-pretty.git
        source-tag: v13.1.2
        pnpm-use-wrapper: false
        pnpm-version: 10.12.1
        pnpm-task: run lint
        build-packages:
          - nodejs

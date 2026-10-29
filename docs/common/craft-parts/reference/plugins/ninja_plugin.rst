.. _craft_parts_ninja_plugin:

Ninja plugin
============

Ninja plugin is a plugin that simplifies building projects that use the Ninja
build system. By default, it is equivalent to running:

.. code-block:: shell

	ninja

When ``ninja-install`` is enabled, this plugin also runs:

.. code-block:: shell

	DESTDIR=$CRAFT_PART_INSTALL ninja install

Keys
----

This plugin provides the following unique keys.


ninja-configure-command
~~~~~~~~~~~~~~~~~~~~~~~

**Type:** string

Optional command that runs before the Ninja build command (for example,
``cmake -S . -B build -G Ninja``).


ninja-build-directory
~~~~~~~~~~~~~~~~~~~~~

**Type:** string

Directory passed to Ninja with ``-C``. Default is ``.``.


ninja-target
~~~~~~~~~~~~

**Type:** string

Optional Ninja target to build.


ninja-parameters
~~~~~~~~~~~~~~~~~~~

**Type:** list of strings

Additional command-line arguments passed to the Ninja command.


ninja-install
~~~~~~~~~~~~~

**Type:** boolean

Whether to run ``ninja install`` after the build command. Default is ``False``.


Dependencies
------------

The plugin requires ``ninja`` to be available in the build environment. By default,
the plugin requests ``ninja-build`` as a build package.


Example
-------

This example builds and installs the yyjson project using a CMake configure step
followed by Ninja build and install commands.

.. code-block:: yaml

    parts:
      yyjson-ninja:
        plugin: ninja
        source: https://github.com/ibireme/yyjson.git
        source-tag: 0.10.0
        ninja-configure-command: cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
        ninja-build-directory: build
        ninja-target: all
        ninja-install: true
        build-packages:
          - cmake
          - build-essential

.. _craft_parts_colcon_plugin:

Colcon plugin
=============

The colcon plugin manages the colcon_ build tool inside a part.
It supports projects that build with CMake_ and Python_ packages
that build with ``setup.py``.

It stores build artifacts in the ``$CRAFT_PART_INSTALL`` path.

This plugin requires core24 or higher.


Keys
----

This plugin provides the following unique keys.

.. py:currentmodule:: craft_parts.plugins.colcon_plugin

.. kitbash-field:: ColconPluginProperties colcon_cmake_args

.. kitbash-field:: ColconPluginProperties colcon_packages

.. kitbash-field:: ColconPluginProperties colcon_packages_ignore


Environment variables
---------------------

The plugin sets:

- ``AMENT_PYTHON_EXECUTABLE`` to "/usr/bin/python3". This is required for ROS 2
  packages.
- ``COLCON_PYTHON_EXECUTABLE`` to "/usr/bin/python3".


Dependencies
------------

The colcon plugin needs the ``colcon`` executable to build the source.

The colcon plugin needs the ``colcon-core`` package to start ``colcon``,
``gcc/g++`` and ``cmake`` to build ``C/C++`` packages.
Additionally, extensions like ``colcon-cmake``,
``colcon-package-selection``,
``colcon-python-setup-py`` and ``colcon-parallel-executor``
are needed to support basic builds.
These dependencies are provided and handled by the plugin.


How it works
------------

During the build step the plugin performs the following actions:

#. Source colcon workspaces present in any stage snaps, and on the system.
#. Call ``colcon build`` with any colcon-specific keys set in the part,
   with ``--install-base $CRAFT_PART_INSTALL`` to install the built artifacts

The plugin injects ``-DCMAKE_BUILD_TYPE=Release`` and ``-DBUILD_TESTING=OFF``
into the CMake arguments by default. Each argument can be overridden with its own entry
in the ``colcon-cmake-args`` key.


Example
-------

The following snippet declares a part using the ``colcon`` plugin.
It fetches the GoogleTest source code from GitHub,
and builds only the ``gtest`` package.
It sets the CMAKE_BUILD_TYPE_ to ``RelWithDebInfo``
to generate debug symbols from the build:

.. code-block:: yaml

    parts:
      hello:
        source: https://github.com/google/googletest.git
        plugin: colcon
        colcon-cmake-args:
          - -DCMAKE_BUILD_TYPE=RelWithDebInfo
        colcon-packages:
            - gtest

.. _colcon: https://colcon.readthedocs.io/
.. _Python: https://www.python.org/
.. _CMake: https://cmake.org/
.. _CMAKE_BUILD_TYPE: https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_TYPE.html

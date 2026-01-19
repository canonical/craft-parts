.. _craft_parts_colcon_plugin:

Colcon plugin
=============

The colcon plugin configures projects using the colcon_ build tool.
This plugin supports by default CMake_ based projects as well as
Python_ based packages using ``setup.py``.

After a successful build, this plugin will install the generated artifacts in
``$CRAFT_PART_INSTALL``.


Keys
----

This plugin provides the following unique keys.


colcon-cmake-args
~~~~~~~~~~~~~~~~~

**Type:** list of strings

Arguments to pass to cmake projects.
Note that any arguments here which match colcon arguments
need to be prefixed with a space.
This can be done by quoting each argument with a leading space.


colcon-packages
~~~~~~~~~~~~~~~

**Type:** string

List of colcon packages to build.
If not specified, all packages in the workspace will be built.
If set to an empty list ([]), no packages will be built,
which could be useful if you only want Debian packages in the snap.

colcon-packages-ignore
~~~~~~~~~~~~~~~~~~~~~~

**Type:** string

List of packages for colcon to ignore.

Environment variables
---------------------

The plugin sets:
    - ``AMENT_PYTHON_EXECUTABLE``: "/usr/bin/python3" -- This is required for ROS 2
      packages.
    - ``COLCON_PYTHON_EXECUTABLE``: "/usr/bin/python3",


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
#. Call ``colcon build`` with any colcon-specific keywords set in the part,
   with ``--install-base $CRAFT_PART_INSTALL`` to install the built artifacts


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

.. _craft_parts_cmake_plugin:

CMake plugin
============

The CMake plugin configures projects using CMake_ and builds them
either using `GNU Make`_ or Ninja_.

After a successful build, this plugin will install the generated
binaries in ``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

cmake-parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Parameters to configure the project using common CMake semantics.

cmake-generator
~~~~~~~~~~~~~~~
**Type:** string
**Default:** "Unix Makefiles"

Determine the tool to use to build.  Can be either set to ``Ninja`` or ``Unix
Makefiles``.


Environment variables
---------------------

The plugin sets the CMAKE_PREFIX_PATH_ to the stage directory.

Dependencies
------------

The CMake plugin needs the ``cmake`` executable to configure, and
``make`` or ``ninja`` executable to build. ``make`` and ``ninja`` are
dependant on the selected ``cmake-generator``. These dependencies are
provided by the plugin as a ``build-packages`` entry.

The plugin also sets up ``gcc``.  Other compiler or library
dependencies the source requires to build are to be provided.

How it works
------------

During the build step the plugin performs the following actions:

* Run ``cmake`` in the build directory referring to the pulled source
  directory (this plugin runs an out of tree build). The preferred
  generator is set at this stage, and the project is configured with
  any ``cmake-parameters`` that might have been set.
* ``cmake --build`` is run to build the source, ``cmake`` itself takes
  care of calling ``make`` or ``ninja``;
* ``cmake`` calls the ``install`` target with ``DESTDIR`` set to
  ``$CRAFT_PART_INSTALL``.

Examples
--------

The following snippet declares a part using the ``cmake`` plugin. It
sets the CMAKE_BUILD_TYPE_ to ``RelWithDebInfo`` to generate debug
symbols from the build:

.. code-block:: yaml

    parts:
      hello:
        source: .
        plugin: cmake
        cmake-parameters:
          - -DCMAKE_BUILD_TYPE=RelWithDebInfo

.. _GNU Make: https://www.gnu.org/software/make/
.. _Ninja: https://ninja-build.org/
.. _CMake: https://cmake.org/
.. _CMAKE_PREFIX_PATH: https://cmake.org/cmake/help/latest/variable/CMAKE_PREFIX_PATH.html
.. _CMAKE_BUILD_TYPE: https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_TYPE.html

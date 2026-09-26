.. _craft_parts_cmake_plugin:

CMake plugin
============

The CMake plugin configures projects using `CMake <https://cmake.org>`__ and builds them
either using `GNU Make <https://www.gnu.org/software/make>`__ or `Ninja
<https://ninja-build.org>`__ as the build system.

After a successful build, this plugin will install the generated binaries in
``$CRAFT_PART_INSTALL``.


Keys
----

This plugin provides the following unique keys.

.. py:currentmodule:: craft_parts.plugins.cmake_plugin

.. kitbash-field:: CMakePluginProperties cmake_generator

.. kitbash-field:: CMakePluginProperties cmake_parameters


Environment variables
---------------------

The plugin sets the :literalref:`CMAKE_PREFIX_PATH <https://cmake.org/cmake/help/latest/variable/CMAKE_PREFIX_PATH.html>` to the stage directory.


Dependencies
------------

The CMake plugin needs the ``cmake`` executable to configure, and ``make`` or ``ninja``
executable to build. ``make`` and ``ninja`` are dependent on the selected
``cmake-generator``. These dependencies are provided by the plugin as a
``build-packages`` entry.

The plugin also sets up ``gcc``.  Other compiler or library dependencies the source
requires to build are to be provided.


How it works
------------

During the build step the plugin performs the following actions:

#. Run ``cmake`` in the build directory referring to the pulled source directory (this
   plugin runs an out of tree build). The preferred generator is set at this stage, and
   the project is configured with any ``cmake-parameters`` that might have been set.
#. ``cmake --build`` is run to build the source, ``cmake`` itself takes care of calling
   ``make`` or ``ninja``.
#. ``cmake`` calls the ``install`` target with ``DESTDIR`` set to
   ``$CRAFT_PART_INSTALL``.


Example
-------

The following snippet declares a part using the ``cmake`` plugin. It sets the
:literalref:`CMAKE_BUILD_TYPE <https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_TYPE.html>` to ``RelWithDebInfo`` to generate debug symbols from the build:

.. code-block:: yaml

    parts:
      hello:
        source: .
        plugin: cmake
        cmake-parameters:
          - -DCMAKE_BUILD_TYPE=RelWithDebInfo

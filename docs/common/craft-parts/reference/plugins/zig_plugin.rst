.. _craft_parts_zig_plugin:

.. meta::
    :description: Reference for the Zig plugin, including its configuration keys, dependencies, and example part definitions in YAML.

Zig plugin
==========

The Zig plugin builds projects that use the `Zig build system`_. The project must
contain a ``build.zig`` file at the root of the source, or in the directory set by
``source-subdir``. After a successful build, the plugin installs the artifacts from the
project's ``install`` step in ``$CRAFT_PART_INSTALL``.

The plugin builds for the architecture of the build environment. It doesn't choose an
optimization mode, CPU, or target for the project.


Keys
----

This plugin provides the following unique keys.

.. py:currentmodule:: craft_parts.plugins.zig_plugin

.. kitbash-field:: ZigPluginProperties zig_build_parameters

.. kitbash-field:: ZigPluginProperties zig_install_prefix

Each item in ``zig-build-parameters`` is passed to ``zig build`` as a single argument.
Shell expressions and environment variables, such as ``$ORIGIN``, aren't expanded. An
option that takes a separate value, such as ``--summary all``, must be given as two
items.


Environment variables
---------------------

During the build, this plugin sets the following variables:

* ``ZIG_LOCAL_CACHE_DIR`` to ``.zig-cache`` in the part's build directory. This cache
  is removed when the build step is cleaned.
* ``ZIG_GLOBAL_CACHE_DIR`` to ``zig/global`` in the part's cache directory. This cache
  is kept between builds of the part.

The install command sets ``DESTDIR`` to ``$CRAFT_PART_INSTALL``, and
``zig-install-prefix`` sets the prefix inside it. For example, with the default prefix
of ``/``, an executable installed to ``bin`` ends up in ``$CRAFT_PART_INSTALL/bin``.
With a prefix of ``/usr``, it ends up in ``$CRAFT_PART_INSTALL/usr/bin``.


.. _zig-details-begin:

Dependencies
------------

The Zig plugin needs Zig 0.11.0 or later. The version must also work with the
project's ``build.zig`` file and its dependencies.

By default, the plugin installs the compiler from the ``latest/beta`` channel of the
``zig`` snap. The compiler is used during the build and isn't shipped with the
application.

To use a different Zig version, define a part named ``zig-deps`` that provides the
compiler, and declare it in the ``after`` key of the part that uses the ``zig`` plugin.
When ``after`` includes ``zig-deps``, the plugin doesn't install the snap. For example,
the ``zig-deps`` part can install the snap from another channel with the
``build-snaps`` key, or stage a Zig distribution.

.. _zig-details-end:


How it works
------------

During the build step, the plugin performs the following actions:

#. Check that ``zig`` is available and that its version is supported.
#. Call ``zig build install`` in the part's build directory, with ``DESTDIR`` set to
   ``$CRAFT_PART_INSTALL``.
#. Pass the installation prefix, the parallel build count, and the items in
   ``zig-build-parameters``.
#. If the stage directory or its ``usr`` subdirectory exists, pass it with
   ``--search-prefix`` so the build can find what earlier parts staged.

The search prefixes don't include architecture-specific library directories, such
as ``usr/lib/<triplet>``. Projects that use ``pkg-config`` find staged libraries through
the ``PKG_CONFIG_PATH`` set by Craft Parts. Other projects need to add these library
paths in ``build.zig``.

Zig fetches project dependencies during the build step, so the build needs network
access unless the dependencies are already in the Zig cache.


Examples
--------

The following snippet declares a part that builds with the standard ``optimize``
option and installs the executable in ``$CRAFT_PART_INSTALL/usr/bin``:

.. code-block:: yaml

    parts:
      hello:
        plugin: zig
        source: .
        zig-install-prefix: /usr
        zig-build-parameters:
          - -Doptimize=ReleaseSafe

The following snippet uses the development version of Zig from the ``latest/edge``
channel of the ``zig`` snap:

.. code-block:: yaml

    parts:
      zig-deps:
        plugin: nil
        build-snaps:
          - zig/latest/edge
      hello:
        plugin: zig
        source: .
        after:
          - zig-deps


.. _Zig build system: https://ziglang.org/learn/build-system/

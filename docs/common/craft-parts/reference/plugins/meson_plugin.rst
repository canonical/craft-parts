.. _craft_parts_meson_plugin:

Meson plugin
============

The Meson plugin configures projects using Meson_ and builds them using Ninja_.

After a successful build, this plugin will install the generated
binaries in ``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

meson_parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Parameters to configure the project. See the reference to the `setup command`_
for a list of valid options.

Dependencies
------------

The plugin needs the ``meson`` executable to configure the project, and the
``ninja`` executable to build it. These are not installed by default but can
typically be provisioned via ``build-packages`` or ``build-snaps``.

Another alternative is to define another part with the name ``meson-deps``, and
declare that the part using the ``meson`` plugin comes :ref:`after <after>` the
``meson-deps`` part. In this case, the plugin will assume that this new part will
stage the ``meson`` and ``ninja`` executables to be used in the build step.
This can be useful, for example, in cases where specific, unreleased versions of
the tools are desired but unavailable as a snap or an Ubuntu package.

How it works
------------

During the build step the plugin performs the following actions:

* Run ``meson`` in the build directory referring to the pulled source
  directory (this plugin runs an out of tree build). The project is configured
  with any ``meson-parameters`` that might have been set;
* ``ninja`` is run to build the source;
* ``ninja install`` is called with ``DESTDIR`` set to ``$CRAFT_PART_INSTALL``.

Examples
--------

The following snippet declares a part using the ``meson`` plugin. It uses
``--buildtype=release`` to generate optimised release binaries with no debug
symbols. The declaration of the ``meson`` package as a ``build-package`` will
also pull in the ``ninja-build`` package as a dependency.

.. code-block:: yaml

    parts:
      my-meson-part:
        source: .
        plugin: meson
        build-packages:
          - meson
        meson-parameters:
          - "--buildtype=release"

.. _Meson: https://mesonbuild.com/
.. _Ninja: https://ninja-build.org/
.. _setup command: https://mesonbuild.com/Commands.html#setup

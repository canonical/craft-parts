.. _craft_parts_scons_plugin:

SCons plugin
============

The SCons plugin builds projects using SCons_.

After a successful build, this plugin will install the generated
binaries in ``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

scons-parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Parameters to pass to SCons for building and installation.

Environment variables
---------------------

This plugin sets ``DESTDIR`` to ``$CRAFT_PART_INSTALL``.

Dependencies
------------

The SCons plugin needs the ``scons`` executable to build, but does not
provision it by itself.

The common means of providing ``scons`` is through a
:ref:`build-packages <build_packages>` entry which for Ubuntu, would be ``scons``.

Another alternative is to define another part with the name ``scons-deps``, and
declare that the part using the ``scons`` plugin comes :ref:`after <after>` the
``scons-deps`` part. In this case, the plugin will assume that this new part will
provide the ``scons`` executable to be used in the build step. This can be useful,
for example, in cases where a specific, unreleased version of ``scons`` is desired
but only possible by either building the tool itself from source or through some
other custom mechanism.


How it works
------------

During the build step the plugin performs the following actions:

* Run ``scons`` with any ``scons-parameters`` that might have been set;
* Run ``scons install`` with any ``scons-parameters`` that might have been set,
  the ``DESTDIR`` environment variable would affect the final installation path.

Examples
--------

The following snippet declares a part using the ``scons`` plugin. It
sets the ``scons-parameters`` for a ``prefix`` to be set to
``/usr``. To ``scons`` executable dependency is satisfied with
:ref:`build-packages <build_packages>`:

.. code-block:: yaml

    parts:
      gpsd:
        source: .
        plugin: scons
        scons-parameters:
          - prefix=/usr
        build-packages:
          - scons


.. _SCons: https://scons.org/


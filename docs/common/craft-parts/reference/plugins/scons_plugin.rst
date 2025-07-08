.. _craft_parts_scons_plugin:

SCons plugin
============

The SCons plugin builds projects using SCons_.

After a successful build, this plugin will install the generated
binaries in ``$CRAFT_PART_INSTALL``.

Keys
----

This plugin provides the following unique keys.

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

The SCons plugin needs the ``scons`` executable to build, but does not provision it by
itself.

The common means of providing ``scons`` is through a ``build-packages`` entry which for
Ubuntu, would be ``scons``.

Another alternative is to define another part with the name ``scons-deps``, and declare
that the part using the ``scons`` plugin comes after the ``scons-deps`` part with the
``after`` key. In this case, the plugin will assume that this new part will provide the
``scons`` executable to be used in the build step. This can be useful, for example, in
cases where a specific, unreleased version of ``scons`` is desired but only possible by
either building the tool itself from source or through some other custom mechanism.


How it works
------------

During the build step the plugin performs the following actions:

* Run ``scons`` with any ``scons-parameters`` that might have been set;
* Run ``scons install`` with any ``scons-parameters`` that might have been set,
  the ``DESTDIR`` environment variable would affect the final installation path.

Example
-------

The following snippet declares a part using the ``scons`` plugin. It sets the
``scons-parameters`` for a ``prefix`` to be set to ``/usr``. To ``scons`` executable
dependency is satisfied by the ``build-packages`` key.

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

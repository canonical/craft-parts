.. _craft_parts_nil_plugin:

Nil plugin
==========

The Nil plugin can be used to by-pass the need for a plugin when only parts primitives
are required.

Common cases include:

- Adding only staging packages in a discrete part
- Building source for when there is no suitable plugin with the ``override-build`` key.


Keys
----

This plugin has no unique keys.

Dependencies
------------

This plugin has no dependencies.


How it works
------------

This plugin does nothing. It serves as a *noop* when there is a need to only use default
part properties.

Examples
--------

The following snippet declares a part using the ``nil`` plugin to fetch and unpack
``hello`` defined in the ``stage-packages`` key:

.. code-block:: yaml

    parts:
      nil:
        plugin: nil
        stage-packages:
          - hello

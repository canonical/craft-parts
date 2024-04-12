.. _how_to_nil_plugin:

Nil Plugin
==========

.. _how_to_unsupported_plugin:

How to build with no plugin support
-----------------------------------

The following snippet makes use of `ref: override-build <part-properties-override-build>`
to run a build and ensure that the built artifacts are staged. The following example uses
`Tup`_ to build the ``hello`` target from the ``Tupfile`` provided in the ``source`` and
later installed at the root of the part's installation directory to be ready for staging:

.. code-block:: yaml

   parts:
     custom:
       source: .
       build-packages:
         - tup
       override-build: |
         tup
         install -m 755 hello $CRAFT_PART_INSTALL/


.. _Tup: https://gittup.org/tup/     

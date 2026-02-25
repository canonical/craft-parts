.. _craft_parts_npm_use_plugin:

npm Use plugin
================

The NPM Use plugin packages `npm`_-based projects and, unlike the
:ref:`craft_parts_npm_plugin`, exports artifacts to a shared local directory.


Keys
----

This plugin has no unique keys.


.. _npm_use_self-contained_start:

Attributes
----------

This plugin supports the ``self-contained`` build attribute. Declaring this attribute
prevents access to any npm registries. All dependencies must then be provided in an
earlier part using the NPM Use plugin.

When this attribute is declared, NPM Use resolves dependency versions from what is
locally available in the shared directory.

.. _npm_use_self-contained_end:

.. _npm_use_details_begin:


Dependencies
------------

The NPM Use plugin needs the ``node`` and ``npm`` executables to build npm projects but
does not provision them to allow flexibility in the choice of version.

To provide these, one can either specify the appropriate Ubuntu packages as
``build-packages`` or use a ``build-snap`` such as ``node``.

.. _npm_use_details_end:


How it works
------------

If the self-contained build attribute is present, the plugin performs the following
actions during the build step:

#. Install dependencies from cached tarballs.
#. Update ``package.json`` to include ``bundledDependencies`` for all non-dev dependencies.
#. Run ``npm pack`` to create a tarball of the package with bundled dependencies.
#. Export the tarball to the shared cache directory.

If the self-contained attribute is not present, ``npm pack`` is run to create a tarball
of the package without bundled dependencies.

Examples
--------

The following snippet declares two parts: ``hello-dep``, which uses the ``npm-use``
plugin, and ``hello-app``. Before ``hello-app`` can build, the contents of ``hello-dep``
must be staged. This dependency is handled by declaring that ``hello-app`` must build
``after`` the ``hello-dep`` part.

.. code-block:: yaml

  parts:
    hello-dep:
      source: dep/
      plugin: npm-use
      build-snaps:
        - node
      build-attributes:
        - self-contained
    hello-app:
      source: app/
      plugin: npm
      build-snaps:
        - node
      build-attributes:
        - self-contained
      after:
        - hello-dep

.. _npm: https://www.npmjs.com/

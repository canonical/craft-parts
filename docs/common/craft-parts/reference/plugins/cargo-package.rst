.. _craft_parts_cargo-package_plugin:

cargo-package plugin
====================

The cargo-package plugin can be used for Rust projects that are dependencies of
other Rust packages. It is a companion plugin meant to be used with the
:ref:`Rust plugin <craft_parts_rust_plugin>`. Use of this plugin makes rust
builds in all parts happen offline.

.. _craft_parts_cargo-package_plugin-keywords:

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the
following plugin-specific keywords:

cargo-package-features
~~~~~~~~~~~~~~~~~~~~~~
**Type:** list of strings

Features used to build optional dependencies.
This is equivalent to the ``--features`` option in Cargo.

cargo-package-cargo-command
~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Type:** string

What command to use as the ``cargo`` executable. Can be used if a non-default
version of cargo is needed. For example: ``cargo: /usr/bin/cargo-1.82``

.. _craft_parts_uv_plugin-environment_variables:

Environment variables
---------------------

CARGO_REGISTRY_DIRECTORY
~~~~~~~~~~~~~~~~~~~~~~~~

The location where cargo will publish the crate.

.. _cargo-details-begin:

Dependencies
------------

cargo must already be installed on the build system in order to use this plugin.
.. _cargo-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

#. It sets up the system to use a local craft-parts directory registry
#. It packages the crate
#. It publishes the crate to a local directory registry for use by other parts

When setting up the system, it makes the craft-parts directory registry, which is
the destination of all parts using this plugin, the default registry. It also installs
an ``apt`` registry to allow dependent parts to collect dependencies from
``librust-*-dev`` packages if they choose.

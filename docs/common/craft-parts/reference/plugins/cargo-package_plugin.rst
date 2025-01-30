.. _craft_parts_cargo-package_plugin:

Cargo package plugin
====================

The Cargo package plugin can be used for Rust projects that are dependencies of
other Rust packages. It is a companion plugin meant to be used with the
:ref:`Rust plugin <craft_parts_rust_plugin>`. Use of this plugin makes Rust
builds in *all* parts happen offline.

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

**Example:** ``cargo: /usr/bin/cargo-1.82``

What command to use as the ``cargo`` executable. Can be used if a custom
version of Cargo is needed.

.. _craft_parts_cargo-package_plugin-environment_variables:

Environment variables
---------------------

CARGO_REGISTRY_DIRECTORY
~~~~~~~~~~~~~~~~~~~~~~~~

The location where Cargo will publish the crate. This doesn't need to be changed
in most cases.

.. _cargo-details-begin:

Dependencies
------------

Cargo must already be installed on the build system in order to use this plugin.

.. _cargo-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

#. It sets up the system to use a local ``craft-parts`` directory registry
#. It packages the crate
#. It publishes the crate to a local ``craft-parts`` directory registry for use by
   other parts

When setting up the system, it creates a ``craft-parts`` directory registry and makes
it the default registry for Cargo. It also installs an ``apt`` registry to allow
dependent parts to collect dependencies from ``librust-*-dev`` packages if they
choose. In this case, the final part's crate will need to `override dependencies
<https://doc.rust-lang.org/cargo/reference/overriding-dependencies.html>`_ to get the
correct crates from the correct locations.

Examples
--------

The following snippet declares a part named ``ascii`` using the ``cargo-package``
plugin and a ``hello`` part that uses it. Note how the ``hello`` part uses the
``after`` keyword to define that it only builds after the ``ascii`` part is run.

.. code-block:: yaml

    ascii:
      plugin: cargo-package
      source: https://github.com/tomprogrammer/rust-ascii.git
      source-tag: v1.1.0
    hello:
      after: [ascii]
      plugin: rust
      source: .
      rust-channel: none

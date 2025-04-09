.. _craft_parts_cargo_use_plugin:

Cargo Use plugin
=====================

The Cargo Use plugin allows for setting up a local `cargo registry`_ for `Rust`_ crates. It is
a companion plugin meant to be used with the :ref:`Rust plugin <craft_parts_rust_plugin>`.
Use of this plugin sets up local cargo registry and affects all Rust parts.

Keywords
--------

There are no additional keywords to the the common :ref:`plugin <part-properties-plugin>`
and :ref:`sources <part-properties-sources>` keywords.

.. _cargo-use-details-begin:

Dependencies
------------

The are no additional dependencies required by a plugin as it works similarly 
to :ref:`Dump plugin <craft_parts_dump_plugin>`.

.. _cargo-use-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Setup a local `cargo registry`_ if it has not been setup;
* Copy sources from ``<source-dir>`` to the local cargo registry dir;
* Add an empty ``.cargo-checksum.json`` file to satisfy registry requirements;

Examples
--------

The following snippet declares a parts named ``librust-cfg-if`` using the ``cargo-use`` plugin and
a ``hello`` part that declares this ``cfg-if``` in its ``Cargo.toml`` project file 
using the ``rust`` plugin.
Correct ordering is achieved with the use of the ``after`` keyword in the ``hello`` part.

.. code-block:: yaml

    parts:
      librust-cfg-if:
        source: https://github.com/rust-lang/cfg-if.git
        source-tag: 1.0.0
        plugin: cargo-use
      hello:
        build-snaps:
          - rustup
        plugin: rust
        source: .
        after:
        - librust-cfg-if


.. _Rust: https://doc.rust-lang.org/stable/
.. _cargo registry: https://doc.rust-lang.org/cargo/reference/registries.html

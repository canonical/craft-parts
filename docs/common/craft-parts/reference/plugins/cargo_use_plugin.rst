.. _craft_parts_cargo_use_plugin:

Cargo Use plugin
=====================

The Cargo Use plugin sets up a local `cargo registry`_ for `Rust`_ crates. It's
a companion plugin meant to be used with the :ref:`Rust plugin <craft_parts_rust_plugin>`.
It affects all Rust parts in a project.

Keywords
--------

The plugin provides the common :ref:`plugin <part-properties-plugin>`
and :ref:`sources <part-properties-sources>` keywords.

.. _cargo-use-details-begin:

Dependencies
------------

The ``cargo-use`` plugin has no dependencies.

.. _cargo-use-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Setup a local `cargo registry`_ if it has not been setup;
* Copy sources from ``<source-dir>`` to the local cargo registry dir;
* Add an empty ``.cargo-checksum.json`` file to satisfy registry requirements;

Examples
--------

The following snippet declares a pair of parts.

The first is named ``librust-cfg-if`` and uses the ``cargo-use`` plugin.

The second, the app of the pair, is named ``hello`` and uses the ``rust`` plugin. The
app's source has ``cfg-if`` as a dependency, which is why the ``librust-cfg-if`` part is
needed. The ``after`` keyword in the ``hello`` part establishes the correct ordering of
these parts, ensuring that ``librust-cfg-if`` is processed first.

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

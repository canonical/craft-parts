.. _craft_parts_rust_plugin:

.. meta::
    :description: Reference for the Rust plugin, including its configuration keys, Rust toolchain behavior, and example part definitions in YAML.

Rust plugin
=============

The Rust plugin can be used for Rust projects that use the Cargo build system.


Keys
----

This plugin provides the following unique keys.

.. py:currentmodule:: craft_parts.plugins.rust_plugin

.. kitbash-field:: RustPluginProperties rust_channel

.. kitbash-field:: RustPluginProperties rust_features
    :label: rust-features

.. kitbash-field:: RustPluginProperties rust_no_default_features
    :label: rust-no-default-features

.. kitbash-field:: RustPluginProperties rust_path

.. kitbash-field:: RustPluginProperties rust_use_global_lto
    :label: rust-use-global-lto

.. kitbash-field:: RustPluginProperties rust_ignore_toolchain_file

.. kitbash-field:: RustPluginProperties rust_cargo_parameters

.. kitbash-field:: RustPluginProperties rust_inherit_ldflags


Environment variables
---------------------

This plugin sets the PATH environment variable so the Rust compiler is accessible in the
build environment.

Some environment variables may also influence the Rust compiler or Cargo build tool. For
more information, see `Cargo documentation
<https://doc.rust-lang.org/cargo/reference/environment-variables.html>`_ for the
details.


Dependencies
------------

If Cargo and the Rust compiler are already available in the build environment, this plugin
uses them directly. Otherwise, it uses ``rustup`` to install or select a Rust toolchain.

To provide Rust through another part instead of ``rustup``, define a part named
``rust-deps``, list ``cargo`` and ``rustc`` with the ``stage-packages`` key, and declare it in
the ``after`` key of the part using the toolchain. For example:

.. code-block:: yaml

    parts:
      rust-deps:
        plugin: nil
        stage-packages:
          - cargo
          - rustc

      my-app:
        plugin: rust
        source: .
        after:
          - rust-deps

When ``after`` includes ``rust-deps``, or when ``rust-channel`` is set to ``"none"``,
the plugin validates that Cargo and the Rust compiler are available and does not use
``rustup``. Do not combine ``after: [rust-deps]`` when ``rust-channel`` is set to anything
but ``"none"``.


.. _perf-tuning:

Performance tuning
-------------------

.. warning::

    Keep in mind that due to individual differences between different projects, some of
    the optimisations may not work as expected or even incur performance penalties.

    Some programs may even behave differently or crash if aggressive optimisations are
    used.

Many Rust programs boast their performance over similar programs implemented in other
programming languages. To get even better performance, you might want to follow the tips
below.

* Use the :ref:`rust-use-global-lto` option to enable LTO support. This is suitable for
  most projects. However, analysing the whole program during the build time requires
  more memory and CPU time.
* Specify ``codegen-units=1`` in ``Cargo.toml`` to reduce LLVM parallelism. This may
  sound counter-intuitive, but reducing code generator threads could improve the quality
  of generated machine code. This option will also reduce the build time performance
  since the code generator uses only one thread per translation unit.
* Disable ``incremental=true`` in ``Cargo.toml`` to improve inter-procedural
  optimisations. Many projects may have already done this for the release profile. You
  should check if that is the case for your project.
* (Advanced) Perform cross-language LTO. This requires installing the correct version of
  LLVM/Clang and setting the right environment variables. You must know which LLVM
  version of your selected Rust toolchain is using. You can use ``rustc -vV`` to check
  the LLVM version used by the compiler. For example, you can see Rust 1.81 uses LLVM
  18.1 because it prints an output like this:

  .. terminal::
      :output-only:

      rustc 1.81.0 (eeb90cda1 2024-09-04)
      binary: rustc
      commit-hash: eeb90cda1969383f56a2637cbd3037bdf598841c
      commit-date: 2024-09-04
      host: x86_64-unknown-linux-gnu
      release: 1.81.0
      LLVM version: 18.1.7

  On Rust toolchains that don't include the LLVM version, you can check the LLVM version
  number by examining the ``lib`` directory. For example, Rust 1.81 uses LLVM 18.1
  because it bundles a ``libLLVM.so.18.1-rust-1.81.0-stable`` file under the ``lib``
  directory. In this case, you would install ``clang-18`` and ``lld-18`` from the Ubuntu
  archive.

  * You will need to set these environment variables for Clang:

    .. code-block:: yaml

        parts:
          my-app:
            plugin: rust
            source: .
            build-packages:
              - clang-18
              - lld-18
            build-environment:
              - CC: clang-18
              - CXX: clang++-18
              - CFLAGS: -flto=full -O3
              - CXXFLAGS: -flto=full -O3
              - RUSTFLAGS: "-Cembed-bitcode=yes -Clinker-plugin-lto -Clinker=clang-18 -Clink-arg=-flto=full -Clink-arg=-fuse-ld=lld -Clink-arg=-Wl,--lto-O3"

    For some projects that manipulate the object files during the build, you may also
    need:

    .. code-block:: bash

        export NM=llvm-nm-18
        export AR=llvm-ar-18
        export RANLIB=llvm-ranlib-18

    You can refer to the `rustc documentation
    <https://doc.rust-lang.org/rustc/codegen-options/index.html>`_ for more information
    on the meaning of those options.

  * You will need significantly more memory and CPU time for large projects to build and
    link. For instance, Firefox under full LTO requires about 80 GiB of memory to pass
    the linking phase.

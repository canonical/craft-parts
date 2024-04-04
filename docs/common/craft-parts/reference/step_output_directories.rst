.. _craft_parts_step_output_directories:

Step output directories
-----------------------

Some of the environment variables above reference directories that are the
output locations for specific steps. These are repeated below for fast
reference:

- ``PULL``:
   - ``CRAFT_PART_SRC`` locates the source of the part.
   - ``CRAFT_PART_SRC_WORK`` locates the source subdirectory if overridden.
- ``OVERLAY``:
   - ``CRAFT_OVERLAY`` locates the combined overlay output from all parts.
- ``BUILD``:
   - ``CRAFT_PART_INSTALL`` contains the location of the build output step.
     This directory is the expected location of ``CARGO_INSTALL_ROOT`` for `Rust
     <https://doc.rust-lang.org/cargo/commands/cargo-install.html>`_,
     ``GOBIN`` for `go
     <https://pkg.go.dev/cmd/go#hdr-Compile_and_install_packages_and_dependencies>`_
     or ``DESTDIR`` for `make
     <https://www.gnu.org/software/make/manual/make.html#DESTDIR>`_.
- ``STAGE``:
   - ``CRAFT_STAGE`` contains the expected location of all staged outputs.
- ``PRIME``:
   - ``CRAFT_PRIME`` contains the path of the primed payload directory. This
     directory is shared by all parts.

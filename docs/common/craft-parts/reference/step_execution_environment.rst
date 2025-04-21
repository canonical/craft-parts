.. _craft_parts_step_execution_environment:

Step execution environment
--------------------------

Craft-parts defines the following environment for use during step
processing and execution of user-defined scriptlets:

.. list-table::
  :header-rows: 1

  * - Variable Name
    - Description
  * - ``CRAFT_ARCH_TRIPLET_BUILD_FOR``
    - The architecture triplet of the build target. For example:

      - ``x86_64-linux-gnu``
      - ``riscv64-linux-gnu``
  * - ``CRAFT_ARCH_TRIPLET_BUILD_ON``
    - The architecture triplet of the host running the build. For example:

      - ``x86_64-linux-gnu``
      - ``riscv64-linux-gnu``
  * - ``CRAFT_ARCH_BUILD_FOR``
    - The architecture of the build target. For example:

      - ``amd64``
      - ``riscv64``
  * - ``CRAFT_ARCH_BUILD_ON``
    - The architecture of the build target. For example:

      - ``amd64``
      - ``riscv64``
  * - ``CRAFT_PARALLEL_BUILD_COUNT``
    - The maximum number of concurrent build jobs to execute.
  * - ``CRAFT_PART_NAME``
    - The name of the part currently being processed.
  * - ``CRAFT_PART_SRC``
    - The path to the part source directory. This is where sources are located
      after the ``PULL`` step.
  * - ``CRAFT_PART_SRC_WORK``
    - The path to the part source subdirectory, if any. Defaults to the part
      source directory.
  * - ``CRAFT_PART_BUILD``
    - The path to the part build directory. This is where parts are built during
      the ``BUILD`` step.
  * - ``CRAFT_PART_BUILD_WORK``
    - The path to the part build subdirectory in case of out-of-tree builds.
      Defaults to the part source directory.
  * - ``CRAFT_PART_INSTALL``
    - The path to the part install directory. This is where built artefacts are
      installed after the ``BUILD`` step.
  * - ``CRAFT_OVERLAY``
    - (If overlays are enabled) The path to the part's layer directory during the
      ``OVERLAY`` step.
  * - ``CRAFT_STAGE``
    - The path to the project's staging directory. This is where installed
      artefacts are migrated during the ``STAGE`` step.
  * - ``CRAFT_PRIME``
    - The path to the final primed payload directory after the ``PRIME`` step.

The following environment variables are also included, but are deprecated:

.. list-table::
  :header-rows: 1

  * - Variable Name
    - Description
  * - ``CRAFT_ARCH_TRIPLET``
    - The machine-vendor-os platform triplet definition.
      Use ``CRAFT_ARCH_TRIPLET_BUILD_ON`` or ``CRAFT_ARCH_TRIPLET_BUILD_FOR`` instead.
  * - ``CRAFT_TARGET_ARCH``
    - The architecture of the build target. Use ``CRAFT_ARCH_BUILD_FOR`` instead.

Some standard environment variables are also modified during parts execution steps.

``PATH``
~~~~~~~~

Several paths are prepended to ``PATH`` during step execution, allowing staged
executables from previous parts as well as already-built executables from the current
path to be executed without calling their full path. The paths are only added to
``PATH`` if they exist. These paths are, in order:

- ``$CRAFT_PART_INSTALL/usr/sbin``
- ``$CRAFT_PART_INSTALL/usr/bin``
- ``$CRAFT_PART_INSTALL/sbin``
- ``$CRAFT_PART_INSTALL/bin``
- ``$CRAFT_STAGE/usr/sbin``
- ``$CRAFT_STAGE/usr/bin``
- ``$CRAFT_STAGE/sbin``
- ``$CRAFT_STAGE/bin``

``CPPFLAGS``, ``CFLAGS``, ``CXXFLAGS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each of these variables is set with a series of ``-isystem`` parameters
to add the following include paths to most C and C++ compilers, if they exist:

- ``$CRAFT_PART_INSTALL/include``
- ``$CRAFT_PART_INSTALL/usr/include``
- ``$CRAFT_PART_INSTALL/include/$CRAFT_ARCH_TRIPLET_BUILD_FOR``
- ``$CRAFT_PART_INSTALL/usr/include/$CRAFT_ARCH_TRIPLET_BUILD_FOR``
- ``$CRAFT_STAGE/include``
- ``$CRAFT_STAGE/usr/include``
- ``$CRAFT_STAGE/include/$CRAFT_ARCH_TRIPLET_BUILD_FOR``
- ``$CRAFT_STAGE/usr/include/$CRAFT_ARCH_TRIPLET_BUILD_FOR``

``LDFLAGS``
~~~~~~~~~~~

``LDFLAGS`` gets set with ``-L<directory>`` parameters for linkers to
include the following library paths when linking, if the paths exist:

- ``$CRAFT_PART_INSTALL/lib``
- ``$CRAFT_PART_INSTALL/usr/lib``
- ``$CRAFT_PART_INSTALL/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR``
- ``$CRAFT_PART_INSTALL/usr/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR``
- ``$CRAFT_STAGE/lib``
- ``$CRAFT_STAGE/usr/lib``
- ``$CRAFT_STAGE/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR``
- ``$CRAFT_STAGE/usr/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR``

``PKG_CONFIG_PATH``
~~~~~~~~~~~~~~~~~~~

``PKG_CONFIG_PATH`` is set so ``pkg-config`` will check the following extra paths,
if they exist:

- ``$CRAFT_PART_INSTALL/lib/pkgconfig``
- ``$CRAFT_PART_INSTALL/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR/pkgconfig``
- ``$CRAFT_PART_INSTALL/usr/lib/pkgconfig``
- ``$CRAFT_PART_INSTALL/usr/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR/pkgconfig``
- ``$CRAFT_PART_INSTALL/usr/share/pkgconfig``
- ``$CRAFT_PART_INSTALL/usr/local/lib/pkgconfig``
- ``$CRAFT_PART_INSTALL/usr/local/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR/pkgconfig``
- ``$CRAFT_PART_INSTALL/usr/local/share/pkgconfig``
- ``$CRAFT_STAGE/lib/pkgconfig``
- ``$CRAFT_STAGE/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR/pkgconfig``
- ``$CRAFT_STAGE/usr/lib/pkgconfig``
- ``$CRAFT_STAGE/usr/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR/pkgconfig``
- ``$CRAFT_STAGE/usr/share/pkgconfig``
- ``$CRAFT_STAGE/usr/local/lib/pkgconfig``
- ``$CRAFT_STAGE/usr/local/lib/$CRAFT_ARCH_TRIPLET_BUILD_FOR/pkgconfig``
- ``$CRAFT_STAGE/usr/local/share/pkgconfig``


.. _plugin-variables:

Plugin variables
----------------

A part's plugin can add its own set of environment variables or expand on
build-related flags.

The ``build-environment`` key can be used to either override the default
environment variables or define new ones. The following example overrides
default flags and searches for libraries in a non-standard path:

.. code-block:: yaml

    parts:
      hello-part:
        source: gnu-hello.tar.gz
        plugin: autotools
        build-environment:
          - CFLAGS: "$CFLAGS -O3"  # add -O3 to the existing flags
          - LDFLAGS: "-L$CRAFT_STAGE/non-standard/lib"

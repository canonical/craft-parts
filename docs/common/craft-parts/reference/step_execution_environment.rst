.. _craft_parts_step_execution_environment:

Step execution environment
--------------------------

Craft-parts defines the following environment for use during step
processing and execution of user-defined scriptlets:

- ``CRAFT_ARCH_TRIPLET``: The the machine-vendor-os platform triplet
  definition.
- ``CRAFT_TARGET_ARCH``: The architecture we're building for.
- ``CRAFT_PARALLEL_BUILD_COUNT``: The maximum number of concurrent build
  jobs to execute.
- ``CRAFT_PROJECT_DIR``: The path to the current project's subtree in
  the filesystem.
- ``CRAFT_PART_NAME``: The name of the part currently being processed.
- ``CRAFT_PART_SRC``: The path to the part source directory. This is
  where sources are located after the ``PULL`` step.
- ``CRAFT_PART_SRC_WORK``: The path to the part source subdirectory, if
  any. Defaults to the part source directory.
- ``CRAFT_PART_BUILD``: The path to the part build directory. This is
  where parts are built during the ``BUILD`` step.
- ``CRAFT_PART_BUILD_WORK``: The path to the part build subdirectory in
  case of out-of-tree builds. Defaults to the part source directory.
- ``CRAFT_PART_INSTALL``: The path to the part install directory.
  This is where built artefacts are installed after the ``BUILD`` step.
- ``CRAFT_OVERLAY``: The path to the part's layer directory during
  the ``OVERLAY`` step if overlays are enabled.
- ``CRAFT_STAGE``: The path to the project's staging directory. This
  is where installed artefacts are migrated after the ``STAGE`` step.
- ``CRAFT_PRIME``: The path to the final primed payload directory
  after the ``PRIME`` step.

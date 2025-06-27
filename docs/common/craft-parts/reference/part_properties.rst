.. _part_properties:

Part properties
===============

This reference describes the purpose and usage of all keys that can be declared for
a part, separated by the build step they influence.


Top-level keys
--------------

.. _part-properties-plugin:

.. kitbash-field:: parts.PartSpec plugin


.. _pull_step_keys:

Pull step keys
--------------

Pull step keys define the part's external dependencies and how they are retrieved
from the given location.

.. _part-properties-sources:

.. _source:

.. kitbash-field:: parts.PartSpec source

.. _source_type:

.. kitbash-field:: parts.PartSpec source_type

.. _source_checksum:

.. kitbash-field:: parts.PartSpec source_checksum

.. _source_branch:

.. kitbash-field:: parts.PartSpec source_branch

.. _source_tag:

.. kitbash-field:: parts.PartSpec source_tag

.. _source_commit:

.. kitbash-field:: parts.PartSpec source_commit

.. _source_depth:

.. kitbash-field:: parts.PartSpec source_depth

.. _source_submodules:

.. kitbash-field:: parts.PartSpec source_submodules

.. _source_subdir:

.. kitbash-field:: parts.PartSpec source_subdir

.. _override_pull:

.. kitbash-field:: parts.PartSpec override_pull


.. _overlay_step_keys:

Overlay step keys
-----------------

For craft applications that support filesystem overlays, the overlay step keys modify
the part's overlay layer and determine how its contents are represented in the stage
directory.


.. _overlay_files:

.. kitbash-field:: parts.PartSpec overlay_files

.. _overlay_packages:

.. kitbash-field:: parts.PartSpec overlay_packages

.. _overlay_script:

.. kitbash-field:: parts.PartSpec overlay_script


.. _build_step_keys:

Build step keys
---------------

Build step keys modify the behavior of the build step and the contents of the part's
build environment.

.. _after:

.. kitbash-field:: parts.PartSpec after

.. _disable_parallel:

.. kitbash-field:: parts.PartSpec disable_parallel

.. _build_environment:

.. kitbash-field:: parts.PartSpec build_environment

.. _build_packages:

.. kitbash-field:: parts.PartSpec build_packages

.. _build_snaps:

.. kitbash-field:: parts.PartSpec build_snaps

.. _override-build:

.. kitbash-field:: parts.PartSpec override_build

.. _organize:

.. kitbash-field:: parts.PartSpec organize_files


.. _stage_step_keys:

Stage step keys
---------------

Stage step keys modify the behavior of the stage step and determine how files from the
build directory are represented in the stage directory.

.. _stage:

.. kitbash-field:: parts.PartSpec stage_files
    :override-type: list[str]

.. _stage_packages:

.. kitbash-field:: parts.PartSpec stage_packages

.. _stage_snaps:

.. kitbash-field:: parts.PartSpec stage_snaps

.. _override_stage:

.. kitbash-field:: parts.PartSpec override_stage


.. _prime_step_keys:

Prime step keys
---------------

Prime step keys modify the behavior of the prime step and determine how the contents of
the stage directory are are reflected in the final payload.

.. _prime:

.. kitbash-field:: parts.PartSpec prime_files
    :override-type: list[str]

.. _override-prime:

.. kitbash-field:: parts.PartSpec override_prime


.. _permissions_keys:

Permissions keys
----------------

.. _permissions:

.. kitbash-field:: parts.PartSpec permissions

.. kitbash-field:: permissions.Permissions path

.. kitbash-field:: permissions.Permissions owner

.. kitbash-field:: permissions.Permissions group

.. kitbash-field:: permissions.Permissions mode

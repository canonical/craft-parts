.. _part_properties:

Part properties
===============

This reference describes the purpose and usage of all keys that can be declared for
a part.


Top-level keys
--------------

.. _reference-part-properties-plugin:

.. kitbash-field:: parts.PartSpec plugin


.. _reference-pull-step-keys:

Pull step keys
--------------

The following keys define the part's external dependencies and how they are retrieved
from the declared location.

.. _reference-part-properties-sources:

.. _reference-part-properties-source:

.. kitbash-field:: parts.PartSpec source

.. _reference-part-properties-source-type:

.. kitbash-field:: parts.PartSpec source_type

.. _reference-part-properties-source-checksum:

.. kitbash-field:: parts.PartSpec source_checksum

.. _reference-part-properties-source-branch:

.. kitbash-field:: parts.PartSpec source_branch

.. _reference-part-properties-source-tag:

.. kitbash-field:: parts.PartSpec source_tag

.. _reference-part-properties-source-commit:

.. kitbash-field:: parts.PartSpec source_commit

.. _reference-part-properties-source-depth:

.. kitbash-field:: parts.PartSpec source_depth

.. _reference-part-properties-source-submodules:

.. kitbash-field:: parts.PartSpec source_submodules

.. _reference-part-properties-source-subdir:

.. kitbash-field:: parts.PartSpec source_subdir

.. _reference-part-properties-override-pull:

.. kitbash-field:: parts.PartSpec override_pull


.. _reference-part-properties-overlay-step-keys:

Overlay step keys
-----------------

For craft applications that support filesystem overlays, the following keys modify the
part's overlay layer and determine how the layer's contents are represented in the stage
directory.

For more details on the overlay step, see :ref:`Overlay step <overlays>`.

.. _reference-part-properties-overlay-files:

.. kitbash-field:: parts.PartSpec overlay_files

.. _reference-part-properties-overlay-packages:

.. kitbash-field:: parts.PartSpec overlay_packages

.. _reference-part-properties-overlay-script:

.. kitbash-field:: parts.PartSpec overlay_script


.. _reference-part-properties-build-step-keys:

Build step keys
---------------

The following keys modify the build step's behavior and the contents of the part's
build environment.

.. _reference-part-properties-after:

.. kitbash-field:: parts.PartSpec after

.. _reference-part-properties-disable-parallel:

.. kitbash-field:: parts.PartSpec disable_parallel

.. _reference-part-properties-build-environment:

.. kitbash-field:: parts.PartSpec build_environment

.. _reference-part-properties-build-packages:

.. kitbash-field:: parts.PartSpec build_packages

.. _reference-part-properties-build-snaps:

.. kitbash-field:: parts.PartSpec build_snaps

.. _reference-part-properties-organize:

.. kitbash-field:: parts.PartSpec organize_files

.. _reference-part-properties-override-build:

.. kitbash-field:: parts.PartSpec override_build


.. _reference-part-properties-stage-step-keys:

Stage step keys
---------------

The following keys modify the stage step's behavior and determine how files from the
part's build directory are represented in the stage directory.

.. _reference-part-properties-stage:

.. kitbash-field:: parts.PartSpec stage_files
    :override-type: list[str]

.. _reference-part-properties-stage-packages:

.. kitbash-field:: parts.PartSpec stage_packages

.. _reference-part-properties-stage-snaps:

.. kitbash-field:: parts.PartSpec stage_snaps

.. _reference-part-properties-override-stage:

.. kitbash-field:: parts.PartSpec override_stage


.. _reference-part-properties-prime-step-keys:

Prime step keys
---------------

The following keys modify the prime step's behavior and determine how the contents
of the stage directory are reflected in the final payload.

.. _reference-part-properties-prime:

.. kitbash-field:: parts.PartSpec prime_files
    :override-type: list[str]

.. _reference-part-properties-override-prime:

.. kitbash-field:: parts.PartSpec override_prime


.. _reference-part-properties-permissions-keys:

Permissions keys
----------------

.. _reference-part-properties-permissions:

.. kitbash-field:: parts.PartSpec permissions

.. kitbash-field:: permissions.Permissions path

.. kitbash-field:: permissions.Permissions owner

.. kitbash-field:: permissions.Permissions group

.. kitbash-field:: permissions.Permissions mode

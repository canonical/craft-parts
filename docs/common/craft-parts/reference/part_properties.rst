.. _reference-part-properties:

Part properties
===============

This reference describes the purpose and usage of all keys that can be declared for
a part.


Top-level keys
--------------

.. py:currentmodule:: craft_parts.parts

.. kitbash-field:: PartSpec plugin
    :label: reference-part-properties-plugin


.. _reference-pull-step-keys:

Pull step keys
--------------

The following keys define the part's external dependencies and how they are retrieved
from the declared location.

.. kitbash-field:: PartSpec source
    :label: reference-part-properties-source

.. kitbash-field:: PartSpec source_type
    :label: reference-part-properties-source-type

.. kitbash-field:: PartSpec source_checksum
    :label: reference-part-properties-source-checksum

.. kitbash-field:: PartSpec source_branch
    :label: reference-part-properties-source-branch

.. kitbash-field:: PartSpec source_tag
    :label: reference-part-properties-source-tag

.. kitbash-field:: PartSpec source_commit
    :label: reference-part-properties-source-commit

.. kitbash-field:: PartSpec source_depth
    :label: reference-part-properties-source-depth

.. kitbash-field:: PartSpec source_submodules
    :label: reference-part-properties-source-submodules

.. kitbash-field:: PartSpec source_subdir
    :label: reference-part-properties-source-subdir

.. kitbash-field:: PartSpec override_pull
    :label: reference-part-properties-override-pull


.. _reference-part-properties-overlay-step-keys:

Overlay step keys
-----------------

For craft applications that support filesystem overlays, the following keys modify the
part's overlay layer and determine how the layer's contents are represented in the stage
directory.

.. kitbash-field:: PartSpec overlay_files
    :label: reference-part-properties-overlay

.. kitbash-field:: PartSpec overlay_packages
    :label: reference-part-properties-overlay-packages

.. kitbash-field:: PartSpec overlay_script
    :label: reference-part-properties-overlay-script


.. _reference-part-properties-build-step-keys:

Build step keys
---------------

The following keys modify the build step's behavior and the contents of the part's
build environment.

.. kitbash-field:: PartSpec after
    :label: reference-part-properties-after

.. kitbash-field:: PartSpec disable_parallel
    :label: reference-part-properties-disable-parallel

.. kitbash-field:: PartSpec build_attributes
    :label: reference-part-properties-build-attributes

.. kitbash-field:: PartSpec build_environment
    :label: reference-part-properties-build-environment

.. kitbash-field:: PartSpec build_packages
    :label: reference-part-properties-build-packages

.. kitbash-field:: PartSpec build_snaps
    :label: reference-part-properties-build-snaps

.. kitbash-field:: PartSpec organize_files
    :label: reference-part-properties-organize

.. kitbash-field:: PartSpec override_build
    :label: reference-part-properties-override-build


.. _reference-part-properties-stage-step-keys:

Stage step keys
---------------

The following keys modify the stage step's behavior and determine how files from the
part's build directory are represented in the stage directory.

.. kitbash-field:: PartSpec stage_files
    :override-type: list[str]
    :label: reference-part-properties-stage

.. kitbash-field:: PartSpec stage_packages
    :label: reference-part-properties-stage-packages

.. kitbash-field:: PartSpec stage_snaps
    :label: reference-part-properties-stage-snaps

.. kitbash-field:: PartSpec override_stage
    :label: reference-part-properties-override-stage


.. _reference-part-properties-prime-step-keys:

Prime step keys
---------------

The following keys modify the prime step's behavior and determine how the contents
of the stage directory are reflected in the final payload.

.. kitbash-field:: PartSpec prime_files
    :override-type: list[str]
    :label: reference-part-properties-prime

.. kitbash-field:: PartSpec override_prime
    :label: reference-part-properties-override-prime


.. _reference-part-properties-permissions-keys:

Permissions keys
----------------

.. kitbash-field:: PartSpec permissions
    :label: reference-part-properties-permissions

.. py:currentmodule:: craft_parts.permissions

.. kitbash-field:: Permissions path

.. kitbash-field:: Permissions owner

.. kitbash-field:: Permissions group

.. kitbash-field:: Permissions mode

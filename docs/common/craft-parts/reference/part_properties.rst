.. _reference-part-properties:

Part properties
===============

This reference describes the purpose and usage of all keys that can be declared for
a part.


Top-level keys
--------------

.. kitbash-field:: parts.PartSpec plugin
    :label: reference-part-properties-plugin


.. _reference-pull-step-keys:

Pull step keys
--------------

The following keys define the part's external dependencies and how they are retrieved
from the declared location.

.. kitbash-field:: parts.PartSpec source
    :label: reference-part-properties-source

.. kitbash-field:: parts.PartSpec source_type
    :label: reference-part-properties-source-type

.. kitbash-field:: parts.PartSpec source_checksum
    :label: reference-part-properties-source-checksum

.. kitbash-field:: parts.PartSpec source_branch
    :label: reference-part-properties-source-branch

.. kitbash-field:: parts.PartSpec source_tag
    :label: reference-part-properties-source-tag

.. kitbash-field:: parts.PartSpec source_commit
    :label: reference-part-properties-source-commit

.. kitbash-field:: parts.PartSpec source_depth
    :label: reference-part-properties-source-depth

.. kitbash-field:: parts.PartSpec source_submodules
    :label: reference-part-properties-source-submodules

.. kitbash-field:: parts.PartSpec source_subdir
    :label: reference-part-properties-source-subdir

.. kitbash-field:: parts.PartSpec override_pull
    :label: reference-part-properties-override-pull


.. _reference-part-properties-overlay-step-keys:

Overlay step keys
-----------------

For craft applications that support filesystem overlays, the following keys modify the
part's overlay layer and determine how the layer's contents are represented in the stage
directory.

.. kitbash-field:: parts.PartSpec overlay_files
    :label: reference-part-properties-overlay-files

.. kitbash-field:: parts.PartSpec overlay_packages
    :label: reference-part-properties-overlay-packages

.. kitbash-field:: parts.PartSpec overlay_script
    :label: reference-part-properties-overlay-script


.. _reference-part-properties-build-step-keys:

Build step keys
---------------

The following keys modify the build step's behavior and the contents of the part's
build environment.

.. kitbash-field:: parts.PartSpec after
    :label: reference-part-properties-after

.. kitbash-field:: parts.PartSpec disable_parallel
    :label: reference-part-properties-disable-parallel

.. kitbash-field:: parts.PartSpec build_environment
    :label: reference-part-properties-build-environment

.. kitbash-field:: parts.PartSpec build_packages
    :label: reference-part-properties-build-packages

.. kitbash-field:: parts.PartSpec build_snaps
    :label: reference-part-properties-build-snaps

.. kitbash-field:: parts.PartSpec organize_files
    :label: reference-part-properties-organize

.. kitbash-field:: parts.PartSpec override_build
    :label: reference-part-properties-override-build


.. _reference-part-properties-stage-step-keys:

Stage step keys
---------------

The following keys modify the stage step's behavior and determine how files from the
part's build directory are represented in the stage directory.

.. kitbash-field:: parts.PartSpec stage_files
    :override-type: list[str]
    :label: reference-part-properties-stage

.. kitbash-field:: parts.PartSpec stage_packages
    :label: reference-part-properties-stage-packages

.. kitbash-field:: parts.PartSpec stage_snaps
    :label: reference-part-properties-stage-snaps

.. kitbash-field:: parts.PartSpec override_stage
    :label: reference-part-properties-override-stage


.. _reference-part-properties-prime-step-keys:

Prime step keys
---------------

The following keys modify the prime step's behavior and determine how the contents
of the stage directory are reflected in the final payload.

.. kitbash-field:: parts.PartSpec prime_files
    :override-type: list[str]
    :label: reference-part-properties-prime

.. kitbash-field:: parts.PartSpec override_prime
    :label: reference-part-properties-override-prime


.. _reference-part-properties-permissions-keys:

Permissions keys
----------------

.. kitbash-field:: parts.PartSpec permissions
    :label: reference-part-properties-permissions

.. kitbash-field:: permissions.Permissions path

.. kitbash-field:: permissions.Permissions owner

.. kitbash-field:: permissions.Permissions group

.. kitbash-field:: permissions.Permissions mode

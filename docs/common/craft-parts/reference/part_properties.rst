.. Ideally, this would be automatically generated.

.. _part_properties:

Part properties
===============

.. _after:

after
-----
**Type:** list[string]

**Step:** build

Specifies a list of parts that a given part will be built *after*.
The array must contain at least one item.

.. ifconfig:: project in ("Snapcraft",)

   .. _build_attributes:

   build-attributes
   ----------------
   **Type:** array of unique strings with at least 1 item from "core22-step-dependencies", "enable-patchelf", "no-patchelf", "no-install", "debug", "keep-execstack".

   **Step:** build

   The customisations to apply to the build.

.. _build_environment:

build-environment
-----------------
**Type:** list[dict[string, string]]

**Step:** build

The environment variables to be defined in the build environment specified as
a list of key-value pairs.

**Example:**

.. code:: yaml

   build-environment:
     - MESSAGE: "Hello world"
     - NAME: "Craft Parts"

.. _build_packages:

build-packages
--------------
**Type:** list[string]

**Step:** build

The system packages to be installed in the build environment before the build
is performed. These are installed using the host's native package manager,
such as :command:`apt` or :command:`dnf`, and they provide libraries and
executables that the part needs during the build process.

.. _build_snaps:

build-snaps
-----------
**Type:** list[string]

**Step:** build

The snaps to be installed in the build environment before the build is
performed. These provide libraries and executables that the part needs during
the build process. They take the form of ``<snap>/<version>/<channel>``,
``<snap>/<channel>`` or just ``<snap>``. For example, the ``node`` snap could be
specified as ``node/18/stable``, ``node/latest/stable`` or ``node/stable`` to
select different versions.

.. _organize:

organize
--------
**Type:** dict[string, string]

**Step:** build

Describes how files in the building area should be represented in the staging
area.

In the following example, the ``hello.py`` file in the build area is copied
to the ``bin`` directory in the staging area and renamed to ``hello``:

.. code:: yaml

   organize:
     hello.py: bin/hello

If partitions are in use by the application, they may be referenced by prepending the partition name, surrounded by parentheses, to the destination path.  Only the destination path may specify a partition; source paths always reference the ``default`` partition.  Omitting the partition name in the destination path causes the file to be copied to the ``default`` partition.

The following example is exactly equivalent to the above example:

.. code:: yaml

   organize:
     hello.py: (default)/bin/hello

In this example, the file is instead copied to the application-defined ``boot`` partition:

.. code:: yaml

   organize:
     vmlinuz-6.2.0-39-generic: (boot)/vmlinuz

.. _override_build:

override-build
--------------
**Type:** string

**Step:** pull

A string containing commands to be run in a shell instead of performing those
defined by the plugin for the build step.

override-prime
--------------
**Type:** string

**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the prime step.

.. _override_pull:

override-pull
-------------
**Type:** string

**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the pull step.

.. Possibly mention the use of | at the start of the value and the type of
   shell and its options.

.. _override_stage:

override-stage
--------------
**Type:** string

**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the stage step.

parse-info
----------
**Type:** string

**Step:** all

.. _part-properties-plugin:

plugin
------
**Type:** string

**Step:** all steps

The plugin used to build the part. Available plugins include the following:

+-----------+-----------------------+
| **Name**  | **Note**              |
+===========+=======================+
| ant       | `Apache Ant`_         |
+-----------+-----------------------+
| autotools | `Autotools`_          |
+-----------+-----------------------+
| cmake     | `CMake`_              |
+-----------+-----------------------+
| dotnet    | `.NET`_               |
+-----------+-----------------------+
| dump      | Simple file unpacking |
+-----------+-----------------------+
| go        | `Go`_                 |
+-----------+-----------------------+
| make      | `Make`_               |
+-----------+-----------------------+
| maven     | `Apache Maven`_       |
+-----------+-----------------------+
| meson     | `Meson`_              |
+-----------+-----------------------+
| nil       | No default actions    |
+-----------+-----------------------+
| npm       | `NPM`_                |
+-----------+-----------------------+
| python    | `Python package`_     |
+-----------+-----------------------+
| rust      | Rust with `Cargo`_    |
+-----------+-----------------------+
| scons     | `SCons`_              |
+-----------+-----------------------+

.. _prime:

prime
-----
**Type:** list[string]

**Step:** prime

The files to copy from the staging area to the priming area,
see :ref:`filesets_specifying_paths`. The list must contain
at least one item.

.. _part-properties-sources:
.. _source:

source
------
**Type:** string

**Step:** pull

The location of the source code and data.

.. _source_branch:

source-branch
-------------
**Type:** string

**Step:** pull

The branch in the source repository to use when pulling the source code.

.. _source_checksum:

source-checksum
---------------
**Type:** string

**Step:** pull

For plugins that use files, this key contains a checksum value to be compared
against the checksum of the downloaded file.

.. _source_commit:

source-commit
-------------
**Type:** string

**Step:** pull

The commit to use to select a particular revision of the source code obtained
from a repository.

.. _source_depth:

source-depth
------------
**Type:** integer

**Step:** pull

The number of commits in a repository's history that should be fetched instead
of the complete history.

.. _source_subdir:

source-subdir
-------------
**Type:** string

**Step:** pull

The subdirectory in the unpacked sources where builds will occur.

.. note:: This key restricts the build to the subdirectory specified,
          preventing access to files in the parent directory and elsewhere in
          the file system directory structure.

.. _source_submodules:

source-submodules
-----------------
**Type:** list[string]

**Step:** pull

The submodules to fetch in the source repository.

.. _source_tag:

source-tag
----------
**Type:** string

**Step:** pull

The tag to use to select a particular revision of the source code obtained
from a repository.

.. _source_type:

source-type
-----------
**Type:** one of ``deb | file | git | local | rpm | snap | tar | zip``

**Step:** pull

The type of container for the source code. If not specified, Craft Parts will
attempt to auto-detect the source type. A list of supported formats can be
found in the :mod:`craft_parts.sources` file.

.. _stage:

stage
-----
**Type:** list[string]

**Step:** stage

The files to copy from the building area to the staging area,
see :ref:`filesets_specifying_paths`. The list must contain
at least one item.

.. _stage_packages:

stage-packages
--------------
**Type:** list[string]

**Step:** stage

The packages to install in the staging area for deployment with the build
products. These provide libraries and executables to support the deployed
part.

This keyword also support  supports
`Chisel <https://github.com/canonical/chisel>`_ slices.

To install a package slice instead of the whole package, simply follow the
Chisel convention *<packageName>_<sliceName>*.

NOTE: at the moment, it is not possible to mix packages and slices in the
same stage-packages field.

.. _stage_snaps:

stage-snaps
-----------
**Type:** list[string]

**Step:** stage

The snaps to install in the staging area for deployment with the build
products. These provide libraries and executables to support the deployed
part.

Summary of keys and steps
-------------------------

The following table shows the keys that are used in each build step.
The ``plugin`` and ``parse-info`` keys apply to all steps.

+-------------------+-------------------+-------------------+----------------+
| Pull              | Build             | Stage             | Prime          |
+===================+===================+===================+================+
| source            | after             | stage             | prime          |
+-------------------+-------------------+-------------------+----------------+
| source-checksum   | build-attributes  | stage-snaps       |                |
+-------------------+-------------------+-------------------+----------------+
| source-branch     | build-environment | stage-packages    |                |
+-------------------+-------------------+-------------------+----------------+
| source-commit     | build-packages    |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-depth      | build-snaps       |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-submodules | organize          |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-subdir     |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-tag        |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-type       |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| override-pull     | override-build    | override-stage    | override-prime |
+-------------------+-------------------+-------------------+----------------+

.. _`Apache Ant`: https://ant.apache.org/
.. _`Apache Maven`: https://maven.apache.org/
.. _`Autotools`: https://www.gnu.org/software/automake/
.. _`Cargo`: https://crates.io/
.. _`CMake`: https://cmake.org/
.. _`Go`: https://go.dev/
.. _`Make`: https://www.gnu.org/software/make/manual/make.html
.. _`Meson`: https://mesonbuild.com/
.. _`.NET`: https://github.com/dotnet/core
.. _`NPM`: https://www.npmjs.com/
.. _`Python package`: https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/
.. _`SCons`: https://scons.org/

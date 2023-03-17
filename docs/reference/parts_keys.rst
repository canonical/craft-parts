Part properties
===============

.. Ideally, this would be automatically generated.

after
-----
**Type:** array of unique strings with at least 1 item |br|
**Step:** build

Specifies a list of parts that a given part will be built *after*.

build-attributes
----------------
**Type:** array of unique strings with at least 1 item from "core22-step-dependencies", "enable-patchelf", "no-patchelf", "no-install", "debug", "keep-execstack". |br|
**Step:** build

The customisations to apply to the build.

build-environment
-----------------
**Type:** build-environment-grammar |br|
**Step:** build

The environment variables to be defined in the build environment specified as
a list of key-value pairs.

build-packages
--------------
**Type:** grammar-array |br|
**Step:** build

The system packages to be installed in the build environment before the build
is performed. These are installed using the host's native package manager,
such as :command:`apt` or :command:`dnf`, and they provide libraries and
executables that the part needs during the build process.

build-snaps
-----------
**Type:** grammar-array |br|
**Step:** build

The snaps to be installed in the build environment before the build is
performed. These provide libraries and executables that the part needs during
the build process.

disable-parallel
----------------
**Type:** boolean |br|
**Step:** build

By default, Craft Parts builds independent parts in parallel. This can be
disabled by setting the ``disable-parallel`` key to ``True``.

filesets
--------
**Type:** dictionary mapping strings to lists of strings |br|
**Step:** all

Defines named lists of paths to files and directories that can be referred to
by name in keys that accept lists of paths. See :doc:`Filesets`_ for more
information.

organize
--------
**Type:** ordered dictionary mapping strings to strings |br|
**Step:** stage

Describes how files in the building area should be represented in the staging
area.

override-build
--------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing those
defined by the plugin for the build step.

override-prime
--------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the prime step.

override-pull
-------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the pull step.

.. Possibly mention the use of | at the start of the value and the type of
   shell and its options.

override-stage
--------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the stage step.

parse-info
----------
**Type:** string |br|
**Step:** all

plugin
------
**Type:** string |br|
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
| dotnet    | `.Net`_               |
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


prime
-----
**Type:** array of unique strings with at least 1 item |br|
**Step:** prime

The files to copy from the staging area to the priming area.

source
------
**Type:** grammar-string |br|
**Step:** pull

The location of the source code and data.

source-branch
-------------
**Type:** string |br|
**Step:** pull

The branch in the source repository to use when pulling the source code.

source-checksum
---------------
**Type:** string |br|
**Step:** pull

For plugins that use files, this key contains a checksum value to be compared
against the checksum of the downloaded file.

source-commit
-------------
**Type:** string |br|
**Step:** pull

The commit to use to select a particular revision of the source code obtained
from a repository.

source-depth
------------
**Type:** integer |br|
**Step:** pull

The number of commits in a repository's history that should be fetched instead
of the complete history.

source-subdir
-------------
**Type:** string |br|
**Step:** pull

The subdirectory in the unpacked sources where builds will occur.

.. note:: This key restricts the build to the subdirectory specified,
          preventing access to files in the parent directory and elsewhere in
          the file system directory structure.

source-submodules
-----------------
**Type:** array of unique strings with 0 or more items |br|
**Step:** pull

The submodules to fetch in the source repository.

source-tag
----------
**Type:** string |br|
**Step:** pull

The tag to use to select a particular revision of the source code obtained
from a repository.

source-type
-----------
**Type:** one of "bzr", "git", "hg", "mercurial", "subversion", "svn", "tar", "zip", "deb", "rpm", "7z", "local" |br|
**Step:** pull

The type of container for the source code. If not specified, Craft Parts will
attempt to auto-detect the source type.

stage
-----
**Type:** array of unique strings with at least item |br|
**Step:** stage

The files to copy from the building area to the staging area.

stage-packages
--------------
**Type:** grammar-array |br|
**Step:** stage

The packages to install in the staging area for deployment with the build
products. These provide libraries and executables to support the deployed
part.

stage-snaps
-----------
**Type:** grammar-array |br|
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
| source-submodules | disable-parallel  |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-subdir     | filesets          |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-tag        | organize          |                   |                |
+-------------------+-------------------+-------------------+----------------+
| source-type       |                   |                   |                |
+-------------------+-------------------+-------------------+----------------+
| override-pull     | override-build    | override-stage    | override-prime |
+-------------------+-------------------+-------------------+----------------+

.. include:: /links.txt

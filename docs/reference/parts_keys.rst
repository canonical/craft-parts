Keys used by parts
==================

.. Ideally, this would be automatically generated.

plugin
------
**Type:** string |br|
**Step:** all steps

The plugin used to build the part.

source
------
**Type:** grammar-string |br|
**Step:** pull

The location of the source code and data.

source-checksum
---------------
**Type:** string |br|
**Step:** pull

For plugins that use files, this key contains a checksum value to be compared
against the checksum of the downloaded file.

source-branch
-------------
**Type:** string |br|
**Step:** pull

The branch in the source repository to use when pulling the source code.

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

source-submodules
-----------------
**Type:** array of unique strings with 0 or more items |br|
**Step:** pull

The submodules to fetch in the source repository.

source-subdir
-------------
**Type:** string |br|
**Step:** pull

The subdirectory in the unpacked sources
where builds will occur.

.. note:: This key restricts the build to the subdirectory specified,
          preventing access to files in the parent directory and elsewhere in
          the file system directory structure.

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

disable-parallel
----------------
**Type:** boolean |br|
**Step:** build

By default, Craft Parts builds independent parts in parallel. This can be
disabled by setting the ``disable-parallel`` key to ``True``.

after
-----
**Type:** array of unique strings with at least 1 item |br|
**Step:** build

stage-snaps
-----------
**Type:** grammar-array |br|
**Step:** stage


stage-packages
--------------
**Type:** grammar-array |br|
**Step:** stage


build-snaps
-----------
**Type:** grammar-array |br|
**Step:** build

The snaps to be installed in the build environment before the build is
performed.

build-packages
--------------
**Type:** grammar-array |br|
**Step:** build

The system packages to be installed in the build environment before the build
is performed. These are installed using the host's native package manager,
such as :command:`apt` or :command:`dnf`.

build-environment
-----------------
**Type:** build-environment-grammar |br|
**Step:** build

The environment variables to be defined in the build environment specified as
a list of key-value pairs.

build-attributes
----------------
**Type:** array of unique strings with at least 1 item from "core22-step-dependencies", "enable-patchelf", "no-patchelf", "no-install", "debug", "keep-execstack". |br|
**Step:** build

The customisations to apply to the build.

organize
--------

filesets
--------

stage
-----
**Type:** array of unique strings with at least item |br|
**Step:** stage

The files to copy from the building area to the staging area.

prime
-----
**Type:** array of unique strings with at least 1 item |br|
**Step:** prime

The files to copy from the staging area to the priming area.

override-pull
-------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the pull step.

.. Possibly mention the use of | at the start of the value and the type of
   shell and its options.

override-build
--------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing those
defined by the plugin for the build step.

override-stage
--------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the stage step.

override-prime
-------------
**Type:** string |br|
**Step:** pull

A string containing commands to be run in a shell instead of performing the
standard actions for the prime step.

parse-info
----------
**Type:** string |br|
**Step:** all

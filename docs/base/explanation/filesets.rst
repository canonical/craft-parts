.. _filesets_explanation:

Filesets
========

Filesets are named collections of files and directories that can be migrated
between steps in the process of :ref:`building a part <parts>`. They are used
within Craft Parts to collect and filter the files and directories a part
needs in its *stage* and *prime* processing :ref:`steps <lifecycle>`.

Tools that depend on Craft Parts can use filesets to simplify and automate
migration of files and directories between build steps. Users of those tools
may need to know about filesets if they need to adjust the contents of the
packages that the tools produce.

Fileset names
-------------

Internally, Craft Parts uses the ``overlay``, ``stage`` and ``prime`` filesets
to migrate files from all parts into the corresponding steps. For example,
the *stage* fileset refers to all the files and directories that will be moved
into the staging area ready for the *stage* step to be run.

Defining filesets
-----------------

Filesets are defined using the :py:class:`craft_parts.executor.Fileset` class
which is used to perform operations on lists of file paths. This accepts a
string containing the name of the fileset and a list of strings containing the
file paths.

Filesets are defined for individual parts. The scope of each fileset is the
part it is defined in. Filesets defined in one part cannot be used by another
part, and filesets cannot be shared between parts.

.. _filesets_specifying_paths:

Specifying paths
~~~~~~~~~~~~~~~~

The paths used in filesets specify locations *relative* to the working
directory where they will be used. Absolute paths cannot be used.

Paths can specify single files or directories, such as these examples:

* :file:`usr/bin/hello`
* :file:`usr/share`

They can also contain wildcards to select multiple files and directories, such
as these:

* :file:`usr/bin/*`
* :file:`usr/lib/**/*.so*`

The second of these examples selects all the shared libraries in all nested
directories inside the :file:`usr/lib` directory.

Filesets can also *exclude* files and directories. This is done by prefixing
a path with the ``-`` character, as in these examples:

* :file:`-usr/bin/hello`
* :file:`-usr/share/**/*.gz`

The second example selects and discards gzipped files in all nested directories
inside the :file:`usr/share` directory.

Using filesets
--------------

Built-in filesets for the *stage* and *prime* steps are both applied to the
directory containing the artefacts from the *build* step. These are used to
specify the files and directories to migrate to the *stage* and *prime* steps.

The contents of the filesets for these steps are specified using the
:ref:`stage` and :ref:`prime` properties when defining a part.

The order in which paths are defined in a fileset is not important. The paths
are collected so that all files and directories to be included are first
located, then paths that exclude files and directories are used to filter out
those that are not needed.

Summary
-------

When defined:

* Filesets specify named collections of files and directories using file
  paths that can contain wildcards. Only relative paths are allowed.
* They can both include and exclude sets of files and directories.
* They are defined for a given part, not for multiple parts.

When used:

* Filesets are used at the start of a step to collect and filter artefacts
  from an earlier step.
* Their file paths are applied to the directory containing the artefacts
  from the earlier step.
* All files and directories included by filesets are first located, then
  filtered by the filesets that exclude paths.

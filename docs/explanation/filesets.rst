.. _filesets_explanation:

Filesets
========

Filesets are named collections of files and directories that can be migrated
between areas in the process of :ref:`building a part <parts>`. They are used
within Craft Parts to collect and filter the files and directories a part
needs in the *stage* and *prime* :ref:`steps <lifecycle>`.

Tools that depend on Craft Parts can use filesets to simplify and automate
migration of files and directories between build steps. Users of those tools
may need to know about filesets if they need to adjust the contents of the
packages that the tools produce.

Specifying paths
----------------

The paths used in filesets specify locations *relative* to a starting
directory. Absolute paths cannot be used.

Paths can specify single files or directories, like these:

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

The second example selects and discards gzipped files in all nested directories inside the :file:`usr/share` directory.

Defining filesets
-----------------

Parts specify filesets using the :ref:`filesets` property. This defines a
dictionary that maps the name of each fileset to a list of file paths.

The following example shows a fileset called **binaries** that selects all the
files in a particular directory:

.. code:: yaml

   filesets:
     binaries: [usr/bin/*]

Filesets can be defined in any order.

Using filesets
--------------

Filesets can be used where file paths are expected. The list of paths for
each fileset is expanded when the name of the fileset is prefixed with the
``$`` character.

In the following example, the **binaries** fileset is expanded when it is
used in the :ref:`stage` property:

.. code:: yaml

    filesets:
      binaries: [usr/bin/*]
    stage:
      - $binaries

Filesets are applied to the directory containing the artifacts from the
previous step in the build process. In the above example, the products of the
build step that match the paths in the ``binaries`` fileset are placed in the
staging area.

The order in which filesets are used in a given step is not important. All
definitions are merged so that all files and directories to be included are
first located, then filesets that *exclude* paths are used to filter those
that are not needed.

The following example shows a part that unpacks the contents of the ``hello``
package ready for staging, but filters it so that the documentation directory
is removed:

.. code:: yaml

    parts:
      my-part:
        plugin: nil
        stage-packages: [hello]
        filesets:
          usr-files: [usr/*]
          exclude-docs: [-usr/share/doc]
        stage: [$usr-files, $exclude-docs]

If the order of the two filesets in the :ref:`stage` property is reversed,
the :file:`usr/share/doc` directory is still excluded.

Summary
-------

When defined:

* Filesets specify named collections of files and directories using file
  paths that can contain wildcards. Only relative paths are allowed.
* They can both include and exclude sets of files and directories.
* They are defined for a given part, not for multiple parts.

When used:

* Filesets are used at the start of a step to collect and filter artifacts
  from the previous step.
* Their file paths are applied to the directory containing the artifacts
  from the previous step.
* All files and directories included by filesets are first located, then
  filtered by the filesets that *exclude* paths.
